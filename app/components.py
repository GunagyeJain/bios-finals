"""Shared Streamlit helpers (ui-design.md §1). Owner: Gunagye. Data comes from egovision.index.query."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

LIGHT = {"green": "#2E9E5B", "yellow": "#E0A800", "red": "#D64545"}
LIGHT_EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
HAND = {"left": "#3BA3FF", "right": "#FF8A3B"}
CONTACT_OPACITY = {"portable": 1.0, "fixed": 0.45}
ALERT = {"safety": "#D64545", "step_missing": "#E0A800", "step_order": "#E0A800", "step_extra": "#9A9A9A"}
ROWS = ["Light", "Left", "Right", "Steps", "Alerts"]


def mmss(s: float) -> str:
    s = max(0, int(round(s)))
    return f"{s // 60}:{s % 60:02d}"


def pct(v) -> str:
    return "–" if v is None or pd.isna(v) else f"{100 * v:.0f}%"


def kpi_row(items: list[tuple[str, str, str]]) -> None:
    """items: (label, value with unit, how it was measured)."""
    for col, (label, value, help_) in zip(st.columns(len(items)), items):
        col.metric(label, value, help=help_)


def light_bar(segments: pd.DataFrame, duration: float, height: int = 14) -> None:
    """Thin stacked bar of the clip's light over time (grey = not graded)."""
    if segments.empty or not duration:
        st.caption("Light: not graded yet (quality stage)")
        return
    parts = "".join(
        f'<div title="{mmss(r.t_start)}–{mmss(r.t_end)} {r.light} {r.reasons or ""}" '
        f'style="flex:{r.t_end - r.t_start};background:{LIGHT.get(r.light, "#555")}"></div>'
        for r in segments.sort_values("t_start").itertuples())
    st.markdown(f'<div style="display:flex;height:{height}px;border-radius:3px;overflow:hidden">{parts}</div>',
                unsafe_allow_html=True)


def _bars(fig: go.Figure, df: pd.DataFrame, row: str, start: str, end: str, color, text=None, hover=None,
          opacity=None) -> None:
    if df.empty:
        return
    fig.add_bar(y=[row] * len(df), x=(df[end] - df[start]).clip(lower=0.15), base=df[start], orientation="h",
                marker=dict(color=color, opacity=opacity if opacity is not None else 1.0, line_width=0),
                text=text, textposition="inside", insidetextanchor="start", textfont_size=11,
                customdata=df[start], hovertext=hover, hoverinfo="text", showlegend=False)


def event_timeline(d: dict[str, pd.DataFrame], duration: float, t: float) -> go.Figure:
    """One Plotly figure, rows Light / Left / Right / Steps / Alerts. customdata = start time (s)."""
    fig = go.Figure()
    fig.add_scatter(x=[0] * len(ROWS), y=ROWS, mode="markers", marker_opacity=0, hoverinfo="skip",
                    showlegend=False)                     # keeps every row visible when it is empty
    seg = d["segments"]
    _bars(fig, seg, "Light", "t_start", "t_end", [LIGHT.get(v, "#555") for v in seg["light"]],
          hover=[f"{mmss(a)} {li} {r or ''}" for a, li, r in zip(seg["t_start"], seg["light"], seg["reasons"])])
    for side in ("left", "right"):
        c = d["contacts"][d["contacts"]["hand"] == side]
        _bars(fig, c, side.title(), "t_start", "t_end", HAND[side],
              opacity=[CONTACT_OPACITY.get(s, 1.0) for s in c["state"]],
              hover=[f"{mmss(a)}–{mmss(b)} {st_} · {o}" for a, b, st_, o in
                     zip(c["t_start"], c["t_end"], c["state"], c["object_name"])])
    s = d["steps"]
    _bars(fig, s, "Steps", "start_s", "end_s", "#7C8799", text=s["verb"],
          hover=[f"{mmss(a)} {v} {o} ({h})" for a, v, o, h in zip(s["start_s"], s["verb"], s["object"], s["hand"])])
    a = d["alerts"]
    _bars(fig, a, "Alerts", "t_start", "t_end", [ALERT.get(k, "#999") for k in a["kind"]],
          text=["⛑" if k == "safety" else "⚠" for k in a["kind"]],
          hover=[f"{mmss(x)} {k}: {det}" for x, k, det in zip(a["t_start"], a["kind"], a["detail"])])
    fig.add_vline(x=t, line_color="#FFFFFF", line_width=2)
    fig.update_layout(barmode="overlay", height=230, margin=dict(l=0, r=0, t=4, b=0), bargap=0.25,
                      clickmode="event+select", dragmode=False, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)")
    fig.update_yaxes(categoryorder="array", categoryarray=ROWS[::-1], fixedrange=True)
    fig.update_xaxes(range=[0, duration], fixedrange=True, ticksuffix=" s", showgrid=False)
    return fig


def video_at(path: Path, t: float) -> None:
    st.video(str(path), start_time=int(t))
