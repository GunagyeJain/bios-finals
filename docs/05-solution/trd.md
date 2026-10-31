# TRD: EgoVision Data Engine

_What to build and how. Product scope: `prd.md`. Formats: `data-schema.md`._

## 1. Stack (pinned in `requirements.txt`, Python 3.11, venv)
| Need | Choice | Why |
|---|---|---|
| Hands (CPU) | MediaPipe Hand Landmarker 1.x, Tasks API, VIDEO mode | Real time on CPU; starter code (p.10) |
| Hands, second opinion (CPU) | rtmlib `Hand` (RTMDet + RTMPose, ONNX) | Independent model → agreement signal |
| Hands, hard frames (GPU) | WiLoR on Abhijay's RTX 3050 or Colab | Best on blur/gloves; only flagged frames |
| Objects | Ultralytics YOLOE (text prompts), small model | Open-vocabulary on CPU |
| Video / quality / blur | OpenCV, YuNet face detector, ffmpeg (H.264) | Laptop-cheap |
| Step captions | Gemini API (`google-genai`), short windows only, cached | Free tier; meaning, not finger positions |
| Storage | Per-clip files + one SQLite index (`outputs/index.db`) | Parallel-friendly; fast app |
| Export | Parquet (pyarrow) + JSON, LeRobot-style layout | What robot teams load |
| App | Streamlit + Plotly | Python only; one dev can own it |
| Tests | pytest on pure functions | Fast; no footage in tests |

## 2. Repo layout
```
src/egovision/
  __main__.py      CLI: run / index / export / app            (Gunagye)
  schema.py        dataclasses + read/write helpers           (Gunagye, shared: announce edits)
  config.py        paths only                                 (shared)
  stages.py        ordered stage registry (lazy imports)      (Gunagye)
  contract.py      `check` command: validates outputs         (Gunagye)
  fixtures.py      synthetic clips with every output          (Gunagye)
  */params.py      each module's own thresholds               (module owner)
  io/frames.py     frame iterator, meta.json                  (Gunagye)
  hands/           baseline, tracking, smoothing, gapfill, wilor_fuse   (Abhijay)
  recovery/        rtmlib second opinion, ROI re-detect, low-light       (Bhavyam)
  quality/         checks, light, redact (blur faces/screens)            (Bhavyam)
  contact/         objects (YOLOE), contact rule, grip tags              (Gunagye)
  steps/           gemini captioner, order check                         (Shefali)
  safety/          machine-proximity alerts                              (Bhavyam)
  products/        export (LeRobot), work_module, render overlay         (Gunagye / Shefali)
  eval/            label tool, metrics                                   (Shefali / Abhijay)
  index/           SQLite build + queries                                (Gunagye)
app/               Streamlit: Home.py + pages/                           (Gunagye; Shefali 2 pages)
tests/             pytest
```
Rule: stay in your folder. Shared files (`schema.py`, `config.py`, `stages.py`, `__main__.py`, `contract.py`, `requirements.txt`) change only through a Request to Gunagye (`../06-plan/start.md` §3).

## 3. CLI (one command for judges)
```
python -m egovision run --clip factory_001     # all stages for one clip, resumable
python -m egovision run --all                  # every clip; skips stages whose output exists
python -m egovision run --clip X --stage hands # one stage (hands|recover|quality|contact|steps|safety|render)
python -m egovision index                      # rebuild outputs/index.db from files
python -m egovision export --name demo_v1 --light green
streamlit run app/Home.py
```
Each stage reads files and writes files (`outputs/<clip>/`). A stage never edits another stage's output.

## 4. Pipeline order
`frames → hands(baseline) → recover → hands(final) → quality → contact → steps → safety → render → index`
Details and the diagram: `app-flow.md`.

## 5. Algorithms
### 5.1 Hands (F1, Abhijay + Bhavyam)
1. **Baseline:** MediaPipe VIDEO mode, `clips_480p`, step 2, `num_hands=2`, confidences 0.4. Save untouched as `hands_baseline.jsonl` (our "before").
2. **Mirror fix:** verify on 3 clips; swap MediaPipe left/right if backwards (p.10).
3. **Track IDs:** Hungarian match on side + IoU + wrist distance; keep a lost track alive 2 s for re-entry.
4. **Side voting:** a track's side = majority over its frames + egocentric prior (left hand mostly in left half). Kills single-frame swaps.
5. **Recovery when a hand is missing or low-score:** ROI crop around last box, upscale ×2, CLAHE if dark, re-run MediaPipe; else rtmlib. Mark `source`.
6. **WiLoR escalation:** frames still flagged (`low_conf`, `disagree`, `missing` inside an active track) → batch to WiLoR on GPU → fuse (replace kp2d, keep ID/side). Report % of frames sent.
7. **Sanity:** bone-length ratios and max wrist speed; violations → flag + low confidence.
8. **Gap fill:** linear interpolation for gaps ≤ 5 frames; mark `interp`. Then fill skipped frames (step 2).
9. **Smoothing:** One-Euro per coordinate (p.11), `min_cutoff=1.0, beta=0.01`, tune on demo clips.
10. **Agreement:** mean wrist+tip distance MediaPipe vs rtmlib, normalised by box size → `agreement` 0–1.

### 5.2 Data Health light (F2, Bhavyam)
Per 1 s segment: blur (Laplacian variance + optical-flow head speed), brightness (dark / clipped share), hands visible %, hands cut at frame edge, camera angle (mean hand y), frozen frames, agreement, no-task time.
- 🔴 if any hard fail (hands visible < 30 %, very dark, frozen, blur extreme).
- 🟡 if 1–2 soft fails or agreement < 0.6.
- 🟢 otherwise. `reasons` = the failed checks in words. Thresholds in `config.py`, tuned against labels (prove with accuracy per colour).

### 5.3 Redaction (F10, Bhavyam)
YuNet faces (+ padding) → Gaussian blur; screens/documents via YOLOE prompts ("monitor", "screen", "paper document") → blur. Applied to every exported or module video. Never blur inside a hand box.

### 5.4 Objects + contacts (F6, Gunagye)
- YOLOE every 5th processed frame with a factory vocabulary (edit after watching clips); boxes tracked between runs.
- Vocabulary split into `portable` (tool, part, box, screwdriver…) and `fixed` (machine, table, shelf, conveyor…).
- Contact = ≥ 2 fingertips (4, 8, 12, 16, 20) inside box + 15 % pad (p.12) **and** hand closure; hysteresis: on after 4 frames, off after 6.
- Output state per hand: `none | portable | fixed`, grab/release events.

### 5.5 Steps (F7, Shefali)
- Windows = between consecutive grab/release events (min 1 s, max 20 s). Cut the window (480p, faces blurred) and send to Gemini with a **fixed verb list** (`pick, place, fasten, insert, press, cut, inspect, adjust, carry, other`) → JSON `{verb, object, hand, caption}`.
- Cache every response in `gemini_cache/<sha1(clip,t0,t1,prompt)>.json`; one request at a time, retry with backoff; delete uploads after each call.

### 5.6 Order check (F7, Shefali)
- Concatenate the step lists of a factory's clips in order → one sequence of `verb:object` tokens.
- Find the most frequent repeated sub-sequence (length 3–8) = **reference cycle**.
- Align each cycle to the reference (edit distance) → alerts `step_missing`, `step_order`, `step_extra`.
- No repeat found → no alerts; the app offers "mark these steps as reference" (saved to `outputs/references/<factory>.json`).

### 5.7 Safety (F9, Bhavyam)
Fixed-object boxes from 5.4 whose pixels move (frame difference inside box > threshold) = **moving machine**. Alert when any fingertip is within `0.5 × hand size` of that box for ≥ 0.5 s. Report per task and time, never per worker.

### 5.8 Products (Gunagye, Shefali)
- **Export (F3):** green segments merged into episodes (min 3 s), cut at step boundaries when present. Layout: `data-schema.md` §4.
- **Work Module (F8):** for one task: clearest (highest green share + most complete) cycle → ffmpeg cut per step, caption bar, hand overlay, title card; ≤ 60 s.
- **Render:** annotated H.264 video per clip for the app and the Drive demo.

## 6. Performance budget (Yoga CPU, 480p, step 2)
MediaPipe ~30 FPS · rtmlib only on flagged frames · YOLOE every 5th frame · quality checks on downscaled 160 px frames. Target ≥ 10 FPS overall; log FPS per stage into `metrics.json`.

## 7. Testing
pytest on: schema round-trip, One-Euro, side voting, contact rule + hysteresis, light rules, order alignment, export layout (synthetic data, no footage). Run `pytest -q` before each push of shared files.

## 8. Security and data rules
`GEMINI_API_KEY` from env only. `outputs/`, `exports/`, `data/egohack-data/`, `gemini_cache/`, videos, `*.db` are git-ignored. End of event: delete everything (`../03-ideation/bhavyam/bhavyam-plan-discussion.md` §A15).
