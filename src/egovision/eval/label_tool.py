"""S1 · owner: Shefali. `python -m egovision.eval.label_tool --clip X --labeller name --n 40`
Writes eval/labels/<clip>__<labeller>.json (coordinates only). Frame images stay in eval/frames/ (git-ignored).

How to label: run the command above (add `--shared` for the common 30-frame set). A window opens on the
first frame. For each visible hand, click the wrist first, then the 5 fingertips (thumb, index, middle,
ring, little; a hidden tip goes where you think it is), then press `l` or `r` for its side. A second hand
starts with the next click. Press Enter (or `n`) to save the frame and go on; a frame with no clicks is
saved as "no hands", which is a valid label. `x` skips an unusable frame, `u` undoes the last click, `t` then a
digit toggles a tag (1 blur, 2 glove, 3 dark, 4 overlap, 5 reentry), `q` saves and quits. Every frame is
written to disk at once, so quitting and running the same command again resumes where you stopped.
"""
from __future__ import annotations

import argparse
import json
import random
import zlib
from dataclasses import dataclass, field
from pathlib import Path

from .. import config
from ..schema import QUALITY_COLS, SIDES, ClipPaths, read_csv, read_hands, read_meta

FRAMES_DIR = config.ROOT / "eval" / "frames"
SHARED_DIR = config.EVAL_LABELS / "shared"       # frame lists only, so --shared picks match on every laptop
TAGS = ("blur", "glove", "dark", "overlap", "reentry")
N_POINTS = 6                                      # wrist + 5 tips
BOX_PAD = 0.15                                    # box = min/max of points, grown by 15 % of its size per side
HARD_SHARE = 0.6
SHARED_N = 30
SHARED_SEED = 1702
MAX_HANDS = 2
WINDOW = "label_tool"
DEBUG = False                                     # --debug: print every key and click to the terminal
FIT = (1200, 660)                                 # max frame size on screen (MacBook Air), header bar above it
BAR = 94                                          # header bar height in px
POINT_NAMES = ("wrist", "thumb tip", "index tip", "middle tip", "ring tip", "little tip")


# ---------- frame picking ----------
def hard_frames(clip: str, n_frames: int, fps: float, step: int) -> list[int]:
    """Frames the baseline likely got wrong: no hands, a flagged hand, or a dark/red quality second."""
    p = ClipPaths(clip)
    hard: set[int] = set()
    if p.hands_baseline.exists():
        for fr in read_hands(p.hands_baseline):
            if not fr.hands or any(h.flags for h in fr.hands):
                hard.add(fr.frame)
    if p.quality.exists():
        for row in read_csv(p.quality, QUALITY_COLS):
            if row["light"] == "red" or "dark" in row["reasons"]:
                a, b = int(float(row["t_start"]) * fps), int(float(row["t_end"]) * fps)
                hard.update(range(a, min(b, n_frames)))
    return sorted(f - f % step for f in hard if f < n_frames)


def pick_frames(n: int, n_frames: int, hard: list[int], seed: int, step: int = 1,
                min_gap: int = 0) -> list[int]:
    """`n` distinct frames, multiples of `step` (so the baseline has a prediction there):
    60 % from `hard` (fewer if there are not enough), the rest random. Picks keep `min_gap` frames apart
    when the clip is long enough. Same inputs and seed give the same list."""
    rng = random.Random(seed)
    candidates = list(range(0, n_frames, step))
    n = min(n, len(candidates))
    hard = sorted({f for f in hard if f % step == 0 and 0 <= f < n_frames})
    rng.shuffle(hard)
    rng.shuffle(candidates)
    out: list[int] = []

    def take(pool: list[int], k: int, gap: int) -> None:
        for f in pool:
            if len(out) >= k:
                return
            if f not in out and all(abs(f - o) >= gap for o in out):
                out.append(f)

    n_hard = round(n * HARD_SHARE)
    for gap in (min_gap, 0):                      # relax the gap only if the clip is too short for it
        take(hard, min(n_hard, len(hard)), gap)
        take(candidates, n, gap)
    return sorted(out)


def seed_for(clip: str, labeller: str) -> int:
    return zlib.crc32(f"{clip}:{labeller}".encode())


def labelling_order(n: int, n_frames: int, hard: list[int], seed: int, step: int, min_gap: int) -> list[int]:
    """The `n` picked frames in random order (so a stop half way still has the 60/40 mix), then as many
    backups, which replace skipped frames."""
    first = pick_frames(n, n_frames, hard, seed, step, min_gap)
    backups = [f for f in pick_frames(2 * n, n_frames, hard, seed + 1, step, min_gap) if f not in first]
    random.Random(seed).shuffle(first)
    return first + backups


def shared_frames(clip: str, n_frames: int, fps: float, step: int) -> list[int]:
    """The common frame list: read from eval/labels/shared/<clip>.json, or picked with a fixed seed and saved."""
    path = SHARED_DIR / f"{clip}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["frames"]
    frames = pick_frames(SHARED_N, n_frames, hard_frames(clip, n_frames, fps, step), SHARED_SEED,
                         step, min_gap=int(fps))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"clip": clip, "frames": frames}) + "\n", encoding="utf-8")
    return frames


# ---------- label model ----------
def box_from_points(points: list[list[float]], width: int, height: int) -> list[float]:
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
    px, py = (x2 - x1) * BOX_PAD, (y2 - y1) * BOX_PAD
    return [round(max(0.0, x1 - px), 1), round(max(0.0, y1 - py), 1),
            round(min(width - 1.0, x2 + px), 1), round(min(height - 1.0, y2 + py), 1)]


@dataclass
class HandDraft:
    points: list[list[float]] = field(default_factory=list)
    side: str | None = None

    @property
    def complete(self) -> bool:
        return len(self.points) == N_POINTS and self.side in SIDES


@dataclass
class FrameDraft:
    frame: int
    hands: list[HandDraft] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def click(self, x: float, y: float) -> bool:
        if not self.hands or len(self.hands[-1].points) == N_POINTS:
            if len(self.hands) == MAX_HANDS:
                return False
            self.hands.append(HandDraft())
        self.hands[-1].points.append([round(x, 1), round(y, 1)])
        return True

    def set_side(self, side: str) -> None:
        if self.hands:
            self.hands[-1].side = side

    def undo(self) -> None:
        if not self.hands:
            return
        self.hands[-1].points.pop()
        if not self.hands[-1].points:
            self.hands.pop()

    def toggle_tag(self, tag: str) -> None:
        if tag in self.tags:
            self.tags.remove(tag)
        else:
            self.tags.append(tag)

    def problem(self) -> str | None:
        """Why this frame cannot be saved yet, or None."""
        for i, h in enumerate(self.hands):
            if len(h.points) < N_POINTS:
                return f"hand {i + 1}: {N_POINTS - len(h.points)} clicks missing"
            if h.side not in SIDES:
                return f"hand {i + 1}: press l or r"
        sides = [h.side for h in self.hands]
        if len(set(sides)) < len(sides):
            return "both hands have the same side"
        return None

    def to_label(self, width: int, height: int) -> dict:
        assert self.problem() is None, self.problem()
        return {"frame": self.frame, "tags": [t for t in TAGS if t in self.tags],
                "hands": [{"side": h.side, "bbox": box_from_points(h.points, width, height),
                           "wrist": h.points[0], "tips": h.points[1:]} for h in self.hands]}


# ---------- label file ----------
def labels_path(clip: str, labeller: str) -> Path:
    return config.EVAL_LABELS / f"{clip}__{labeller}.json"


def load_labels(path: Path, clip: str, labeller: str) -> dict:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["clip"] == clip and data["labeller"] == labeller, path
        return data
    return {"clip": clip, "labeller": labeller, "frames": []}


def save_labels(path: Path, data: dict, label: dict) -> None:
    """Add or replace one frame's label and rewrite the file (sorted by frame), so a crash loses nothing."""
    validate_label(label)
    data["frames"] = sorted([f for f in data["frames"] if f["frame"] != label["frame"]] + [label],
                            key=lambda f: f["frame"])
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def validate_label(label: dict) -> None:
    assert set(label) == {"frame", "tags", "hands"}, sorted(label)
    assert all(t in TAGS for t in label["tags"]), label["tags"]
    for h in label["hands"]:
        assert h["side"] in SIDES and len(h["bbox"]) == 4 and len(h["wrist"]) == 2, h
        assert len(h["tips"]) == 5 and all(len(t) == 2 for t in h["tips"]), h


# ---------- video ----------
def clip_info(clip: str) -> tuple[int, int, int, float, int]:
    """(width, height, n_frames, fps, step), from meta.json when it exists, else from the video."""
    import cv2
    p = ClipPaths(clip)
    if p.meta.exists():
        m = read_meta(p.meta)
        return m["width"], m["height"], m["n_frames"], m["fps"], m.get("step", config.FRAME_STEP)
    cap = cv2.VideoCapture(str(p.video))
    if not cap.isOpened():
        raise SystemExit(f"video not found: {p.video} (real clips go in {config.CLIPS_DIR})")
    info = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), cap.get(cv2.CAP_PROP_FPS) or 30.0, config.FRAME_STEP)
    cap.release()
    return info


def frame_image(clip: str, frame: int):
    """Frame from eval/frames/<clip>/ if cached, else read from the video and cached there."""
    import cv2
    path = FRAMES_DIR / clip / f"{frame:06d}.jpg"
    if path.exists():
        return cv2.imread(str(path))
    cap = cv2.VideoCapture(str(ClipPaths(clip).video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
    ok, img = cap.read()
    cap.release()
    if not ok:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return img


# ---------- UI ----------
COLOURS = {"left": (60, 160, 255), "right": (255, 140, 40), None: (200, 200, 200)}   # BGR


def draw(img, d: FrameDraft, scale: float, header: str, message: str):
    import cv2
    frame = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    out = cv2.copyMakeBorder(frame, BAR, 0, 0, 0, cv2.BORDER_CONSTANT, value=(25, 25, 25))
    for h in d.hands:
        col = COLOURS[h.side]
        pts = [(int(x * scale), int(y * scale) + BAR) for x, y in h.points]
        for p in pts[1:]:
            cv2.line(out, pts[0], p, col, 1, cv2.LINE_AA)
        for k, p in enumerate(pts):
            cv2.circle(out, p, 5 if k == 0 else 3, col, -1, cv2.LINE_AA)
        if pts:
            cv2.putText(out, (h.side or "?")[0].upper(), (pts[0][0] + 8, pts[0][1] + 16),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2, cv2.LINE_AA)
    k = len(d.hands[-1].points) % N_POINTS if d.hands else 0
    need = POINT_NAMES[k] + (" of a new hand" if k == 0 and d.hands else "")
    lines = [header, f"next click: {need} | tags: {', '.join(d.tags) or '-'}",
             "ENTER save + next   x skip   u undo   l/r side   t+1..5 tag   q quit", message]
    for i, text in enumerate(lines):
        cv2.putText(out, text, (8, 20 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (80, 200, 255) if i == 3 else (235, 235, 235), 1, cv2.LINE_AA)
    return out


def label_frame(img, d: FrameDraft, scale: float, header: str) -> str:
    """Run the window for one frame. Returns 'next', 'skip' or 'quit'."""
    import cv2
    state = {"msg": "", "tag_mode": False}

    def on_mouse(event, x, y, _flags, _param):
        if event == cv2.EVENT_LBUTTONDOWN and DEBUG:
            print(f"click at window ({x}, {y})")
        if event == cv2.EVENT_LBUTTONDOWN and y >= BAR:
            state["msg"] = "" if d.click(x / scale, (y - BAR) / scale) else f"max {MAX_HANDS} hands"

    cv2.setMouseCallback(WINDOW, on_mouse)
    while True:
        if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:   # window closed with the mouse
            print("window was closed: stopping")
            return "quit"
        msg = "tag: 1 blur  2 glove  3 dark  4 overlap  5 reentry" if state["tag_mode"] else state["msg"]
        cv2.imshow(WINDOW, draw(img, d, scale, header, msg))
        key = cv2.waitKey(30) & 0xFF
        if key == 255:
            continue
        ch = chr(key).lower()
        if DEBUG:
            print(f"key {key} {ch!r}")
        if state["tag_mode"]:
            state["tag_mode"] = False
            if ch in "12345":
                d.toggle_tag(TAGS[int(ch) - 1])
        elif ch in "lr":
            d.set_side("left" if ch == "l" else "right")
        elif ch == "u":
            d.undo()
        elif ch == "t":
            state["tag_mode"] = True
        elif ch == "x":
            return "skip"
        elif ch in ("q", "\x1b"):
            print("q pressed: stopping")
            return "quit"
        elif ch in ("n", "\r", "\n", " "):
            state["msg"] = d.problem() or ""
            if not state["msg"]:
                return "next"


def run(clip: str, labeller: str, n: int, shared: bool, scale: float | None) -> Path:
    import cv2
    labeller = labeller.strip().lower()
    width, height, n_frames, fps, step = clip_info(clip)
    if shared:
        todo = shared_frames(clip, n_frames, fps, step)
    else:
        todo = labelling_order(n, n_frames, hard_frames(clip, n_frames, fps, step),
                               seed_for(clip, labeller), step, int(fps))
    out = labels_path(clip, labeller)
    data = load_labels(out, clip, labeller)
    skip_file = FRAMES_DIR / clip / f"skipped__{labeller}.txt"
    skipped = set(map(int, skip_file.read_text().split())) if skip_file.exists() else set()
    done = {f["frame"] for f in data["frames"]}
    goal = len(todo) if shared else n
    scale = scale or min(2.0, FIT[0] / width, FIT[1] / height)
    cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
    try:
        for frame in todo:
            if len(done) >= goal:
                break
            if frame in done or frame in skipped:
                continue
            img = frame_image(clip, frame)
            if img is None:
                continue
            d = FrameDraft(frame)
            header = f"{clip}  frame {frame} ({frame / fps:.1f} s)  labelled {len(done)}/{goal}"
            action = label_frame(img, d, scale, header)
            if action == "quit":
                break
            if action == "skip":
                skipped.add(frame)
                skip_file.parent.mkdir(parents=True, exist_ok=True)
                skip_file.write_text(" ".join(map(str, sorted(skipped))) + "\n")
                print(f"skipped frame {frame}")
                continue
            save_labels(out, data, d.to_label(width, height))
            done.add(frame)
            print(f"saved frame {frame}: {len(d.hands)} hand(s), tags {d.tags or '-'}  ({len(done)}/{goal})")
    finally:
        cv2.destroyAllWindows()
        cv2.waitKey(1)
    print(f"{len(done)}/{goal} frames labelled → {out}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m egovision.eval.label_tool", description=__doc__.split("\n")[0])
    ap.add_argument("--clip", required=True)
    ap.add_argument("--labeller", required=True, help="your first name, lowercase")
    ap.add_argument("--n", type=int, default=40, help="frames to label (ignored with --shared)")
    ap.add_argument("--shared", action="store_true", help=f"the common {SHARED_N}-frame set (same frames for everyone)")
    ap.add_argument("--debug", action="store_true", help="print every key and click")
    ap.add_argument("--scale", type=float, default=None, help="window zoom (default: fit the frame in 1200x660)")
    a = ap.parse_args(argv)
    global DEBUG
    DEBUG = a.debug
    run(a.clip, a.labeller, a.n, a.shared, a.scale)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
