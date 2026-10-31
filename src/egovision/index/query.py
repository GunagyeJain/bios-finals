"""Read-only queries over outputs/index.db for the app pages (G5, S5). No Streamlit here, so it is
testable; pages cache the results. Owner: Gunagye."""
from __future__ import annotations

import sqlite3
from contextlib import closing

import pandas as pd

from egovision import config
from egovision.schema import ClipPaths, read_hands

TABLES = ("segments", "contacts", "steps", "alerts", "frame_summary")


def has_index() -> bool:
    return config.INDEX_DB.exists()


def sql(query: str, params: tuple = ()) -> pd.DataFrame:
    with closing(sqlite3.connect(config.INDEX_DB)) as db:
        return pd.read_sql_query(query, db, params=params)


def library() -> pd.DataFrame:
    """One row per clip with alert counts, for the Library table."""
    return sql("""SELECT c.*, COALESCE(a.n, 0) AS n_alerts FROM clips c
                  LEFT JOIN (SELECT clip, COUNT(*) AS n FROM alerts GROUP BY clip) a USING (clip)
                  ORDER BY c.factory, c.seq_in_factory, c.clip""")


def kpis(lib: pd.DataFrame) -> dict[str, float | None]:
    """Library KPIs. Shares are weighted by clip duration; NaN where nothing is processed yet."""
    dur = lib["duration_s"]
    has_q = lib["green_share"].notna()
    fps = sql("SELECT AVG(value) AS v FROM metrics WHERE key = 'fps'")["v"].iloc[0]
    return {
        "clips": len(lib),
        "hours": dur.sum() / 3600,
        "green": (lib.loc[has_q, "green_share"] * dur[has_q]).sum() / dur[has_q].sum() if has_q.any() else None,
        "hands": lib["hands_found_share"].mean() if lib["hands_found_share"].notna().any() else None,
        "fps": fps,
    }


def clip_data(clip: str) -> dict[str, pd.DataFrame]:
    """Every per-clip table of the review page; empty frames where a stage hasn't run."""
    out = {"clip": sql("SELECT * FROM clips WHERE clip = ?", (clip,))}
    for t in TABLES:
        out[t] = sql(f"SELECT * FROM {t} WHERE clip = ?", (clip,))
    return out


def hand_lookup(clip: str) -> dict[int, list[dict]]:
    """frame → [{side, source, score, flags}] from the best hand file, for the 'This moment' panel."""
    p = ClipPaths(clip).hands_input()
    if not p.exists():
        return {}
    return {fr.frame: [{"side": h.side, "source": h.source, "score": h.score, "flags": h.flags}
                       for h in fr.hands] for fr in read_hands(p)}


def nearest_frame(frames: list[int], fps: float, t: float) -> int | None:
    if not frames:
        return None
    target = t * fps
    return min(frames, key=lambda f: abs(f - target))


def at(df: pd.DataFrame, t: float, start: str = "t_start", end: str = "t_end") -> pd.DataFrame:
    """Rows whose [start, end) interval contains t (end inclusive for the last row)."""
    if df.empty:
        return df
    return df[(df[start] <= t) & ((t < df[end]) | ((t == df[end]) & (df[end] == df[end].max())))]


def flagged_runs(frames: pd.DataFrame, gap_s: float = 0.5) -> pd.DataFrame:
    """Merge consecutive flagged frames (same flags, < gap_s apart) into runs for the Flagged tab."""
    f = frames[frames["flags"].fillna("") != ""].sort_values("t")
    runs = []
    for r in f.itertuples():
        if runs and r.flags == runs[-1]["flags"] and r.t - runs[-1]["t_end"] < gap_s:
            runs[-1]["t_end"] = r.t
            runs[-1]["frames"] += 1
        else:
            runs.append({"t_start": r.t, "t_end": r.t, "flags": r.flags, "frames": 1})
    return pd.DataFrame(runs, columns=["t_start", "t_end", "flags", "frames"])
