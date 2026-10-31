"""S5 (moved to Gunagye in sprint 2). Metrics: how much better than the baseline, and does the light grade
predict accuracy? ui-design.md §6. Reads outputs/<clip>/metrics.json (data-schema.md §1.3)."""
import json
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import LIGHT, MONO, MUTED, kpi_strip, mmss, num, title
from egovision.index import query
from egovision.schema import ClipPaths

SHARES = [("detection_recall", "Hands found"), ("detection_precision", "Detections that are hands"),
          ("lr_accuracy", "Left/right correct"), ("pck_0.2", "Keypoints within 20 %")]


@st.cache_data(ttl=30)
def load() -> list[dict]:
    if not query.has_index():
        return []
    out = []
    for clip in query.library()["clip"]:
        p = ClipPaths(clip).metrics
        if p.exists():
            out.append({"clip": clip, **json.loads(p.read_text(encoding="utf-8"))})
    real = [m for m in out if not m["clip"].startswith("fixture")]
    return real or out


def weighted(ms: list[dict], *path: str) -> float | None:
    """Mean over clips, weighted by labelled frames; None when no clip has the value."""
    vals = []
    for m in ms:
        v = m
        for k in path:
            v = v.get(k) if isinstance(v, dict) else None
        if isinstance(v, (int, float)):
            vals.append((float(v), m.get("n_labels", 1) or 1))
    return sum(v * w for v, w in vals) / sum(w for _, w in vals) if vals else None


def fmt(v, share=True, unit=""):
    if v is None:
        return "—"
    return f"{100 * v:.0f}%" if share else f"{v:.1f}{unit}"


def bars(rows: list[tuple[str, float | None, float | None]]) -> go.Figure:
    labels = [r[0] for r in rows]
    fig = go.Figure()
    for name, idx, colour in (("Baseline", 1, "#3a3a3e"), ("Ours", 2, "#4a8ad6")):
        vals = [r[idx] for r in rows]
        fig.add_bar(y=labels, x=vals, orientation="h", name=name, marker_color=colour,
                    text=[fmt(v) for v in vals], textposition="outside", textfont=dict(family=MONO, size=12),
                    hovertemplate="%{y}: %{x:.0%}<extra>" + name + "</extra>")
    return _style(fig, 60 * len(rows) + 40)


def _style(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(barmode="group", height=height, margin=dict(l=0, r=40, t=8, b=0), bargap=0.35,
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Public Sans, sans-serif", color=MUTED, size=12),
                      legend=dict(orientation="h", y=1.08, x=0, font=dict(size=12)))
    fig.update_xaxes(range=[0, 1.12], tickformat=".0%", tickvals=[0, 0.25, 0.5, 0.75, 1], gridcolor="#2b2b2e",
                     zeroline=False, tickfont=dict(family=MONO))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return fig


ms = load()
if not ms:
    title("Metrics", "No metrics yet.")
    st.html('<div class="ev-empty">Label frames, then run <code>python -m egovision.eval.metrics --clip &lt;id&gt;'
            '</code> (A5). This page reads <code>outputs/&lt;clip&gt;/metrics.json</code>.</div>')
    st.stop()

synthetic = all(m["clip"].startswith("fixture") for m in ms)
n_labels = sum(m.get("n_labels", 0) for m in ms)
partial = any(m.get("partial") for m in ms)
title("Metrics", f'Measured on <b class="ev-num">{n_labels}</b> hand-labelled frames from '
                 f'<b class="ev-num">{len(ms)}</b> clip{"s" if len(ms) != 1 else ""}'
                 + (" · partial: labelling still in progress" if partial else ""))
if synthetic:
    st.html('<div class="ev-empty" style="border-color:#d9a441;color:#d9a441;margin-bottom:16px">These are the '
            'synthetic fixture numbers, not measurements. Real numbers appear once A5 writes metrics.json for a '
            'real clip.</div>')


def kpi(key: str, label: str, share: bool = True, unit: str = "", lower_better: bool = False):
    o, b = weighted(ms, "ours", key), weighted(ms, "baseline", key)
    v = fmt(o, share, unit)
    sub = f"baseline {fmt(b, share, unit)}" if b is not None else "no baseline"
    if o is not None and b is not None:
        d = (o - b) * (100 if share else 1)
        better = d < 0 if lower_better else d > 0
        sub += f" · {'+' if d > 0 else ''}{d:.0f}{' pts' if share else unit} {'better' if better else 'worse'}"
    return (label, num(v), sub)


kpi_strip([kpi("detection_recall", "Hands found"), kpi("lr_accuracy", "Left/right correct"),
           kpi("pck_0.2", "Keypoints within 20 %"),
           kpi("swaps_per_min", "Side swaps", False, " /min", True), kpi("jitter_px", "Jitter", False, " px", True)])

left, right = st.columns([3, 2], gap="medium")
with left, st.container(border=True):
    st.html('<h3 style="font-size:16px;font-weight:600;margin:0">Baseline vs ours</h3>'
            '<p style="color:#8a8c92;font-size:12px;margin:2px 0 0">MediaPipe alone, then with tracking, side '
            'voting, gap fill and smoothing. Same labelled frames.</p>')
    st.plotly_chart(bars([(lab, weighted(ms, "baseline", k), weighted(ms, "ours", k)) for k, lab in SHARES]),
                    width="stretch", config={"displayModeBar": False})
with right, st.container(border=True):
    st.html('<h3 style="font-size:16px;font-weight:600;margin:0">Does the light predict accuracy?</h3>'
            '<p style="color:#8a8c92;font-size:12px;margin:2px 0 0">Keypoints within 20 % (ours) on frames graded '
            'green, yellow and red. If the light is right, red should score lowest.</p>')
    rows = [(li, weighted(ms, "per_light", li, "ours", "pck_0.2"),
             sum((m.get("per_light", {}).get(li, {}) or {}).get("n", 0) for m in ms)) for li in LIGHT]
    fig = go.Figure(go.Bar(x=[r[0].title() for r in rows], y=[r[1] for r in rows],
                           marker_color=[LIGHT[r[0]] for r in rows], text=[f"{fmt(r[1])}<br>n={r[2]}" for r in rows],
                           textposition="outside", textfont=dict(family=MONO, size=12),
                           hovertemplate="%{x}: %{y:.0%}<extra></extra>"))
    fig = _style(fig, 300)
    fig.update_xaxes(range=None, tickformat=None, tickvals=None, gridcolor=None, showgrid=False)
    fig.update_yaxes(range=[0, 1.15], tickformat=".0%", autorange=None, gridcolor="#2b2b2e", showgrid=True,
                     tickfont=dict(family=MONO))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

speed, check = st.columns([3, 2], gap="medium")
with speed, st.container(border=True):
    st.html('<h3 style="font-size:16px;font-weight:600;margin:0 0 8px">Speed on CPU</h3>')
    stages = sorted({k for m in ms for k in (m.get("fps") or {})})
    if stages:
        st.dataframe(pd.DataFrame({"stage": stages, "frames per second": [weighted(ms, "fps", s) for s in stages]}),
                     hide_index=True, width="stretch",
                     column_config={"frames per second": st.column_config.NumberColumn(format="%.1f")})
    hw = sorted({m.get("hardware") for m in ms if m.get("hardware")})
    st.caption("Hardware: " + (", ".join(hw) if hw else "not recorded"))
with check, st.container(border=True):
    st.html('<h3 style="font-size:16px;font-weight:600;margin:0 0 8px">Label check</h3>')
    pre, man, pf = (weighted(ms, "labels", k) for k in ("prefilled_share", "pck_manual", "pck_prefilled"))
    st.html('<div class="ev-kv" style="grid-template-columns:1fr auto;margin-top:0">'
            f'<div class="k">Labels started from a suggestion</div><div class="m">{fmt(pre)}</div>'
            f'<div class="k">Accuracy on hand-made labels</div><div class="m">{fmt(man)}</div>'
            f'<div class="k">Accuracy on suggested labels</div><div class="m">{fmt(pf)}</div></div>'
            '<p style="color:#8a8c92;font-size:12px;margin:8px 0 0">Every label was checked by a person. If the '
            'two accuracies match, the suggestions did not bias the numbers.</p>')

fails = [{"clip": m["clip"], "time": mmss(f.get("t", 0)), "what failed": f.get("what", ""), "why": f.get("why", "")}
         for m in ms for f in (m.get("failures") or [])]
st.html('<h3 style="font-size:16px;font-weight:600;margin:24px 0 8px">Where it still fails</h3>')
if fails:
    st.dataframe(pd.DataFrame(fails), hide_index=True, width="stretch")
else:
    st.html('<div class="ev-empty">No failure cases written yet (metrics.json → failures).</div>')
st.caption(" · ".join(escape(m["clip"]) for m in ms))
