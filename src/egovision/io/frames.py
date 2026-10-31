"""Frame iterator (problem statement p.10) and meta.json writer. Owner: Gunagye."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import cv2
import numpy as np

from .. import config
from ..schema import ClipPaths, write_meta


def frames(path: Path, step: int = 1, width: int | None = None) -> Iterator[tuple[int, float, np.ndarray]]:
    """Yield (frame_index, time_s, BGR image) for every `step`-th frame."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise FileNotFoundError(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    i = 0
    try:
        while True:
            ok, img = cap.read()
            if not ok:
                break
            if i % step == 0:
                if width:
                    img = cv2.resize(img, (width, int(img.shape[0] * width / img.shape[1])))
                yield i, i / fps, img
            i += 1
    finally:
        cap.release()


def factory_of(clip: str) -> str:
    """Factory id from the clip name: `MTL-SGF00106-021` → `MTL-SGF00106`, `mytronlabs-000003-002` →
    `mytronlabs-000003` (last dash-separated part is the clip number). Fixtures keep `fixture`."""
    return clip.rsplit("-", 1)[0] if "-" in clip else clip.rsplit("_", 1)[0]


def build_meta(clip: str, is_demo: bool = False) -> dict:
    p = ClipPaths(clip).mkdir()
    cap = cv2.VideoCapture(str(p.video))
    if not cap.isOpened():
        raise FileNotFoundError(p.video)
    meta = {
        "clip": clip, "factory": factory_of(clip), "video": str(p.video),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": cap.get(cv2.CAP_PROP_FPS) or 30.0, "n_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "step": config.FRAME_STEP, "is_demo": is_demo, "pipeline_version": config.PIPELINE_VERSION,
    }
    cap.release()
    write_meta(p.meta, meta)
    return meta
