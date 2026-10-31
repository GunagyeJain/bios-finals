# Tasks: Shefali · labels, steps, order check, Work Modules, pitch

**Machine:** MacBook Air M4. **Protocol:** `../start.md`. **Team checkpoints:** `../checkpoints.md`.
**Your files:** `src/egovision/eval/label_tool.py`, `src/egovision/steps/**`, `src/egovision/products/work_module.py`, `app/pages/3_Work_modules.py`, `app/pages/4_Metrics.py`, `eval/labels/` (format), `README.md`, `docs/07-pitch/**`, `tests/test_steps_*.py`, `tests/test_label_*.py`.
**Read first:** `../../05-solution/trd.md` §5.5, §5.6, §5.8 · `../../05-solution/data-schema.md` §1.2, §2 · `../../05-solution/ui-design.md` §5–6 · `src/egovision/schema.py`
**Setup extra:** Gemini key from Google AI Studio → `export GEMINI_API_KEY=...` in your shell (never in a file in the repo).

## S1 · Label tool (1.5 h) · P0 · everyone needs it by 20:00
- [x] `python -m egovision.eval.label_tool --clip X --labeller <name> --n 40`: picks frames (60 % hard: from baseline flags/no-hands/dark if present, else random; 40 % random), saves them to `eval/frames/` (git-ignored), OpenCV window: click wrist then 5 tips per hand, key `l`/`r` for side, Enter/`n` save + next, `x` skip, `t` add tag (blur/glove/dark/overlap/reentry), `u` undo. Box = min/max of clicked points + 15 %.
- [x] `--shared` mode: the same 30 frames (fixed seed) for Abhijay + Bhavyam.
- [x] Writes `eval/labels/<clip>__<labeller>.json` exactly as data-schema §2. Coordinates only. These files **are committed**.
- [x] One-paragraph how-to at the top of the file; post the command in chat.
- Done when: test for the JSON writer; you labelled 5 frames end to end on a real clip.

- [x] Pre-labelling: `python -m egovision.eval.prelabel --clip X --labeller <name>` (rtmlib points, no side), then label as usual; `--shared` stays manual.

⛔ **CHECKPOINT S-1** · Show: label 3 frames live in front of the member; the JSON written.

## S2 · Gemini step captions → `steps.csv` (2.5 h) · P1
- [x] `steps/caption.py: run(clip)`: windows = between consecutive grab/release events in `contacts.csv` (min 1 s, max 20 s). Cut each window (480p) with ffmpeg/OpenCV, pass frames through `quality.redact.redact_frame`, send to Gemini with the fixed verb list `schema.VERBS` + JSON response schema `{verb, object, hand, caption}`.
- [x] Cache: `gemini_cache/<sha1(clip,t0,t1,prompt)>.json`; never call twice. One request at a time, exponential backoff on 429. Delete each upload after use (`client.files.delete`). _Windows go inline with the request (≤ 3 MB each), so nothing is uploaded or left to delete._
- [x] Model name in `steps/params.py` (check AI Studio for the current free-tier model). _`gemini-3.8-flash` (stable, free tier, video input; docs checked 31 Oct). Gunagye runs S2 on the demo clips._
- [x] Columns exactly `schema.STEP_COLS`; `source="gemini"`, or `"contact"` with `verb="other"` if the call failed.
- Fallback: real `contacts.csv` missing → fixed 8 s windows.
- Done when: test with a mocked client (no network); steps for one real clip.

⛔ **CHECKPOINT S-2** · Show: steps table for one real clip next to the video; how many look right out of 10; API calls used.

## S3 · Order check → `alerts_steps.csv` (2 h) · P1
- [x] `steps/order.py: run(clip)`: concatenate steps of all clips of the same factory (`meta.json` → `factory`, order by clip name) into `verb:object` tokens; most frequent repeated sub-sequence of length 3–8 = reference cycle; or `outputs/references/<factory>.json` if a reviewer marked one.
- [x] Align each cycle to the reference (edit distance) → `step_missing`, `step_order`, `step_extra` alerts for **this clip**. Also fill `cycle_idx` logic description in the docstring.
- [x] No repeat → write an empty `alerts_steps.csv` (header only) so the stage counts as done.
- [x] Function `save_reference(factory, steps: list[dict])` for the app's "Mark as reference" button.
- Done when: tests for cycle finding + alignment on synthetic token lists; `fixture_001` gives the known `step_missing`.

⛔ **CHECKPOINT S-3** · Show: reference cycle per factory (or "none"), alerts for one clip, true or false?

## S4 · Work Module generator (3 h) · P1
- [-] _Cut in sprint 2 (`../sprint-2.md`)._ `products/work_module.py: make_module(factory, task) -> str`: pick the cycle with the highest green share + fewest alerts; per step cut the clip, burn caption bar (verb, object, hand), hand overlay from `hands_input()`, title card; all frames through `redact_frame`; ffmpeg H.264; ≤ 60 s → `exports/modules/<factory>_<task>.mp4`.
- [-] _Cut in sprint 2._ Register in `products` table when `index.db` exists (use Gunagye's helper; Request if missing).
- Done when: module for `fixture_001` and one real factory.

⛔ **CHECKPOINT S-4** · Show: play the module; is it useful for a new worker?

## S5 · App pages (1.5 h) · P1
- [-] _Moved to Gunagye in sprint 2 (Metrics page); Work modules page hidden._ `app/pages/3_Work_modules.py` and `4_Metrics.py` per ui-design §5–6, using `app/components.py` from Gunagye (Request if a component is missing). Metrics page reads every `outputs/*/metrics.json`.
- Fallback: components not pushed yet → plain `st.dataframe` + `st.video`, swap later.

⛔ **CHECKPOINT S-5** · Show: both pages on fixtures and on one real clip.

## S6 · README, slides, demo video, submission (3 h, from 06:00) · P0
- [x] `README.md` (judges' rubric p.15): setup, **one command** `python -m egovision run --all`, PS5 on PS1, laptop/GPU per stage, every library/model/API with licence, no footage.
- [x] 5–6 slides in `docs/07-pitch/` (outline: Bhavyam's plan §A14), repo link on slide 1, **mock-ups only, no real frames**. _Content in `slides.md`; numbers from the Metrics page; deck export to Drive still to do._
- [ ] Demo video ≤ 2 min from demo-clip renders → organisers' Drive only.
- [ ] 09:30 fresh-clone test on your Mac (TC6).

⛔ **CHECKPOINT S-6** · Show: slides + video to the whole team at 08:00.

## Everyone tasks
- [ ] E2 (by 17:00): skim 5 clips → `docs/04-research/clip-notes.md`.
- [x] E1 (by 21:00): label 40 frames.

## Requests (to shared-file owners)
_none yet_
