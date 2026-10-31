# UI design (Streamlit)

_Owner: Gunagye (shell, Library, Clip review, Export) · Shefali (Work Modules, Metrics pages). Flow: `app-flow.md`._

## 1. Rules
- Streamlit multipage: `app/Home.py` + `app/pages/1_Clip_review.py`, `2_Export.py`, `3_Work_modules.py`, `4_Metrics.py`.
- Reads only `outputs/index.db`, `hands.jsonl`, `render.mp4`. **Never runs the pipeline** (keeps the demo instant).
- Wide layout, dark theme (`.streamlit/config.toml`). One accent per light: 🟢 `#2E9E5B` · 🟡 `#E0A800` · 🔴 `#D64545`; hand colours left `#3BA3FF`, right `#FF8A3B`.
- Every number has a unit and a tooltip saying how it was measured.
- Shared helpers in `app/components.py`: `light_bar()`, `event_timeline()`, `video_at(t)`, `kpi_row()`.
- Slides use our own mock-ups only; no real frames in anything public.

## 2. Home = Library
```
┌ EgoVision Data Engine ─────────────────────────────────────────────┐
│ [20 clips] [62% green] [hands found 94%] [11.8 FPS on CPU]         │  kpi_row
├────────────────────────────────────────────────────────────────────┤
│ Factory ▾  Demo only ☐  Light ▾                         [Search]   │
│ clip         factory  dur   light share (bar)       hands  alerts  │
│ factory_001  F1       3:02  ██████████▒▒▒░          96%    2 ⚠     │
│ factory_002  F1       2:58  ███████▒▒▒░░░░          88%    0       │
│ ...                                        (click row → review)    │
└────────────────────────────────────────────────────────────────────┘
```

## 3. Clip review (main screen)
```
┌ factory_001 · F1 · demo clip ─────────────────── [Baseline | Ours] ┐
│ ┌──────────────────────────────┐  ┌ This moment ───────────────┐   │
│ │                              │  │ Light: 🔴 dark; hands_out   │   │
│ │      render.mp4 (overlay)    │  │ Left: wilor 0.81 ✓         │   │
│ │                              │  │ Right: missing (edge)      │   │
│ └──────────────────────────────┘  │ Contact: R holds drill     │   │
│ time slider ───────●──────────    └────────────────────────────┘   │
│ Light   ████████▒▒░░████████████▒▒██████   (click → jump)          │
│ Left    ──■■■■──────■■■■■■────■■──        grab/release bars        │
│ Right   ■■■■■■──■■■■──────■■■■■■■■                                 │
│ Steps   |pick bolt|fasten|place panel|inspect|                     │
│ Alerts        ⚠order       ⛑safety                                 │
├ Tabs: [Steps] [Safety] [Flagged frames] [Quality numbers] ─────────┤
│ Steps: # · start-end · verb · object · hand · caption · alert      │
│        [Mark as reference for F1]                                  │
└────────────────────────────────────────────────────────────────────┘
```
- Timeline = one Plotly figure, shared x-axis, 5 rows. Click sets `st.session_state.t`; video re-renders with `st.video(path, start_time=t)`.
- Baseline/Ours toggle swaps `render_baseline.mp4` / `render.mp4` (side-by-side optional).
- Flagged frames tab: table of times with flags; click → jump. No thumbnails saved to disk outside `outputs/`.

## 4. Export (hero)
```
┌ Build robot dataset ───────────────────────────────────────────────┐
│ Name [demo_v1]  Light [green ▾]  Factories [all ▾]                 │
│ Grip [2f ☐ 5f ☐ generic ☐]  Task contains [      ]                 │
│ Preview: 37 episodes · 14:20 min · 25 740 frames · 0 red           │
│ [Build dataset]                                                    │
│ ✓ exports/demo_v1/  · datasheet.md rendered below · parquet head    │
└────────────────────────────────────────────────────────────────────┘
```
Calls the same function as `python -m egovision export` (no duplicated logic).

## 5. Work Modules (Shefali)
Pick factory + task (from reference cycle) → [Generate] → progress → `st.video` of the module + step list with captions. Lists earlier modules from `products`.

## 6. Metrics (Shefali)
- KPI row: detection recall, L/R accuracy, PCK@0.2, swaps/min, jitter, FPS + hardware.
- Bar chart: baseline vs each fix (mirror, IDs, ROI, rtmlib, WiLoR, smoothing).
- Bar chart: accuracy on 🟢 / 🟡 / 🔴 segments (proves the light).
- Table: failure cases (time, clip, what failed, why). Honest, short.

## 7. States
Empty (no index.db) → "Run `python -m egovision run --clip <id>` first". Missing optional file (no steps yet) → tab shows "not processed yet", rest of page works.
