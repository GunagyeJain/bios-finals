"""G6 · owner: Gunagye. Task: docs/06-plan/tasks/gunagye.md

Annotated H.264 video: hands, light, contacts.
In: video, hands_input(), quality.csv, contacts.csv  Out: render.mp4 (+ render_baseline.mp4).
One pass over the video writes both; faces are blurred once (quality.redact) and shared by both.
"""
from __future__ import annotations

from typing import Callable

import cv2
import pandas as pd

from egovision import config
from egovision.io.frames import frames
from egovision.io.video import H264Writer
from egovision.schema import CONTACT_COLS, QUALITY_COLS, ClipPaths, read_csv, read_hands, read_meta

from . import overlay

WIDTH = 960
CRF = 30          # app playback only: about 40 MB per 3-min clip instead of 80


def _table(path, cols: list[str], times: tuple[str, str]) -> pd.DataFrame:
    df = pd.DataFrame(read_csv(path, cols), columns=cols) if path.exists() else pd.DataFrame(columns=cols)
    return df.astype({c: float for c in times})


def _at(df: pd.DataFrame, t: float) -> pd.DataFrame:
    return df[(df["t_start"] <= t) & (t < df["t_end"])]


def render(clip: str, redact: Callable | None = None) -> None:
    if redact is None:
        from egovision.quality.redact import redact_frame as redact
    p = ClipPaths(clip)
    meta = read_meta(p.meta)
    step, fps = int(meta.get("step", config.FRAME_STEP)), float(meta["fps"])
    duration = meta["n_frames"] / fps
    final = {f.frame: f.hands for f in read_hands(p.hands_input())}
    base = {f.frame: f.hands for f in read_hands(p.hands_baseline)} if p.hands_baseline.exists() else final
    seg = _table(p.quality, QUALITY_COLS, ("t_start", "t_end"))
    contacts = _table(p.contacts, CONTACT_COLS, ("t_start", "t_end"))
    scale = WIDTH / int(meta["width"])
    size = (WIDTH, int(round(int(meta["height"]) * scale / 2)) * 2)
    with (H264Writer(p.render, fps / step, size, CRF) as ours,
          H264Writer(p.render_baseline, fps / step, size, CRF) as before):
        for i, t, img in frames(p.video, step=step):
            small = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
            fh, bh = final.get(i, []), base.get(i, [])
            clean = redact(small, keep=[[v * scale for v in h.bbox] for h in fh + bh])
            now = _at(seg, t)
            light, reasons = (now.iloc[0]["light"], now.iloc[0]["reasons"]) if not now.empty else (None, "")
            held = {r.hand: r.object_name for r in _at(contacts, t).itertuples()}
            for writer, hand_list, held_now, view in ((ours, fh, held, "Ours"), (before, bh, {}, "Baseline: MediaPipe only")):
                out = clean.copy()
                overlay.hands(out, hand_list, scale, held_now)
                overlay.header(out, t, light, reasons, view)
                overlay.strip(out, seg, duration, t)
                writer.write(out)


def run(clip: str) -> None:
    render(clip)
