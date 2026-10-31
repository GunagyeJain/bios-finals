"""G4 · owner: Gunagye. Which stretches of which clips become robot episodes (data-schema.md §4).
Pure functions over index tables, so the Export page can preview a dataset without writing it."""
from __future__ import annotations

import pandas as pd

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


def _overlap(a: float, b: float, s: pd.Series, e: pd.Series) -> pd.Series:
    return (e.clip(upper=b) - s.clip(lower=a)).clip(lower=0)


def task_of(a: float, b: float, steps: pd.DataFrame, contacts: pd.DataFrame) -> str:
    """'verb object' of the step covering most of the episode; else the most-held object; else generic."""
    if not steps.empty:
        ov = _overlap(a, b, steps["start_s"], steps["end_s"])
        if ov.max() > 0:
            s = steps.loc[ov.idxmax()]
            return f"{s['verb']} {s['object']}".strip()
    if not contacts.empty:
        held = _overlap(a, b, contacts["t_start"], contacts["t_end"]).groupby(contacts["object_name"]).sum()
        if held.max() > 0:
            return f"handle {held.idxmax()}"
    return "hand activity"


def plan(clips: pd.DataFrame, segments: pd.DataFrame, steps: pd.DataFrame, contacts: pd.DataFrame, light: str,
         factories: list[str] | None = None, grips: list[str] | None = None,
         task_contains: str = "") -> pd.DataFrame:
    """One row per episode: clip, t_start, t_end, task, light_share, grip_types, steps."""
    rows = []
    for c in clips.itertuples():
        if factories and c.factory not in factories:
            continue
        seg, st, co = (df[df["clip"] == c.clip] for df in (segments, steps, contacts))
        cuts = list(st["start_s"]) + list(st["end_s"]) if not st.empty else []
        for run in usable_runs(seg, c.duration_s, light):
            for a, b in split(run, cuts):
                inside = co[(co["t_end"] > a) & (co["t_start"] < b)]
                grip_types = sorted(set(inside["grip"]))
                if grips and not set(grips) & set(grip_types):
                    continue
                task = task_of(a, b, st, co)
                if task_contains and task_contains.lower() not in task.lower():
                    continue
                ov = _overlap(a, b, seg["t_start"], seg["t_end"]) if not seg.empty else pd.Series(dtype=float)
                share = {li: round(float(ov[seg["light"] == li].sum()) / (b - a), 3)
                         for li in ("green", "yellow")} if not seg.empty else {"green": 0.0, "yellow": 1.0}
                in_steps = st[(st["end_s"] > a) & (st["start_s"] < b)]
                rows.append({"clip": c.clip, "factory": c.factory, "t_start": a, "t_end": b, "task": task,
                             "light_share": share, "grip_types": grip_types,
                             "steps": in_steps[["step_idx", "start_s", "end_s", "verb", "object", "hand"]]
                             .to_dict("records")})
    return pd.DataFrame(rows, columns=["clip", "factory", "t_start", "t_end", "task", "light_share", "grip_types",
                                       "steps"])
