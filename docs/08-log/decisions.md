# Decisions

Append-only. Format: `YYYY-MM-DD · who · decision · why`

- 2026-10-31 · Gunagye · Shared repo with per-member ideation folders · lets four people ideate in parallel without merge conflicts
- 2026-10-31 · Gunagye · Docs straight to `main`, code via short-lived branches + PR · speed for docs, review for code
- 2026-10-31 · Gunagye · Everything on `main`, no branches or PRs; git sync fully automatic every session (supersedes the branch/PR rule above) · 24 h hack, zero time spent on manual git
- 2026-10-31 · Gunagye · PS5 on PS1: Data Health light + robot dataset export as hero, then step-order, Work Modules, safety · merges all three plans; protects the 30 hand-accuracy points
- 2026-10-31 · Gunagye · No worker-behaviour scoring (drop real-vs-faked rhythm grading) · surveillance optics, no labels to prove it
- 2026-10-31 · Gunagye · Hands: MediaPipe + fixes + rtmlib + WiLoR on flagged frames only · accuracy where it matters, CPU speed elsewhere
- 2026-10-31 · Gunagye · Storage: per-clip files + SQLite index; export LeRobot-style; app Streamlit; Python 3.11 venv · parallel work, fast demo, one language
- 2026-10-31 · Gunagye · Gemini only on short grab/release windows, cached; order-check reference = repeated cycle inside a factory's job · clips are consecutive parts of one job, tasks don't repeat across clips
- 2026-10-31 · Gunagye · Owners: Gunagye export+app+contacts+index, Abhijay hands+WiLoR+metrics, Bhavyam recovery+light+redaction+safety, Shefali labels+steps+modules+slides · see `../06-plan/work-split.md`
- 2026-10-31 · Gunagye · Problem statement PDF stays in `docs/02-problem/` · team reference
- 2026-10-31 · Gunagye · Build protocol: per-member task files with ⛔ checkpoints, team checkpoints TC0–TC6, synthetic fixtures + plug-in stubs so nobody waits; alerts split into `alerts_steps.csv` / `alerts_safety.csv` (one writer per file) · parallel work without blocking
- 2026-10-31 · Gunagye · Footage guard: pre-commit/pre-push/CI block video, images, PDFs, archives, data files (own diagrams only in `assets/diagrams/`); end-of-event deletion checklist with owners · organisers' data-use agreement, breaking it = disqualification
- 2026-10-31 · Bhavyam · Redaction blurs faces only; screens/documents skipped for now · YOLOE takes ~310 ms per frame on CPU against ~20 ms for YuNet, about 28 min per clip; revisit at B-1 if real clips show readable screens
- 2026-10-31 · Gunagye · Brief PDF never goes public; this repo stays private, submission gets a fresh public copy without the PDF and `eval/labels/`; git takes an allowlist of file types only · brief is the organisers' private document, history can't be cleaned without a force-push
- 2026-10-31 · Bhavyam · Screens/documents stay skipped; face cutoff stays 0.6 pending the human spot check · scan of all 40 clips found monitors/screens in 3 and paper in 3 of 1200 frames; weak faces (under 0.8) are often false alarms but cover only ~0.4 % of a frame, while a missed face is a privacy failure
