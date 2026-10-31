"""B4 · owner: Bhavyam. Blur faces and screens/documents (trd.md §5.3). Applied to every exported or
module video, so a missing detector raises instead of passing footage through unblurred.
Never blur inside `keep` boxes (hands). `python -m egovision.quality.redact --clip X --out path.mp4`."""
from __future__ import annotations

import argparse
import time
import urllib.request
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from . import params
from ..io.frames import frames
from ..schema import ClipPaths, read_hands


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


def face_boxes(img: np.ndarray) -> list[list[float]]:
    """Padded [x1, y1, x2, y2] per face, may overhang the frame."""
    det = _yunet()
    det.setInputSize((img.shape[1], img.shape[0]))
    _, faces = det.detect(img)
    if faces is None:
        return []
    pad = params.FACE_PAD
    return [[float(x - pad * w), float(y - pad * h), float(x + (1 + pad) * w), float(y + (1 + pad) * h)]
            for x, y, w, h in faces[:, :4]]


def _clip_box(box: list[float], w: int, h: int) -> tuple[int, int, int, int]:
    """Whole pixels inside the frame, rounded outwards."""
    x1, y1, x2, y2 = box
    return max(0, int(np.floor(x1))), max(0, int(np.floor(y1))), min(w, int(np.ceil(x2))), min(h, int(np.ceil(y2)))


def blur_boxes(img: np.ndarray, boxes: list[list[float]], keep: list[list[float]] | None = None) -> np.ndarray:
    """Blur `boxes` on a copy, then restore `keep` from the original, so hands win over faces."""
    if not boxes:
        return img
    h, w = img.shape[:2]
    out = img.copy()
    for box in boxes:
        x1, y1, x2, y2 = _clip_box(box, w, h)
        if x2 <= x1 or y2 <= y1:
            continue
        k = max(x2 - x1, y2 - y1, params.BLUR_MIN_KERNEL) | 1     # kernel scales with the box: stays strong on near faces
        out[y1:y2, x1:x2] = cv2.GaussianBlur(img[y1:y2, x1:x2], (k, k), 0)
    for box in keep or []:
        x1, y1, x2, y2 = _clip_box(box, w, h)
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
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    preview(a.clip, a.out)
