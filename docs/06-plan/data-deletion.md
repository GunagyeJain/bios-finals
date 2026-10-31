# Data deletion (end of event)

Organisers' data-use rule: delete **every copy** of the data, including uploads to Colab, Kaggle and API file storage, when the event ends. Breaking it means disqualification.
**When:** 1 Nov, right after judging (~11:15), before anyone leaves the venue. **Owner:** Gunagye checks every row is ticked.

## 1. Every laptop (each member, on their own machine)
- [ ] `python scripts/wipe_event_data.py` (dry run), check the list, then `--yes`. Removes `data/egohack-data/`, `outputs/`, `exports/`, `eval/frames/`, `gemini_cache/`.
- [ ] Downloaded archive(s) of the clips (Downloads folder, desktop, USB stick) deleted.
- [ ] Recycle Bin / Trash emptied.
- [ ] Clips, frames or screenshots in phone galleries or team chat (WhatsApp etc.) deleted.

| Member | Laptop | Chat/phone | Time |
|---|---|---|---|
| Gunagye | [ ] | [ ] | |
| Abhijay | [ ] | [ ] | |
| Bhavyam | [ ] | [ ] | |
| Shefali | [ ] | [ ] | |

## 2. Cloud copies
| Where | Owner | Done |
|---|---|---|
| Gemini Files API uploads (script deletes them where `GEMINI_API_KEY` is set; then check AI Studio) | Shefali | [ ] |
| Colab runtime files + any Google Drive folder Colab used for clips / `wilor.jsonl` | Abhijay | [ ] |
| Kaggle datasets / notebooks with clips, if any | whoever made them | [ ] |
| Private team Drive folder (`wilor.jsonl`, renders, demo cuts), then Drive Trash | Gunagye | [ ] |

The submission copy in the **organisers'** Drive is theirs; leave it.

## 3. Public posts (during and after the event)
- No clip, frame or screenshot of the footage anywhere public: GitHub, LinkedIn, YouTube, Instagram.
- Posts about the project use our own diagrams (`assets/diagrams/`) and numbers only.
- The git hooks block footage, frames, PDFs and data files (`scripts/check-files.sh`); never bypass them.

## 4. Making the repo public (submission)
Never flip this repo to public: its history holds the private brief. Instead push a fresh single-commit copy of `main` to a new public repo, without `docs/02-problem/problem-statement.pdf`, `docs/02-problem/brief.md` text copied from it, and `eval/labels/` (coordinates from the clips). Owner: Gunagye, before 11:00.
