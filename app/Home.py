"""G5 · owner: Gunagye. App entry point: `streamlit run app/Home.py`. Spec: docs/05-solution/ui-design.md.

Routes the five screens and draws the shared top bar; each screen lives in its own file."""
import streamlit as st

from components import setup, top_bar
from egovision.index import query

PAGES = {
    "library": st.Page("library.py", title="Library", default=True),
    "review": st.Page("pages/1_Clip_review.py", title="Clip review", url_path="review"),
    "export": st.Page("pages/2_Export.py", title="Export", url_path="export"),
    "modules": st.Page("pages/3_Work_modules.py", title="Work modules", url_path="modules"),
    "metrics": st.Page("pages/4_Metrics.py", title="Metrics", url_path="metrics"),
}
page = st.navigation(list(PAGES.values()), position="hidden")
setup(page.title)


@st.cache_data(ttl=30)
def scope() -> str:
    if not query.has_index():
        return "no clips indexed"
    lib = query.library()
    return f"Factory footage · {lib['factory'].nunique()} factories · {len(lib)} clips"


top_bar(next(k for k, p in PAGES.items() if p.title == page.title), scope(), PAGES)
page.run()
