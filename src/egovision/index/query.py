"""Read-only queries over outputs/index.db for the app pages (G5, S5). No Streamlit here, so it is
testable; pages cache the results. Owner: Gunagye."""
from __future__ import annotations

import sqlite3
from contextlib import closing

import pandas as pd

from egovision import config
from egovision.schema import ClipPaths, read_hands

TABLES = ("segments", "contacts", "steps", "alerts", "frame_summary")
ROBOT_CAN_COPY = {"2f": {"2f", "generic"}, "5f": {"2f", "5f", "generic"}}   # grips each robot hand can copy


def has_index() -> bool:
    return config.INDEX_DB.exists()


def sql(query: str, params: tuple = ()) -> pd.DataFrame:
    with closing(sqlite3.connect(config.INDEX_DB)) as db:
        return pd.read_sql_query(query, db, params=params)


def library() -> pd.DataFrame:
    """One row per clip with alert counts, for the Library table."""
    return sql("""SELECT c.*, COALESCE(a.n, 0) AS n_alerts, COALESCE(k.n, 0) AS n_contacts FROM clips c
                  LEFT JOIN (SELECT clip, COUNT(*) AS n FROM alerts GROUP BY clip) a USING (clip)
                  LEFT JOIN (SELECT clip, COUNT(*) AS n FROM contacts GROUP BY clip) k USING (clip)
                  ORDER BY c.factory, c.seq_in_factory, c.clip""")


def all_segments() -> pd.DataFrame:
    """Light segments of every clip, for the Library's quality strips."""
    return sql("SELECT clip, t_start, t_end, light FROM segments ORDER BY clip, t_start")


def kpis(lib: pd.DataFrame) -> dict[str, float | None]:
    """Library KPIs. Shares are weighted by clip duration; NaN where nothing is processed yet."""
    dur = lib["duration_s"]
    has_q = lib["green_share"].notna()
    fps = sql("SELECT AVG(value) AS v FROM metrics WHERE key = 'fps.hands'")["v"].iloc[0]
    return {
        "clips": len(lib),
        "hours": dur.sum() / 3600,
        "green": (lib.loc[has_q, "green_share"] * dur[has_q]).sum() / dur[has_q].sum() if has_q.any() else None,
        "hands": lib["hands_found_share"].mean() if lib["hands_found_share"].notna().any() else None,
        "fps": fps,
    }


def robot_fit(contacts: pd.DataFrame) -> dict:
    """Share of grabs a 2-finger and a 5-finger robot can copy; 'unsure' grabs count as not copyable."""
    n = len(contacts)
    if not n:
        return {"2f": None, "5f": None, "unsure": None, "grabs": 0}
    grips = contacts["grip"].fillna("unsure")
    return {**{robot: float(grips.isin(ok).mean()) for robot, ok in ROBOT_CAN_COPY.items()},
            "unsure": float((grips == "unsure").mean()), "grabs": n}


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


def light_runs(segments: pd.DataFrame, light: str) -> pd.DataFrame:
    """Merge touching segments of one light into stretches, longest first, with their reasons joined."""
    s = segments[segments["light"] == light].sort_values("t_start")
    runs = []
    for r in s.itertuples():
        reasons = {x for x in (r.reasons or "").split(";") if x}
        if runs and r.t_start - runs[-1]["t_end"] < 1e-6:
            runs[-1]["t_end"] = r.t_end
            runs[-1]["reasons"] |= reasons
        else:
            runs.append({"t_start": r.t_start, "t_end": r.t_end, "reasons": reasons})
    out = pd.DataFrame([{**r, "reasons": " · ".join(sorted(r["reasons"]))} for r in runs],
                       columns=["t_start", "t_end", "reasons"])
    return out.assign(length=out["t_end"] - out["t_start"]).sort_values("length", ascending=False, kind="stable")


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
