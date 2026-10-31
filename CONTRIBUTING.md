# Contributing

Four people, four laptops, 24 hours. These rules keep us out of each other's way.

## 1. Git is automatic — nobody does it by hand
Every session handles git itself. No one should have to type a git command or click anything on GitHub.
1. **Before any work** (start of the session and before every task): `git pull --rebase --autostash`.
2. Read `STATUS.md`, then the `_index.md` of the folder you are working in. Open only the files you need.
3. **After every change**, without asking: `git add -A` → commit (format in §6) → `git pull --rebase --autostash` → `git push`.
4. **Never end a session with uncommitted or unpushed work.** Check `git status` is clean and nothing is ahead of `origin/main`.
5. Push fails because someone pushed first? Pull with rebase and push again, automatically.

## 1b. Build phase: `start`
Typing **`start`** (or **`continue`**) in a coding session follows `docs/06-plan/start.md`: sync, open your task file in `docs/06-plan/tasks/`, build the next unchecked task in your own files, stop at every ⛔ checkpoint until you say `continue`.

## 2. Where things go
| Folder | What |
|---|---|
| `docs/00-hackathon/` | Event facts (rules, timeline, judging). Facts only, with source. |
| `docs/01-team/` | Members, contacts, hardware |
| `docs/02-problem/` | Official statement (do not edit the PDF) + `understanding.md` |
| `docs/03-ideation/<your-name>/` | **Your** ideas. Only you write in your folder. |
| `docs/03-ideation/synthesis/` | Merged shortlist and final pick (Gunagye compiles) |
| `docs/04-research/` | Datasets, prior art, domain notes |
| `docs/05-solution/` | Architecture, ML approach, API contract |
| `docs/06-plan/` | Work split, tasks, milestones |
| `docs/07-pitch/` | Deck, demo script, Q&A |
| `docs/08-log/` | `decisions.md` (append-only), `meetings/` |
| `src/`, `notebooks/`, `tests/` | Code |
| `data/`, `models/` | Large files: git-ignored, share links in their README |

## 3. File rules (docs)
- Markdown only for notes. One topic per file. `kebab-case.md` names.
- **Max ~150 lines per file.** Bigger? Split into a subfolder with its own `_index.md`.
- Every docs folder has an `_index.md` with one line per file. Add/rename/delete a file → update it.
- Facts get a source link. Guesses get tagged `(assumption)`. Link to other files instead of copying.
- Phase or to-do changed → update `STATUS.md`. Decision made → append to `docs/08-log/decisions.md`.

## 4. Ideation flow
1. Copy `docs/03-ideation/idea-template.md` into your own folder as `idea-<short-name>.md`. One idea per file.
2. Write freely in your folder — nobody else edits it, so no conflicts.
3. Push. When everyone is done, ideas are merged into `docs/03-ideation/synthesis/`, scored, and one is chosen.
4. The pick and the reasons go into `docs/08-log/decisions.md`.

## 5. Branches: just `main`
- **Everything (docs and code) goes straight to `main`.** No feature branches, no pull requests.
- Small, frequent commits keep `main` close to everyone's copy, so rebases stay trivial.
- Don't push code that breaks someone else's part. Unfinished code stays in your own file/module until it runs.
- Never force-push. Never rewrite pushed history.

## 6. Commits
- Format: `<type>(<area>): <what>` — types `feat fix docs refactor test chore data`.
  Example: `docs(ideation): add idea-offline-sync`.
- **One author per commit: you.** No `Co-authored-by` trailers, no tool-generated footers.
  The hooks strip/block these and CI rejects them. Your `git config user.email` must be in
  `.github/team-emails.txt` (add yours there if you use a different address).
- Never commit secrets (`.env`, keys, tokens), raw datasets, or model weights.

## 7. Conflicts
Resolved during the automatic pull: `git status` → fix the marked files → `git add` → `git rebase --continue` → push.
- Both edits clearly belong (e.g. two new lines in an `_index.md` or table): keep both, no need to ask.
- Same lines changed in different directions, or someone else's code: stop and ask the user which version wins.
- `git rebase --abort` gets back to a clean state if anything looks wrong.
