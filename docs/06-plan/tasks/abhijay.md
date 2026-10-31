# Tasks: Abhijay · hands core, WiLoR, metrics

**Machine:** HP Omen, RTX 3050 (GPU work: A4). **Protocol:** `../start.md`. **Team checkpoints:** `../checkpoints.md`.
**Your files:** `src/egovision/hands/**`, `src/egovision/eval/metrics.py`, `requirements-gpu.txt`, `tests/test_hands_*.py`, `tests/test_metrics.py`.
**Read first:** `../../05-solution/trd.md` §5.1 · `../../05-solution/data-schema.md` §1.1, §2 · `src/egovision/schema.py` · `src/egovision/recovery/api.py`
**You unblock:** everyone (real hands). Push A1 as early as possible.

## A1 · MediaPipe baseline + mirror check (1.5 h) · P0
- [x] `hands/baseline.py: run(clip)`: starter code p.10 (Tasks API, VIDEO mode, `num_hands=2`, conf 0.4), `clips_480p`, `config.FRAME_STEP`. Write `hands_baseline.jsonl` with `schema.Hand` (source `"mediapipe"`, `kp3d` = world landmarks). Never post-process this file.
- [x] Download `hand_landmarker.task` to `models/` (git-ignored); path constant in `hands/params.py`.
- [x] `python -m egovision.hands.baseline --clip X --preview` writes `outputs/<clip>/preview_baseline.mp4` (starter step 7 drawing, left blue / right orange, side label).
- [ ] Mirror check on 3 clips: are MediaPipe's left/right backwards on head-cam video? Put `MIRROR = True/False` in `hands/params.py`; append the answer to `docs/08-log/decisions.md`. Baseline stays raw; the swap happens in A2.
- [ ] Run `python -m egovision run --all --stage hands_baseline`; note FPS.
- Done when: `python -m egovision check --clip <real clip>` OK for `hands_baseline`; a test for the JSON conversion on a fake MediaPipe result.

⛔ **CHECKPOINT A-1** · Show: preview of one demo clip at a hard moment (blur/gloves/re-entry), FPS, mirror decision, share of frames with 0/1/2 hands.

## A2 · Track IDs, side voting, re-entry (2.5 h) · P0
- [ ] `hands/refine.py: run(clip)`: read baseline; apply `MIRROR`; Hungarian match on side + IoU + wrist distance (`scipy.optimize.linear_sum_assignment`); keep a lost track 2 s for re-entry.
- [ ] Side voting: track side = majority over its frames + prior (left hand mostly in left half). No single-frame swaps.
- [ ] When a hand is missing inside a live track, call `recovery.api.recover_missing(img, frame, t, side, last)`; when present, store `recovery.api.agreement(img, hand)` in `hand.agreement`. Both are no-ops until Bhavyam fills them; don't wait.
- Fallback: none needed (input is your own A1).

## A3 · Sanity, gap fill, smoothing → `hands.jsonl` (2 h) · P0
- [ ] Sanity: bone-length ratios, max wrist speed → flag `sanity`, lower score.
- [ ] Gap fill: linear ≤ 5 frames (`source="interp"`), then fill skipped frames so `hands.jsonl` has **every** frame.
- [ ] One-Euro per coordinate (p.11), params in `params.py`.
- [ ] Flags: `low_conf` (score < 0.5), `edge` (box touches frame edge), `sanity`.
- [ ] `--preview` also for refine → `preview_refined.mp4`.
- [ ] Numbers before/after: swaps per minute, jitter (mean frame-to-frame wrist motion when the hand is still).
- Done when: tests for side voting, gap fill and One-Euro on synthetic tracks; `check` OK on 2 real clips.

⛔ **CHECKPOINT A-2** · Show: baseline vs refined preview side by side on the same 10 s; swaps/min and jitter before/after.

## A4 · WiLoR on flagged frames (4 h) · P0 for accuracy
- [ ] **Now, before 02:00:** register at mano.is.tue.mpg.de and download `MANO_RIGHT.pkl` (WiLoR needs it; registration can take a while). Licence: WiLoR CC-BY-NC-ND + MANO non-commercial → list both in `models/README.md` for the datasheet. Never commit the `.pkl`.
- [ ] Set up WiLoR on your RTX 3050 (Colab if it fails); exact versions → `requirements-gpu.txt`.
- [ ] `python -m egovision.hands.wilor --clip X`: select frames where a hand is `missing` inside a live track or flagged `low_conf`/`disagree`; batch; write `wilor.jsonl` (`source="wilor"`, 21 kp2d + 3D joints).
- [ ] `refine.py`: when `wilor.jsonl` exists, replace kp2d/kp3d of flagged hands (keep ID and voted side).
- [ ] Report: % of frames sent to WiLoR, WiLoR FPS on your GPU.
- [ ] Copy `wilor.jsonl` of demo clips to the private team Drive for Gunagye's integration run.
- Fallback: WiLoR won't install in 1.5 h → stop, tell the team, skip to A5; refine works without it.

⛔ **CHECKPOINT A-3** · Show: the 10 hardest seconds, refined vs refined+WiLoR; % escalated.

## A5 · Metrics from labels (2 h) · P0
- [ ] `python -m egovision.eval.metrics --clip X` → `outputs/<clip>/metrics.json` for **both** `hands_baseline` and `hands`: detection recall + precision, left/right accuracy, PCK@0.2 (wrist + 5 tips, normalised by box size), swaps/min, jitter, FPS + hardware, accuracy per light colour (from `quality.csv` if present).
- [ ] Inter-labeller agreement on the 30 double-labelled frames.
- [ ] Split by tags (`blur`, `glove`, `dark`, `overlap`, `reentry`).
- Fallback: labels incomplete → run on what exists, write `"partial": true`.
- Done when: tests with tiny synthetic labels and predictions.

⛔ **CHECKPOINT A-4** · Show: metrics table baseline vs ours; worst tag; 3 failure moments with times.

## A6 · Tune on demo clips (rest of the time) · P0
- [ ] Fix the biggest failure from A-4 first. Re-run metrics after every change; log each before/after in `metrics.json` history.

## Everyone tasks
- [ ] E2 (by 17:00): skim 5 clips → `docs/04-research/clip-notes.md` (factory, task, gloves, machines, demo clip?).
- [ ] E1 (by 21:00): label 40 frames with S1's tool + the 30 shared frames.

## Requests (to shared-file owners)
_none yet_
