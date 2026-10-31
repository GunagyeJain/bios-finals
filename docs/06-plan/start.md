# Start protocol (build phase)

When a member types **`start`** (or **`continue`**) in their coding session, follow these steps exactly.

## 1. Every time
1. Sync: `git pull --rebase --autostash`.
2. Find the member: match `git config user.name` to `docs/01-team/team.md`. Open `docs/06-plan/tasks/<firstname>.md` (lowercase). Not sure → ask the member.
3. Read only: `STATUS.md`, that task file, and the docs under its **Read first**. Nothing else unless a task says so.
4. Take the **first unchecked task**. If the member replied `continue` after a checkpoint, apply their feedback first.

## 2. First time on a laptop (setup, ~15 min)
```
python -m venv .venv
.venv\Scripts\activate            # Mac: source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
python scripts/check_env.py       # every line OK (GEMINI_API_KEY only needed by Shefali)
python -m egovision fixtures      # synthetic clips fixture_001/002 with every output
pytest -q                         # all pass
```
Real clips: put the organisers' folder at `data/egohack-data/` (`clips_480p/` inside). It is git-ignored. Never move clips anywhere else.

## 3. How to build without waiting for anyone
- **Your files only.** Each task file lists them. Never edit another member's folder.
- **Shared files** (`src/egovision/schema.py`, `config.py`, `stages.py`, `__main__.py`, `contract.py`, `requirements.txt`): don't edit them. Write the change you need under **Requests** in your task file, push, and tell Gunagye in chat. He merges it within 30 min.
- **Inputs not ready yet?** Every stage has a fallback:
  1. Develop and test on `fixture_001` / `fixture_002`. They contain every file of the contract.
  2. On real clips, use `ClipPaths(clip).hands_input()` (final hands if they exist, else baseline).
  3. Each task lists its own fallback (e.g. fixed windows instead of contacts).
- **Plug-in functions** (`recovery/api.py`, `quality/redact.py`) have fixed signatures and safe defaults. Callers use them now; owners fill them in later. Never change a signature without a Request.
- Thresholds go in your module's own `params.py`, never in `config.py`.

## 4. Definition of done (every task)
1. The task's **Done when** passes.
2. `pytest -q` passes. Add at least one test for the pure logic of your task (synthetic data, never footage).
3. `python -m egovision check --clip fixture_001` and, where your stage ran, `--clip <real clip>` show no FAIL.
4. Commit + push: `<type>(<area>): <what>`, e.g. `feat(hands): track ids and side voting`. Then tick the task box in your task file, commit, push.
5. Update your row in `STATUS.md` → **In progress** (one line, your row only).

## 5. Checkpoints: stop and wait for a human
- A line starting with **⛔ CHECKPOINT** means: finish and push the task, then **stop**. Post the report below and wait.
- Only the member's reply `continue` (or feedback) unlocks the next task. Silence is not approval.
- **Team checkpoints** (`checkpoints.md`) happen at fixed clock times. When one is due, finish the current small step, push, post the report, then join the team sync.

Report template (post exactly this, short):
```
CHECKPOINT <id> · <member> · <time>
Built: <1–3 bullets, what now works>
See it: <one command + what to look at, e.g. open outputs/factory_003/preview_baseline.mp4 at 1:20>
Numbers: <measured numbers, or "none yet">
Problems: <what failed or looks wrong, honestly>
Next: <next task id + one line>
Needs from others: <none / Request to X>
```

## 6. Rules that never bend
- **No footage in git**: no videos, frames, screenshots, notebook image outputs. `outputs/`, `exports/`, `data/egohack-data/`, `eval/frames/`, `gemini_cache/` stay local (git-ignored). Coordinates and CSVs of real clips also stay in `outputs/`.
- Share big results (e.g. `wilor.jsonl`, demo renders) only through the **private team Drive folder**.
- API keys only in environment variables. Never commit `.env`.
- Never `--no-verify`, never force-push, never rewrite history. Push rejected → pull with rebase, push again.
- Docs, comments and commit messages describe the code only.
- Blocked > 30 min → say it in chat and take your next task (or the fallback).
