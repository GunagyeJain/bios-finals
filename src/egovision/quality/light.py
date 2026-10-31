"""B3 · owner: Bhavyam. Task: docs/06-plan/tasks/bhavyam.md

Data Health light per 1 s segment with reasons (trd.md §5.2).
In: video, hands_input()  Out: quality.csv (schema.QUALITY_COLS).
Hand columns stay -1 when no hand file exists yet, so the stage can run early and be rerun later.
"""
from __future__ import annotations

from collections import defaultdict

import cv2
import numpy as np

from . import params as P
from .. import config
from ..io.frames import build_meta, frames
from ..schema import QUALITY_COLS, ClipPaths, FrameHands, read_hands, read_meta, write_csv


def shrink(gray: np.ndarray, width: int) -> np.ndarray:
    return cv2.resize(gray, (width, round(gray.shape[0] * width / gray.shape[1])), interpolation=cv2.INTER_AREA)


def frame_metrics(gray: np.ndarray, prev: np.ndarray | None, detail: np.ndarray | None = None) -> dict:
    """One small grayscale frame. `prev` is the sample before it, None on the first one. Sharpness
    reads `detail`, a larger copy of the frame: at 160 px it barely reacts to motion blur."""
    m = {"blur": cv2.Laplacian(gray if detail is None else detail, cv2.CV_64F).var(),
         "brightness": gray.mean() / 255, "dark": (gray < P.DARK_PIXEL).mean(),
         "clipped": (gray > P.CLIPPED_PIXEL).mean()}
    if prev is not None:
        flow = cv2.calcOpticalFlowFarneback(prev, gray, None, 0.5, 2, 9, 2, 5, 1.1, 0)
        m["speed"] = float(np.median(np.hypot(flow[..., 0], flow[..., 1])))
        m["diff"] = float(cv2.absdiff(gray, prev).mean())
    return m


def hand_metrics(frames_hands: list[FrameHands], w: int, h: int) -> dict:
    """Hand columns for one segment, -1 where there is nothing to measure."""
    out = {"hands_visible": -1.0, "edge_cut": -1.0, "hand_y": -1.0, "agreement": -1.0}
    if not frames_hands:
        return out
    seen = [f for f in frames_hands if f.hands]
    out["hands_visible"] = len(seen) / len(frames_hands)
    if seen:
        m = P.EDGE_MARGIN
        cut = [any(b[0] < m or b[1] < m or b[2] > w - m or b[3] > h - m for b in (x.bbox for x in f.hands))
               for f in seen]
        out["edge_cut"] = float(np.mean(cut))
        out["hand_y"] = float(np.mean([(x.bbox[1] + x.bbox[3]) / 2 / h for f in seen for x in f.hands]))
    agree = [x.agreement for f in seen for x in f.hands if x.agreement is not None]
    if agree:
        out["agreement"] = float(np.mean(agree))
    return out


def judge(m: dict) -> tuple[str, str]:
    """Light + reasons from one segment's numbers. A hand value of -1 means unknown: that check is skipped."""
    hard, soft = [], []
    if m["dark_share"] > P.DARK_HARD:
        hard.append("dark")
    elif m["dark_share"] > P.DARK_SOFT:
        soft.append("dim")
    if m["clipped_share"] > P.CLIPPED_SOFT:
        soft.append("clipped")
    if m["frozen"]:
        hard.append("frozen")
    if m["blur_rel"] < P.BLUR_HARD:
        hard.append("blur")
    elif m["blur_rel"] < P.BLUR_SOFT:
        soft.append("blur")
    if m["speed"] > P.SPEED_SOFT:
        soft.append("fast_head")
    if 0 <= m["hands_visible"] < P.HANDS_HARD:
        hard.append("hands_out")
    elif 0 <= m["hands_visible"] < P.HANDS_SOFT:
        soft.append("hands_partial")
    if m["edge_cut"] > P.EDGE_SOFT:
        soft.append("edge_cut")
    if m["hand_y"] >= 0 and not P.HAND_Y_MIN <= m["hand_y"] <= P.HAND_Y_MAX:
        soft.append("camera_angle")
    if 0 <= m["agreement"] < P.AGREEMENT_SOFT:
        soft.append("disagree")
    reasons = hard + soft
    if hard or len(soft) >= 3:
        return "red", ";".join(reasons)
    return ("yellow" if soft else "green"), ";".join(reasons)


def segment(samples: list[dict], hands: dict) -> dict:
    """One second's frame samples and hand numbers -> the numbers `judge` reads."""
    moving = [s for s in samples if "diff" in s]
    return {"blur": float(np.mean([s["blur"] for s in samples])),
            "brightness": float(np.mean([s["brightness"] for s in samples])),
            "dark_share": float(np.mean([s["dark"] for s in samples])),
            "clipped_share": float(np.mean([s["clipped"] for s in samples])),
            "speed": float(np.mean([s["speed"] for s in moving])) if moving else 0.0,
            "frozen": bool(moving) and max(s["diff"] for s in moving) < P.FROZEN_DIFF, **hands}


def run(clip: str) -> None:
    p = ClipPaths(clip).mkdir()
    meta = read_meta(p.meta) if p.meta.exists() else build_meta(clip)
    per_second: dict[int, list[FrameHands]] = defaultdict(list)
    if p.hands_input().exists():
        for f in read_hands(p.hands_input()):
            per_second[int(f.t)].append(f)
    samples: dict[int, list[dict]] = defaultdict(list)
    prev = None
    for _, t, img in frames(p.video, step=P.SAMPLE_STEP):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        small = shrink(gray, P.SMALL_WIDTH)
        samples[int(t)].append(frame_metrics(small, prev, shrink(gray, P.BLUR_WIDTH)))
        prev = small
    segments = {sec: segment(s, hand_metrics(per_second.get(sec, []), meta["width"], meta["height"]))
                for sec, s in sorted(samples.items())}
    # shortcut: sharpness is relative to the clip, factories differ 2x; a clip blurred end to end stays green
    typical = float(np.median([m["blur"] for m in segments.values()])) or 1.0
    rows = []
    for sec, m in segments.items():
        light, reasons = judge({**m, "blur_rel": m["blur"] / typical})
        rows.append({"clip": clip, "t_start": sec, "t_end": sec + 1, "light": light, "reasons": reasons,
                     "blur": round(m["blur"], 1), "brightness": round(m["brightness"], 3),
                     "hands_visible": round(m["hands_visible"], 3), "edge_cut": round(m["edge_cut"], 3),
                     "agreement": round(m["agreement"], 3), "frozen": int(m["frozen"])})
    write_csv(p.quality, QUALITY_COLS, rows)
    print(f"{clip}: {len(rows)} s, " + ", ".join(f"{k} {sum(r['light'] == k for r in rows)}"
                                                for k in ("green", "yellow", "red")))
