"""G5 · owner: Gunagye. Library page. `streamlit run app/Home.py`. Spec: docs/05-solution/ui-design.md §2."""
import pandas as pd
import streamlit as st

from components import LIGHT_EMOJI, kpi_row, mmss, pct
from egovision.index import query

st.set_page_config(page_title="EgoVision Data Engine", layout="wide")
st.title("EgoVision Data Engine")

if not query.has_index():
    st.info("No index yet. Run `python -m egovision run --clip <id>` then `python -m egovision index`.")
    st.stop()


@st.cache_data(ttl=30)
def load() -> pd.DataFrame:
    return query.library()


lib = load()
k = query.kpis(lib)
kpi_row([
    ("Clips", f"{k['clips']} · {k['hours']:.1f} h", "Clips in outputs/index.db and their total duration"),
    ("Green time", pct(k["green"]), "Share of graded seconds that are green (usable), weighted by clip length"),
    ("Hands found", pct(k["hands"]), "Mean share of processed frames with at least one hand"),
    ("Speed", "–" if k["fps"] is None or pd.isna(k["fps"]) else f"{k['fps']:.1f} FPS",
     "Mean pipeline FPS on CPU from metrics.json"),
])

f1, f2, f3, f4 = st.columns([2, 1, 2, 2])
factories = f1.multiselect("Factory", sorted(lib["factory"].unique()))
demo_only = f2.checkbox("Demo only")
light = f3.selectbox("Light", ["All", "Mostly green (≥ 50 %)", "Has red", "Not graded"])
search = f4.text_input("Search clip")

view = lib
if factories:
    view = view[view["factory"].isin(factories)]
if demo_only:
    view = view[view["is_demo"] == 1]
if light == "Mostly green (≥ 50 %)":
    view = view[view["green_share"] >= 0.5]
elif light == "Has red":
    view = view[view["red_share"] > 0]
elif light == "Not graded":
    view = view[view["green_share"].isna()]
if search:
    view = view[view["clip"].str.contains(search, case=False, regex=False)]


def light_text(r) -> str:
    if pd.isna(r.green_share):
        return "not graded"
    return " · ".join(f"{LIGHT_EMOJI[li]} {100 * getattr(r, f'{li}_share'):.0f}" for li in ("green", "yellow", "red"))


table = pd.DataFrame({
    "clip": view["clip"], "factory": view["factory"], "duration": view["duration_s"].map(mmss),
    "green": view["green_share"], "light %": [light_text(r) for r in view.itertuples()],
    "hands": view["hands_found_share"], "alerts": view["n_alerts"],
    "demo": view["is_demo"].map({1: "★", 0: ""}),
})
st.caption(f"{len(table)} of {len(lib)} clips · select a row to open it")
event = st.dataframe(
    table, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
    key="library", column_config={
        "green": st.column_config.ProgressColumn("green", min_value=0, max_value=1, format="percent",
                                                 help="Share of the clip graded green"),
        "hands": st.column_config.NumberColumn("hands", format="percent",
                                               help="Share of processed frames with at least one hand"),
        "alerts": st.column_config.NumberColumn("alerts", help="Order + safety alerts"),
    })
if event.selection.rows:
    st.session_state.clip = table.iloc[event.selection.rows[0]]["clip"]
    st.session_state.t = 0.0
    st.switch_page("pages/1_Clip_review.py")
