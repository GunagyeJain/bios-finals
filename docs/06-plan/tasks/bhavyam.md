# Tasks: Bhavyam · hand recovery, Data Health light, redaction, safety

**Machine:** Lenovo LOQ, RTX 2050. **Protocol:** `../start.md`. **Team checkpoints:** `../checkpoints.md`.
**Your files:** `src/egovision/recovery/**`, `src/egovision/quality/**`, `src/egovision/safety/**`, `tests/test_quality_*.py`, `tests/test_recovery_*.py`, `tests/test_safety_*.py`.
**Read first:** `../../05-solution/trd.md` §5.1 (steps 5, 10), §5.2, §5.3, §5.7 · `../../05-solution/data-schema.md` §1 · `src/egovision/schema.py`
**Fixed signatures you implement:** `recovery/api.py` (`recover_missing`, `agreement`), `quality/redact.py` (`redact_frame`). Callers already use them; don't change the signatures.

## B4 · Redaction (1.5 h) · P0 · no dependencies, do it first
- [x] `quality/redact.py: redact_frame(img, keep=None)`: OpenCV YuNet faces (+20 % padding) → strong Gaussian blur. Model file in `models/` (git-ignored), path in `quality/params.py`. _Downloads on first use; raises if it cannot, so footage never passes through unblurred._
- [x] Screens/documents: YOLOE text prompts ("monitor", "screen", "paper document") if fast enough, else skip and note it. _Skipped: ~310 ms per frame on CPU vs ~20 ms for YuNet. Revisit at B-1 if real clips show readable screens._
- [x] Never blur inside `keep` boxes (hands).
- [x] `python -m egovision.quality.redact --clip X --out <path>` writes a redacted preview (local only).
- Done when: test on a synthetic image (face-like detector mocked); manual 20-frame spot check on a real clip. _(done: tests pass, Bhavyam passed the 20-frame sheet by eye)_
- Known limits, measured on stock photos: faces under ~20 px at 480p are missed; profile faces can be missed; each frame is detected alone, so a weak face can flicker for single frames; a hand box over a face stays sharp, as specified.
- Scan of all 40 clips (one frame per 2 s, totals only): faces in 1196 of 3600 frames, every clip has some. Of faces scoring ≥ 0.9, 16 of 16 sit inside a detected person; 47 of 68 at 0.8–0.9; about 40 % below 0.8, so many weak ones are false alarms. A person with no face found in 230 of 385 frames (back views, side views or real misses; human check needed). Screens in 3, paper in 3 of 1200 frames. Detection alone on real 1080p frames: 68 ms per frame. Full preview on the clip with most faces: 190 ms per frame, about 17 min for a 3-min clip (read, detect, blur, write).

⛔ **CHECKPOINT B-1** · Show: redacted preview of a clip with a face or screen; any misses.

## B3 · Data Health light → `quality.csv` (3 h) · P0
- [x] `quality/light.py: run(clip)`: per 1 s segment on 160 px frames: blur (Laplacian variance + optical-flow head speed), brightness (dark share, clipped share), frozen frames, plus from `ClipPaths(clip).hands_input()`: hands visible %, edge cut %, camera angle (mean hand y), mean `agreement` if present.
- [x] Rules (trd §5.2): red on hard fail, yellow on 1–2 soft fails or agreement < 0.6, else green. `reasons` = failed checks joined by `;` (`dark;hands_out`). Thresholds in `quality/params.py`.
- [x] Columns exactly `schema.QUALITY_COLS`.
- Fallback: real hands not ready → run video-only checks and leave hands columns at -1; rerun later.
- Done when: tests for the light rules on synthetic numbers; `check` OK on 2 real clips.
- Measured on all 40 clips (7200 s): blur and speed are the only pixel checks that fire. Dark, clipped and frozen never fire: these factories are well lit and no clip stalls, so those checks stay as guards. Sharpness is measured at 480 px, relative to each clip, because factories differ 2x. `hands_out` drives nearly all reds and comes from raw MediaPipe, so it may mean the detector failed, not that hands left the frame; rerun on final hands.
- Final, on 0.2-threshold hands, all 40 clips: 59 % green, 16 % yellow, 25 % red, 0 contract failures (raw MediaPipe gave 53 / 14 / 34). Red by factory: SGF 31 %, SKL 2 %, 000003 6 %, 000060 62 %. Demo clips: 5, 3 and 2 red seconds of 180. Light validity against labels is still unproven: only 1 labelled frame fell on a red second.

⛔ **CHECKPOINT B-2** · Show: the light per second for one demo clip next to the video (a quick matplotlib strip is fine, local only); 3 red seconds and their reasons — do they match what you see?
_B-2 passed: Bhavyam checked the red seconds on the sheet; hands really are out of sight._

## B1 + B2 · Recovery plug-ins · CUT (sprint-2), api.py back to no-op defaults
_Built and measured before the cut, then reverted: commit 9129397, undone by the revert commit after it. Hidden-hand test on 4 clips: 137 of 160 found (108 close to truth), 15 of 125 false in frames where hands are gone, 33 ms per call. Scale 4x crop beat the 2x recipe (64 % vs 28 %); CLAHE gained nothing. `git revert` of the revert restores it._
- [ ] `agreement(img, hand)`: rtmlib `Hand` (ONNX, CPU) on the hand box ± 20 %; mean wrist+tip distance / box size → 0..1.
- [ ] `recover_missing(img, frame, t, side, last)`: (1) ROI crop around `last.bbox` × 2, upscale ×2, CLAHE if dark, re-run MediaPipe (IMAGE mode) → `source="roi"`; (2) else rtmlib on the ROI → `source="rtmlib"`; map back to full-frame pixels; return `None` if nothing.
- [ ] Keep CLAHE only if it raises recall on dark labelled frames (A/B with Abhijay's metrics).
- [ ] Speed: run only where refine asks; report ms per call.
- Done when: tests for coordinate mapping (crop → full frame); with Abhijay, recall on labels rises vs A3 alone.

⛔ **CHECKPOINT B-3** · Show: recall with and without plug-ins (A5 numbers), 3 recovered moments, ms per call.

## B5 · Safety alerts → `alerts_safety.csv` (2 h) · P1
- [x] `safety/run.py: run(clip)`: from `objects.jsonl`, fixed objects with `moving: true` (or frame-difference inside the box > threshold); alert when any fingertip is within `0.5 × hand size` for ≥ 0.5 s. `kind="safety"`, detail says hand, distance, object. Per task/time, never per worker.
- Fallback: G2 not ready → develop on `fixture_001` (has a moving "press machine").
- Done when: test on synthetic tracks; alerts on one real clip checked by eye.
- Eye check on 15 alerts across 2 demo clips failed: the boxes did not match the objects, and every alert box scored near 0.12. Alerts now need a box scored 0.4 or more, which leaves 0 alerts on all 3 demo clips (28 rows before). The rule works on the synthetic clip, but it has never fired correctly on real footage, so it stays out of the demo.

⛔ **CHECKPOINT B-4** · Show: each alert time on one demo clip; true or false alarm?

## B6 · Capture-feedback paragraph (1 h) · P2
- [x] Function `capture_feedback(clip) -> str` in `quality/feedback.py` ("camera too high 40 %", "dark from 01:10"). Gunagye's datasheet calls it if present.

## Everyone tasks
- [ ] E2 (by 17:00): skim 5 clips → `docs/04-research/clip-notes.md`.
- [ ] E1 (by 21:00): label 40 frames + the 30 shared frames.

## Requests (to shared-file owners)
- To Gunagye (G4 datasheet): say "faces blurred", not "faces/screens blurred" (`data-schema.md` §4, `trd.md` §5.3), unless B-1 brings screens back.
- To Gunagye (speed budget): my copy of `clips_480p/` is 1920×1080, not 480p (40 clips, 30 fps, 180 s each). Check whether yours is too; trd §6 assumes 480p.
- To Shefali (slides.md, slide 6): take the text from `../../07-pitch/business-legal.md`; WiLoR and MANO are cut, so drop them from the licence line.
- To Gunagye (contact): `moving` fires on furniture; a workbench read as moving in up to 41 % of rows on the demo clips. Safety filters it with `NEVER_MOVES`, but check anything else that reads the flag.
- To Gunagye (requirements, TC6): YOLOE needs the `clip` package, which ultralytics installs itself at run time, plus a 572 MB `mobileclip_blt.ts` download (about 8 min here). Add `clip` to `requirements.txt` and have the fresh-clone test allow for the download.
