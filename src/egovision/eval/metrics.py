"""A5 · owner: Abhijay. `python -m egovision.eval.metrics --clip X` (or `--all`) → outputs/<clip>/metrics.json
Compares hands_baseline.jsonl and hands.jsonl against eval/labels/; accuracy per light colour from quality.csv.
Format: docs/05-solution/data-schema.md 1.3 (`baseline` and `ours` hold the numbers and breakdowns); `history`
keeps earlier runs for before/after. `--fps` times MediaPipe; `hands` FPS comes from outputs/<clip>/hands_stats.json.
Pooled numbers over all labelled clips: outputs/metrics_summary.json.
"""
from __future__ import annotations

import argparse
import json
import math
import platform
import time
from collections import defaultdict
from datetime import datetime
from itertools import islice
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

from egovision import config
from egovision.schema import QUALITY_COLS, SIDES, TIPS, ClipPaths, FrameHands, Hand, read_csv, read_hands, read_meta

LINK_SIZES = 1.0     # a hand continues a chain if its wrist moved less than this many hand sizes
STILL_WINDOW = 5     # chain steps either side when deciding a hand is still
STILL_SIZES = 0.25   # net wrist motion across the window, in hand sizes
KP = (0, *TIPS)      # wrist + 5 tips, the labelled points
PCK_THRESHOLD = 0.2  # share of the box size
MATCH_MAX = 0.5      # a prediction counts as this hand if its mean point error is under this share of the box size
FULL_LABELS = 160    # fewer labelled frames than this across the team → "partial": true
FPS_FRAMES = 300
TAGS = ("blur", "glove", "dark", "overlap", "reentry")


def _size(h: Hand) -> float:
    return max(h.bbox[2] - h.bbox[0], h.bbox[3] - h.bbox[1], 1.0)


def chains(frames: list[FrameHands], step: int) -> list[list[Hand]]:
    """Links hands across consecutive sampled frames by nearest wrist alone. Ignores ids and sides, so
    the raw baseline and the final file are measured by the same rule."""
    done: list[list[Hand]] = []
    live: list[list[Hand]] = []
    last_frame = None
    for fr in frames:
        if fr.frame % step:
            continue
        if last_frame is not None and fr.frame - last_frame > step:
            done += live
            live = []
        pairs = sorted(((math.dist(c[-1].kp2d[0], h.kp2d[0]), ci, hi) for ci, c in enumerate(live)
                        for hi, h in enumerate(fr.hands)), key=lambda p: p[0])
        used_c, used_h = set(), set()
        for d, ci, hi in pairs:
            if ci in used_c or hi in used_h or d > LINK_SIZES * _size(live[ci][-1]):
                continue
            used_c.add(ci)
            used_h.add(hi)
            live[ci].append(fr.hands[hi])
        done += [c for ci, c in enumerate(live) if ci not in used_c]
        live = [c for ci, c in enumerate(live) if ci in used_c]
        live += [[h] for hi, h in enumerate(fr.hands) if hi not in used_h]
        last_frame = fr.frame
    return done + live


def swaps_per_min(frames: list[FrameHands], step: int, minutes: float) -> float:
    """Side label changes along a continuously visible hand."""
    n = sum(a.side != b.side for c in chains(frames, step) for a, b in zip(c, c[1:]))
    return n / max(minutes, 1e-6)


def pair_order(frames: list[FrameHands], step: int) -> dict[str, int]:
    """Two-hand frames by label: left hand on the image left (right_order), on the image right
    (wrong_order, unless the arms really cross), or both hands given one side (same_side)."""
    out = {"right_order": 0, "wrong_order": 0, "same_side": 0}
    for fr in frames:
        if fr.frame % step or len(fr.hands) != 2:
            continue
        a, b = fr.hands
        if a.side == b.side:
            out["same_side"] += 1
        else:
            left, right = (a, b) if a.side == "left" else (b, a)
            out["right_order" if left.kp2d[0][0] < right.kp2d[0][0] else "wrong_order"] += 1
    return out


def jitter(frames: list[FrameHands], step: int) -> float:
    """Mean frame-to-frame wrist motion in pixels while the hand is still."""
    moves = []
    for c in chains(frames, step):
        for i in range(STILL_WINDOW, len(c) - STILL_WINDOW):
            net = math.dist(c[i - STILL_WINDOW].kp2d[0], c[i + STILL_WINDOW].kp2d[0])
            if net < STILL_SIZES * _size(c[i]):
                moves.append(math.dist(c[i - 1].kp2d[0], c[i].kp2d[0]))
    return sum(moves) / len(moves) if moves else 0.0


# ---------- labels against predictions ----------
def label_points(h: dict) -> np.ndarray:
    return np.array([h["wrist"], *h["tips"]], dtype=float)


def label_size(h: dict) -> float:
    b = h["bbox"]
    return max(b[2] - b[0], b[3] - b[1], 1.0)


def match(label_hands: list[dict], pred: list[Hand]) -> list[tuple[int, int, np.ndarray]]:
    """Pairs labels with predictions by point error alone, not side, so a right hand called left is a
    side error and not a miss. Returns (label index, pred index, per-point error / box size)."""
    if not label_hands or not pred:
        return []
    errs = [[np.linalg.norm(label_points(lh) - np.asarray(p.kp2d, dtype=float)[list(KP)], axis=1) / label_size(lh)
             for p in pred] for lh in label_hands]
    cost = np.array([[e.mean() for e in row] for row in errs])
    return [(int(i), int(j), errs[i][j]) for i, j in zip(*linear_sum_assignment(cost)) if cost[i, j] <= MATCH_MAX]


class Tally:
    """Counts for one group of labelled hands; `result` turns them into the reported rates."""

    def __init__(self):
        self.labels = self.preds = self.matched = self.side_ok = self.pts = self.pts_ok = 0
        self.frames = 0
        self.wrist_err: list[float] = []

    def add(self, label_hands: list[dict], pred: list[Hand], count_preds: bool = True) -> None:
        self.frames += 1
        self.labels += len(label_hands)
        if count_preds:
            self.preds += len(pred)
        for i, j, err in match(label_hands, pred):
            self.matched += 1
            self.side_ok += label_hands[i]["side"] == pred[j].side
            self.pts += len(err)
            self.pts_ok += int((err <= PCK_THRESHOLD).sum())
            self.wrist_err.append(float(err[0]))

    def result(self) -> dict:
        def rate(a, b):
            return round(a / b, 4) if b else None
        return {"frames": self.frames, "labels": self.labels,
                "detection_recall": rate(self.matched, self.labels),
                "detection_precision": rate(self.matched, self.preds),
                "lr_accuracy": rate(self.side_ok, self.matched),
                "pck_0.2": rate(self.pts_ok, self.pts),
                "pck_0.2_with_misses": rate(self.pts_ok, self.labels * len(KP)),
                "wrist_error_box": round(float(np.median(self.wrist_err)), 4) if self.wrist_err else None}


def load_labels(clip: str) -> dict[str, dict[int, dict]]:
    """labeller → frame → label, for every label file of this clip."""
    out: dict[str, dict[int, dict]] = {}
    for path in sorted(config.EVAL_LABELS.glob(f"{clip}__*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        out[data["labeller"]] = {f["frame"]: f for f in data["frames"]}
    return out


def merged_labels(by_labeller: dict[str, dict[int, dict]]) -> dict[int, dict]:
    """One label per frame. A frame with several labellers uses the first name; agreement is reported apart."""
    out: dict[int, dict] = {}
    for name in sorted(by_labeller):
        for frame, label in by_labeller[name].items():
            out.setdefault(frame, label)
    return out


def shared_list(clip: str) -> set[int]:
    path = config.EVAL_LABELS / "shared" / f"{clip}.json"
    return set(json.loads(path.read_text(encoding="utf-8"))["frames"]) if path.exists() else set()


def light_by_second(clip: str) -> list[tuple[float, float, str]]:
    p = ClipPaths(clip)
    if not p.quality.exists():
        return []
    return [(float(r["t_start"]), float(r["t_end"]), r["light"]) for r in read_csv(p.quality, QUALITY_COLS)]


def light_at(lights: list[tuple[float, float, str]], t: float) -> str | None:
    return next((c for a, b, c in lights if a <= t < b), None)


def score_file(rows: dict[int, FrameHands], labels: dict[int, dict], shared: set[int],
               lights: list[tuple[float, float, str]], fps: float) -> tuple[dict, dict[str, Tally]]:
    """Every group is a Tally. Manual vs prefilled splits by the labelled hand, so a frame's two hands can
    fall in different groups; only `all` counts predictions, and the manual/prefilled splits don't use precision."""
    groups: dict[str, Tally] = defaultdict(Tally)
    for frame, label in sorted(labels.items()):
        pred = rows[frame].hands if frame in rows else []
        hands = label["hands"]
        groups["all"].add(hands, pred)
        for tag in label.get("tags", []):
            groups[f"tag:{tag}"].add(hands, pred)
        light = light_at(lights, frame / fps)
        if light:
            groups[f"light:{light}"].add(hands, pred)
        for side in SIDES:
            which = [h for h in hands if h["side"] == side]
            if which:
                groups[f"side:{side}"].add(which, pred, count_preds=False)
        manual = [h for h in hands if not h.get("prefill")]
        filled = [h for h in hands if h.get("prefill")]
        if frame in shared and manual:
            groups["shared_manual"].add(manual, pred, count_preds=False)
        if filled:
            groups["prefilled"].add(filled, pred, count_preds=False)
    out = groups["all"].result()
    out["by_tag"] = {k[4:]: g.result() for k, g in groups.items() if k.startswith("tag:")}
    out["by_light"] = {k[6:]: g.result() for k, g in groups.items() if k.startswith("light:")}
    out["by_side"] = {k[5:]: g.result() for k, g in groups.items() if k.startswith("side:")}
    out["pck_shared_manual"] = groups["shared_manual"].result()["pck_0.2"] if "shared_manual" in groups else None
    out["pck_prefilled"] = groups["prefilled"].result()["pck_0.2"] if "prefilled" in groups else None
    return out, groups


def prefilled_share(labels: dict[int, dict]) -> float | None:
    hands = [h for f in labels.values() for h in f["hands"]]
    return round(sum(bool(h.get("prefill")) for h in hands) / len(hands), 4) if hands else None


def agreement(by_labeller: dict[str, dict[int, dict]]) -> dict | None:
    """Labellers against each other on frames they both labelled: how good a perfect tracker could look."""
    names = sorted(by_labeller)
    frames = n_pts = pts_ok = same_count = same_side = pairs = 0
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for f in by_labeller[a].keys() & by_labeller[b].keys():
                ha, hb = by_labeller[a][f]["hands"], by_labeller[b][f]["hands"]
                frames += 1
                same_count += len(ha) == len(hb)
                if not ha or not hb:
                    continue
                errs = [[np.linalg.norm(label_points(x) - label_points(y), axis=1) / label_size(x) for y in hb] for x in ha]
                cost = np.array([[e.mean() for e in row] for row in errs])
                for r, c in zip(*linear_sum_assignment(cost)):
                    pairs += 1
                    same_side += ha[r]["side"] == hb[c]["side"]
                    n_pts += len(errs[r][c])
                    pts_ok += int((errs[r][c] <= PCK_THRESHOLD).sum())
    if not frames:
        return None
    return {"frames": frames, "pck_0.2": round(pts_ok / n_pts, 4) if n_pts else None,
            "same_hand_count": round(same_count / frames, 4), "same_side": round(same_side / pairs, 4) if pairs else None}


def total_labelled_frames() -> int:
    total = 0
    for path in config.EVAL_LABELS.glob("*__*.json"):
        total += len(json.loads(path.read_text(encoding="utf-8"))["frames"])
    return total


def worst_moments(rows: dict[int, FrameHands], labels: dict[int, dict], fps: float, k: int = 5) -> list[dict]:
    """Labelled frames with the most missed hands, wrong sides and bad points, for finding the biggest failure."""
    scored = []
    for frame, label in labels.items():
        pred = rows[frame].hands if frame in rows else []
        pairs = match(label["hands"], pred)
        found = {i for i, _, _ in pairs}
        missed = [h["side"] for i, h in enumerate(label["hands"]) if i not in found]
        extra = len(pred) - len(pairs)
        wrong_side = [label["hands"][i]["side"] for i, j, _ in pairs if label["hands"][i]["side"] != pred[j].side]
        bad = sum(int((e > PCK_THRESHOLD).sum()) for _, _, e in pairs)
        score = 8 * len(missed) + 8 * len(wrong_side) + 4 * extra + bad
        if score:
            scored.append({"frame": frame, "t": round(frame / fps, 2), "missed": missed, "extra": extra,
                           "wrong_side": wrong_side, "bad_points": bad, "tags": label.get("tags", []), "score": score})
    return sorted(scored, key=lambda s: -s["score"])[:k]


def failures(moments: list[dict]) -> list[dict]:
    """Worst moments in the Metrics page's words. `why` only states what was measured or tagged."""
    out = []
    for w in moments:
        parts = [f"{s} hand missing" for s in w["missed"]] + [f"{s} hand called the other side" for s in w["wrong_side"]]
        if w["extra"]:
            parts.append("hand found where none is labelled")
        if w["bad_points"]:
            parts.append(f"{w['bad_points']} points off")
        out.append({"t": w["t"], "what": "; ".join(parts),
                    "why": f"labelled {', '.join(w['tags'])}" if w["tags"] else "no tag on this frame"})
    return out


def measure_fps(clip: str, n: int = FPS_FRAMES) -> float:
    """MediaPipe alone on one clip's first sampled frames. Run with nothing else busy to get a fair number."""
    from egovision.hands.baseline import _detect
    t0 = time.time()
    done = sum(1 for _ in islice(_detect(clip), n))
    return round(done / max(time.time() - t0, 1e-6), 1)


def hardware() -> str:
    return f"{platform.processor() or platform.machine()}, {platform.system()}, CPU only"


# ---------- one clip ----------
def _clean(d: dict) -> dict:
    """A key that can't be computed is left out (data-schema.md 1.3)."""
    return {k: v for k, v in d.items() if v is not None}


def per_light(results: dict[str, dict]) -> dict:
    out: dict = {}
    for name, r in results.items():
        for light, v in r.get("by_light", {}).items():
            row = out.setdefault(light, {"n": v["labels"]})
            row[name] = _clean({k: v[k] for k in ("pck_0.2", "detection_recall", "lr_accuracy")})
    return out


def evaluate(clip: str, fps_measure: bool = False, note: str = "") -> dict:
    """Format: docs/05-solution/data-schema.md 1.3. Extra keys are breakdowns for tuning."""
    p = ClipPaths(clip)
    meta = read_meta(p.meta)
    fps, n, step = meta["fps"], meta["n_frames"], meta.get("step", config.FRAME_STEP)
    minutes = n / fps / 60
    by_labeller = load_labels(clip)
    labels = merged_labels(by_labeller)
    shared, lights = shared_list(clip), light_by_second(clip)
    total = total_labelled_frames()

    def full(path: Path) -> dict:
        rows = list(read_hands(path))
        by_frame = {fr.frame: fr for fr in rows}
        out, _ = score_file(by_frame, labels, shared, lights, fps)
        out["swaps_per_min"] = round(swaps_per_min(rows, step, minutes), 2)
        out["jitter_px"] = round(jitter(rows, step), 2)
        out["two_hand_frames"] = pair_order(rows, step)
        out["worst_moments"] = worst_moments(by_frame, labels, fps)
        return _clean(out)

    results = {name: full(path) for name, path in (("baseline", p.hands_baseline), ("ours", p.hands)) if path.exists()}
    old = json.loads(p.metrics.read_text(encoding="utf-8")) if p.metrics.exists() else {}
    speed = dict(old.get("fps") or {}) if isinstance(old.get("fps"), dict) else {}
    if fps_measure:
        speed["hands_baseline"] = measure_fps(clip)
    stats = p.dir / "hands_stats.json"
    if stats.exists() and "fps" in (s := json.loads(stats.read_text(encoding="utf-8"))):
        speed["hands"] = s["fps"]
    ours = results.get("ours", {})
    m: dict = {"clip": clip, "partial": total < FULL_LABELS, "n_labels": len(labels), "labels_total_team": total,
               "labellers": sorted(by_labeller), **results, "per_light": per_light(results),
               "labels": _clean({"prefilled_share": prefilled_share(labels), "pck_manual": ours.get("pck_shared_manual"),
                                 "pck_prefilled": ours.get("pck_prefilled")}),
               "fps": speed, "hardware": hardware(), "failures": failures(ours.get("worst_moments", []))}
    if (agree := agreement(by_labeller)):
        m["inter_labeller"] = agree
    keys = ("detection_recall", "detection_precision", "lr_accuracy", "pck_0.2", "swaps_per_min", "jitter_px")
    m["history"] = old.get("history", []) + [{"at": datetime.now().isoformat(timespec="seconds"), "note": note,
                                              **{f"{name}.{k}": r.get(k) for name, r in results.items() for k in keys}}]
    p.metrics.write_text(json.dumps(m, indent=2), encoding="utf-8")
    return m


def summary(clips: list[str], note: str = "") -> dict:
    """Pools the raw counts over clips, so a clip with more labels weighs more."""
    out: dict = {"clips": clips, "labels_total_team": total_labelled_frames()}
    out["partial"] = out["labels_total_team"] < FULL_LABELS
    for name, attr in (("baseline", "hands_baseline"), ("ours", "hands")):
        pooled: dict[str, Tally] = defaultdict(Tally)
        for clip in clips:
            p = ClipPaths(clip)
            path = getattr(p, attr)
            if not path.exists():
                continue
            labels = merged_labels(load_labels(clip))
            rows = {fr.frame: fr for fr in read_hands(path)}
            fps = read_meta(p.meta)["fps"]
            _, groups = score_file(rows, labels, shared_list(clip), light_by_second(clip), fps)
            for key, g in groups.items():
                t = pooled[key]
                for a in ("labels", "preds", "matched", "side_ok", "pts", "pts_ok", "frames"):
                    setattr(t, a, getattr(t, a) + getattr(g, a))
                t.wrist_err += g.wrist_err
        if "all" in pooled:
            out[name] = {**pooled["all"].result(),
                         "by_tag": {k[4:]: g.result() for k, g in pooled.items() if k.startswith("tag:")},
                         "by_light": {k[6:]: g.result() for k, g in pooled.items() if k.startswith("light:")},
                         "by_side": {k[5:]: g.result() for k, g in pooled.items() if k.startswith("side:")},
                         "pck_shared_manual": pooled["shared_manual"].result()["pck_0.2"] if "shared_manual" in pooled else None,
                         "pck_prefilled": pooled["prefilled"].result()["pck_0.2"] if "prefilled" in pooled else None}
    path = config.OUTPUTS / "metrics_summary.json"
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    snapshot = {k: out.get("ours", {}).get(k) for k in ("detection_recall", "detection_precision", "lr_accuracy", "pck_0.2")}
    out["history"] = old.get("history", []) + [{"at": datetime.now().isoformat(timespec="seconds"), "note": note, **snapshot}]
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def labelled_clips() -> list[str]:
    return sorted({p.stem.split("__")[0] for p in config.EVAL_LABELS.glob("*__*.json")})


def _line(name: str, m: dict) -> str:
    def v(k):
        return "  n/a" if m.get(k) is None else f"{m[k]:5.3f}"
    return (f"  {name:9s} recall {v('detection_recall')}  precision {v('detection_precision')}  "
            f"L/R {v('lr_accuracy')}  PCK {v('pck_0.2')}  labels {m.get('labels')}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m egovision.eval.metrics", description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--clip")
    g.add_argument("--all", action="store_true", help="every clip that has labels")
    ap.add_argument("--fps", action="store_true", help=f"also time MediaPipe on {FPS_FRAMES} frames; run with the laptop idle")
    ap.add_argument("--note", default="", help="what changed, kept in the history")
    a = ap.parse_args(argv)
    clips = labelled_clips() if a.all else [a.clip]
    done = []
    for clip in clips:
        if not ClipPaths(clip).meta.exists():
            print(f"{clip}: no outputs on this laptop, skipped")
            continue
        m = evaluate(clip, a.fps, a.note)
        done.append(clip)
        print(f"{clip}: {m['n_labels']} labelled frames{' (partial)' if m['partial'] else ''}")
        for name in ("baseline", "ours"):
            if name in m:
                print(_line(name, m[name]))
    if done:
        s = summary(done, a.note)
        print(f"ALL {len(done)} clips, {s['labels_total_team']} team labels{' (partial)' if s['partial'] else ''}")
        for name in ("baseline", "ours"):
            if name in s:
                print(_line(name, s[name]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
