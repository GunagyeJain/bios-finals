"""Checks an exported dataset against docs/05-solution/data-schema.md §4. Prints PASS or FAIL per check.
    python scripts/validate_export.py exports/demo_v1
Exit code 1 if any check fails."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
import pandas as pd

SIDES = ("left", "right")
BASE_COLS = ["frame_index", "timestamp", "episode_index", "task_index", "step_index", "light"]
HAND_COLS = ["present", "kp2d", "kp3d", "score", "source", "contact", "object"]
COLUMNS = {*BASE_COLS, *(f"{s}.{c}" for s in SIDES for c in HAND_COLS)}
SOURCES = {"mediapipe", "roi", "rtmlib", "wilor", "interp"}
CONTACTS = {"none", "portable", "fixed"}
LIGHTS = {"green", "yellow"}
INFO_KEYS = {"fps", "total_episodes", "total_frames", "total_tasks", "features", "source_clips", "pipeline_version"}
EPISODE_KEYS = {"episode_index", "clip", "t_start", "t_end", "n_frames", "task", "light_share", "grip_types", "steps"}
SHOW = 5    # problems listed per check


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _empty(v) -> bool:
    return v is None or (isinstance(v, float) and np.isnan(v))


class Export:
    """Everything the checks read, loaded once. Missing files stay empty; check_layout reports them."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.info = {}
        if (self.root / "meta" / "info.json").exists():
            self.info = json.loads((self.root / "meta" / "info.json").read_text(encoding="utf-8"))
        self.episodes = _jsonl(self.root / "meta" / "episodes.jsonl") if (self.root / "meta" / "episodes.jsonl").exists() else []
        self.tasks = _jsonl(self.root / "meta" / "tasks.jsonl") if (self.root / "meta" / "tasks.jsonl").exists() else []
        self.tables: dict[int, pd.DataFrame] = {}
        for path in sorted((self.root / "data").rglob("episode_*.parquet")):
            self.tables[int(path.stem.split("_")[1])] = pd.read_parquet(path)
        self.videos = {int(p.stem.split("_")[1]): p for p in (self.root / "videos").rglob("episode_*.mp4")}


def check_layout(e: Export) -> list[str]:
    need = ["meta/info.json", "meta/episodes.jsonl", "meta/tasks.jsonl", "datasheet.md"]
    out = [f"missing {n}" for n in need if not (e.root / n).exists()]
    if not e.episodes:
        out.append("no episodes in episodes.jsonl")
    return out


def check_meta_keys(e: Export) -> list[str]:
    out = [f"info.json has no {k}" for k in sorted(INFO_KEYS - set(e.info))]
    for ep in e.episodes:
        out += [f"episode {ep.get('episode_index')} has no {k}" for k in sorted(EPISODE_KEYS - set(ep))]
    return out


def check_files_match(e: Export) -> list[str]:
    ids = {ep["episode_index"] for ep in e.episodes}
    out = [f"episode {i}: no parquet" for i in sorted(ids - set(e.tables))]
    out += [f"episode {i}: no video" for i in sorted(ids - set(e.videos))]
    out += [f"parquet {i}: not in episodes.jsonl" for i in sorted(set(e.tables) - ids)]
    out += [f"video {i}: not in episodes.jsonl" for i in sorted(set(e.videos) - ids)]
    return out


def check_columns(e: Export) -> list[str]:
    out = []
    for i, df in e.tables.items():
        missing, extra = COLUMNS - set(df.columns), set(df.columns) - COLUMNS
        if missing:
            out.append(f"episode {i}: missing {sorted(missing)}")
        if extra:
            out.append(f"episode {i}: unexpected {sorted(extra)}")
    return out


def check_shapes(e: Export) -> list[str]:
    """Keypoints are 42 and 63 floats on frames with that hand and empty without it; kp3d may be null."""
    out = []
    for i, df in e.tables.items():
        for side in SIDES:
            if f"{side}.present" not in df:
                continue
            for n, (present, k2, k3) in enumerate(zip(df[f"{side}.present"], df[f"{side}.kp2d"], df[f"{side}.kp3d"])):
                if present and (_empty(k2) or len(k2) != 42):
                    out.append(f"episode {i} row {n}: {side}.kp2d is not 42 floats")
                if present and not _empty(k3) and len(k3) != 63:
                    out.append(f"episode {i} row {n}: {side}.kp3d is not 63 floats")
                if not present and not _empty(k2):
                    out.append(f"episode {i} row {n}: {side}.kp2d set but the hand is not present")
                if present and not _empty(k2) and not np.isfinite(np.asarray(k2, dtype=float)).all():
                    out.append(f"episode {i} row {n}: {side}.kp2d is not finite")
    return out


def check_time_order(e: Export) -> list[str]:
    out = []
    for i, df in e.tables.items():
        if "timestamp" in df and len(df) > 1 and not (np.diff(df["timestamp"].to_numpy()) > 0).all():
            out.append(f"episode {i}: timestamps do not increase")
        if "frame_index" in df and df["frame_index"].tolist() != list(range(len(df))):
            out.append(f"episode {i}: frame_index is not 0..n-1")
        if "episode_index" in df and set(df["episode_index"]) - {i}:
            out.append(f"episode {i}: rows carry another episode_index")
    return out


def check_no_red(e: Export) -> list[str]:
    out = []
    allowed = {"green"} if e.info.get("light") == "green" else LIGHTS
    for i, df in e.tables.items():
        if "light" not in df:
            continue
        counts = df["light"].value_counts()
        if counts.get("red", 0):
            out.append(f"episode {i}: {counts['red']} red frames")
        bad = set(counts.index) - allowed - {"red"}
        if bad:
            out.append(f"episode {i}: light values {sorted(bad)} in a {e.info.get('light')} export")
    return out


def check_video_frames(e: Export) -> list[str]:
    out = []
    for i, df in e.tables.items():
        if i not in e.videos:
            continue
        cap = cv2.VideoCapture(str(e.videos[i]))
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if cap.isOpened() else -1
        cap.release()
        if n != len(df):
            out.append(f"episode {i}: video has {n} frames, parquet {len(df)} rows")
    return out


def check_tasks(e: Export) -> list[str]:
    out = []
    by_index = {t["task_index"]: t["task"] for t in e.tasks}
    if sorted(by_index) != list(range(len(by_index))):
        out.append("task_index in tasks.jsonl is not 0..n-1")
    used = set()
    for ep in e.episodes:
        i = ep["episode_index"]
        df = e.tables.get(i)
        if df is None or "task_index" not in df:
            continue
        indices = set(df["task_index"])
        used |= indices
        if len(indices) > 1:
            out.append(f"episode {i}: several task_index values {sorted(indices)}")
        for t in indices:
            if t not in by_index:
                out.append(f"episode {i}: task_index {t} not in tasks.jsonl")
            elif by_index[t] != ep.get("task"):
                out.append(f"episode {i}: task {ep.get('task')!r} but tasks.jsonl says {by_index[t]!r}")
    out += [f"task {t} is used by no episode" for t in sorted(set(by_index) - used)]
    return out


def check_counts(e: Export) -> list[str]:
    out = []
    if e.info.get("total_episodes") != len(e.episodes):
        out.append(f"info total_episodes {e.info.get('total_episodes')}, episodes.jsonl has {len(e.episodes)}")
    rows = sum(len(df) for df in e.tables.values())
    if e.info.get("total_frames") != rows:
        out.append(f"info total_frames {e.info.get('total_frames')}, parquet has {rows}")
    if e.info.get("total_tasks") != len(e.tasks):
        out.append(f"info total_tasks {e.info.get('total_tasks')}, tasks.jsonl has {len(e.tasks)}")
    clips = sorted({ep["clip"] for ep in e.episodes})
    if sorted(e.info.get("source_clips", [])) != clips:
        out.append(f"info source_clips differ from episodes.jsonl: {clips}")
    for ep in e.episodes:
        df = e.tables.get(ep["episode_index"])
        if df is not None and ep.get("n_frames") != len(df):
            out.append(f"episode {ep['episode_index']}: n_frames {ep.get('n_frames')}, parquet {len(df)} rows")
    return out


def check_values(e: Export) -> list[str]:
    """Hand sources and contact states stay in the schema's lists."""
    out = []
    for i, df in e.tables.items():
        for side in SIDES:
            for col, allowed in ((f"{side}.source", SOURCES), (f"{side}.contact", CONTACTS)):
                if col in df:
                    bad = {v for v in df[col].dropna().unique()} - allowed
                    if bad:
                        out.append(f"episode {i}: {col} has {sorted(bad)}")
    return out


CHECKS: list[tuple[str, Callable[[Export], list[str]]]] = [
    ("layout", check_layout), ("meta keys", check_meta_keys), ("files match episodes", check_files_match),
    ("columns", check_columns), ("keypoint shapes", check_shapes), ("timestamps increase per episode", check_time_order),
    ("no red frames", check_no_red), ("video frames = parquet rows", check_video_frames),
    ("tasks and episodes consistent", check_tasks), ("counts in info.json", check_counts), ("allowed values", check_values),
]


def validate(root: Path) -> dict[str, list[str]]:
    e = Export(root)
    results = {}
    for name, fn in CHECKS:
        try:
            results[name] = fn(e)
        except Exception as err:  # a broken file fails its check and the rest still run
            results[name] = [f"check crashed: {type(err).__name__}: {err}"]
    return results


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    results = validate(Path(argv[0]))
    for name, problems in results.items():
        print(f"{'PASS' if not problems else 'FAIL'}  {name}")
        for p in problems[:SHOW]:
            print(f"      {p}")
        if len(problems) > SHOW:
            print(f"      ... and {len(problems) - SHOW} more")
    failed = sum(bool(p) for p in results.values())
    print(f"{len(results) - failed}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
