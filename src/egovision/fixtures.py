"""Synthetic clips with every pipeline output, so each stage can be built and tested before the
stage before it exists. `python -m egovision fixtures` → data/fixture/*.mp4 + outputs/fixture_00X/.
Shapes are realistic; content is fake (drawn hands, not detectable by MediaPipe). Owner: Gunagye."""
from __future__ import annotations

import json
import math
import shutil
from dataclasses import replace

import cv2
import numpy as np

from . import config
from .io.video import H264Writer
from .schema import (ALERT_COLS, CONTACT_COLS, QUALITY_COLS, STEP_COLS, ClipPaths, FrameHands,
                     Hand, write_csv, write_hands, write_jsonl, write_meta)

W, H, FPS, SECONDS = 640, 360, 30, 12
SCREWDRIVER = [300, 200, 360, 260]
MACHINE = [480, 40, 620, 200]


def _hand(side: str, cx: float, cy: float, s: float = 40.0) -> Hand:
    sign = -1 if side == "left" else 1
    kp = [[cx, cy + s]]                                   # wrist
    for f in range(5):                                    # 5 fingers x 4 joints
        ang = math.radians(-60 + f * 30) * sign
        for j in range(1, 5):
            r = s * (0.4 + 0.3 * j)
            kp.append([cx + r * math.sin(ang), cy + s - r * math.cos(ang)])
    xs, ys = zip(*kp)
    kp3d = [[(x - cx) / 1000, (y - cy) / 1000, 0.0] for x, y in kp]
    return Hand(side=side, bbox=[min(xs), min(ys), max(xs), max(ys)], score=0.9, kp2d=kp, kp3d=kp3d,
                id=0 if side == "left" else 1)


def _hands_at(t: float) -> list[Hand]:
    out = [_hand("right", 330 + 60 * math.sin(t), 230 + 20 * math.cos(t))]
    if not 8.0 <= t < 9.5:                                # left hand leaves the view
        out.append(_hand("left", 180 + 40 * math.cos(t * 0.7), 240))
    return out


def _video(path, seconds: int) -> None:
    with H264Writer(path, FPS, (W, H)) as vw:
        _draw(vw, seconds)


def _draw(vw: H264Writer, seconds: int) -> None:
    for i in range(seconds * FPS):
        t = i / FPS
        img = np.full((H, W, 3), 90, np.uint8)
        shade = int(120 + 80 * math.sin(t * 6))           # "moving machine": flickering box
        cv2.rectangle(img, MACHINE[:2], MACHINE[2:], (shade, shade, 160), -1)
        cv2.rectangle(img, SCREWDRIVER[:2], SCREWDRIVER[2:], (40, 160, 220), -1)
        for h in _hands_at(t):
            col = (255, 160, 60) if h.side == "left" else (60, 140, 255)
            for x, y in h.kp2d:
                cv2.circle(img, (int(x), int(y)), 3, col, -1)
        if 6.0 <= t < 7.0:                                # dark second → red light
            img = (img * 0.15).astype(np.uint8)
        vw.write(img)


def make(clip: str, seconds: int = SECONDS) -> ClipPaths:
    p = ClipPaths(clip).mkdir()
    _video(p.video, seconds)
    n = seconds * FPS
    write_meta(p.meta, {"clip": clip, "factory": "fixture", "video": str(p.video), "width": W,
                        "height": H, "fps": FPS, "n_frames": n, "step": config.FRAME_STEP,
                        "is_demo": False, "pipeline_version": config.PIPELINE_VERSION})
    all_frames = [FrameHands(i, i / FPS, _hands_at(i / FPS)) for i in range(n)]
    base = [f for f in all_frames if f.frame % config.FRAME_STEP == 0]
    base = [replace(f, hands=f.hands[:1]) if k % 7 == 0 else f    # baseline misses some hands
            for k, f in enumerate(base)]
    write_hands(p.hands_baseline, base)
    write_hands(p.hands, all_frames)
    lights = ["green", "green", "yellow", "green", "green", "green", "red", "green", "red", "yellow", "green", "green"]
    write_csv(p.quality, QUALITY_COLS, [
        {"clip": clip, "t_start": s, "t_end": s + 1, "light": lights[s % len(lights)],
         "reasons": {"green": "", "yellow": "blur", "red": "dark" if s == 6 else "hands_out"}[lights[s % len(lights)]],
         "blur": 120.0, "brightness": 0.1 if s == 6 else 0.5, "hands_visible": 0.5 if s == 8 else 1.0,
         "edge_cut": 0.0, "agreement": 0.8, "frozen": 0} for s in range(seconds)])
    write_jsonl(p.objects, ({"frame": i, "t": i / FPS, "objects": [
        {"id": 0, "name": "screwdriver", "kind": "portable", "bbox": SCREWDRIVER, "score": 0.7, "moving": False},
        {"id": 1, "name": "press machine", "kind": "fixed", "bbox": MACHINE, "score": 0.8, "moving": True}]}
        for i in range(0, n, 5)))
    write_csv(p.contacts, CONTACT_COLS, [
        {"clip": clip, "t_start": 1.0, "t_end": 4.0, "hand": "right", "state": "portable", "object_name": "screwdriver", "object_id": 0, "confidence": 0.8, "grip": "5f"},
        {"clip": clip, "t_start": 4.5, "t_end": 6.0, "hand": "left", "state": "fixed", "object_name": "press machine", "object_id": 1, "confidence": 0.7, "grip": "generic"},
        {"clip": clip, "t_start": 7.0, "t_end": 10.0, "hand": "right", "state": "portable", "object_name": "screwdriver", "object_id": 0, "confidence": 0.8, "grip": "2f"}])
    steps = [("pick", "screwdriver", "right", 1.0, 2.0), ("fasten", "screw", "right", 2.0, 4.0),
             ("press", "press machine", "left", 4.5, 6.0), ("pick", "screwdriver", "right", 7.0, 8.0),
             ("fasten", "screw", "right", 8.0, 10.0)]
    write_csv(p.steps, STEP_COLS, [
        {"clip": clip, "step_idx": k, "start_s": a, "end_s": b, "verb": v, "object": o, "hand": h,
         "caption": f"{h} hand {v}s the {o}", "source": "gemini", "cycle_idx": 0 if k < 3 else 1}
        for k, (v, o, h, a, b) in enumerate(steps)])
    write_csv(p.alerts_steps, ALERT_COLS, [{"clip": clip, "t_start": 7.0, "t_end": 10.0, "kind": "step_missing",
                                            "severity": "warn", "hand": "", "detail": "cycle 1 missing 'press press machine'"}])
    write_csv(p.alerts_safety, ALERT_COLS, [{"clip": clip, "t_start": 4.5, "t_end": 6.0, "kind": "safety",
                                             "severity": "warn", "hand": "left", "detail": "left fingertips 12 px from moving 'press machine'"}])
    p.metrics.write_text(json.dumps({
        "partial": True, "n_labels": 20,
        "baseline": {"detection_recall": 0.81, "detection_precision": 0.95, "lr_accuracy": 0.86, "pck_0.2": 0.70,
                     "swaps_per_min": 3.1, "jitter_px": 4.2},
        "ours": {"detection_recall": 0.93, "detection_precision": 0.96, "lr_accuracy": 0.97, "pck_0.2": 0.80,
                 "swaps_per_min": 0.3, "jitter_px": 1.2},
        "per_light": {li: {"n": n, "baseline": {"pck_0.2": b}, "ours": {"pck_0.2": o}}
                      for li, n, b, o in (("green", 12, 0.78, 0.88), ("yellow", 5, 0.62, 0.74), ("red", 3, 0.35, 0.41))},
        "labels": {"prefilled_share": 0.6, "pck_manual": 0.79, "pck_prefilled": 0.81},
        "fps": {"hands_baseline": 26.4, "hands": 75.0, "quality": 30.6, "contact": 7.7, "render": 7.7},
        "hardware": "fixture", "failures": [{"t": 8.5, "what": "left hand missing", "why": "out of view"}]},
        indent=2))
    shutil.copy(p.video, p.render)                         # stand-in until G6 render exists
    return p


def make_all() -> None:
    for clip in ("fixture_001", "fixture_002"):
        p = make(clip)
        print(f"wrote {p.dir} and {p.video}")
