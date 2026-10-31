# PRD: EgoVision Data Engine

_Owner: Gunagye · Status: frozen for the hack (31 Oct 2026). Change only via `../08-log/decisions.md`._

## 1. One-liner
A laptop pipeline that turns raw head-camera factory video into **robot-ready, quality-graded hand data**, plus the four uses the brief lists: robot learning, step checking, worker training clips, and safety alerts.

## 2. Track and judging
- **PS5 (open innovation) built on PS1 (hand tracking).** Uses PS2 contacts and PS3 steps as building blocks.
- Fallback: if the PS5 layer is thin at the **02:00 go/no-go**, we declare PS1 and polish hands + the Data Health light.
- Rubric (problem statement p.15): hand accuracy 30 · PS results 20 · technical 15 · usefulness 10 · innovation 10 · efficiency 5 · presentation 10. **Hand accuracy is also the tiebreak**, so 2 of 4 people work on hands the whole time.

## 3. Users
| Who | Company (A–B–C model, see `../03-ideation/bhavyam/bhavyam-plan-discussion.md` §0) | What they need |
|---|---|---|
| Data-ops reviewer | B: Mytron Labs (primary user of the app) | Know which footage is usable and why; export clean data fast |
| Robot-learning engineer | C: robotics buyer | Hand trajectories + grab/release + step labels in a format they already load |
| Factory trainer | A: the factory | Short training clips of a task's key steps |
| Safety lead | A: the factory | Timestamps where hands got close to a moving machine |

## 4. Principles
1. **Grade footage, never workers.** No per-worker scores, rankings or "fake work" flags (rejected: see decisions log).
2. **Hands first.** Every feature reads `hands.jsonl`; better hands improve everything.
3. **Every output carries a reason and a confidence.** No silent guesses.
4. **Data rules are product requirements** (no footage in git, faces blurred in exports, API uploads deleted).

## 5. Features
P0 = must ship. P1 = the four brief use cases, ship after P0 works. P2 = only if time.

| ID | Feature | Priority | Brief use case | Acceptance |
|---|---|---|---|---|
| F1 | Robust hand tracking (MediaPipe + fixes + rtmlib second opinion + WiLoR on hard frames) | P0 | all | `hands.jsonl` for every demo clip; beats baseline on our labelled frames |
| F2 | Data Health light 🟢🟡🔴 per 1 s segment, with reasons | P0 | all | `quality.csv`; tracker accuracy higher on green than red |
| F3 | **Robot dataset export (hero)** LeRobot-style episodes, green segments only, faces blurred, datasheet | P0 | Teach robots | One command builds a dataset; loads in pandas; datasheet lists every number |
| F4 | Streamlit app: library, clip review, export | P0 | all | Opens a processed demo clip in < 3 s |
| F5 | Eval: 160 labelled frames, metrics, before/after | P0 | all | `metrics.json` with detection %, L/R accuracy, PCK, swaps/min, jitter, FPS |
| F6 | Contacts: grab/release per hand, portable vs fixed object | P1 | Teach robots, steps | `contacts.csv`; events visible on the timeline |
| F7 | Step timeline + order check | P1 | Check steps in order | `steps.csv` + alerts for missing / out-of-order steps |
| F8 | Work Module: auto-cut training clip with captions + hand overlay | P1 | Train new workers | MP4 ≤ 60 s from one task |
| F9 | Safety alerts: hand near a moving machine part | P1 | Unsafe hand positions | `alerts` rows with time, hand, distance, reason |
| F10 | Face/screen blur in every exported video | P0 | data rules | No face visible in any export (spot-check 20 frames) |
| F11 | Grip-type tags (2-finger / 5-finger / generic) per grab | P2 | Teach robots | Filter export by robot hand type |
| F12 | Benchmark pack (held-out clips + task card) | P2 | Teach robots | Never mixed into a training export |
| F13 | Capture-feedback report ("camera too high 40%") | P2 | — | One paragraph per clip in the datasheet |

## 6. What the footage forces (from the team's first look)
- ~20 clips (+480p copies), several factories, **7–8 clips per factory**, each clip a **continuation** of one job; tasks do not repeat across clips.
- So: step-order check builds its reference from **repeated cycles inside a factory's job**, not from other clips. If no cycle repeats, the app shows the timeline and lets the reviewer mark a sequence as the reference (see `trd.md` §5.6).

## 7. Success metrics (all measured by us, shown in slides)
| Metric | Target |
|---|---|
| Hand detection recall on labelled frames | > baseline MediaPipe by ≥ 10 points |
| Left/right accuracy | ≥ 95 % |
| PCK@0.2 (wrist + 5 tips, on 40-frame subset) | report, beat baseline |
| Left/right swaps per minute | ≤ 0.5 |
| Pipeline speed | ≥ 10 FPS on the Yoga CPU (480p, step 2) |
| Light validity | accuracy on 🟢 − accuracy on 🔴 ≥ 15 points |
| Share of footage auto-approved (green) | report |

## 8. Non-goals
- Worker ranking, productivity scores, "real vs faked work".
- Training a model from scratch (no labels exist).
- Live processing on stage (demo clips are processed beforehand; the app is live).
- Mobile apps.

## 9. Deliverables (problem statement p.15)
- Public GitHub repo: README with setup, **one command** (`python -m egovision run --all`), PS5-on-PS1, hardware used, every library/model/API.
- Demo videos ≤ 2 min total → organisers' Drive folder only.
- 5–6 slides, repo link on slide 1 → same Drive folder.
- Live 5-min demo + 3-min Q&A; every member can explain every module.

Related: `trd.md` · `app-flow.md` · `data-schema.md` · `ui-design.md` · `../06-plan/work-split.md`
