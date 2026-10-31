# Slides (6)

Rules (problem statement p.15): 5 to 6 slides; problem, approach, results, what failed, what next; **repo link on
slide 1**. Only our own diagrams and drawn mock-ups: no frames, crops or screenshots of the footage, not even in
notes. Numbers only from the Metrics page; until then they stay as "from Metrics page" placeholders.
Business and legal points: Bhavyam's plan §A4 and §A11 (`../03-ideation/bhavyam/bhavyam-plan-discussion.md`).

---

## 1 · Raw head-cam video in, robot-ready hand data out
- Factories record hours of first-person video. Turning it into data "is mostly labelled by hand, which is
  slow and expensive" (problem statement p.1).
- We built the engine a data company runs on that footage: grade it, track the hands, find the steps, export.
- PS5 on PS1 · laptop CPU only · team Caffeinated Nerds
- **Repo: github.com/GunagyeJain/bios-finals** _(swap for the public submission copy)_

Visual: our A → B → C strip (factory → data company → robotics buyer), drawn, no photos.

## 2 · What we built
- Pipeline diagram (README "Pipeline"): MediaPipe hands → IDs, left/right vote, smoothing, gap fill → quality
  light per second → objects + fingertip contacts → Gemini step captions → order check + safety alerts → app
  and robot export.
- Every output carries a reason: a red second says "dark" or "hands out of view", not just "bad".
- Grade footage, never workers: no per-worker scores.

Visual: the pipeline as boxes and arrows in the app's colours.

## 3 · Live demo path
Library → Clip review on a demo clip (Baseline / Ours) → a red second and its reason → Steps tab with an order
alert → Safety tab → Export (green only) → Metrics. Script: `demo-script.md`.

Visual: drawn mock-up of the Clip review layout (video box, light strip, grab/release bars, step row, alert
markers), labelled "illustration".

## 4 · Numbers (all from the Metrics page)
| | Baseline MediaPipe | Ours |
|---|---|---|
| Hands found on labelled frames | from Metrics page | from Metrics page |
| Left/right correct | from Metrics page | from Metrics page |
| PCK@0.2 (wrist + 5 tips) | from Metrics page | from Metrics page |
| Left/right swaps per minute | from Metrics page | from Metrics page |
| FPS on CPU (hardware named) | from Metrics page | from Metrics page |
- Accuracy on green vs red seconds: from Metrics page (proves the light means something).
- Labels: pre-filled by rtmlib, every frame checked by a person; shared hand-made frames as a bias check.
- What failed: the top failure cases from the Metrics page, shown honestly.

## 5 · The robot dataset
- One command or one button: green seconds only, faces blurred, LeRobot-style layout.
- Per frame: both hands' 2D and 3D points, score, contact (none / portable / fixed), object, step, light.
- `datasheet.md` with every number, limit, licence and the hardware used.

Visual: the folder tree (`meta/`, `data/`, `videos/`, `datasheet.md`) and one drawn row of the Parquet table.

## 6 · Business and next steps
- One pipeline, three products: training datasets and benchmark clips for robotics teams; training videos for
  the factory itself (designed, not built in the hackathon).
- Before any launch, legal checks: who owns and may resell the footage; worker consent specific to each
  purpose (India's DPDP Act 2023); trade secrets visible in the video; licences of every model (YOLOE is
  AGPL-3.0, WiLoR and MANO are non-commercial). We are not lawyers: these are questions for an advisor.
- Next technical steps: live quality light while recording, a glove-specific hand model, offline captions,
  3D hand trajectories for simulators.

## Checks before export
- [ ] Repo link on slide 1 is the public submission copy.
- [ ] No real frame, crop or screenshot anywhere.
- [ ] Every number read off the Metrics page on the day.
- [ ] No em dashes, no filler words.
