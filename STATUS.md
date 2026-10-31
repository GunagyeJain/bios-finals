# STATUS

_Updated 2026-10-31 by Gunagye_

Spec: `docs/05-solution/prd.md` · `trd.md` · `app-flow.md` · `data-schema.md` · `ui-design.md`

## Now
- **Phase:** **Sprint 2**: follow `docs/06-plan/sprint-2.md` (cuts, demo clips, timeline to 05:00, one prompt per member). No personal checkpoints.
- **Hack window:** 24 h · **hard stop: 1 Nov 2026, 11:00** (submission must be in before this)
- **Submission status:** not started · who submits: _fill in_

## Next steps
- [x] Repo structure, rules, commit hooks, automatic git sync
- [ ] Everyone: clone + run setup (onboarding message), add hardware details to `docs/01-team/hardware.md`
- [x] Everyone: ideas in `docs/03-ideation/<name>/`
- [x] Synthesis: merge, score, pick one → `docs/03-ideation/synthesis/`, `docs/08-log/decisions.md`
- [x] Solution design → `docs/05-solution/`
- [x] Work split by hardware → `docs/06-plan/work-split.md`
- [ ] Build → `src/` (type `start` in your session; see `docs/06-plan/start.md`)
- [ ] Pitch + demo → `docs/07-pitch/`
- [ ] Submit

## In progress
| Who | What |
|---|---|
| Gunagye | Sprint 2: hand + forearm masks in render, 3 demo clips end to end, Metrics page |
| Abhijay | Done: A6 frozen (recall 41 to 66, L/R 96.6 to 95.7 on 282 hands), `validate_export.py` (11/11 on a real export), `where-it-fails.md`. Gloves and dark have no labelled frames |
| Shefali | Done: 40 labels, S2 (gemini-3.8-flash, mocked tests; Gunagye runs demo clips), S3 order check, README, slides.md + demo script + Q&A · Next: deck export from slides.md once Metrics numbers exist, demo video, 09:30 fresh-clone test |
| Bhavyam | Done: B3 on final hands (59 / 16 / 25 green, yellow, red on 40 clips), B5 (0 alerts on demo clips after eye check failed, keep Safety out of the demo), B6, labels, business + legal text, `robot_overlay.py`, `robot-view.md` · Now: face blur precision, real-clip overlay check · **Flag:** robot-fit rests on unlabelled grabs with median confidence 0.15; see `robot-view.md` |
| All | E2 skim 5 clips each → `docs/04-research/clip-notes.md` |

## Key dates
| When | What |
|---|---|
| 2026-10-31 ~11:00 | Finals start (on-site, Thapar) |
| **2026-11-01 11:00** | **Finals end: submission + judging** |
| 2026-11-01 ~11:15 | Delete every copy of the footage: `docs/06-plan/data-deletion.md` |

## Open questions
- Sponsors / partners and any sponsor-specific prizes?
- Which clips are the demo clips?
- Files in our `clips_480p/` are 1920x1080, not 480p: is that the organisers' folder, or the full-res set?
