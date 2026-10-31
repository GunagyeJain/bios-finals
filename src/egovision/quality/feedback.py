"""B6 · owner: Bhavyam. Task: docs/06-plan/tasks/bhavyam.md

One line for the capture team: what went wrong in a clip, how much and when, from quality.csv.
The export datasheet calls `capture_feedback` for every clip.
"""
from __future__ import annotations

from . import params as P
from ..schema import QUALITY_COLS, ClipPaths, read_csv

WORDS = {"dark": "dark", "dim": "dim", "clipped": "overexposed", "frozen": "frozen video", "blur": "blurry",
         "fast_head": "head moving fast", "hands_out": "hands out of view",
         "hands_partial": "hands partly out of view", "edge_cut": "hands cut by the frame edge",
         "camera_angle": "camera angle off", "disagree": "hand trackers disagree"}


def clock(s: float) -> str:
    return f"{int(s) // 60}:{int(s) % 60:02d}"


def longest_run(seconds: list[float]) -> tuple[float, float]:
    """Sorted segment starts -> (start, end) of the longest unbroken stretch, in seconds."""
    best = run = (seconds[0], seconds[0] + 1)
    for s in seconds[1:]:
        run = (run[0], s + 1) if s == run[1] else (s, s + 1)
        if run[1] - run[0] > best[1] - best[0]:
            best = run
    return best


def summarise(rows: list[dict]) -> str:
    """quality.csv rows -> one line, biggest problem first."""
    found: dict[str, list[float]] = {}
    for r in rows:
        for reason in filter(None, r["reasons"].split(";")):
            found.setdefault(reason, []).append(float(r["t_start"]))
    parts = []
    for reason, secs in sorted(found.items(), key=lambda kv: -len(kv[1])):
        text = f"{WORDS.get(reason, reason)} {100 * len(secs) / len(rows):.0f} %"
        a, b = longest_run(secs)
        if b - a >= P.FEEDBACK_MIN_RUN_S:
            text += f", longest {clock(a)}–{clock(b)}"
        parts.append(text)
    return "; ".join(parts) or "no capture problems found"


def capture_feedback(clip: str) -> str:
    return summarise(read_csv(ClipPaths(clip).quality, QUALITY_COLS))
