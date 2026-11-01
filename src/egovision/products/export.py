"""G4 · owner: Gunagye. LeRobot-style robot dataset (data-schema.md §4). Uses quality.redact.redact_frame.

`python -m egovision export --name demo_v1 --light green` and the Export page call `export()`;
`preview()` plans the same episodes without writing anything."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Callable

import cv2
import pandas as pd

from egovision import config
from egovision.index import query
from egovision.index.build import register_product
from egovision.io.frames import frames
from egovision.io.video import H264Writer
from egovision.schema import SIDES, ClipPaths, read_hands, read_meta

from . import datasheet
from .episodes import plan, select

VIDEO_WIDTH = 640
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,47}")    # the name becomes a folder that a rebuild deletes


def _json(o) -> str:
    """numpy scalars from pandas become plain numbers."""
    return json.dumps(o, default=lambda v: v.item() if hasattr(v, "item") else str(v))


def _tables() -> dict[str, pd.DataFrame]:
    return {"clips": query.library(), "segments": query.sql("SELECT * FROM segments"),
            "steps": query.sql("SELECT * FROM steps"), "contacts": query.sql("SELECT * FROM contacts")}


def preview(light: str = "green", factories: list[str] | None = None, grips: list[str] | None = None,
            task_contains: str = "", robot: str | None = None) -> pd.DataFrame:
    t = _tables()
    return plan(t["clips"], t["segments"], t["steps"], t["contacts"], light, factories, grips, task_contains, robot)


def _hand_cols(hands: list, side: str) -> dict:
    mine = [h for h in hands if h.side == side]
    h = max(mine, key=lambda x: x.score) if mine else None
    return {f"{side}.present": h is not None,
            f"{side}.kp2d": [float(v) for xy in h.kp2d for v in xy] if h else None,
            f"{side}.kp3d": [float(v) for xyz in h.kp3d for v in xyz] if h and h.kp3d else None,
            f"{side}.score": float(h.score) if h else None,
            f"{side}.source": h.source if h else None}


def _frame_row(t: float, hands: list, seg: pd.DataFrame, contacts: pd.DataFrame, steps: pd.DataFrame) -> dict:
    row = {}
    for side in SIDES:
        row |= _hand_cols(hands, side)
        held = query.at(contacts[contacts["hand"] == side], t)
        row[f"{side}.contact"] = held.iloc[0]["state"] if not held.empty else "none"
        row[f"{side}.object"] = held.iloc[0]["object_name"] if not held.empty else ""
    step = query.at(steps, t, "start_s", "end_s")
    row["step_index"] = int(step.iloc[0]["step_idx"]) if not step.empty else -1
    light = query.at(seg, t)
    row["light"] = light.iloc[0]["light"] if not light.empty else "yellow"   # not graded = yellow
    return row


def _write_clip(clip: str, eps: pd.DataFrame, tables: dict, root: Path, redact: Callable) -> list[dict]:
    """Every episode of one clip in a single pass over its video. Returns episode metadata."""
    p = ClipPaths(clip)
    meta = read_meta(p.meta)
    step, fps = int(meta.get("step", config.FRAME_STEP)), float(meta["fps"])
    hands = {fr.frame: fr.hands for fr in read_hands(p.hands_input())}
    seg, steps, contacts = (tables[k][tables[k]["clip"] == clip] for k in ("segments", "steps", "contacts"))
    w, h = int(meta["width"]), int(meta["height"])
    scale = VIDEO_WIDTH / w
    size = (VIDEO_WIDTH, int(round(h * scale / 2)) * 2)
    rows = {e.Index: [] for e in eps.itertuples()}
    writers = {}
    try:
        for i, t, img in frames(p.video, step=step):
            for e in eps.itertuples():
                if not e.t_start <= t < e.t_end:
                    continue
                if e.Index not in writers:
                    path = root / "videos" / "chunk-000" / "egocentric" / f"episode_{e.episode_index:06d}.mp4"
                    writers[e.Index] = H264Writer(path, fps / step, size)
                frame_hands = hands.get(i, [])
                small = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
                keep = [[v * scale for v in hd.bbox] for hd in frame_hands]
                writers[e.Index].write(redact(small, keep=keep))
                rows[e.Index].append({"frame_index": len(rows[e.Index]), "timestamp": round(t - e.t_start, 4),
                                      "episode_index": e.episode_index, "task_index": e.task_index,
                                      **_frame_row(t, frame_hands, seg, contacts, steps)})
    finally:
        for wr in writers.values():
            wr.close()
    out = []
    for e in eps.itertuples():
        df = pd.DataFrame(rows[e.Index])
        path = root / "data" / "chunk-000" / f"episode_{e.episode_index:06d}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)
        out.append({"episode_index": int(e.episode_index), "clip": clip, "factory": e.factory,
                    "t_start": e.t_start, "t_end": e.t_end, "n_frames": len(df), "task": e.task,
                    "light_share": e.light_share, "grip_types": e.grip_types, "steps": e.steps,
                    "source_size": [w, h], "video_size": list(size),
                    "red_frames": int((df["light"] == "red").sum()) if len(df) else 0})
    return out


def _info(name: str, eps: list[dict], fps: float, light: str, filters: dict) -> dict:
    hand = {"present": ("bool", [1]), "kp2d": ("float32", [42]), "kp3d": ("float32", [63]),
            "score": ("float32", [1]), "source": ("string", [1]), "contact": ("string", [1]),
            "object": ("string", [1])}
    features = {"frame_index": {"dtype": "int64", "shape": [1]}, "timestamp": {"dtype": "float32", "shape": [1]},
                "episode_index": {"dtype": "int64", "shape": [1]}, "task_index": {"dtype": "int64", "shape": [1]},
                **{f"{s}.{k}": {"dtype": d, "shape": sh} for s in SIDES for k, (d, sh) in hand.items()},
                "step_index": {"dtype": "int64", "shape": [1]}, "light": {"dtype": "string", "shape": [1]},
                "observation.images.egocentric": {"dtype": "video", "shape": [eps[0]["video_size"][1],
                                                                              eps[0]["video_size"][0], 3]}}
    return {"name": name, "codebase_version": "lerobot-style v2", "fps": fps, "robot_type": "human_hands",
            "total_episodes": len(eps), "total_frames": sum(e["n_frames"] for e in eps),
            "total_tasks": len({e["task"] for e in eps}), "chunks_size": 1000,
            "data_path": "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet",
            "video_path": "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4",
            "features": features, "light": light, "filters": filters,
            "coordinates": "kp2d in source-video pixels (episodes.jsonl source_size); kp3d MediaPipe world "
                           "metres around the hand centre, or WiLoR joints",
            "source_clips": sorted({e["clip"] for e in eps}), "pipeline_version": config.PIPELINE_VERSION}


def export(name: str, light: str = "green", factories: list[str] | None = None, grips: list[str] | None = None,
           task_contains: str = "", redact: Callable | None = None, robot: str | None = None,
           clips: list[str] | None = None) -> dict:
    """Write exports/<name>/ and register it in the index. Returns the numbers the Export page shows."""
    if not NAME.fullmatch(name):
        raise ValueError("Dataset name: letters, digits, - and _ only (up to 48), starting with a letter or digit.")
    if redact is None:
        from egovision.quality.redact import redact_frame as redact
    tables = _tables()
    eps = plan(tables["clips"], tables["segments"], tables["steps"], tables["contacts"], light, factories,
               grips, task_contains, robot)
    if clips:
        eps = select(eps, clips=clips)
    if eps.empty:
        raise ValueError("No episode matches these filters (needs a usable stretch of at least 3 s).")
    final = config.EXPORTS / name
    root = config.EXPORTS / f".{name}.building"     # a stopped build never touches the last finished one
    if root.exists():
        shutil.rmtree(root)
    tasks = sorted(eps["task"].unique())
    eps = eps.assign(episode_index=range(len(eps)), task_index=eps["task"].map(tasks.index))
    episodes = []
    for clip, grp in eps.groupby("clip", sort=False):
        episodes += _write_clip(clip, grp, tables, root, redact)
    fps = float(read_meta(ClipPaths(episodes[0]["clip"]).meta)["fps"]) / int(
        read_meta(ClipPaths(episodes[0]["clip"]).meta).get("step", config.FRAME_STEP))
    filters = {"light": light, "factories": factories or [], "grips": grips or [], "task_contains": task_contains,
               "robot": robot or "", "clips": clips or []}
    (root / "meta").mkdir(parents=True, exist_ok=True)
    info = _info(name, episodes, fps, light, filters)
    (root / "meta" / "info.json").write_text(json.dumps(json.loads(_json(info)), indent=2), encoding="utf-8")
    (root / "meta" / "episodes.jsonl").write_text(
        "".join(_json({k: v for k, v in e.items() if k != "red_frames"}) + "\n" for e in episodes),
        encoding="utf-8")
    (root / "meta" / "tasks.jsonl").write_text(
        "".join(_json({"task_index": i, "task": t}) + "\n" for i, t in enumerate(tasks)), encoding="utf-8")
    summary = {"name": name, "path": str(final), "episodes": len(episodes), "frames": info["total_frames"],
               "seconds": round(sum(e["t_end"] - e["t_start"] for e in episodes), 1), "tasks": len(tasks),
               "clips": len(info["source_clips"]), "red_seconds": sum(e["red_frames"] for e in episodes) / fps}
    datasheet.write(root, summary, episodes, tables["clips"], filters)
    if final.exists():
        shutil.rmtree(final)
    root.rename(final)
    register_product("dataset", name, final, filters, len(episodes))
    return summary
