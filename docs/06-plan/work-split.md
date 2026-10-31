# Work split

_Hard stop: **1 Nov 11:00**. Scope: `../05-solution/prd.md`. How: `../05-solution/trd.md`. Formats: `../05-solution/data-schema.md`._
Rule: finish your P0 tasks before P1. Blocked > 30 min → say so in chat, use the task's fallback or take the next task.

## Owners
| Member | Machine | Owns |
|---|---|---|
| **Gunagye** | Yoga, Ultra 7 CPU | Skeleton + schemas + CLI, contacts, SQLite index, **robot export (hero)**, Streamlit shell + main pages, integration |
| **Abhijay** | Omen, RTX 3050 | Hands core, WiLoR on GPU, eval metrics |
| **Bhavyam** | LOQ, RTX 2050 | Hand recovery (rtmlib, ROI), Data Health light, redaction, safety alerts |
| **Shefali** | MacBook Air M4 | Label tool, Gemini steps + order check, Work Modules, 2 app pages, README, slides, demo video |

## Tasks
One file per member, with checkpoints: `tasks/gunagye.md` · `tasks/abhijay.md` · `tasks/bhavyam.md` · `tasks/shefali.md`.
How a session starts and when it stops for review: `start.md`. Team gates: `checkpoints.md`.
Everyone: E1 label 40 frames (by 21:00) · E2 skim 5 clips into `../04-research/clip-notes.md` (by 17:00).

## Timeline (31 Oct → 1 Nov)
| Clock | Milestone | Check |
|---|---|---|
| 16:30 | Kickoff, venv on all 4 laptops, E2 | `python scripts/check_env.py` passes |
| 18:00 | **G1 + A1 done; formats frozen** | `hands_baseline.jsonl` for all clips |
| 20:00 | S1 ready → **E1 labelling** | `eval/labels/` has 160 frames |
| 00:00 | **Integration 1:** one clip end to end, app shows it; E3 | Demo path runs on 1 clip |
| 02:00 | **Go/no-go:** PS5 layer solid? else declare PS1 | Decision in log |
| 06:00 | **Feature freeze:** all demo clips processed | Only fixes after this |
| 08:00 | Numbers final, slides drafted; E3 | `metrics.json` frozen |
| 09:30 | **Code freeze, last push** | README one command works on a clean clone |
| 10:00 | Demo videos + slides in Drive | Total video ≤ 2 min |
| 10:00–11:00 | Rehearse twice | Backup recording ready |
Sleep in shifts after 02:00 if needed: never both hands people at once.

## Critical path
G1 (done) → A1 → A2/A3 → (B3, G2) → (S2, B5, G3) → G4 + G5 → G6. If anything on this path slips > 1 h, cut P1 features in this order: F9 safety → F8 Work Module → F7 order check. Never cut F1, F2, F3, F5.
