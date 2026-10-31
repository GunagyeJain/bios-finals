# Sprint 2 · finish everything by 05:00 (from 19:20, 31 Oct)

Replaces the order in `tasks/*.md` from now on. Task files stay the reference for *how*; this file says *what, in which order, and what is cut*.

## How we work now
1. **No personal ⛔ checkpoints.** Claude sessions do not stop and wait for a human. Finish a step, push, post 2 lines in chat (`done: … / next: …`), start the next step.
2. **Two Claude sessions per person**, on different files: one builds, one runs batch jobs (labels, pipeline runs). CPUs never idle.
3. **Time boxes are hard.** At the end of a box: push what works, say what's missing, move on.
4. **Team sync = 5 min, at 21:00, 00:00, 02:00.** Push before each sync. Gunagye runs integration on the demo clips right after.
5. Shared files still go through Gunagye (Requests in chat, merged within 15 min).

## Cut (decided, in `../08-log/decisions.md`)
- **A4 WiLoR / MANO**: registration and GPU setup are a 4 h bet with no result yet. Refined MediaPipe + metrics is the hand story.
- **B1/B2 recovery plug-ins**: `recovery/api.py` keeps its no-op defaults.
- **S4 Work Modules** (F8): the robot export is the product. The Work modules page is hidden.
- Fully hand-made labels: everyone uses the pre-labeller (`eval/prelabel.py`): Enter accepts, a click fixes. The 30 shared frames stay hand-made (clean reference for the bias check).

## Demo clips (fixed now)
`MTL-SKL00089-005` (bench assembly, hands in 93 % of frames) · `MTL-SKL00089-006` · `mytronlabs-000003-002` (polishing, close hands).
Gunagye processes all three end to end on his laptop and keeps them current in the app.

## Timeline
| Block | Gunagye | Abhijay | Bhavyam | Shefali |
|---|---|---|---|---|
| 19:30–21:00 | Hand + forearm masks in render; demo clips through the pipeline | Labels (20 min) → A5 metrics | B3 last fixes → quality on all clips (background) → labels (20 min) | Labels (20 min) → S2 steps on the 3 demo clips |
| **21:00 sync** | demo clips in app | labels pushed, metrics v1 on ≥ 1 clip | quality on 40 clips | steps on demo clips |
| 21:00–00:00 | Metrics page (S5), integration, Robot view if user wants | A5 done on all labelled clips → A6 biggest failure | B5 safety alerts → B6 capture feedback | S3 order check → README one-command |
| **00:00 sync** | full demo path on 3 clips | metrics final v1 | safety on demo clips | alerts_steps on demo clips |
| 00:00–02:00 | polish, renders final, help where blocked | A6 tuning, numbers for slides | slides: business + legal (plan §A14) | slides + demo script |
| **02:00 freeze** | code freeze, fresh-clone test | | | demo video from renders |
| 02:00–05:00 | sleep in shifts; video + slides final by 04:00 | | | |
| 09:00–10:30 | rehearse twice, submit by 10:30 | | | |

## Prompts (paste into each person's Claude session after `git pull`)
### Abhijay
```
Pull. Read docs/06-plan/sprint-2.md and follow your column without stopping for checkpoints.
A4 WiLoR/MANO is cut: stop it now. Leave that code uncommitted unless its tests pass.
1. (20 min) Labels with the pre-labeller: `python -m egovision.eval.prelabel --clip <clip> --labeller abhijay`,
   then the label tool with --web; Enter accepts, fix only wrong points. 40 frames + the 30 shared (shared by hand). Push.
2. (90 min) A5: `python -m egovision.eval.metrics --clip X` → outputs/<clip>/metrics.json for hands_baseline AND hands:
   detection recall/precision, L/R accuracy, PCK@0.2 (wrist + 5 tips, box-normalised), swaps/min, jitter, FPS,
   accuracy per light colour (quality.csv), labels_prefilled_share, PCK on shared (manual) vs prefilled frames.
   "partial": true if < 160 labels. Tests on synthetic labels. Run on every labelled clip. Push code (not outputs).
3. (until 02:00) A6: the single biggest failure the metrics show on the 3 demo clips; re-run metrics after each change;
   before/after in metrics.json. Post "done/next" in chat after every step.
```
### Bhavyam
```
Pull. Read docs/06-plan/sprint-2.md and follow your column without stopping for checkpoints.
B1/B2 recovery are cut: recovery/api.py keeps its defaults.
1. (30 min) B3: last fixes (use hands.jsonl when it exists, not the baseline, for hands_out); tests; push.
   Then in a second session: `python -m egovision run --all --stage quality --force` in the background.
2. (20 min) Labels with the pre-labeller (40 frames + 30 shared by hand). Push.
3. (2 h) B5 safety → alerts_safety.csv per trd §5.6: fixed objects with moving=true in objects.jsonl; alert when any
   fingertip is within 0.5 × hand size of that box for ≥ 0.5 s; one row per alert. Tests on synthetic boxes.
   objects.jsonl for the demo clips: run `python -m egovision run --clip <demo> --stage contact` (about 6 min each).
4. (30 min) B6: capture_feedback(clip) in quality/feedback.py from quality.csv reasons ("dark 0:41–0:58",
   "hands out of view 22 %"); the export datasheet picks it up automatically.
5. From 00:00: business + legal slides from your plan §A14 (docs/07-pitch/). Post "done/next" after every step.
```
### Shefali
```
Pull. Read docs/06-plan/sprint-2.md and follow your column without stopping for checkpoints.
S4 Work Modules is cut. Gunagye builds the Metrics page (S5).
1. (20 min) Finish your 40 labels with the pre-labeller (Enter accepts). Push.
2. (60 min) S2 on the 3 demo clips: GEMINI_API_KEY set, model name in steps/params.py,
   `python -m egovision run --clip <demo> --stage steps`; check steps.csv reads right; push code (not outputs).
   Then copy the three steps.csv files to the team Drive for Gunagye.
3. (60 min) S3 simple: per factory, reference = save_reference(...) if set, else the first full cycle;
   align cycles by edit distance → step_missing / step_order / step_extra; header-only file if no repeat. Tests.
4. (from 22:30) S6 now, not at 06:00: README with the one command, 5–6 slides (mock-ups only, no real frames),
   demo-video script (≤ 2 min, follows app-flow.md §3). Post "done/next" after every step.
```
### Gunagye
```
Masks of hands and forearms in render.mp4 (MediaPipe multiclass segmenter, skin class, coloured by the nearest hand);
the 3 demo clips through every stage; Metrics page; hide Work modules; integration after each sync.
```
