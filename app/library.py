"""G5 · owner: Gunagye. Library: which clips give usable robot data, and where. ui-design.md §2."""
from html import escape

import pandas as pd
import streamlit as st

from components import clip_table, kpi_strip, num, pct, title
from egovision.index import query

if not query.has_index():
    title("Library", "No clips indexed yet.")
    st.html('<div class="ev-empty">Run <code>python -m egovision run --clip &lt;id&gt;</code>, then '
            '<code>python -m egovision index</code>.</div>')
    st.stop()


@st.cache_data(ttl=30)
def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    return query.library(), query.all_segments()


lib, segments = load()
k = query.kpis(lib)
graded = int(lib["green_share"].notna().sum())
worst = lib.dropna(subset=["red_share"]).sort_values("red_share", ascending=False).head(1)
finding = (f' · most unusable: <b class="ev-num">{escape(worst.iloc[0]["clip"])}</b> '
           f'<span class="ev-num">{pct(worst.iloc[0]["red_share"])}</span> red' if len(worst) else "")

left, right = st.columns([5, 1], vertical_alignment="bottom")
with left:
    title("Library", f'<b class="ev-num">{pct(k["green"])}</b> of graded footage is usable · '
                     f'<span class="ev-num">{graded}</span> of <span class="ev-num">{len(lib)}</span> clips graded'
                     + finding)
right.page_link("pages/2_Export.py", label="Build a dataset →")

kpi_strip([
    ("Clips", num(len(lib)), f"{lib['factory'].nunique()} factories"),
    ("Footage", num(f"{k['hours']:.1f}", "h"), f"{lib['duration_s'].median() / 60:.0f} min per clip"),
    ("Usable", num(pct(k["green"])), "of graded seconds"),
    ("Hands found", num(pct(k["hands"])), "processed frames with a hand"),
    ("Contacts", num(f"{int(lib['n_contacts'].sum()):,}"), "grab-to-release intervals"),
    ("Speed", num(None if k["fps"] is None or pd.isna(k["fps"]) else f"{k['fps']:.1f}", "FPS"), "pipeline on CPU"),
])

f1, f2, f3, _ = st.columns([2, 2, 2, 3])
factory = f1.selectbox("Factory", ["All factories"] + sorted(lib["factory"].unique()), label_visibility="collapsed")
light = f2.selectbox("Light", ["Any quality", "Has unusable seconds", "Mostly usable (≥ 50 %)", "Not graded"],
                     label_visibility="collapsed")
search = f3.text_input("Search", placeholder="Search clip", label_visibility="collapsed")

view = lib
if factory != "All factories":
    view = view[view["factory"] == factory]
if light == "Has unusable seconds":
    view = view[view["red_share"] > 0]
elif light == "Mostly usable (≥ 50 %)":
    view = view[view["green_share"] >= 0.5]
elif light == "Not graded":
    view = view[view["green_share"].isna()]
if search:
    view = view[view["clip"].str.contains(search, case=False, regex=False)]

if view.empty:
    st.html('<div class="ev-empty">No clip matches these filters.</div>')
else:
    clip_table(view, segments, "review")
