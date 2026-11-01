"""G4 · owner: Gunagye. Which stretches of which clips become robot episodes (data-schema.md §4).
Pure functions over index tables, so the Export page can preview a dataset without writing it."""
from __future__ import annotations

import numpy as np
import pandas as pd

from egovision.index.query import ROBOT_CAN_COPY

MIN_EPISODE_S = 3.0
ALLOWED = {"green": {"green"}, "yellow": {"green", "yellow"}}


def usable_runs(segments: pd.DataFrame, duration: float, light: str,
                min_len: float = MIN_EPISODE_S) -> list[tuple[float, float]]:
    """Touching segments whose light is allowed, merged, at least min_len long. Red is never allowed.
    A clip without quality.csv counts as yellow (whole clip)."""
    if segments.empty:
        return [(0.0, float(duration))] if light == "yellow" and duration >= min_len else []
    runs: list[list[float]] = []
    for r in segments.sort_values("t_start").itertuples():
        if r.light not in ALLOWED[light]:
            continue
        if runs and abs(r.t_start - runs[-1][1]) < 1e-6:
            runs[-1][1] = float(r.t_end)
        else:
            runs.append([float(r.t_start), float(r.t_end)])
    return [(a, b) for a, b in runs if b - a >= min_len]


def split(run: tuple[float, float], cuts: list[float], min_len: float = MIN_EPISODE_S) -> list[tuple[float, float]]:
    """Cut a run at step boundaries, but only where both sides stay at least min_len long."""
    a, b = run
    out, start = [], a
    for c in sorted(set(cuts)):
        if start < c < b and c - start >= min_len and b - c >= min_len:
            out.append((start, c))
            start = c
    out.append((start, b))
    return out


def _overlap(a: float, b: float, s: pd.Series, e: pd.Series) -> np.ndarray:
    """Seconds of each [s, e) interval inside [a, b). numpy, not pandas: the planner calls this per episode."""
    return np.maximum(np.minimum(e.to_numpy(float), b) - np.maximum(s.to_numpy(float), a), 0.0)


def task_of(a: float, b: float, steps: pd.DataFrame, contacts: pd.DataFrame) -> str:
    """'verb object' of the step covering most of the episode; else the most-held object; else generic."""
    if not steps.empty:
        ov = _overlap(a, b, steps["start_s"], steps["end_s"])
        if ov.max() > 0:
            s = steps.iloc[int(ov.argmax())]
            verb = "handle" if s["verb"] in ("other", "", None) else s["verb"]   # captioner's catch-all verb
            return f"{verb} {s['object'] or ''}".strip()
    if not contacts.empty:
        held = pd.Series(_overlap(a, b, contacts["t_start"], contacts["t_end"]),
                         index=contacts["object_name"].to_numpy()).groupby(level=0).sum()
        if held.max() > 0:
            return f"handle {held.idxmax()}"
    return "hand activity"


def select(eps: pd.DataFrame, factories: list[str] | None = None, grips: list[str] | None = None,
           task_contains: str = "", robot: str | None = None) -> pd.DataFrame:
    """Filter planned episodes. Cheap, so the Export page plans once per light and filters on every change.
    robot='2f' or '5f' keeps only episodes whose every grab that robot hand can copy."""
    keep = pd.Series(True, index=eps.index)
    if factories:
        keep &= eps["factory"].isin(factories)
    if grips:
        keep &= eps["grip_types"].map(lambda g: bool(set(grips) & set(g)))
    if robot:
        keep &= eps["grip_types"].map(lambda g: bool(g) and set(g) <= ROBOT_CAN_COPY[robot])
    if task_contains:
        keep &= eps["task"].str.contains(task_contains, case=False, regex=False)
    return eps[keep].reset_index(drop=True)


def plan(clips: pd.DataFrame, segments: pd.DataFrame, steps: pd.DataFrame, contacts: pd.DataFrame, light: str,
         factories: list[str] | None = None, grips: list[str] | None = None,
         task_contains: str = "", robot: str | None = None) -> pd.DataFrame:
    """One row per episode: clip, factory, t_start, t_end, task, light_share, grip_types, steps. Filters: select()."""
    rows = []
    by_clip = [{k: g for k, g in df.groupby("clip")} for df in (segments, steps, contacts)]
    for c in clips.itertuples():
        if factories and c.factory not in factories:
            continue
        seg, st, co = (g.get(c.clip, df.iloc[0:0]) for g, df in zip(by_clip, (segments, steps, contacts)))
        cuts = list(st["start_s"]) + list(st["end_s"]) if not st.empty else []
        for run in usable_runs(seg, c.duration_s, light):
            for a, b in split(run, cuts):
                inside = co[(co["t_end"] > a) & (co["t_start"] < b)]
                ov = _overlap(a, b, seg["t_start"], seg["t_end"]) if not seg.empty else np.zeros(0)
                share = {li: round(float(ov[(seg["light"] == li).to_numpy()].sum()) / (b - a), 3)
                         for li in ("green", "yellow")} if not seg.empty else {"green": 0.0, "yellow": 1.0}
                in_steps = st[(st["end_s"] > a) & (st["start_s"] < b)]
                rows.append({"clip": c.clip, "factory": c.factory, "t_start": a, "t_end": b,
                             "task": task_of(a, b, st, co), "light_share": share,
                             "grip_types": sorted(set(inside["grip"])),
                             "steps": in_steps[["step_idx", "start_s", "end_s", "verb", "object", "hand"]]
                             .to_dict("records")})
    eps = pd.DataFrame(rows, columns=["clip", "factory", "t_start", "t_end", "task", "light_share", "grip_types",
                                      "steps"])
    return select(eps, None, grips, task_contains, robot)
