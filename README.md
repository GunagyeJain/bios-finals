# EgoVision Data Engine

Team **Caffeinated Nerds** · Thapar Institute BIOS Hackathon finals, 31 Oct to 1 Nov 2026.

A laptop pipeline that turns raw head-camera factory video into graded, robot-ready hand data: hand tracks,
grab/release contacts, task steps with order checks, safety alerts, and a dataset export, reviewed in one app.

## Problem statement
**PS5 (open innovation) built on PS1 (hand tracking).** PS2 contacts and PS3 task steps are building blocks.
Every result reads the same hand tracks, so better hands improve everything downstream.

## Hardware
**Laptop only, CPU, no GPU and no cloud GPU.** The pipeline was built and run on four laptops (Apple M4,
Intel Core Ultra 7 155H, Intel i7-13700HX, and a Lenovo LOQ), all on CPU. The only cloud call is the Gemini
API for step captions, on short clips with faces blurred.

## Setup (once)
Python 3.11 and git.
```bash
git clone https://github.com/GunagyeJain/bios-finals.git
cd bios-finals
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
python scripts/check_env.py        # every line should say OK
```
Put the organisers' clip folder at `data/egohack-data/` (with `clips_480p/` inside). It is git-ignored and is
never part of this repo. For step captions, set `GEMINI_API_KEY` in your shell (free key from Google AI Studio).
Without it the pipeline still runs and steps fall back to grab/release windows.

## The one command
```bash
python -m egovision run --all
```
Runs every stage on every clip and writes `outputs/<clip>/`. Stages whose output exists are skipped, so a
stopped run resumes. Then open the app:
```bash
streamlit run app/Home.py
```
Other commands: `python -m egovision run --clip <clip> --stage <stage> --force` (one stage),
`python -m egovision check --clip <clip>` (validates outputs), `python -m egovision index`,
`python -m egovision export --name demo --light green` (robot dataset from green segments only).

## What the pipeline does
| Stage | Output | How |
|---|---|---|
| `hands_baseline` | `hands_baseline.jsonl` | MediaPipe Hand Landmarker, VIDEO mode, every 2nd frame |
| `hands` | `hands.jsonl` | Track IDs, left/right side voting per track, smoothing, gap fill to every frame |
| `quality` | `quality.csv` | Green/yellow/red light per second with reasons (dark, blur, hands out of view, frozen) |
| `contact` | `objects.jsonl`, `contacts.csv` | YOLOE text-prompt objects; fingertip-in-box rule with hysteresis; portable vs fixed; grip type |
| `steps` | `steps.csv` | Windows between grab/release events, cut to 480p with faces blurred, captioned by Gemini with a fixed verb list; cached |
| `order` | `alerts_steps.csv` | Reference cycle per factory (marked in the app, or the most frequent repeated cycle); each cycle aligned by edit distance: missing, out-of-order, extra steps |
| `safety` | `alerts_safety.csv` | Fingertips near a moving fixed machine part |
| `render` | `render.mp4` | Hands, masks and events drawn on the video for the app |
| `export` | `exports/<name>/` | LeRobot-style episodes (Parquet + JSON), green segments only, faces blurred, datasheet |

Formats: [`docs/05-solution/data-schema.md`](docs/05-solution/data-schema.md). Design:
[`docs/05-solution/trd.md`](docs/05-solution/trd.md).

## Results
Measured by us on frames we labelled by hand (`eval/`, `python -m egovision.eval.metrics --clip <clip>`).

> **TO FILL from `metrics.json` before submission. Do not invent numbers.**

| Metric | Baseline MediaPipe | Ours |
|---|---|---|
| Hands found (recall on labelled frames) | _[TO FILL]_ | _[TO FILL]_ |
| Left/right correct | _[TO FILL]_ | _[TO FILL]_ |
| PCK@0.2 (wrist + 5 fingertips) | _[TO FILL]_ | _[TO FILL]_ |
| Left/right swaps per minute | _[TO FILL]_ | _[TO FILL]_ |
| Accuracy on green vs red seconds | _[TO FILL]_ | _[TO FILL]_ |

Speed: the MediaPipe hand stage ran at 43.6 FPS on a 3-minute 1080p demo clip (every 2nd frame) on an
Apple M4, CPU only. Speeds for every stage: _[TO FILL from metrics.json]_.

What failed: _[TO FILL: the biggest failure cases we found and what we did about them]_.

### Labels and how we kept them honest
`python -m egovision.eval.label_tool --clip <clip> --labeller <name> --web` picks 60 % hard frames (baseline
misses, dark seconds) and 40 % random ones. `python -m egovision.eval.prelabel` can pre-fill points from rtmlib
(RTMPose hand); every saved hand records whether it was pre-filled and edited. A shared 30-frame set is always
labelled fully by hand by every labeller, so the numbers can show whether pre-filling biased them.

## Libraries, models and APIs
| Tool | Used for | Licence |
|---|---|---|
| MediaPipe Hand Landmarker | Hand points (baseline and tracks) | Apache-2.0 |
| rtmlib (RTMDet + RTMPose hand) | Label pre-filling | Apache-2.0 |
| Ultralytics YOLOE + CLIP | Text-prompt object boxes for contacts | AGPL-3.0 (YOLOE), MIT (CLIP) |
| YuNet face detector (OpenCV Zoo) | Face blurring in everything we export or send | MIT |
| Google Gemini API (`google-genai`) | Step captions on short blurred windows | API terms of service; SDK Apache-2.0 |
| OpenCV, NumPy, SciPy, pandas, PyArrow | Video, maths, tables, Parquet | Apache-2.0 / BSD |
| ONNX Runtime | rtmlib inference on CPU | MIT |
| imageio-ffmpeg | H.264 video writing | BSD-2 (bundles FFmpeg, LGPL/GPL) |
| Streamlit, Plotly | Review app and charts | Apache-2.0, MIT |
| pytest | Tests (synthetic data only) | MIT |

## Data rules we follow
- No videos, frames, screenshots or per-clip outputs in git (`outputs/`, `exports/`, `data/egohack-data/`
  are git-ignored; commit hooks and CI block media files).
- Faces are blurred before anything leaves the laptop (Gemini windows, exports).
- Gemini windows are sent inline with each request, not uploaded to file storage.
- Every copy of the footage is deleted after the event.

## Repo map
```
src/egovision/   pipeline: hands, quality, contact, steps, safety, products, eval, index
app/             Streamlit review app
tests/           pytest on synthetic data
docs/            plan, design, decisions log
eval/labels/     our hand labels (coordinates only)
scripts/         setup and environment check
```

## Team
| Name | GitHub | Built |
|---|---|---|
| Gunagye Jain | [@GunagyeJain](https://github.com/GunagyeJain) | Core, contacts, render, export, app |
| Abhijay Nagal | _add_ | Hand tracking, metrics |
| Bhavyam Misra | [@bhavyammisra](https://github.com/bhavyammisra) | Quality light, redaction, safety |
| Shefali Sharma | [@shefali1702](https://github.com/shefali1702) | Label tool, step captions, order check, pitch |

Workflow: [`CONTRIBUTING.md`](CONTRIBUTING.md) · live status: [`STATUS.md`](STATUS.md).
