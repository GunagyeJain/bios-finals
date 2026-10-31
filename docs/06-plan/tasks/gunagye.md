# Tasks: Gunagye · foundation, contacts, index, robot export, app, integration

**Machine:** Lenovo Yoga, Core Ultra 7 (CPU). Integration machine: the final demo runs here. **Protocol:** `../start.md`. **Team checkpoints:** `../checkpoints.md`.
**Your files:** shared files (`schema.py`, `config.py`, `stages.py`, `__main__.py`, `contract.py`, `fixtures.py`, `io/`, `requirements.txt`, `pyproject.toml`), `src/egovision/contact/**`, `index/**`, `products/export.py`, `products/render.py`, `app/Home.py`, `app/components.py`, `app/pages/1_*`, `app/pages/2_*`, `.streamlit/`.
**Read first:** `../../05-solution/trd.md` §3–5.4, §5.8 · `../../05-solution/data-schema.md` (all) · `../../05-solution/ui-design.md`
**Also your job:** merge teammates' **Requests** within 30 min (check every task file's Requests section at each checkpoint).

## G1 · Foundation (done)
- [x] Package skeleton, schema, CLI, stage registry with stubs, contract checker, synthetic fixtures, tests, requirements.

## G2 · Objects + contacts → `objects.jsonl`, `contacts.csv` (3 h) · P1, unblocks S2 + B5
- [ ] `contact/run.py: run(clip)`: YOLOE (smallest model) every 5th processed frame with text prompts from `contact/params.py` (`PORTABLE`, `FIXED` lists; edit after E2 clip notes). Object ids by IoU between runs; `moving` = frame difference inside the box.
- [ ] Contact rule (p.12): ≥ 2 tips in box + 15 % pad, plus closure; hysteresis on after 4 frames, off after 6 → intervals per hand with state `none|portable|fixed`.
- [ ] `grip` column: `unsure` for now (F11 is P2: `2f` if only thumb + index tips in box, `5f` if ≥ 3).
- Done when: tests for the rule + hysteresis; `check` OK on one real clip.

⛔ **CHECKPOINT G-1** · Show: contact intervals for 1 min of a real clip vs the video; object names right?

## G3 · SQLite index (1.5 h) · P0
- [ ] `index/build.py: build()`: DDL from data-schema §3; load every `outputs/*/` (skip `references`); `alerts` = `alerts_steps` + `alerts_safety`; per-clip shares into `clips`. Helper `register_product(kind, name, path, filter, n)` for S4/G4.
- Done when: test builds an index from the fixture in a temp dir.

## G5a · App on fixtures (3 h) · P0
- [ ] `app/components.py`: `kpi_row`, `light_bar`, `event_timeline` (one Plotly figure, rows light/left/right/steps/alerts, click → `st.session_state.t`), `video_at(path, t)`.
- [ ] `Home.py` Library + `1_Clip_review.py` per ui-design §2–3 incl. Baseline/Ours toggle, Steps/Safety/Flagged tabs, "Mark as reference" (calls `steps.order.save_reference`; button hidden until S3 lands).
- [ ] Empty states per ui-design §7.

⛔ **CHECKPOINT G-2** · Show: `streamlit run app/Home.py` on fixtures: library → review → click a red second → video jumps.

## G4 · Robot export (hero) (3 h) · P0
- [ ] `products/export.py: export(name, light)`: episodes from green (or green+yellow) runs ≥ 3 s, split at step boundaries; parquet per episode with the columns of data-schema §4; `meta/info.json`, `episodes.jsonl`, `tasks.jsonl`; episode videos through `redact_frame`; `datasheet.md` (numbers from `metrics.json`, hardware, licences, limits, `capture_feedback` if present). Missing `quality.csv` = yellow.
- [ ] `2_Export.py` page per ui-design §4, calling the same function.
- Done when: test exports the fixture and reloads the parquet with pandas; no red second inside any episode.

⛔ **CHECKPOINT G-3** · Show: build `demo_v1` from the app; open datasheet; `pd.read_parquet` of one episode.

## G6 · Render + integration (2 h, then ongoing) · P0
- [ ] `products/render.py: run(clip)`: H.264 overlay (hands by side + ID, light strip at the bottom, contact label) → `render.mp4`; same for baseline → `render_baseline.mp4`.
- [ ] TC3/TC5: pull, copy demo-clip `wilor.jsonl` from team Drive, `run --clip <demo> --force`, `index`, open the app. File bugs to owners in chat with clip + time.

⛔ **CHECKPOINT G-4** · Show: full demo path (app-flow.md §3) on a real demo clip.

## Everyone tasks
- [ ] E2 (by 17:00): skim 5 clips → `docs/04-research/clip-notes.md` (create it: table clip · factory · task · gloves · machines · demo?).
- [ ] E1 (by 21:00): label 40 frames.

## Requests received
_none yet_
