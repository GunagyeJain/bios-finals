"""G5 · owner: Gunagye. Clip review: is this second usable, and what are the hands doing? ui-design.md §3."""
from html import escape

import pandas as pd
import streamlit as st

from components import (ACCENT, ALERT, HAND, LIGHT, event_timeline, legend, mmss, moment_panel, pct, title,
                        video_at)
from egovision.index import query
from egovision.schema import ClipPaths

if not query.has_index():
    title("Clip review", "No clips indexed yet.")
    st.html('<div class="ev-empty">Run <code>python -m egovision index</code> after processing a clip.</div>')
    st.stop()


@st.cache_data(ttl=30)
def clips() -> list[str]:
    return query.library()["clip"].tolist()


@st.cache_data(ttl=30)
def data(clip: str) -> dict:
    return query.clip_data(clip)


@st.cache_data
def hands(clip: str) -> dict:
    return query.hand_lookup(clip)


def jump(t: float) -> None:
    st.session_state.t = float(t)
    st.rerun()


def open_clip(clip: str) -> None:
    st.session_state.clip, st.session_state.t = clip, 0.0
    st.query_params["clip"] = clip
    st.rerun()


def new_event(key: str, value) -> bool:
    """Selections persist across reruns; act on each click only once."""
    if value is not None and st.session_state.get(f"_seen_{key}") != value:
        st.session_state[f"_seen_{key}"] = value
        return True
    return False


names = clips()
if not names:
    title("Clip review", "The index has no clips yet.")
    st.stop()
clip = st.session_state.get("clip") or st.query_params.get("clip") or names[0]
clip = clip if clip in names else names[0]
st.query_params["clip"] = clip
st.session_state.setdefault("t", 0.0)

d = data(clip)
info = d["clip"].iloc[0]
duration, fps = float(info["duration_s"]), float(info["fps"])
t = min(float(st.session_state.t), duration)
p = ClipPaths(clip)
i = names.index(clip)

# ---------- title row ----------
head, prev_c, pick, next_c, mode_c = st.container(key="titlerow").columns([5, 0.5, 2.2, 0.5, 1.8],
                                                                         vertical_alignment="bottom")
with head:
    usable = f'<b class="ev-num">{pct(info["green_share"])}</b> usable' if pd.notna(info["green_share"]) else "not graded"
    title(clip, f'{escape(info["factory"])} · <span class="ev-num">{mmss(duration)}</span> · {usable} · '
                f'<span class="ev-num">{len(d["contacts"])}</span> contacts · '
                f'<span class="ev-num">{len(d["alerts"])}</span> alerts')
if prev_c.button("←", help="Previous clip", disabled=i == 0, use_container_width=True):
    open_clip(names[i - 1])
chosen = pick.selectbox("Clip", names, index=i, label_visibility="collapsed")
if chosen != clip:
    open_clip(chosen)
if next_c.button("→", help="Next clip", disabled=i == len(names) - 1, use_container_width=True):
    open_clip(names[i + 1])
mode = mode_c.radio("View", ["Ours", "Baseline"], horizontal=True, label_visibility="collapsed")

# ---------- video + this moment ----------
vid, side = st.container(key="stage").columns([7, 5], gap="medium")
with vid:
    render = p.render_baseline if mode == "Baseline" else p.render
    if render.exists():
        video_at(render, t)
    else:
        st.html(f'<div class="ev-empty"><code>{render.name}</code> is not rendered yet, so this is the source clip '
                'without overlays. It may not play in every browser.</div>')
        if p.video.exists():
            video_at(p.video, t)
    new_t = st.slider("Time", 0.0, duration, t, step=0.5, format="%.1f s", label_visibility="collapsed")
    if new_t != t:
        jump(new_t)
with side:
    h = hands(clip)
    frame = query.nearest_frame(list(h), fps, t)
    by_side = {x["side"]: x for x in h.get(frame, [])} if frame is not None else {}
    moment_panel(t, query.at(d["segments"], t), by_side, query.at(d["contacts"], t),
                 query.at(d["steps"], t, "start_s", "end_s"), query.at(d["alerts"], t))
    with st.container(key="runs"):
        bad = query.light_runs(d["segments"], "red")
        st.html(f'<h3 style="font-size:16px;font-weight:600;margin:0 0 6px">Unusable stretches '
                f'<span class="ev-num" style="color:#8a8c92;font-weight:400">{len(bad)}</span></h3>')
        if d["segments"].empty:
            st.html('<div class="ev-empty">Not graded yet: the quality stage has not run on this clip.</div>')
        elif bad.empty:
            st.html('<div class="ev-empty">No unusable seconds in this clip.</div>')
        for k, r in enumerate(bad.head(5).itertuples()):
            if st.button(f"{mmss(r.t_start)}–{mmss(r.t_end)}   {r.length:.0f} s   {r.reasons or 'no reason'}",
                         key=f"run{k}"):
                jump(r.t_start)

# ---------- timeline ----------
with st.container(border=True):
    st.html('<div style="display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap">'
            '<h3 style="font-size:16px;font-weight:600;margin:0">Timeline</h3>'
            + legend([("Usable", LIGHT["green"], False), ("Check", LIGHT["yellow"], False),
                      ("Unusable", LIGHT["red"], False), ("Left hand holds", HAND["left"], True),
                      ("Right hand holds", HAND["right"], True), ("Now", ACCENT, False)])
            + '</div><p style="color:#8a8c92;font-size:12px;margin:4px 0 0">Click any bar to jump there. '
              'Faded contact bars are fixed objects (bench, machine).</p>')
    ev = st.plotly_chart(event_timeline(d, duration, t), width="stretch", on_select="rerun",
                         selection_mode="points", key="timeline", config={"displayModeBar": False})
    points = ev.selection.points if ev and ev.selection else []
    if points:
        pt = points[0]
        start = pt.get("customdata", pt.get("x"))
        start = start[0] if isinstance(start, list) else start
        if start is not None and new_event("timeline", (pt.get("curve_number"), pt.get("point_index"))):
            jump(start)


# ---------- tabs ----------
def table_jump(df: pd.DataFrame, key: str, time_col: str, config: dict | None = None) -> None:
    ev = st.dataframe(df, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
                      key=key, column_config=config)
    rows = ev.selection.rows
    if rows and new_event(key, rows[0]):
        jump(df.iloc[rows[0]][time_col])


def sec(label: str):
    return st.column_config.NumberColumn(label, format="%.1f s")


def labels(**names: str) -> dict:
    return {k: (sec(v[:-2]) if v.endswith(" s") else v) for k, v in names.items()}


TIMES = labels(t_start="Start s", t_end="End s")
steps_tab, safety_tab, flag_tab, quality_tab = st.tabs(
    [f"Steps {len(d['steps'])}", f"Safety {int((d['alerts']['kind'] == 'safety').sum())}",
     "Flagged frames", "Quality numbers"])
with steps_tab:
    s = d["steps"]
    if s.empty:
        st.html('<div class="ev-empty">Steps are not processed for this clip yet.</div>')
    else:
        order = d["alerts"][d["alerts"]["kind"].str.startswith("step_")]
        if not order.empty:
            st.html("".join(f'<div class="ev-kv" style="grid-template-columns:120px 1fr;margin:0 0 12px">'
                            f'<div class="m" style="color:{ALERT.get(a.kind)}">{mmss(a.t_start)}–{mmss(a.t_end)}'
                            f'</div><div>{escape(a.detail)}</div></div>' for a in order.itertuples()))
        table_jump(s[["step_idx", "start_s", "end_s", "verb", "object", "hand", "caption", "cycle_idx"]],
                   "steps_table", "start_s", labels(step_idx="#", start_s="Start s", end_s="End s", verb="Verb",
                                                    object="Object", hand="Hand", caption="Caption", cycle_idx="Cycle"))
        from egovision.steps import order as order_mod
        if hasattr(order_mod, "save_reference") and st.button(f"Mark as reference for {info['factory']}"):
            order_mod.save_reference(clip)
            st.success("Saved as the reference cycle for this factory.")
with safety_tab:
    a = d["alerts"][d["alerts"]["kind"] == "safety"]
    if a.empty:
        st.html('<div class="ev-empty">No safety alerts for this clip, or the safety stage has not run.</div>')
    else:
        table_jump(a[["t_start", "t_end", "hand", "severity", "detail"]], "safety_table", "t_start",
                   {**TIMES, **labels(hand="Hand", severity="Severity", detail="What happened")})
with flag_tab:
    runs = query.flagged_runs(d["frame_summary"])
    if runs.empty:
        st.html('<div class="ev-empty">No frames flagged by the hand pipeline.</div>')
    else:
        table_jump(runs, "flag_table", "t_start", {**TIMES, **labels(flags="Flags", frames="Frames")})
with quality_tab:
    q = d["segments"]
    if q.empty:
        st.html('<div class="ev-empty">Quality is not processed for this clip yet.</div>')
    else:
        table_jump(q.drop(columns=["clip"]), "quality_table", "t_start",
                   {**TIMES, **labels(light="Light", reasons="Reasons", blur="Blur", brightness="Brightness",
                                      hands_visible="Hands visible", edge_cut="Edge cut", agreement="Agreement",
                                      frozen="Frozen")})
