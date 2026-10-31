"""G5 · owner: Gunagye. Clip review: is this second usable, and what are the hands doing? ui-design.md §3.
The synced player (player.py) holds video, timeline, light, "This moment" and the lists; this page adds the clip
picker and the detail tables."""
from html import escape

import pandas as pd
import streamlit as st

from components import mmss, pct, title
from egovision.index import query
from player import player

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


def open_clip(clip: str) -> None:
    st.session_state.clip = clip
    st.query_params["clip"] = clip
    st.rerun()


names = clips()
if not names:
    title("Clip review", "The index has no clips yet.")
    st.stop()
clip = st.session_state.get("clip") or st.query_params.get("clip") or names[0]
clip = clip if clip in names else names[0]
st.query_params["clip"] = clip

d = data(clip)
info = d["clip"].iloc[0]
duration, fps = float(info["duration_s"]), float(info["fps"])
i = names.index(clip)

# ---------- title row ----------
head, prev_c, pick, next_c = st.container(key="titlerow").columns([6, 0.5, 2.4, 0.5], vertical_alignment="bottom")
with head:
    usable = f'<b class="ev-num">{pct(info["green_share"])}</b> usable' if pd.notna(info["green_share"]) else "not graded"
    title(clip, f'{escape(info["factory"])} · <span class="ev-num">{mmss(duration)}</span> · {usable} · '
                f'<span class="ev-num">{len(d["contacts"])}</span> grabs · '
                f'<span class="ev-num">{len(d["steps"])}</span> steps · '
                f'<span class="ev-num">{len(d["alerts"])}</span> alerts')
if prev_c.button("←", help="Previous clip", disabled=i == 0, width="stretch"):
    open_clip(names[i - 1])
chosen = pick.selectbox("Clip", names, index=i, label_visibility="collapsed")
if chosen != clip:
    open_clip(chosen)
if next_c.button("→", help="Next clip", disabled=i == len(names) - 1, width="stretch"):
    open_clip(names[i + 1])

# ---------- synced player ----------
player(clip, d, fps, duration)


# ---------- details ----------
def sec(label: str):
    return st.column_config.NumberColumn(label, format="%.1f s")


def labels(**names: str) -> dict:
    return {k: (sec(v[:-2]) if v.endswith(" s") else v) for k, v in names.items()}


TIMES = labels(t_start="Start s", t_end="End s")
steps_tab, safety_tab, flag_tab, quality_tab = st.tabs(
    ["Steps", "Safety", "Flagged frames", "Quality numbers"])
with steps_tab:
    s = d["steps"]
    if s.empty:
        st.html('<div class="ev-empty">Steps are not processed for this clip yet.</div>')
    else:
        st.dataframe(s[["step_idx", "start_s", "end_s", "verb", "object", "hand", "caption", "cycle_idx"]],
                     hide_index=True, width="stretch",
                     column_config=labels(step_idx="#", start_s="Start s", end_s="End s", verb="Verb", object="Object",
                                          hand="Hand", caption="Caption", cycle_idx="Cycle"))
        from egovision.steps import order as order_mod
        if hasattr(order_mod, "save_reference") and st.button(f"Mark as reference for {info['factory']}"):
            order_mod.save_reference(clip)
            st.success("Saved as the reference cycle for this factory. Re-run the order check to use it.")
with safety_tab:
    a = d["alerts"][d["alerts"]["kind"] == "safety"]
    if a.empty:
        st.html('<div class="ev-empty">No safety alerts for this clip, or the safety stage has not run.</div>')
    else:
        st.dataframe(a[["t_start", "t_end", "hand", "severity", "detail"]], hide_index=True, width="stretch",
                     column_config={**TIMES, **labels(hand="Hand", severity="Severity", detail="What happened")})
with flag_tab:
    runs = query.flagged_runs(d["frame_summary"])
    if runs.empty:
        st.html('<div class="ev-empty">No frames flagged by the hand pipeline.</div>')
    else:
        st.dataframe(runs, hide_index=True, width="stretch",
                     column_config={**TIMES, **labels(flags="Flags", frames="Frames")})
with quality_tab:
    q = d["segments"]
    if q.empty:
        st.html('<div class="ev-empty">Quality is not processed for this clip yet.</div>')
    else:
        st.dataframe(q.drop(columns=["clip"]), hide_index=True, width="stretch",
                     column_config={**TIMES, **labels(light="Light", reasons="Reasons", blur="Blur",
                                                      brightness="Brightness", hands_visible="Hands visible",
                                                      edge_cut="Edge cut", agreement="Agreement", frozen="Frozen")})
