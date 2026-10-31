"""G4 · owner: Gunagye. datasheet.md for an export: what is in it, how it was made, numbers, hardware,
licences, limits, capture feedback. Numbers come from the index (metrics.json per clip)."""
from __future__ import annotations

import os
import platform
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

from egovision import config
from egovision.index import query

LICENCES = [
    ("Footage", "Owned by the company that provided it. Used under the hackathon data-use agreement: event use "
                "only, no redistribution, every copy deleted after the event."),
    ("MediaPipe Hand Landmarker", "Apache-2.0"),
    ("rtmlib / RTMPose", "Apache-2.0"),
    ("YOLOE (Ultralytics)", "AGPL-3.0"),
    ("YuNet face detector (OpenCV Zoo)", "MIT"),
    ("WiLoR + MANO", "CC-BY-NC-ND and MANO non-commercial licence; only where wilor.jsonl was used"),
]
LIMITS = [
    "Faces are blurred (YuNet). Screens and documents are not blurred.",
    "Contacts come from a fingertips-in-box rule on YOLOE boxes: a hand holding a part the detector misses "
    "is recorded as no contact.",
    "Clips without a quality grade are treated as yellow and only appear in yellow exports.",
    "kp2d is in source-video pixels (source_size in episodes.jsonl); episode videos are downscaled.",
    "Left/right are the camera wearer's hands as voted by the hand pipeline; a swapped side is possible "
    "in fast crossings.",
]


def _feedback(clips: list[str]) -> list[str]:
    try:
        from egovision.quality.feedback import capture_feedback
    except ImportError:
        return []
    lines = []
    for c in clips:
        try:
            lines.append(f"- `{c}`: {capture_feedback(c)}")
        except Exception as e:  # feedback is optional; say so instead of failing the export
            lines.append(f"- `{c}`: feedback unavailable ({e.__class__.__name__})")
    return lines


def _metrics(clips: list[str]) -> pd.DataFrame:
    m = query.sql(f"SELECT clip, key, value FROM metrics WHERE clip IN ({','.join('?' * len(clips))})", tuple(clips))
    return m.groupby("key")["value"].agg(["mean", "count"]).round(3) if not m.empty else m


def write(root: Path, summary: dict, episodes: list[dict], clips: pd.DataFrame, filters: dict) -> Path:
    used = sorted({e["clip"] for e in episodes})
    eps = pd.DataFrame(episodes)
    eps["seconds"] = eps["t_end"] - eps["t_start"]
    by_factory = eps.groupby("factory").agg(clips=("clip", "nunique"), episodes=("clip", "size"),
                                            seconds=("seconds", "sum"))
    tasks = Counter(e["task"] for e in episodes).most_common(10)
    metrics = _metrics(used)
    lines = [
        f"# Data sheet: {summary['name']}", "",
        f"Built {datetime.now():%Y-%m-%d %H:%M} by the EgoVision pipeline {config.PIPELINE_VERSION}.", "",
        "## What is in it",
        f"- {summary['episodes']} episodes, {summary['frames']:,} frames, {summary['seconds']:.0f} s of "
        f"two-hand tracks from {summary['clips']} clips, {summary['tasks']} tasks.",
        f"- Light: {'green only' if filters['light'] == 'green' else 'green and yellow'} (red never exported). "
        "Episodes are usable stretches of at least "
        "3 s, cut at step boundaries.",
        f"- Red seconds inside episodes: {summary['red_seconds']:.0f}.",
        f"- Filters: factories {filters['factories'] or 'all'}, grips {filters['grips'] or 'all'}, "
        f"task contains '{filters['task_contains'] or '-'}', "
        f"robot hand {({'2f': 'only grabs a 2-finger robot can copy', '5f': 'only grabs a 5-finger robot can copy'}).get(filters.get('robot'), 'any')}.", "",
        "| Factory | Clips | Episodes | Seconds |", "|---|---:|---:|---:|",
        *[f"| {r.Index} | {int(r.clips)} | {int(r.episodes)} | {r.seconds:.0f} |" for r in by_factory.itertuples()], "",
        "Most common tasks: " + ", ".join(f"{t} ({n})" for t, n in tasks) + ".", "",
        "## How it was made",
        "1. Hands: MediaPipe on every 2nd frame, then side voting, IDs, gap fill and smoothing; "
        "low-confidence frames re-detected (rtmlib, ROI) and, where available, refined with WiLoR.",
        "2. Quality light per second (blur, brightness, hands visible, edge cuts, agreement, frozen frames).",
        "3. Objects (YOLOE) and contacts per hand (fingertips in the object box, hand closed, hysteresis).",
        "4. Steps from grab/release windows, captioned with a fixed verb list.",
        "5. Export: one parquet per episode (data-schema.md §4), faces blurred in every episode video.", "",
        "## Numbers (mean over the exported clips, from metrics.json)",
        *(["| Metric | Mean | Clips |", "|---|---:|---:|",
           *[f"| {k} | {r['mean']} | {int(r['count'])} |" for k, r in metrics.iterrows()]]
          if not metrics.empty else ["No metrics.json for these clips yet."]), "",
        "## Hardware",
        f"- Built on {platform.system()} {platform.release()}, {platform.processor() or platform.machine()}, "
        f"{os.cpu_count()} logical CPUs, no GPU needed for this step.", "",
        "## Licences", *[f"- {k}: {v}" for k, v in LICENCES], "",
        "## Limits", *[f"- {x}" for x in LIMITS], "",
    ]
    feedback = _feedback(used)
    if feedback:
        lines += ["## Capture feedback", *feedback, ""]
    path = root / "datasheet.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
