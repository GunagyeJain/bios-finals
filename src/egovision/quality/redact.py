"""B4 · owner: Bhavyam. Blur faces and screens/documents (trd.md §5.3). Applied to every exported or
module video, so a missing detector raises instead of passing footage through unblurred.
Keep `keep` boxes (hands) sharp, unless one covers most of a face.
`python -m egovision.quality.redact --clip X --scan` saves whole-clip face boxes for clip_redactor; `--out path.mp4` previews."""
from __future__ import annotations

import argparse
import time
import urllib.request
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from . import params
from .. import config
from ..io.frames import frames
from ..schema import ClipPaths, read_hands, read_jsonl, read_meta, write_jsonl


@lru_cache(maxsize=1)
def _yunet():
    """Downloads the model on first use: it is git-ignored, and export must work on a fresh clone."""
    path = Path(params.YUNET_MODEL)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        urllib.request.urlretrieve(params.YUNET_URL, tmp)
        tmp.replace(path)
    return cv2.FaceDetectorYN.create(str(path), "", (320, 320), params.FACE_SCORE, params.FACE_NMS, params.FACE_TOP_K)


def _detect(img: np.ndarray) -> np.ndarray:
    """Rows of x, y, w, h, score in `img` pixels. Small frames are enlarged first: render and caption frames
    lost most faces at their own size."""
    h, w = img.shape[:2]
    s = max(1.0, params.DETECT_WIDTH / w)
    big = img if s == 1 else cv2.resize(img, (round(w * s), round(h * s)), interpolation=cv2.INTER_LINEAR)
    det = _yunet()
    det.setInputSize((big.shape[1], big.shape[0]))
    _, faces = det.detect(big)
    if faces is None:
        return np.empty((0, 5))
    out = faces[:, [0, 1, 2, 3, -1]].astype(float)
    out[:, :4] /= s
    return out


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    return inter / max(a[2] * a[3] + b[2] * b[3] - inter, 1.0)


_tracks: list[dict] = []


def _update(tracks: list[dict], detections: np.ndarray, frame: int, size: tuple[int, int]) -> list[dict]:
    """Match detections to `tracks` and start new ones, in place. Returns the tracks that just ended."""
    faces = list(detections)
    for t in tracks:
        best = max(range(len(faces)), key=lambda k: _iou(t["box"], faces[k]), default=None)
        if best is not None and _iou(t["box"], faces[best]) > params.FACE_MATCH_IOU:
            f = faces.pop(best)
            t.update(box=f[:4], peak=max(t["peak"], f[4]), miss=0)
            t["seen"][frame] = f[:4]
        else:
            t["miss"] += 1
    tracks.extend({"box": f[:4], "peak": f[4], "miss": 0, "size": size, "seen": {frame: f[:4]}} for f in faces)
    ended = [t for t in tracks if t["miss"] > params.FACE_HOLD]
    tracks[:] = [t for t in tracks if t["miss"] <= params.FACE_HOLD]
    return ended


def _follow(img: np.ndarray) -> list[np.ndarray]:
    """x, y, w, h of faces proven by one strong detection, kept through weak frames and short gaps, so real faces
    do not drop out and one-frame false detections never blur. Frames before the strong one stay sharp: scan() fixes
    that when a clip has been scanned.
    shortcut: state is per process and frames are assumed in order; after a jump old boxes linger for FACE_HOLD
    calls, which only over-blurs."""
    size = img.shape[:2]
    if _tracks and _tracks[0]["size"] != size:
        _tracks.clear()
    _update(_tracks, _detect(img), 0, size)
    return [t["box"] for t in _tracks if t["peak"] >= params.FACE_CONFIRM]


def _padded(x: float, y: float, w: float, h: float) -> list[float]:
    pad = params.FACE_PAD
    return [float(x - pad * w), float(y - pad * h), float(x + (1 + pad) * w), float(y + (1 + pad) * h)]


def face_boxes(img: np.ndarray) -> list[list[float]]:
    """Padded [x1, y1, x2, y2] per followed face, may overhang the frame."""
    return [_padded(*box) for box in _follow(img)]


def _faces_file(clip: str) -> Path:
    return ClipPaths(clip).dir / "faces.jsonl"


def scan(clip: str) -> None:
    """Write faces.jsonl: padded source-pixel boxes per processed frame. Knowing the whole clip, a proven face is
    blurred from its first detection, across gaps and FACE_HOLD steps past both ends."""
    p = ClipPaths(clip)
    step = int(read_meta(p.meta).get("step", config.FRAME_STEP))
    tracks: list[dict] = []
    done: list[dict] = []
    for i, _, img in frames(p.video, step=step):
        done += _update(tracks, _detect(img), i, img.shape[:2])
    boxes: dict[int, list[list[float]]] = defaultdict(list)
    for t in done + tracks:
        if t["peak"] < params.FACE_CONFIRM:
            continue
        at = sorted(t["seen"])
        xywh = np.array([t["seen"][f] for f in at])
        for f in range(max(at[0] - params.FACE_HOLD * step, 0), at[-1] + params.FACE_HOLD * step + 1, step):
            boxes[f].append(_padded(*(np.interp(f, at, xywh[:, k]) for k in range(4))))
    write_jsonl(_faces_file(clip), [{"frame": f, "boxes": b} for f, b in sorted(boxes.items())])


def clip_redactor(clip: str) -> Callable:
    """`redact(img, keep=None, frame=None)` for one clip, on any frame size: scanned boxes if the clip has them,
    otherwise redact_frame. `frame` is the source frame index."""
    path = _faces_file(clip)
    if not path.exists():
        return lambda img, keep=None, frame=None: redact_frame(img, keep)
    meta = read_meta(ClipPaths(clip).meta)
    step, width = int(meta.get("step", config.FRAME_STEP)), int(meta["width"])
    boxes = {r["frame"]: r["boxes"] for r in read_jsonl(path)}

    def redact(img: np.ndarray, keep: list[list[float]] | None = None, frame: int | None = None) -> np.ndarray:
        s = img.shape[1] / width
        return blur_boxes(img, [[v * s for v in b] for b in boxes.get(frame - frame % step, [])], keep)
    return redact


def _clip_box(box: list[float], w: int, h: int) -> tuple[int, int, int, int]:
    """Whole pixels inside the frame, rounded outwards."""
    x1, y1, x2, y2 = box
    return max(0, int(np.floor(x1))), max(0, int(np.floor(y1))), min(w, int(np.ceil(x2))), min(h, int(np.ceil(y2)))


def _covered(face: tuple[int, int, int, int], box: tuple[int, int, int, int]) -> float:
    """Share of `face` inside `box`."""
    ix = max(0, min(face[2], box[2]) - max(face[0], box[0]))
    iy = max(0, min(face[3], box[3]) - max(face[1], box[1]))
    return ix * iy / ((face[2] - face[0]) * (face[3] - face[1]))


def blur_boxes(img: np.ndarray, boxes: list[list[float]], keep: list[list[float]] | None = None) -> np.ndarray:
    """Blur `boxes` on a copy, then restore `keep` from the original, so hands win over faces, unless a hand box
    covers most of a face: 12 of 249 strong detections on real clips would have come back sharp."""
    if not boxes:
        return img
    h, w = img.shape[:2]
    out = img.copy()
    faces = [_clip_box(box, w, h) for box in boxes]
    faces = [(x1, y1, x2, y2) for x1, y1, x2, y2 in faces if x2 > x1 and y2 > y1]
    for x1, y1, x2, y2 in faces:
        k = max(x2 - x1, y2 - y1, params.BLUR_MIN_KERNEL) | 1     # kernel scales with the box: stays strong on near faces
        out[y1:y2, x1:x2] = cv2.GaussianBlur(img[y1:y2, x1:x2], (k, k), 0)
    for box in keep or []:
        x1, y1, x2, y2 = _clip_box(box, w, h)
        if any(_covered(f, (x1, y1, x2, y2)) > params.KEEP_MAX_FACE for f in faces):
            continue
        out[y1:y2, x1:x2] = img[y1:y2, x1:x2]
    return out


def redact_frame(img: np.ndarray, keep: list[list[float]] | None = None) -> np.ndarray:
    return blur_boxes(img, face_boxes(img), keep)


def _hand_boxes(clip: str) -> dict[int, list[list[float]]]:
    """Frame -> hand boxes. Empty until hands exist, so the preview works from the first day."""
    path = ClipPaths(clip).hands_input()
    if not path.exists():
        return {}
    return {f.frame: [h.bbox for h in f.hands] for f in read_hands(path)}


def preview(clip: str, out: Path) -> None:
    """Local check only: the output is footage, keep it out of git."""
    p = ClipPaths(clip)
    cap = cv2.VideoCapture(str(p.video))
    if not cap.isOpened():
        raise FileNotFoundError(p.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    size = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    hands = _hand_boxes(clip)
    out.parent.mkdir(parents=True, exist_ok=True)
    vw = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    keep: list[list[float]] = []
    n = with_faces = 0
    t0 = time.time()
    for i, _, img in frames(p.video):
        keep = hands.get(i, keep)                                  # baseline hands exist on every step-th frame only
        boxes = face_boxes(img)
        with_faces += bool(boxes)
        n += 1
        vw.write(blur_boxes(img, boxes, keep))
    vw.release()
    print(f"{out}: {n} frames, {with_faces} with faces, {1000 * (time.time() - t0) / max(n, 1):.1f} ms per frame")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="egovision.quality.redact")
    ap.add_argument("--clip", required=True)
    ap.add_argument("--out", type=Path, help="write a local preview video")
    ap.add_argument("--scan", action="store_true", help="write faces.jsonl for this clip")
    a = ap.parse_args()
    if a.scan:
        scan(a.clip)
    if a.out:
        preview(a.clip, a.out)
