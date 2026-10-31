# Sprint 3 · overnight (31 Oct 23:00 → 1 Nov 07:00)

Submission = **this repo's GitHub link** (full history) + demo video + PDF. Video is the last thing we make.
Same rules as `sprint-2.md`: no personal checkpoints; own files only; `pytest -q` before every push; push after every
finished step; post `done/next` in chat. **Unattended sessions:** laptop plugged in, sleep off; stop at 06:30 and post a
morning report (what works, what doesn't, what to look at). Anything not working at 06:30 is dropped, not patched.

## Decisions
- Audio as a contact check: tested, no better than random on all 3 demo clips → dropped (decisions.md). No audio anywhere.
- Robot view stays (overlay video + 2-finger / 5-finger switch in the player).
- Clip review becomes one synced player: timeline, light, panel and lists follow the video while it plays.

## Morning (1 Nov)
| Time | What |
|---|---|
| 07:00 | Everyone reads the morning reports; Gunagye runs the final integration on the demo clips |
| 08:00 | **Freeze**: no code changes after this |
| 08:00–09:30 | Demo video (≤ 2 min) from the final app; deck final |
| 09:30–10:30 | Rehearse twice; submit link + video + PDF by 10:30 |
| ~11:15 | Data deletion (`data-deletion.md`) |

## Gunagye (this laptop = demo laptop)
1. Synced player for Clip review: video + timeline + light strip + "This moment" + steps/alerts lists in one component,
   moving with the video; click anywhere to seek; views Ours / Baseline / 2-finger robot / 5-finger robot.
2. All 40 clips through the pipeline in the background (no renders), so the Library shows the whole dataset.
3. `docs/07-pitch/numbers.md`: the final numbers for the slides, copied from metrics.json (no hand-typed numbers).
4. Morning: Bhavyam's robot overlays + renders on the 3 demo clips, demo dataset export, final check of every screen.

## Prompts (paste into each person's Claude session after `git pull`)
### Bhavyam (start now)
```
Pull. Read docs/06-plan/sprint-3.md. Work autonomously until 06:30, no checkpoints; pytest before every push;
post done/next in chat after every step; morning report at 06:30.
1. NEW FILE src/egovision/products/robot_overlay.py (yours): render(clip, mode, redact=None) with mode "2f" or "5f"
   → outputs/<clip>/render_robot_<mode>.mp4. Same fps (meta fps / step) and size (960 px wide) as render.mp4,
   H.264 through egovision.io.video.H264Writer, every frame through quality.redact.redact_frame (keep = hand boxes).
   Hands from ClipPaths(clip).hands_input(); draw nothing on frames with no hand.
   - 2f: a two-jaw gripper at the wrist pointing wrist → kp 9; jaw gap = |kp4 − kp8| clamped to 0.1–1.0 × hand size.
   - 5f: a simplified robot hand along kp2d: thick flat links (8 px), round joints.
   - Colour by the hand's active contact (contacts.csv, grip column): green #44a282 = this robot can copy it,
     red #e5566f = it can't, grey #8a8c92 = no contact or grip "unsure". Sets: egovision.index.query.ROBOT_CAN_COPY.
   - Small label top-left on a dark plate: "2-finger robot: can copy" / "cannot copy" / "no grab".
   - Import helpers from products/overlay.py if useful; don't edit Gunagye's files.
   - CLI: `python -m egovision.products.robot_overlay --clip X [--mode 2f|5f|both]`.
   - Tests (synthetic, no footage): gripper geometry (gap clamp, direction), colour rule per grip,
     render on fixture_001 writes a playable mp4 with the right frame count (redact stubbed).
   - Run it on one real clip on your laptop and look at it; the video stays local.
2. Safety: eye-check alerts on the 3 demo clips (MTL-SKL00089-005, -006, mytronlabs-000003-002); fix false alerts.
3. Write the "Robot view" slide text into docs/07-pitch/robot-view.md (what the colours mean, the robot-fit numbers
   from the Library page, what it does NOT claim).
```
### Abhijay
```
Pull. Read docs/06-plan/sprint-3.md. Work autonomously until 06:30, no checkpoints; pytest before every push;
post done/next in chat; morning report at 06:30.
1. Finish A6 and push by 01:00. After 01:00 no more changes to hands/ (the demo clips get re-run on it).
2. scripts/validate_export.py: checks an exports/<name>/ folder against data-schema.md §4 (columns, shapes,
   timestamps increasing per episode, no red frames, video frame count = parquet rows, tasks/episodes consistent);
   prints PASS/FAIL per check. Tests with a fixture export.
3. docs/07-pitch/where-it-fails.md: the 5 biggest failure modes from metrics.json (overlap, edge, gloves, dark,
   fast motion): how often, one example time per clip, what we do about it. Numbers copied from metrics, not typed.
```
### Shefali
```
Pull. Read docs/06-plan/sprint-3.md. Work autonomously until 06:30, no checkpoints; pytest before every push;
post done/next in chat; morning report at 06:30.
1. S3 noise: compare cycles on verb + normalised object (lowercase, singular, drop part/piece/object); alert only
   when a step is missing or out of order in 2+ cycles. Re-check: mytronlabs-000003-002 must not give ~79 alerts.
2. README: "the first run downloads about 600 MB of models (needs internet)"; submission = repo link + video + PDF.
3. Deck: slides.md final, with numbers ONLY from docs/07-pitch/numbers.md (Gunagye writes it tonight),
   speaker notes per slide, a 5-minute talk track, qa.md updated (labels: pre-labelled then checked by a person;
   audio tested and dropped; no claims about identifying people). Export the deck to PDF if you can (exports/, not git).
4. demo-script.md v2 for the synced player: play the demo clip and let the timeline run; click a red stretch;
   switch to 2-finger robot view; Export (green only) → datasheet; Metrics. ≤ 2 minutes.
```

## Handoff for Gunagye's session (from Abhijay, hands code final)
`numbers.md` from 00:09 predates the left/right fix (`19f8618`, 00:30), so its 92.9 % is out of date. Before the 07:00 integration:
1. `git pull`, then re-run the hands stage on the 3 demo clips and every labelled clip: `python -m egovision run --clip <clip> --stage hands --force`. The first run per clip does a new MediaPipe pass (about 4 min); later runs take seconds.
2. `python -m egovision.eval.metrics --all`, then `python scripts/pitch_numbers.py` and `python scripts/where_it_fails.py`. Expect left/right near 95.7 % and recall near 66 %. If not, flag it in `STATUS.md`; don't patch `hands/`.
3. Run `python scripts/validate_export.py exports/<name>` on the final demo export. It passed 11/11 on a test export without steps or contacts.

Pitch wording for left/right: matches the baseline within measurement error while finding many more hands; give the split on hands both versions find (`where-it-fails.md`). Quote the numbers from the regenerated files. No labelled frame covers gloves or dark footage, so make no accuracy claim there.

## Open (decide by 08:00)
- Evaluators need access to a private repo whose history contains the organisers' private brief PDF:
  ask the organisers whether the repo may go public as is, or add the evaluators as collaborators. Never rewrite history.
- Who submits.
