"""G5 · owner: Gunagye. Clip review. Spec: docs/05-solution/ui-design.md §3."""
import pandas as pd
import streamlit as st

from components import HAND, LIGHT_EMOJI, event_timeline, light_bar, mmss, video_at
from egovision.index import query
from egovision.schema import ClipPaths

st.set_page_config(page_title="Clip review · EgoVision", layout="wide")

if not query.has_index():
    st.info("No index yet. Run `python -m egovision run --clip <id>` then `python -m egovision index`.")
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


def new_event(key: str, value) -> bool:
    """Selections persist across reruns; act on each click only once."""
    if value and st.session_state.get(f"_seen_{key}") != value:
        st.session_state[f"_seen_{key}"] = value
        return True
    return False


names = clips()
if not names:
    st.info("Index is empty. Process a clip first.")
    st.stop()
clip = st.session_state.get("clip") or st.query_params.get("clip") or names[0]
clip = clip if clip in names else names[0]
st.session_state.setdefault("t", 0.0)

d = data(clip)
info = d["clip"].iloc[0]
duration, fps = float(info["duration_s"]), float(info["fps"])
p = ClipPaths(clip)

head, pick, mode_col = st.columns([4, 2, 2])
head.subheader(f"{clip} · {info['factory']}" + (" · ★ demo clip" if info["is_demo"] else ""))
chosen = pick.selectbox("Clip", names, index=names.index(clip), label_visibility="collapsed")
if chosen != clip:
    st.session_state.clip, st.session_state.t = chosen, 0.0
    st.rerun()
mode = mode_col.segmented_control("View", ["Baseline", "Ours"], default="Ours", label_visibility="collapsed")
st.query_params["clip"] = clip
t = min(float(st.session_state.t), duration)

# ---------- video + this moment ----------
vid_col, moment_col = st.columns([3, 2])
with vid_col:
    render = p.render_baseline if mode == "Baseline" else p.render
    if render.exists():
        video_at(render, t)
    else:
        st.warning(f"`{render.name}` not rendered yet (G6). Showing the source clip, which may not play in "
                   "every browser.")
        if p.video.exists():
            video_at(p.video, t)
    new_t = st.slider("Time (s)", 0.0, duration, t, step=0.5, format="%.1f s")
    if new_t != t:
        jump(new_t)

with moment_col:
    st.markdown(f"**This moment · {mmss(t)}**")
    seg = query.at(d["segments"], t)
    if seg.empty:
        st.write("Light: not graded yet")
    else:
        r = seg.iloc[0]
        st.write(f"Light: {LIGHT_EMOJI.get(r.light, '')} {r.light}" + (f" · {r.reasons}" if r.reasons else ""))
    h = hands(clip)
    frame = query.nearest_frame(list(h), fps, t)
    present = {x["side"]: x for x in h.get(frame, [])} if frame is not None else {}
    for side in ("left", "right"):
        x = present.get(side)
        dot = f'<span style="color:{HAND[side]}">●</span>'
        text = (f"{x['source']} {x['score']:.2f}" + (f" · {', '.join(x['flags'])}" if x["flags"] else " ✓")
                if x else "missing")
        st.markdown(f"{dot} {side.title()}: {text}", unsafe_allow_html=True)
    now = query.at(d["contacts"], t)
    st.write("Contact: " + ("; ".join(f"{r.hand[0].upper()} holds {r.object_name} ({r.state})"
                                      for r in now.itertuples()) or "none"))
    step = query.at(d["steps"], t, "start_s", "end_s")
    if not step.empty:
        st.write(f"Step: {step.iloc[0]['caption']}")
    for r in query.at(d["alerts"], t).itertuples():
        st.write(f"{'⛑' if r.kind == 'safety' else '⚠'} {r.detail}")

# ---------- timeline ----------
light_bar(d["segments"], duration)
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
def table_jump(df: pd.DataFrame, key: str, time_col: str, **kw) -> None:
    ev = st.dataframe(df, hide_index=True, width="stretch", on_select="rerun",
                      selection_mode="single-row", key=key, **kw)
    rows = ev.selection.rows
    if rows and new_event(key, rows[0]):
        jump(df.iloc[rows[0]][time_col])


steps_tab, safety_tab, flag_tab, quality_tab = st.tabs(["Steps", "Safety", "Flagged frames", "Quality numbers"])
with steps_tab:
    s = d["steps"]
    if s.empty:
        st.info("Steps not processed yet (S2).")
    else:
        order = d["alerts"][d["alerts"]["kind"].str.startswith("step_")]
        for r in order.itertuples():
            st.warning(f"⚠ {mmss(r.t_start)}–{mmss(r.t_end)} · {r.detail}")
        table_jump(s[["step_idx", "start_s", "end_s", "verb", "object", "hand", "caption", "cycle_idx"]],
                   "steps_table", "start_s")
        from egovision.steps import order as order_mod
        if hasattr(order_mod, "save_reference"):
            if st.button(f"Mark as reference for {info['factory']}"):
                order_mod.save_reference(clip)
                st.success("Saved as the reference cycle for this factory.")
with safety_tab:
    a = d["alerts"][d["alerts"]["kind"] == "safety"]
    if a.empty:
        st.info("No safety alerts for this clip (or safety stage not run yet).")
    else:
        table_jump(a[["t_start", "t_end", "hand", "severity", "detail"]], "safety_table", "t_start")
with flag_tab:
    runs = query.flagged_runs(d["frame_summary"])
    if runs.empty:
        st.info("No flagged frames.")
    else:
        st.caption("Frames the hand pipeline flagged (low confidence, disagreement, sanity, edge). Select to jump.")
        table_jump(runs, "flag_table", "t_start")
with quality_tab:
    q = d["segments"]
    if q.empty:
        st.info("Quality not processed yet (B3).")
    else:
        table_jump(q.drop(columns=["clip"]), "quality_table", "t_start")
