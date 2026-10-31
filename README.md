# Caffeinated Nerds · BIOS Hackathon Finals

Team **Caffeinated Nerds** — Thapar Institute BIOS Hackathon, offline finals (24 h, ends **1 Nov 2026, 11:00**).

> Project name, one-line pitch and demo link go here once the idea is final.

- **Where we are right now:** [`STATUS.md`](STATUS.md)
- **How we work (git, files, commits):** [`CONTRIBUTING.md`](CONTRIBUTING.md)
- **Problem statement:** [`docs/02-problem/problem-statement.pdf`](docs/02-problem/problem-statement.pdf)

## Team
| Name | GitHub |
|---|---|
| Gunagye Jain | [@GunagyeJain](https://github.com/GunagyeJain) |
| Bhavyam Misra | [@bhavyammisra](https://github.com/bhavyammisra) |
| Shefali Sharma | [@shefali1702](https://github.com/shefali1702) |
| Abhijay Nagal | _add_ |

Hardware per person: [`docs/01-team/hardware.md`](docs/01-team/hardware.md).

## Getting started (once per laptop)
```bash
git clone https://github.com/GunagyeJain/bios-finals.git
cd bios-finals
git config user.name  "Your Name"
git config user.email "you@example.com"   # must be in .github/team-emails.txt
sh scripts/setup.sh                        # enables the commit hooks
```
Windows: run the commands in **Git Bash**.

## Repo map
```
README.md            this file (project overview, filled in after ideation)
STATUS.md            live state: phase, deadlines, who is doing what
CONTRIBUTING.md      workflow rules: syncing, file rules, commits, branches
docs/
  00-hackathon/      event facts: organisers, timeline, rules, judging
  01-team/           members, contacts, hardware
  02-problem/        official problem statement + our reading of it
  03-ideation/       one folder per member + synthesis/ (merged shortlist)
  04-research/       datasets, prior art, domain notes
  05-solution/       architecture, ML approach, API (after the idea is chosen)
  06-plan/           work split by person/hardware, task list
  07-pitch/          deck, demo script, judge Q&A
  08-log/            decisions.md (append-only) + meeting notes
src/                 application code (structure decided after ideation)
notebooks/           experiments, EDA, training notebooks
tests/               automated tests
data/                datasets (raw/ and processed/ are git-ignored)
models/              trained weights (git-ignored; links in models/README.md)
assets/              images, screenshots, diagrams
scripts/             setup and helper scripts
```
