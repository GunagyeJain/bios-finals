# Work split

_Hard stop: **1 Nov 11:00**. Scope: `../05-solution/prd.md`. How: `../05-solution/trd.md`. Formats: `../05-solution/data-schema.md`._
Rule: finish your P0 tasks before P1. Blocked > 30 min → say so in chat, take the next task.

## Owners
| Member | Machine | Owns |
|---|---|---|
| **Gunagye** | Yoga, Ultra 7 CPU | Skeleton + schemas + CLI, contacts, SQLite index, **robot export (hero)**, Streamlit shell + main pages, integration |
| **Abhijay** | Omen, RTX 3050 | Hands core, WiLoR on GPU, eval metrics |
| **Bhavyam** | LOQ, RTX 2050 | Hand recovery (rtmlib, ROI), Data Health light, redaction, safety alerts |
| **Shefali** | MacBook Air M4 | Label tool, Gemini steps + order check, Work Modules, 2 app pages, README, slides, demo video |

## Tasks (h = estimated hours)
### Gunagye
| ID | Task | h | Needs | Done when |
|---|---|---|---|---|
| G1 | Skeleton: `src/egovision/` folders, `schema.py`, `config.py`, `io/frames.py`, CLI stubs, `requirements.txt`, `scripts/check_env.py`, `.streamlit/config.toml` | 1.5 | — | `python -m egovision run --clip X --stage hands` calls Abhijay's function |
| G2 | Objects + contacts: YOLOE vocab, contact rule + hysteresis → `objects.jsonl`, `contacts.csv` | 3 | A1 | Grab/release on one clip looks right in the render |
| G3 | SQLite index builder | 1.5 | G1 | `index.db` from any processed clip |
| G4 | **Robot export** LeRobot-style + `datasheet.md` | 3 | G3, B3, B4 | `export --name demo_v1` builds; parquet loads |
| G5 | App: Library, Clip review (timeline + video jump), Export page, `components.py` | 4.5 | G3 | Demo path in `../05-solution/app-flow.md` §3 works |
| G6 | Integration: `run --all`, render overlay, process demo clips | 1.5 | all | All demo clips in the app |

### Abhijay
| ID | Task | h | Needs | Done when |
|---|---|---|---|---|
| A1 | MediaPipe baseline on all clips (`hands_baseline.jsonl`), mirror check on 3 clips | 1.5 | G1 (or start standalone) | Files for every clip; mirror answer in decisions log |
| A2 | Track IDs + side voting + re-entry | 2.5 | A1 | Swaps/min drops on demo clips |
| A3 | Sanity checks, gap fill, One-Euro → `hands.jsonl` | 2 | A2 | Jitter before/after number |
| A4 | WiLoR on GPU for flagged frames + fuse; % frames escalated | 4 | A3, B1 | Before/after on hardest 10 s |
| A5 | Metrics from labels → `metrics.json` (recall, L/R, PCK, swaps, jitter, FPS, per-light accuracy) | 2 | S1 labels | Numbers for slides |
| A6 | Tune thresholds on demo clips; fix biggest failure | rest | A5 | — |

### Bhavyam
| ID | Task | h | Needs | Done when |
|---|---|---|---|---|
| B1 | rtmlib second opinion + agreement score | 2.5 | A1 | `agreement` filled in `hands.jsonl` |
| B2 | ROI re-detect + CLAHE on dark frames, A/B kept only if recall rises | 2 | A2 | Recall up on dark/blur labels |
| B3 | Data Health checks + light + reasons → `quality.csv` | 3 | A3 | Light bar looks right on 3 clips |
| B4 | Redaction (faces, screens) for export + module videos | 1.5 | — | 20-frame spot-check: no faces |
| B5 | Safety: moving-machine proximity → `alerts.csv` | 2 | G2 | Alerts on at least one demo clip, checked by eye |
| B6 | P2: capture-feedback paragraph in datasheet | 1 | B3 | — |

### Shefali
| ID | Task | h | Needs | Done when |
|---|---|---|---|---|
| S1 | Label tool (OpenCV click: side, box, wrist, 5 tips) + label-frame picker (60 % hard, 40 % random) | 1.5 | — | Everyone can label 40 frames |
| S2 | Gemini step captioner on grab/release windows, cached → `steps.csv` | 2.5 | G2 | Steps for one demo clip |
| S3 | Order check per factory (reference cycle, alignment) → `alerts.csv` | 2 | S2 | Alerts or "no reference" per factory |
| S4 | Work Module generator (ffmpeg cuts, captions, overlay, title card) | 3 | S2, B4 | ≤ 60 s MP4 for one task |
| S5 | App pages: Work Modules, Metrics | 1.5 | G5 components, A5 | Pages render from `index.db` |
| S6 | README (setup, one command, tools list, hardware), 5–6 slides, demo video ≤ 2 min, Drive upload | 3 | all | Submitted before 10:30 |

### Everyone
- **E1 Labelling:** 40 frames each with S1's tool; 30 frames double-labelled by Abhijay + Bhavyam for agreement. ~30 min.
- **E2 First look:** skim 5 clips each, log factory, task, gloves, machines, demo clips in `../04-research/clip-notes.md`. ~20 min.
- **E3 Walkthroughs:** each person explains their module in 5 min at 00:00 and 08:00 (judges ask anyone anything).

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
G1 → A1 → A2/A3 → (B3, G2) → (S2, B5, G3) → G4 + G5 → G6. If anything on this path slips > 1 h, cut P1 features in this order: F9 safety → F8 Work Module → F7 order check. Never cut F1, F2, F3, F5.
