# Tasks: Bhavyam · hand recovery, Data Health light, redaction, safety

**Machine:** Lenovo LOQ, RTX 2050. **Protocol:** `../start.md`. **Team checkpoints:** `../checkpoints.md`.
**Your files:** `src/egovision/recovery/**`, `src/egovision/quality/**`, `src/egovision/safety/**`, `tests/test_quality_*.py`, `tests/test_recovery_*.py`, `tests/test_safety_*.py`.
**Read first:** `../../05-solution/trd.md` §5.1 (steps 5, 10), §5.2, §5.3, §5.7 · `../../05-solution/data-schema.md` §1 · `src/egovision/schema.py`
**Fixed signatures you implement:** `recovery/api.py` (`recover_missing`, `agreement`), `quality/redact.py` (`redact_frame`). Callers already use them; don't change the signatures.

## B4 · Redaction (1.5 h) · P0 · no dependencies, do it first
- [ ] `quality/redact.py: redact_frame(img, keep=None)`: OpenCV YuNet faces (+20 % padding) → strong Gaussian blur. Model file in `models/` (git-ignored), path in `quality/params.py`.
- [ ] Screens/documents: YOLOE text prompts ("monitor", "screen", "paper document") if fast enough, else skip and note it.
- [ ] Never blur inside `keep` boxes (hands).
- [ ] `python -m egovision.quality.redact --clip X --out <path>` writes a redacted preview (local only).
- Done when: test on a synthetic image (face-like detector mocked); manual 20-frame spot check on a real clip.

⛔ **CHECKPOINT B-1** · Show: redacted preview of a clip with a face or screen; any misses.

## B3 · Data Health light → `quality.csv` (3 h) · P0
- [ ] `quality/light.py: run(clip)`: per 1 s segment on 160 px frames: blur (Laplacian variance + optical-flow head speed), brightness (dark share, clipped share), frozen frames, plus from `ClipPaths(clip).hands_input()`: hands visible %, edge cut %, camera angle (mean hand y), mean `agreement` if present.
- [ ] Rules (trd §5.2): red on hard fail, yellow on 1–2 soft fails or agreement < 0.6, else green. `reasons` = failed checks joined by `;` (`dark;hands_out`). Thresholds in `quality/params.py`.
- [ ] Columns exactly `schema.QUALITY_COLS`.
- Fallback: real hands not ready → run video-only checks and leave hands columns at -1; rerun later.
- Done when: tests for the light rules on synthetic numbers; `check` OK on 2 real clips.

⛔ **CHECKPOINT B-2** · Show: the light per second for one demo clip next to the video (a quick matplotlib strip is fine, local only); 3 red seconds and their reasons — do they match what you see?

## B1 + B2 · Recovery plug-ins (4.5 h) · P0
- [ ] `agreement(img, hand)`: rtmlib `Hand` (ONNX, CPU) on the hand box ± 20 %; mean wrist+tip distance / box size → 0..1.
- [ ] `recover_missing(img, frame, t, side, last)`: (1) ROI crop around `last.bbox` × 2, upscale ×2, CLAHE if dark, re-run MediaPipe (IMAGE mode) → `source="roi"`; (2) else rtmlib on the ROI → `source="rtmlib"`; map back to full-frame pixels; return `None` if nothing.
- [ ] Keep CLAHE only if it raises recall on dark labelled frames (A/B with Abhijay's metrics).
- [ ] Speed: run only where refine asks; report ms per call.
- Done when: tests for coordinate mapping (crop → full frame); with Abhijay, recall on labels rises vs A3 alone.

⛔ **CHECKPOINT B-3** · Show: recall with and without plug-ins (A5 numbers), 3 recovered moments, ms per call.

## B5 · Safety alerts → `alerts_safety.csv` (2 h) · P1
- [ ] `safety/run.py: run(clip)`: from `objects.jsonl`, fixed objects with `moving: true` (or frame-difference inside the box > threshold); alert when any fingertip is within `0.5 × hand size` for ≥ 0.5 s. `kind="safety"`, detail says hand, distance, object. Per task/time, never per worker.
- Fallback: G2 not ready → develop on `fixture_001` (has a moving "press machine").
- Done when: test on synthetic tracks; alerts on one real clip checked by eye.

⛔ **CHECKPOINT B-4** · Show: each alert time on one demo clip; true or false alarm?

## B6 · Capture-feedback paragraph (1 h) · P2
- [ ] Function `capture_feedback(clip) -> str` in `quality/feedback.py` ("camera too high 40 %", "dark from 01:10"). Gunagye's datasheet calls it if present.

## Everyone tasks
- [ ] E2 (by 17:00): skim 5 clips → `docs/04-research/clip-notes.md`.
- [ ] E1 (by 21:00): label 40 frames + the 30 shared frames.

## Requests (to shared-file owners)
_none yet_
