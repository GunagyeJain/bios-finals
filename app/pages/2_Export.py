"""G4 · owner: Gunagye. Export: build a robot dataset from usable footage. ui-design.md §4.
Calls the same functions as `python -m egovision export` (products/export.py)."""
import json
import re
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from components import kpi_strip, mmss, num, title
from egovision import config
from egovision.index import query
from egovision.products.episodes import select
from egovision.products.export import export, preview

SCAN_MIN_PER_CLIP = 2.0     # measured: the whole-clip face scan plus decode, about 2 min per 3-min clip
LONG_BUILD_MIN = 15

if not query.has_index():
    title("Export", "No clips indexed yet.")
    st.html('<div class="ev-empty">Process and index clips first; the dataset is built from the index.</div>')
    st.stop()

@st.cache_data(show_spinner="Planning episodes from the index…")
def planned(light: str, index_mtime: float):
    """Every episode for this light; filters only trim this table, so changing them is instant."""
    return preview(light)


lib = query.library()
title("Export", "A robot dataset from usable footage only: episodes of at least 3 s, cut at step boundaries, "
                "faces blurred, red seconds never included.")

c1, c2, c3, c4, c5, c6 = st.columns([2, 2.2, 2.4, 1.6, 2, 2])
name = c1.text_input("Dataset name", value="demo_v1")
light = c2.radio("Light", ["green", "yellow"], format_func={"green": "Green only", "yellow": "Green + yellow"}.get,
                 horizontal=True)
factories = c3.multiselect("Factories", sorted(lib["factory"].unique()), placeholder="All factories")
grips = c4.multiselect("Grip", ["2f", "5f", "generic", "unsure"], placeholder="Any grip")
robot = c5.selectbox("Robot hand", [None, "2f", "5f"], format_func={None: "Any", "2f": "2-finger can copy",
                                                                   "5f": "5-finger can copy"}.get)
task = c6.text_input("Task contains", placeholder="e.g. fasten")
clips = st.multiselect("Clips", lib["clip"].tolist(), placeholder="All clips that pass the filters above")

eps = select(planned(light, config.INDEX_DB.stat().st_mtime), factories or None, grips or None, task, robot,
             clips or None)
secs = float((eps["t_end"] - eps["t_start"]).sum()) if not eps.empty else 0.0
fps = 15.0
kpi_strip([
    ("Episodes", num(len(eps)), "usable stretches of 3 s or more"),
    ("Duration", num(mmss(secs)), "minutes of two-hand tracks"),
    ("Frames", num(f"{int(secs * fps):,}"), f"at {fps:.0f} frames per second"),
    ("Tasks", num(eps["task"].nunique() if not eps.empty else 0), "from steps, else held object"),
    ("Clips", num(eps["clip"].nunique() if not eps.empty else 0), f"of {len(lib)} indexed"),
    ("Red seconds", num(0), "never exported"),
])

left, right = st.columns([3, 1], vertical_alignment="center")
if eps.empty:
    left.html('<div class="ev-empty">No usable stretch matches these filters. Try green + yellow, or fewer '
              'filters. Clips that are not graded yet only count as yellow.</div>')
else:
    left.caption(f"Preview of the first {min(len(eps), 8)} of {len(eps)} episodes")
    show = eps.head(8).assign(start=lambda d: d["t_start"].map(mmss), end=lambda d: d["t_end"].map(mmss),
                              length=lambda d: (d["t_end"] - d["t_start"]).map(lambda s: f"{s:.1f} s"),
                              grips=lambda d: d["grip_types"].map(lambda g: ", ".join(g) or "—"))
    left.dataframe(show[["clip", "start", "end", "length", "task", "grips"]], hide_index=True, width="stretch")
n_clips = eps["clip"].nunique() if not eps.empty else 0
est = n_clips * SCAN_MIN_PER_CLIP
build = right.button("Build dataset", type="primary", disabled=eps.empty or not name.strip(), width="stretch")
if n_clips:
    right.caption(f"About {est:.0f} min for {n_clips} clip{'s' if n_clips > 1 else ''} (faces are found and "
                  f"blurred in each one). The page waits until it is done.")
if est > LONG_BUILD_MIN:
    right.warning(f"That is a long build. Narrow the filters (one factory, or a task) for a demo set.")

if build:
    with st.spinner(f"Writing exports/{name} (blurring faces in every episode video)…"):
        try:
            st.session_state.last_export = export(name.strip(), light, factories or None, grips or None, task,
                                                  robot=robot, clips=clips or None)
        except ValueError as e:
            st.error(str(e))

products = query.sql("SELECT name, path, filter_json, n_items, created_at FROM products WHERE kind = 'dataset' "
                     "ORDER BY created_at DESC")
products = products[products["path"].map(lambda x: Path(x).exists())].drop_duplicates("name")
if not products.empty:
    st.html('<h2 class="ev-h2">Built datasets</h2>')
    just = (st.session_state.get("last_export") or {}).get("name")
    names = products["name"].tolist()
    pick = st.radio("Dataset", names, index=names.index(just) if just in names else 0, horizontal=True,
                    format_func=lambda n: f"{n} · {products.set_index('name').loc[n, 'n_items']} episodes",
                    label_visibility="collapsed")
    row = products.set_index("name").loc[pick]
    root = Path(row["path"])
    info = json.loads((root / "meta" / "info.json").read_text(encoding="utf-8"))
    st.html(f'<div class="ev-panel" style="margin-top:12px"><h3>{escape(pick)}</h3>'
            f'<p style="color:#8b96ab;margin:0"><span class="ev-num">{info.get("total_episodes", row["n_items"])}'
            f'</span> episodes · <span class="ev-num">{info.get("total_frames", 0):,}</span> frames · '
            f'<span class="ev-num">{info.get("total_tasks", "—")}</span> tasks · built {escape(row["created_at"])} · '
            f'<code>{escape(str(root))}</code></p></div>')
    sheet, data = st.tabs(["Data sheet", "First episode (parquet)"])
    with sheet:
        md = (root / "datasheet.md").read_text(encoding="utf-8")
        st.markdown(re.sub(r"^(#{1,2}) ", lambda m: "#" * (len(m.group(1)) + 2) + " ", md, flags=re.M))
    with data:
        first = pd.read_parquet(root / "data" / "chunk-000" / "episode_000000.parquet")
        st.caption(f"{len(first)} rows × {len(first.columns)} columns · `pd.read_parquet(...)`")
        st.dataframe(first.head(20), hide_index=True, width="stretch")
