"""Shared Streamlit helpers (ui-design.md §1). Owner: Gunagye. Data comes from egovision.index.query;
these functions only draw. Every dynamic string goes through html.escape before it reaches markup."""
from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

CSS = Path(__file__).with_name("style.css")
LIGHT = {"green": "#44a282", "yellow": "#d9a441", "red": "#e5566f"}
LIGHT_WORD = {"green": "Usable", "yellow": "Check", "red": "Unusable"}
HAND = {"left": "#4a8ad6", "right": "#f2f2f3"}
MUTED, RULE, GRID, ACCENT, NONE = "#8a8c92", "#1b1a1f", "#2b2b2e", "#4a8ad6", "#2c2c30"
ALERT = {"safety": "#e5566f", "step_missing": "#d9a441", "step_order": "#d9a441", "step_extra": "#8a8c92"}
ROWS = ["Light", "Left", "Right", "Steps", "Alerts"]
MONO = "IBM Plex Mono, monospace"
PAGES = [("library", "Library"), ("review", "Clip review"), ("export", "Export"), ("metrics", "Metrics")]
MARK = ('<span class="ev-mark" aria-hidden="true"><span style="background:#44a282"></span>'
        '<span style="background:#d9a441"></span><span style="background:#e5566f"></span></span>')


# ---------- formatting ----------
def mmss(s: float, tenths: bool = False) -> str:
    s = max(0.0, float(s))
    if tenths:
        return f"{int(s // 60)}:{s % 60:04.1f}"
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


def pct(v) -> str:
    return "—" if v is None or pd.isna(v) else f"{100 * v:.0f}%"


def num(v, unit: str = "") -> str:
    if v is None or pd.isna(v):
        return '<span class="dim">—</span>'
    return f"{v}{f'<small>{unit}</small>' if unit else ''}"


# ---------- shell ----------
def setup(title: str) -> None:
    st.set_page_config(page_title=f"{title} · EgoVision", layout="wide", initial_sidebar_state="collapsed")
    st.html(f"<style>{CSS.read_text(encoding='utf-8')}</style>")


def top_bar(current: str, scope: str, pages: dict) -> None:
    """Mark + product + scope on the left, the five screens on the right; the current one underlined."""
    cols = st.container(key="topbar").columns([5] + [1.2] * len(PAGES), vertical_alignment="center")
    cols[0].html(f'<div class="ev-brand">{MARK}<b>EgoVision</b><span>{escape(scope)}</span></div>')
    for col, (key, label) in zip(cols[1:], PAGES):
        if key == current:
            col.html(f'<span class="ev-nav-active">{label}</span>')
        else:
            col.page_link(pages[key], label=label)
    st.html('<div class="ev-topbar-rule"></div>')


def title(h1: str, sub: str) -> None:
    """sub may hold markup built by the caller from escaped values."""
    st.html(f'<div class="ev-title"><h1>{escape(h1)}</h1><p>{sub}</p></div>')


def kpi_strip(items: list[tuple[str, str, str]]) -> None:
    """One container split by 1px rules. items: (label, value html, subline)."""
    cells = "".join(f'<div class="ev-kpi"><div class="l">{escape(lab)}</div><div class="v">{val}</div>'
                    f'<div class="s">{escape(sub)}</div></div>' for lab, val, sub in items)
    st.html(f'<div class="ev-kpis" style="--n:{len(items)}">{cells}</div>')


def legend(items: list[tuple[str, str, bool]]) -> str:
    return '<div class="ev-legend">' + "".join(
        f'<span><i class="{"dot" if dot else ""}" style="background:{c}"></i>{escape(t)}</span>'
        for t, c, dot in items) + "</div>"


# ---------- the quality strip (signature element) ----------
def strip(segments: pd.DataFrame, duration: float) -> str:
    """The clip's seconds as a film strip: green usable, yellow check, red unusable, grey not graded.
    Plain divs: st.html removes SVG."""
    if segments.empty or not duration:
        return '<div class="ev-strip" title="not graded yet"></div>'
    cells, last = [], 0.0
    for r in segments.sort_values("t_start").itertuples():
        if r.t_start > last:
            cells.append(f'<span style="flex:{r.t_start - last:.2f}"></span>')
        cells.append(f'<span style="flex:{r.t_end - r.t_start:.2f};background:{LIGHT.get(r.light, NONE)}"></span>')
        last = r.t_end
    if duration > last:
        cells.append(f'<span style="flex:{duration - last:.2f}"></span>')
    return f'<div class="ev-strip">{"".join(cells)}</div>'


# ---------- library ----------
def clip_table(lib: pd.DataFrame, segments: pd.DataFrame, review_url: str) -> None:
    head = ('<tr><th>Clip</th><th>Quality over time</th><th class="r">Usable</th><th class="r">Hands</th>'
            '<th class="r">Contacts</th><th class="r">Alerts</th><th class="r">Length</th></tr>')
    body = []
    for factory, grp in lib.groupby("factory", sort=False):
        graded = grp["green_share"].notna()
        usable = ((grp.loc[graded, "green_share"] * grp.loc[graded, "duration_s"]).sum()
                  / grp.loc[graded, "duration_s"].sum()) if graded.any() else None
        body.append(f'<tr class="grp"><td colspan="7"><b>{escape(str(factory))}</b>{len(grp)} clip{"s" if len(grp) != 1 else ""} · '
                    f'{pct(usable)} usable · {graded.sum()} graded</td></tr>')
        for r in grp.itertuples():
            seg = segments[segments["clip"] == r.clip]
            alerts = f'<span class="ev-pill red">{r.n_alerts}</span>' if r.n_alerts else '<span class="dim">0</span>'
            body.append(
                f'<tr class="row"><td><a href="{review_url}?clip={escape(r.clip)}" target="_self">{escape(r.clip)}</a>'
                f'{" <span class=dim>★ demo</span>" if r.is_demo else ""}</td>'
                f'<td class="strip">{strip(seg, r.duration_s)}</td>'
                f'<td class="r">{pct(r.green_share)}</td><td class="r">{pct(r.hands_found_share)}</td>'
                f'<td class="r">{r.n_contacts}</td><td class="r">{alerts}</td>'
                f'<td class="r">{mmss(r.duration_s)}</td></tr>')
    st.html(f'<div class="ev-panel" style="padding:4px 8px 8px"><table class="ev-table">{head}{"".join(body)}'
            '</table></div>')


# ---------- review ----------
def moment_panel(t: float, seg: pd.DataFrame, hands: dict, contacts: pd.DataFrame, step: pd.DataFrame,
                 alerts: pd.DataFrame) -> None:
    if seg.empty:
        colour, word, why = NONE, "Not graded", "quality stage has not run on this clip"
    else:
        r = seg.iloc[0]
        colour, word, why = LIGHT.get(r.light, NONE), LIGHT_WORD.get(r.light, r.light), (r.reasons or "").replace(";", " · ")
    rows = []
    for side in ("left", "right"):
        h = hands.get(side)
        val = (f'{escape(h["source"])} <span class="m">{h["score"]:.2f}</span>'
               + (f' <span class="dim">· {escape(", ".join(h["flags"]))}</span>' if h["flags"] else "")
               if h else '<span class="dim">not found</span>')
        rows.append(f'<div class="k"><i style="background:{HAND[side]}"></i>{side.title()}</div><div>{val}</div>')
    held = "; ".join(f'{c.hand.title()} · {escape(c.object_name)} <span class="dim">{c.state}</span>'
                     for c in contacts.itertuples()) or '<span class="dim">none</span>'
    rows.append(f'<div class="k">Contact</div><div>{held}</div>')
    rows.append('<div class="k">Step</div><div>' + (escape(step.iloc[0]["caption"]) if not step.empty
                                                     else '<span class="dim">—</span>') + "</div>")
    alert = "; ".join(escape(a.detail) for a in alerts.itertuples()) or '<span class="dim">none</span>'
    rows.append(f'<div class="k">Alert</div><div>{alert}</div>')
    st.html(f'<div class="ev-panel ev-moment"><div class="tc">This moment · {mmss(t, tenths=True)}</div>'
            f'<div class="answer"><i style="background:{colour}"></i>{escape(word)}</div>'
            f'<div class="why">{escape(why) or "&nbsp;"}</div><div class="ev-kv">{"".join(rows)}</div></div>')


def _tick_step(duration: float) -> float:
    for step in (1, 2, 5, 10, 15, 30, 60):
        if duration / step <= 8:
            return step
    return 120


def _bars(fig: go.Figure, df: pd.DataFrame, row: str, start: str, end: str, color, hover, text=None,
          opacity=None) -> None:
    if df.empty:
        return
    fig.add_bar(y=[row] * len(df), x=(df[end] - df[start]).clip(lower=0.2), base=df[start], orientation="h",
                width=0.62, marker=dict(color=color, opacity=opacity if opacity is not None else 1.0, line_width=0),
                text=text, textposition="inside", insidetextanchor="start",
                textfont=dict(size=11, color="#ffffff", family="Public Sans, sans-serif"), customdata=df[start], hovertext=hover,
                hoverinfo="text", showlegend=False)


def event_timeline(d: dict[str, pd.DataFrame], duration: float, t: float) -> go.Figure:
    """One figure, rows Light / Left / Right / Steps / Alerts on a shared time axis. customdata = start (s)."""
    fig = go.Figure()
    fig.add_scatter(x=[0] * len(ROWS), y=ROWS, mode="markers", marker_opacity=0, hoverinfo="skip",
                    showlegend=False)                     # keeps every row visible when it is empty
    seg = d["segments"]
    _bars(fig, seg, "Light", "t_start", "t_end", [LIGHT.get(v, NONE) for v in seg["light"]],
          [f"{mmss(a)}  {LIGHT_WORD.get(li, li)}  {(r or '').replace(';', ' · ')}"
           for a, li, r in zip(seg["t_start"], seg["light"], seg["reasons"])])
    for side in ("left", "right"):
        c = d["contacts"][d["contacts"]["hand"] == side]
        _bars(fig, c, side.title(), "t_start", "t_end", HAND[side],
              [f"{mmss(a)}–{mmss(b)}  {o}  ({s})" for a, b, s, o in
               zip(c["t_start"], c["t_end"], c["state"], c["object_name"])],
              opacity=[1.0 if s == "portable" else 0.45 for s in c["state"]])
    s = d["steps"]
    _bars(fig, s, "Steps", "start_s", "end_s", "#3a3a3e",
          [f"{mmss(a)}  {v} {o}  ({h})" for a, v, o, h in zip(s["start_s"], s["verb"], s["object"], s["hand"])],
          text=s["verb"])
    a = d["alerts"]
    _bars(fig, a, "Alerts", "t_start", "t_end", [ALERT.get(k, MUTED) for k in a["kind"]],
          [f"{mmss(x)}  {k.replace('_', ' ')}: {det}" for x, k, det in zip(a["t_start"], a["kind"], a["detail"])])
    step = _tick_step(duration)
    ticks = [i * step for i in range(int(duration // step) + 1)]
    fig.add_vline(x=t, line_color=ACCENT, line_width=1)
    fig.update_layout(barmode="overlay", height=212, margin=dict(l=0, r=8, t=4, b=0), bargap=0.3,
                      clickmode="event+select", dragmode=False, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Public Sans, sans-serif", color=MUTED, size=12),
                      hoverlabel=dict(bgcolor="#212023", bordercolor="#212023", font=dict(family=MONO, color="#fff", size=12)))
    fig.update_yaxes(categoryorder="array", categoryarray=ROWS[::-1], fixedrange=True, showgrid=True,
                     gridcolor=RULE, ticklabelstandoff=12, zeroline=False)
    fig.update_xaxes(range=[0, duration], fixedrange=True, tickvals=ticks, ticktext=[mmss(v) for v in ticks],
                     tickfont=dict(family=MONO, size=12), showgrid=True, gridcolor=GRID, griddash="dot",
                     zeroline=False, showline=False)
    return fig


def video_at(path: Path, t: float) -> None:
    st.video(str(path), start_time=int(t))
