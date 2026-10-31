"""Synced clip player (ui-design.md §3): one component holds the video, timeline, light strip, "This moment" and
the step/stretch lists, and all of it follows the video while it plays. Python packs the data; player.js draws.
Videos are served by Streamlit's static serving from app/static/media/ (git-ignored hard links to outputs/)."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pandas as pd
import streamlit.components.v1 as components

from egovision.index import query
from egovision.schema import ClipPaths, read_hands

APP = Path(__file__).parent
STATIC = APP / "static" / "media"
VIEWS = [("ours", "Ours", "render"), ("baseline", "Baseline", "render_baseline"),
         ("2f", "2-finger robot", "render_robot_2f"), ("5f", "5-finger robot", "render_robot_5f")]


def media_url(clip: str, src: Path) -> str | None:
    """Hard-link (or copy) a clip video into app/static/media/<clip>/ and return its URL; None if missing."""
    if not src.exists():
        return None
    dest = STATIC / clip / src.name
    st_src = src.stat()
    if not dest.exists() or dest.stat().st_size != st_src.st_size or dest.stat().st_mtime < st_src.st_mtime:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.unlink(missing_ok=True)
        try:
            os.link(src, dest)
        except OSError:
            shutil.copy2(src, dest)
    return f"/app/static/media/{clip}/{src.name}?v={int(st_src.st_mtime)}"


def _rows(df: pd.DataFrame, cols: list[str]) -> list[list]:
    return [] if df.empty else [[None if pd.isna(v) else v for v in r] for r in df[cols].itertuples(index=False)]


def hand_track(clip: str) -> list[list]:
    """Per processed frame: [t, left, right] with each hand [source, score, flags] or 0 when not found."""
    p = ClipPaths(clip).hands_input()
    if not p.exists():
        return []
    out = []
    for fr in read_hands(p):
        side = {}
        for h in fr.hands:
            if h.side not in side or h.score > side[h.side][1]:
                side[h.side] = [h.source, round(h.score, 2), h.flags]
        out.append([round(fr.t, 3), side.get("left", 0), side.get("right", 0)])
    return out


def payload(clip: str, d: dict, fps: float, duration: float) -> dict:
    p = ClipPaths(clip)
    videos = {key: media_url(clip, p.dir / f"{stem}.mp4") for key, _, stem in VIEWS}
    source = None if videos["ours"] else media_url(clip, p.video)
    return {
        "clip": clip, "duration": duration, "fps": fps,
        "views": [{"key": k, "label": lab, "url": videos[k]} for k, lab, _ in VIEWS],
        "source": source,
        "segments": _rows(d["segments"], ["t_start", "t_end", "light", "reasons"]),
        "contacts": _rows(d["contacts"], ["t_start", "t_end", "hand", "state", "object_name", "grip"]),
        "steps": _rows(d["steps"], ["start_s", "end_s", "verb", "object", "hand", "caption"]),
        "alerts": _rows(d["alerts"], ["t_start", "t_end", "kind", "detail", "hand"]),
        "hands": hand_track(clip),
        "robot": {k: sorted(v) for k, v in query.ROBOT_CAN_COPY.items()},
    }


def player(clip: str, d: dict, fps: float, duration: float, height: int = 820) -> None:
    html = (APP / "player.html").read_text(encoding="utf-8")
    html = (html.replace("/*CSS*/", (APP / "player.css").read_text(encoding="utf-8"))
                .replace("/*JS*/", (APP / "player.js").read_text(encoding="utf-8"))
                .replace("/*DATA*/null", json.dumps(payload(clip, d, fps, duration)).replace("</", "<\\/")))
    components.html(html, height=height, scrolling=False)
