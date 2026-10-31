# Checkpoints

Two kinds. **Personal** checkpoints (⛔ in each task file): the session stops after a task until the member reviews it and says `continue`. **Team** checkpoints (below): fixed clock times, everyone pushes, Gunagye runs the integration on his laptop, 10-min sync, then go.

Protocol and report template: `start.md` §5.

## Team checkpoints (31 Oct → 1 Nov)
| ID | Clock | Gate: all must be true | Human check (look at this) | If it fails |
|---|---|---|---|---|
| **TC0** | now | Foundation on `main`: `pytest -q` passes, `python -m egovision fixtures` + `check` OK, every stage skips cleanly | Gunagye runs `python -m egovision run --clip fixture_002` | — (done in this commit) |
| **TC1** | 18:30 | All 4 laptops pass `check_env.py` · A1 baseline on all real clips · mirror decision logged · B4, G2, S1 first versions pushed | Abhijay's `preview_baseline.mp4` on one demo clip: are left/right right? | Mirror unclear → Abhijay + Bhavyam watch 2 clips together, decide in 10 min |
| **TC2** | 21:00 | **160 frames labelled** (40 each) · contacts + quality on 1 real clip · S2 Gemini steps on 1 real clip | Fixture app pages render; contact intervals vs video for 1 min of a real clip | Labels late → label before anything else; it blocks every number |
| **TC3** | 00:00 | **Integration 1:** one real demo clip end to end (`run --clip <demo>` all stages ok) and visible in the app · walkthrough round (5 min each) | Gunagye opens the app: library → review → export on the demo clip | Fix the broken stage first; others keep building on fixtures |
| **TC4** | 02:00 | **Go/no-go:** light + export + at least one of steps/modules/safety work on the demo clip; A5 numbers show improvement over baseline | Metrics page: baseline vs ours; green vs red accuracy | No-go → declare PS1 to organisers; cut F9 → F8 → F7 (work-split.md §Critical path) |
| **TC5** | 06:00 | **Feature freeze:** all demo clips processed; WiLoR results merged; no new features after this | Watch every demo render at 2× speed; list the 3 worst moments | Only fix those 3 moments + crashes |
| **TC6** | 09:30 | **Code freeze:** README one command works on a fresh clone (Shefali tests on her Mac) · last push | Fresh clone: `pip install -r requirements.txt && pip install -e . && python -m egovision run --clip fixture_001` | Revert the last change that broke it |
| — | 10:00 | Demo videos (≤ 2 min) + slides in organisers' Drive | Shefali plays the demo video once, start to end | — |
| — | 10:00–11:00 | Rehearse twice; backup recording on 2 laptops | Timer: 5 min | — |

## Personal checkpoint map (one ⛔ per task, details in the task files)
| Member | Checkpoints |
|---|---|
| Gunagye | G2 contacts · G3+G5a app on fixtures · G4 export · G5b app on real clip · G6 integration |
| Abhijay | A1 baseline + mirror · A2–A3 clean tracks · A4 WiLoR · A5 metrics |
| Bhavyam | B4 redaction · B3 light · B1–B2 recovery · B5 safety |
| Shefali | S1 label tool · S2 steps · S3 order check · S4 Work Module · S5 pages · S6 README/slides |

## Dependency map (who unblocks whom, and the fallback meanwhile)
| Needs | From | Fallback until then |
|---|---|---|
| Real `hands_baseline.jsonl` | A1 | fixture hands |
| Final `hands.jsonl` | A2–A4 | `hands_input()` uses baseline |
| `recover_missing`, `agreement` | B1–B2 | no-op defaults in `recovery/api.py` |
| `redact_frame` | B4 | identity default in `quality/redact.py` |
| `objects.jsonl`, `contacts.csv` | G2 | fixture files; S2 uses fixed 8 s windows |
| `quality.csv` | B3 | fixture file; export treats missing quality as yellow |
| `steps.csv` | S2 | fixture file |
| `index.db` | G3 | pages read fixture files directly via `ClipPaths` |
| Labels `eval/labels/` | E1 (everyone) | A5 runs on whatever labels exist; numbers marked partial |
| `wilor.jsonl` | A4 (GPU) | refine keeps MediaPipe/rtmlib result + flag |
