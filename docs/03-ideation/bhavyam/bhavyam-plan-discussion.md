# BIOS Finals × Mytron Labs: Team Plan

**Team:** Caffeinated Nerds (Bhavyam, Gunagye, Abhijay, Shefali) · **Track:** FORGE, Mytron Labs private brief · **Challenge:** Egocentric Vision, factory video to useful data

> **How this file merges.** **Part A** is the research + plan by Bhavyam. **Part B** is for teammates' research. Number your sections `B1, B2…` and ideas `B-<letter><n>` so nothing collides.
> After both are in, fill **Section C (Combined decisions)** together; that table is final.
> Disagree with something? Reference its ID (e.g. "disagree with D4") in **Open questions** instead of silently editing.

---

## 0. The A–B–C model (read this first)

Three companies. Every idea in this file is described with these letters.

```
   COMPANY A                       COMPANY B                        COMPANY C
   The factory                     MYTRON LABS                      The customer
   (data source)                   (who we build for)               (buys data)
  ┌────────────┐   raw head-cam   ┌──────────────────┐  clean,      ┌────────────────┐
  │ Workers do │ ───────────────► │ Our product runs │  labelled    │ Robotics / AI  │
  │ real tasks │    footage       │ here:            │  datasets ─► │ companies      │
  │            │ ◄─────────────── │ hands, contact,  │  benchmark   │ (and any new   │
  │            │  B pays A; A can │ Data Health light│  clips   ─►  │ buyer "D" is   │
  │            │  buy Work Modules│ modules, export  │              │ just another C)│
  └────────────┘                  └──────────────────┘              └────────────────┘
```

| Letter | Who | What they give | What they get |
|---|---|---|---|
| **A** | The factory where the footage is recorded | Raw egocentric video of workers doing real tasks | Payment from B, plus the option to **buy Work Modules** (training videos for new workers) built from their own footage |
| **B** | **Mytron Labs**, the company we are building this product for | Our pipeline turns raw video into clean, labelled, quality-checked data | Products to sell to C (and A) |
| **C** | Customers: robotics / embodied-AI companies (a new buyer "D" is simply another C) | Money | **Datasets** for training, **Benchmark clips** (human reference) to evaluate their robots |

**What we build in the hackathon is B's engine:** the part that turns A's raw footage into something C will pay for, and something A can use.

---

# PART A: Research and plan (Bhavyam)

## A1. TL;DR

1. **Hand tracking is the base of everything.** It's worth 30/100 whatever we choose, judges check it frame by frame on the demo clips, and it breaks ties.
2. **Our open innovation (PS5): the "Data Health" layer + products for A and C.**
   - Every segment of footage gets a 🟢🟡🔴 light with a reason ("too dark", "camera too high", "hands out of frame", "trackers disagree").
   - Green data becomes **Datasets** and **Benchmark clips** for C, and **Work Modules** for A.
3. **The light is pointed at the footage, never at the worker.** We don't build "this worker is hiding something" flags (see A5.4).
4. **Main technical idea:** a cheap laptop pipeline that measures its own quality and confidence, fixes what it can, and sends only the hard frames to heavier models or a human.
5. **Prove it with numbers:**
   - Baseline vs ours on 150+ frames we label ourselves.
   - Tracking accuracy on 🟢 vs 🔴 segments, which proves the light means something.
   - Honest failure cases.
6. **Fallback:** if the PS5 product isn't solid by **H+14**, tell the organisers we're on **PS1** and polish hands + the light.
7. **Environment:** the repo is ready. `setup.ps1` sets it up, then `python -m egovision run --clip <clip>` runs the baseline.

---

## A2. What B (Mytron) wants, and how we're judged

**About B**
- MyTron Labs (Bangalore, 11–50 people) is "building the data backbone for Physical AI".
- It captures egocentric video (video, audio, depth, IMU) and sells **annotated datasets**, including "hand-object interaction tracking and grasp analysis".
- It also hires human **data annotators**. The hackathon is about automating that labelling.

**Uses the brief names:**
- Robots learning by watching people.
- Checking assembly steps were done in the right order.
- **Training material for new workers.**
- Spotting unsafe hand positions.

**Facts from the brief**
- 20 clips of about 3 minutes each, plus 480p copies, **no labels**, low-quality typical Indian factory footage.
- **No automatic leaderboard.** Judges watch our output on the demo clips.
- Missed hands count directly against accuracy.
- Showing how we detect and fix our own mistakes impresses them.

| Rubric | Points | How we win it |
|---|---|---|
| Hand-tracking accuracy | 30 | No missed hands, no left/right swaps, stable through blur, gloves and occlusion on demo clips |
| Results for our PS (PS5) | 20 | Data Health light working on real clips; at least one product output (Work Module or dataset export) |
| Technical approach | 15 | Real work beyond starter code: self-checking, cross-model agreement, A/B-tested enhancement |
| Usefulness to industry | 10 | Clear A–B–C value story: less money spent labelling bad footage, ready-to-sell data |
| Innovation | 10 | Quality light proven against accuracy; capture-feedback loop; Work Modules from the same data |
| Efficiency | 5 | Laptop FPS; % of frames needing a GPU or human |
| Presentation and honesty | 10 | Baseline vs ours, failures shown, legal/consent limits stated |

> **Important:** we won't really "train a model on the 20 clips". They have no labels. We use pretrained models plus our own fixes, and at most fine-tune a small piece on labels we create (H14). Judges check our labels by watching the demo clips.

---

## A3. Problem statement choice

| Option | Verdict |
|---|---|
| **PS5 open innovation (chosen)** on strong PS1 hands + grab/release from PS2 | Best story for B; uses the same hand data; the brief explicitly lists "quality filters" and "training-video generation" as PS5 examples |
| PS1 only | **Fallback at H+14.** Safest, but weaker on usefulness and innovation |
| PS2 / PS3 / PS4 as primary | Not chosen. We reuse cheap parts: PS2 contact rule → step boundaries; PS3 Gemini captions; PS4 skipped |

**Rule:** 2 of 4 people stay on hand tracking for the whole event. PS5 features never take time from the 30 points.

---

## A4. The business model (A–B–C) and its loopholes

### A4.1 What B sells

| Product | Buyer | What it is | Built from |
|---|---|---|---|
| **1. Training Dataset** | C | Green segments only, with hand keypoints, left/right, grab/release events, object names, quality tags, faces blurred | Hands + Data Health + contact |
| **2. Benchmark (evaluation) clips** | C | Short, clean clips of a human doing a defined task, with step labels, timings and hand trajectories. C runs its robot on the same task and compares: completion, time, step order, grip | Same pipeline + step segmentation |
| **3. Work Modules** | A | Training videos for new workers: the key steps of a task, cut from the clearest green clips, with captions and a hand overlay showing the grip | Same pipeline + captions |

Any new buyer "D" is just another C. A buying Work Modules turns A from only a data supplier into a customer too, which gives A a reason to keep sharing footage.

### A4.2 Verdict: good idea

- **One pipeline, three products.** The same labels serve C's training, C's evaluation and A's training. Little extra engineering.
- **A gets value back.** This is the strongest part: A isn't just paid once, it gets something useful from its own footage, which makes A more willing to keep recording.
- **Benchmark clips are a real need.** Robotics teams need human reference demonstrations to compare robots against.

### A4.3 Loopholes we found (and how to handle each)

| # | Loophole | Why it matters | How we handle it |
|---|---|---|---|
| L1 | **Who owns the footage?** A's workers, A's processes, filmed by B. | B may not have the right to resell A's footage to C at all, unless the contract with A allows it | Contract must state ownership, resale and sublicensing rights, and revenue share. Future scope (A11) |
| L2 | **Worker consent.** Faces, voices and bodies are personal data. | India's DPDP Act needs **specific consent for a stated purpose**. Consent to "record for training" may not cover "sell to robotics companies". Withdrawal must be easy | Separate consent per purpose, in the worker's language; auto-blur faces (D9); delete on withdrawal |
| L3 | **A's trade secrets.** Clips show A's assembly process, machines, documents. | C might be A's competitor, or build robots for A's competitor. A may refuse to share | A approves which clips are sold; blur screens and documents; exclusion list of C's that A forbids |
| L4 | **"Why would A pay for its own footage?"** | Work Modules only sell if B adds real value | Value = auto step-cutting, captions, grip overlay, picking the clearest clip, ready in hours instead of weeks. Price it as a service, not as data |
| L5 | **Choosing "the best clip" can turn into ranking workers.** | Same surveillance trap as the rejected idea (A5.4) | Clips are chosen by **data quality + step completeness**, never by worker score. Worker identity is never stored with modules |
| L6 | **Benchmark contamination.** If benchmark clips are also sold as training data, C's robot has "seen the exam" | Evaluation becomes meaningless | Keep a **held-out benchmark set that is never sold for training**; licence it as "evaluation only" |
| L7 | **Human clips alone aren't a benchmark.** | Robots need task definitions and success criteria, not just video | Each benchmark clip ships with a task card: steps, order, timings, what counts as success |
| L8 | **Reselling with little added value.** Passing A's data to C almost unchanged | May break the A–B contract or data-protection law; also weak business value | B's labels, quality checks and packaging must be the product. See legal scope (A11) |
| L9 | **Workers' data trains robots that may replace them.** | Ethical and PR risk for A and B; a judge may ask | Be honest; consent covers this use explicitly; possible revenue share; Work Modules help current workers |
| L10 | **Cross-border sale.** Many C's are abroad | DPDP allows transfers but the government can restrict them; EU buyers bring GDPR | Check per deal; anonymise before export |
| L11 | **Hackathon scope.** | Judges score the demo, not the business plan | The business model goes on **one slide**; the demo shows hands + light + one product |

> We are not lawyers. These are risks to raise with a legal advisor, not legal conclusions.

---

## A5. The Data Health light 🟢🟡🔴

> **Point it at the footage, not the worker.** "This segment is green: clean data. This one is red: the camera was tilted, it's too dark, or the hands are out of frame."

### A5.1 What gets measured (per second of video, all laptop-cheap)

| Check | How | Typical cause in A's factory |
|---|---|---|
| Blur | Sharpness (Laplacian variance) + head-motion speed (optical flow) | Fast head turns |
| Lighting | Brightness histogram: too dark or washed-out highlights | Tube lights, windows, dark corners |
| Noise / compression | Grain and "blocky" artefact score | Cheap camera, low bitrate |
| Hands visible | % frames with hands; hands cut at the frame edge | Camera worn too high |
| Camera angle | Average hand position in the frame (always at the bottom = camera too high) | Badly mounted headband |
| Dirty lens | Low contrast that stays constant across the clip | Dust or oil on the lens |
| Dropped / frozen frames | Timestamp gaps, identical consecutive frames | Overheating, cheap SD card |
| Tracker agreement | MediaPipe vs RTMPose disagree = unsure | Gloves, occlusion |
| No-task time | Long stretches with no hands or no contact | Walking, breaks (low value for training) |

### A5.2 The rule

- 🟢 **Green:** good enough for Datasets, Benchmarks and Modules as-is.
- 🟡 **Yellow:** usable after automatic fixes (D5) or a quick human check.
- 🔴 **Red:** don't use. Send a fix note to the capture team.

Every light comes with **a reason**, e.g. "🔴 too dark + hands out of frame 62%".

### A5.3 How we prove the light works

Compare our hand tracker's accuracy on 🟢 vs 🔴 segments, using our own labelled frames. *Example of the kind of result we want:* "95% correct on green, 60% on red." That proves the light predicts bad data, and it becomes one of our strongest slides.

### A5.4 Decided against: flagging workers

We discussed flagging workers who "hide work" or "remove things" with a red/yellow/green light per worker. **We are not building this**, for four reasons:
- **No labels:** nothing in our 20 clips can teach or test "hiding".
- **False accusations:** the system would mostly flag camera angles and bad lighting, and a wrong flag could cost a worker their job.
- **Wrong fit:** B sells hand data for robotics, not surveillance.
- **Consent:** it adds to the worker-consent concerns already reported in this industry.

The fair version the brief itself lists: **missed or out-of-order step alerts and unsafe-hand alerts, reported per task, not per worker.**

---

## A6. Architecture and data contract

```
A's raw clip ─► frames (every 2nd on laptop)
   │
   ├─► [H] HANDS (PS1): MediaPipe ─► mirror fix ─► track IDs ─► left/right voting
   │        ─► gap fill ─► One-Euro smoothing ─► sanity checks ─► confidence + flags
   │          └─ hard frames ─► [R] enhance / ROI re-detect / rtmlib ─► (Colab WiLoR)
   │
   ├─► [Q] DATA HEALTH: blur, light, noise, hands-visible, camera angle, agreement
   │        ─► 🟢🟡🔴 per segment + reason
   │
   ├─► [C] CONTACT: YOLOE objects ─► fingertip rule + hysteresis ─► grab/release
   │        ─► step segments (+ Gemini captions on short windows)
   │
   └─► [P] PRODUCTS + DASHBOARD
            ├─ Dataset export for C      (green only, faces blurred)
            ├─ Benchmark pack for C      (held-out clips + task cards)
            ├─ Work Module for A         (key steps cut + captions + grip overlay)
            └─ Streamlit dashboard       (video, lights, timeline, flagged frames)
```

**Files are the interfaces** (`outputs/<clip>/`, formats in `src/egovision/schema.py`). Announce in chat before changing any format.

| File | Owner track | Content |
|---|---|---|
| `meta.json` | 1 | width, height, fps, step, video path, pipeline version |
| `hands_baseline.jsonl` | 1 | raw MediaPipe, never modified (our "before") |
| `hands.jsonl` | 1 | `{"frame","t","hands":[{"id","side","bbox","score","kp2d"[21],"kp3d","source","flags"}],"quality":{}}` |
| `quality.csv` | 2 | `clip,t_start,t_end,light,reasons,blur,brightness,hands_visible,agreement` |
| `contacts.csv` | 3 | `clip,t_start,t_end,hand,state,object_name,confidence` |
| `steps.csv` | 3 | `clip,start_s,end_s,verb,object,hand,caption` |
| `metrics.json` | 4 | detection share, handedness accuracy, swaps/min, jitter, PCK, FPS, accuracy per light colour |
| `export/` | 4 | dataset / benchmark / module outputs (private; contain footage) |

Coordinates are pixels of the video named in `meta.json`. Keypoint order follows MediaPipe (0 wrist, tips 4/8/12/16/20).

---

## A7. Tools, libraries, models, APIs (researched 31 Oct 2026)

"Laptop" means it runs on CPU. Every tool used must be listed in the README (rule).

### A7.1 Hands

| Tool | Version · licence | Laptop? | Notes |
|---|---|---|---|
| **MediaPipe Hand Landmarker** | 1.2.0 · Apache-2.0 | ✅ | **1.x removed `mp.solutions`; use the Tasks API (already in repo).** VIDEO mode. Left/right assumes a mirrored selfie, so swap for head-cam. Weak with gloves and blur |
| **rtmlib `Hand`** (RTMDet + RTMPose) | 0.0.16 · Apache-2.0 | ✅ ONNX | Independent second opinion → tracker agreement for the light |
| **WiLoR** | CC-BY-NC-ND + MANO licence | ❌ Colab | Best on blur and gloves; needs `MANO_RIGHT.pkl` (free registration). Non-commercial: fine for a hackathon, but say so |
| HaMeR / HaWoR | research code | ❌ GPU | Skip (PS4 territory) |
| **100DOH hand-object detector** | MIT | ❌ Colab, old stack | Contact classes N/S/O/P/F match "none / portable / fixed"; use as a reference check |
| Hands23 | MIT | ❌ GPU | Grasp type; stretch goal only |

### A7.2 Objects, quality, video

| Tool | Version · licence | Laptop? | Use |
|---|---|---|---|
| **Ultralytics YOLOE-26 / YOLO26** | 8.4.x · AGPL-3.0 (ok, public repo) | ✅ small | Open-vocabulary objects via text prompts (needs the CLIP package, already in requirements) |
| **OpenCV** | 5.0 | ✅ | Blur, brightness, optical flow, CLAHE enhancement, **YuNet face detector for blurring** |
| MediaPipe Face Detector | 1.2.0 | ✅ | Alternative face detector for privacy blur |
| supervision | 0.31 · MIT | ✅ | Tracking, box utilities |
| SAM 2.1 / SAM 3 | Apache-2.0 / gated HF | ⚠️ / ❌ | Optional object masks; SAM 3 needs access approval and a GPU |
| **Gemini API** (`google-genai` 2.34) | free tier via AI Studio | API | Captions for Work Modules and object names on **short windows/crops only**. Default 1 fps (configurable). **Check AI Studio for current model names and limits.** Free-tier inputs may be used by Google and seen by reviewers, so send the minimum and delete uploads |
| Qwen3-VL | open | ❌ GPU | Offline caption alternative (future) |
| **Streamlit** | 1.66 | ✅ | Dashboard with lights, timeline, flagged frames |
| ffmpeg | system | ✅ | H.264 for demo videos and Work Module cuts |

---

## A8. All ideas (IDs are stable; ★ = must-do)

Effort key: S < 2 h, M 2–5 h, L > 5 h.

### H: Hand tracking (30 pts)

| ID | Idea | Effort |
|---|---|---|
| ★H1 | Mirror fix for MediaPipe left/right; verify on 3 clips | S |
| ★H2 | Track-level left/right voting + egocentric position prior (no single-frame swaps) | S–M |
| ★H3 | Stable IDs + re-entry within about 2 s (Hungarian on side + IoU + wrist distance) | M |
| ★H4 | One-Euro smoothing; report jitter before/after | S |
| ★H5 | Gap filling: interpolate short gaps, optical flow for longer ones; mark as `interp`/`flow` | M |
| ★H6 | ROI re-detection: crop + upscale where the hand was lost, re-run MediaPipe | M |
| H7 | Adaptive low-light enhancement (CLAHE / gamma) only on dark frames | S |
| ★H8 | rtmlib second opinion when MediaPipe misses or is unsure; fuse results | M |
| H9 | Escalate only still-bad frames to WiLoR on Colab; report "% frames needing GPU" | M–L |
| H10 | Anatomical sanity checks (bone lengths, impossible jumps) | S–M |
| ★H11 | Per-hand confidence + flags in output | S |
| H12 | Test-time flip augmentation on hard frames | S |
| H13 | Motion-adaptive frame skipping (speed) | S–M |
| H14 | Stretch: fine-tune a small hand detector on high-confidence practice labels + fake blur/dark/compression | L |

### D: Data Health (the PS5 core)

| ID | Idea | Effort |
|---|---|---|
| ★D1 | Per-second quality checks (A5.1 table) → `quality.csv` | S |
| ★D2 | 🟢🟡🔴 light per segment, with reasons | S |
| ★D3 | Camera-angle and hands-visible checks (detect a badly mounted camera) | S |
| ★D4 | **Prove the light:** tracking accuracy on 🟢 vs 🔴 segments from our labels | S |
| D5 | Fixes, A/B tested: enhancement only kept if detected-hands % goes up on that segment type | S–M |
| ★D6 | Tracker agreement score (MediaPipe vs rtmlib) as a label-confidence signal | M |
| D7 | Capture-feedback report for B's recording team (e.g. "camera too high 40% of session", "lens dirty from 01:10") | S |
| D8 | "% of footage auto-approved" and "annotator time saved" numbers | S |
| ★D9 | Auto-blur faces, screens and documents before any export | S–M |
| D10 | Balance report: left vs right, gloves vs bare, tools seen | S |
| D11 | Remove near-duplicate segments | M |

### C: Contact and steps (supports the products)

| ID | Idea | Effort |
|---|---|---|
| ★C1 | YOLOE text-prompt objects with a factory vocabulary (tune after watching clips) | S–M |
| ★C2 | Contact rule: ≥ 2 fingertips in/near the box + hysteresis → grab/release | S |
| C3 | Grasp-closure feature (closed hand = holding) | S |
| C4 | Co-motion test: portable objects move with the hand, fixed ones stay with the scene | M |
| ★C5 | Steps = segments between grab/release events, then a Gemini caption per short window with a fixed verb list | M |
| C6 | Missed / out-of-order step alert per task (not per worker) | M |
| C7 | Safety: hand near a moving machine part → alert | M |

### M: Products for A and C

| ID | Idea | Buyer | Effort |
|---|---|---|---|
| ★M1 | **Work Module generator:** pick the clearest green clip of a task, cut the key steps, add captions + grip overlay → short MP4 | A | M |
| ★M2 | **Dataset export:** green segments only, hands + contacts + tags, faces blurred (per-episode JSON) | C | S |
| M3 | **Benchmark pack:** held-out clips + task card (steps, order, timings, success rule); never sold for training | C | S–M |
| ★M4 | **Dashboard:** video with overlay, light timeline, flagged frames, product buttons | B | M |
| M5 | Searchable tags (gloves, tool, lighting, hand) for C to filter datasets | C | S |

### E: Evaluation and honesty

| ID | Idea | Effort |
|---|---|---|
| ★E1 | Our own labelling tool (OpenCV, local): present / side / box, plus wrist + 5 fingertips on a subset | M |
| ★E2 | 150+ frames, over-sampling blur, gloves, dark, tools, overlap, re-entry | S |
| ★E3 | Metrics: detection recall/precision, left/right accuracy, swaps/min, PCK, jitter, FPS + hardware, accuracy per light colour, split by left/right/glove | S–M |
| ★E4 | Baseline vs ours table + side-by-side clip of the hardest 10 s | S |
| E5 | Two teammates label the same 30 frames and report how often they agree | S |
| E6 | Failure gallery (private Drive only) | S |

---

## A9. Evaluation plan

1. **H+3:** baseline on the demo clips; note the failure types.
2. **H+6:** labelling tool ready; label 150+ frames (60% hard, 40% random). Labels are coordinates only → `eval/labels/<clip>.json`.
3. **After each fix:** recompute `metrics.json` (baseline vs current + accuracy per light colour).
4. **Report honestly:** what we measured, how many frames, who labelled them, and the limits.

---

## A10. Team split (fill names at kickoff)

| Track | Owner | Owns | Folder |
|---|---|---|---|
| **1. Hands core** | ______ | H1–H5, H10, H11 | `src/egovision/hands/` |
| **2. Hands recovery + Data Health** | ______ | H6–H9, H12–H13, D1–D3, D5–D7, D9 | `src/egovision/recovery/`, `src/egovision/quality/`, `notebooks/` |
| **3. Contact, steps, Work Modules** | ______ | C1–C7, M1, M3 | `src/egovision/contact/`, `src/egovision/products/` |
| **4. Eval, dashboard, delivery** | ______ | E1–E6, D4, D8, D10, M2, M4, M5; README, slides, demo clips, data-rule checks | `src/egovision/eval/`, `app/`, `docs/` |

**Everyone must be able to explain every module** (judges ask). Hold 10-minute walkthroughs at H+12 and H+20.

---

## A11. Future scope (discuss after the hackathon, before any real product)

### A11.1 Legal rights: make sure no feature is illegal

Our principle: **don't build or sell anything until we know we have the right to.** Questions to take to a legal advisor:

1. **Ownership and resale (A → B → C).** Does B's contract with A allow reselling or sublicensing A's footage and labels to C? To which kinds of C? Is there exclusivity or a revenue share?
2. **"Little added value" risk.** Passing A's data to C with very little of our own work could breach the A–B contract or data-protection law, and has weak legal standing as B's own product. We need to understand what counts as B's own work (labels, quality scores, packaging) versus a copy of A's data.
3. **Worker consent under India's DPDP Act 2023.** The Rules were notified in Nov 2025 and phase in, with notice/consent duties due around May 2027.
   - Consent must be **specific to a stated purpose** and **as easy to withdraw as to give**.
   - Does consent cover recording, *and* labelling, *and* selling to C, *and* training robots?
   - What happens to datasets already sold when a worker withdraws?
4. **Trade secrets and NDAs.** A's processes, machines and documents visible in footage. What can C see? Can C be A's competitor?
5. **Licences for C.** Training vs evaluation-only (benchmark), no re-identification of workers, no redistribution, deletion terms.
6. **Cross-border sales.** DPDP transfer conditions; GDPR if C is in the EU.
7. **Workplace monitoring and labour law.** Limits on how recordings can be used about employees. This is why A5.4 stays rejected.
8. **Model and tool licences.** WiLoR (non-commercial), MANO, Ultralytics (AGPL-3.0), SAM 3 terms, and Gemini terms all need checking before commercial use.

### A11.2 Ethics and trust
- Fair payment or revenue share for A and its workers.
- Transparent consent forms in local languages.
- Work Modules that help current workers.

### A11.3 Technical
- Live quality light during recording (fix the camera before bad footage is made).
- Glove-specific hand model trained on B's growing data.
- Offline captions (Qwen3-VL).
- 3D hand trajectories for robot simulators (PS4).
- Multi-factory benchmark leaderboard for C.

---

## A12. GitHub workflow (4 people, one repo)

1. **Setup once:**
   - Clone the repo.
   - Run `powershell -ExecutionPolicy Bypass -File .\setup.ps1`.
   - Put the data in `data/egohack-data/`.
   - Run `python scripts/check_env.py`.
2. **Hook:** `python scripts/install_hooks.py` blocks commits of video, images, weights and `.env` (the brief PDF is git-ignored). **Never bypass it.**
3. **Branches:** `main` must always run. Work on `feat/<track>-<thing>`.
4. **Loop:** `git pull --rebase`, small commits, push, open a PR, a teammate merges. In the last 3 h, merge directly with a heads-up in chat.
5. **Stay in your track folder.** Shared files are `schema.py`, `__main__.py`, `requirements.txt`, `PLAN.md`. Announce in chat before editing them.
6. **New dependency:** add it to `requirements.txt` + the README tools table in the same PR.
7. **Never commit:**
   - footage, frames or screenshots
   - `outputs/`
   - weights
   - `.env`
   - the brief PDF
   - notebooks with image outputs
8. **Code freeze:** last push at **H+22:30**.

---

## A13. 24-hour timeline (H+0 = event start)

| Hours | Track 1 Hands | Track 2 Recovery + Health | Track 3 Contact + Modules | Track 4 Eval + Dashboard |
|---|---|---|---|---|
| 0–3 | Baseline all clips; verify H1 | WiLoR on Colab; rtmlib test; D1 checks | Watch clips, object vocabulary; YOLOE running | Labelling tool E1; README |
| 3–10 | H2–H5 | H6, H8, D2–D3, D9 | C1–C2 grab/release → C5 steps | Label 150 frames; metrics E3 |
| 10–16 | H10–H11, fix biggest failure | D5 A/B fixes, D6 agreement, H9 | M1 Work Module on one clip; **H+14 go/no-go** | D4 proof chart; dashboard M4 |
| 16–21 | Tune on demo clips | D7 capture report; FPS numbers | M3 benchmark pack, C6 if time | M2 export; demo clips ≤ 2 min; slide numbers |
| 21–23 | README methods | README compute | README products | Slides; Drive upload; **push before freeze** |
| 23–24 | Rehearse (everyone) | | | |

---

## A14. Submission and slides

**Checklist**
- [ ] Public GitHub repo:
  - README with setup steps.
  - The one command: `python -m egovision run --all`.
  - PS5 (on PS1).
  - Laptop/GPU used + hardware specs.
  - **Every library, model and API used.**
  - No footage, frames or screenshots.
- [ ] Demo videos (processed demo clips, **≤ 2 min total**) uploaded **only** to the organisers' Drive folder.
- [ ] 5–6 slides in the same Drive location, with the **repo link on slide 1**.

**Slide outline**
1. **Problem + repo link.** A's raw footage is messy; B pays people to label it frame by frame.
2. **Approach.** The A–B–C diagram + pipeline + the 🟢🟡🔴 light.
3. **Hand results.** Baseline vs ours (accuracy, swaps, jitter, FPS, hardware).
4. **PS5 results.** Light proven (accuracy on green vs red), % auto-approved, a Work Module example. **Use a mock-up we draw ourselves; public slides never contain real frames.**
5. **What failed + legal/consent limits** (honesty).
6. **Value + future scope.** Three products, one pipeline; legal checks before launch.

**Live demo (5 min):** dashboard on a demo clip → a red segment with its reason → a green segment turned into a Work Module.

---

## A15. Data rules and end-of-event deletion (disqualification risk)

- The data is for the hackathon only.
- Never post clips, frames or screenshots anywhere public (GitHub, LinkedIn, YouTube, Instagram, public slides).
- Faces, screens and documents never appear in anything public.
- Data stays in `data/` and outputs in `outputs/`, both git-ignored. The hook enforces it.

**At the end, everyone:**
- [ ] Delete `data/egohack-data/` and `outputs/`; empty the Recycle Bin.
- [ ] Delete Colab/Kaggle copies (files, `/content`, datasets, outputs).
- [ ] Delete Drive copies we made (not the organisers' submission folder).
- [ ] Delete Gemini uploads (`client.files.list()` → delete all) and the `gemini/` caches.
- [ ] Delete copies on phones, chat apps, USB drives.

---

## A16. Risks and fallbacks

| Risk | Fallback |
|---|---|
| PS5 product thin by H+14 | Declare PS1; keep the light as a "quality" bonus |
| WiLoR won't install on Colab | Rely on H6 + H8 on CPU; say so |
| YOLOE misses factory objects | Tune the vocabulary per clip; grab/release from hand closure + motion; Gemini names on crops |
| Gemini rate limits | Cache everything; captions only for Work Module clips; modules work without captions |
| Laptop too slow | `step=3`, 480p, rtmlib only on flagged frames |
| Light doesn't correlate with accuracy | Report it honestly; reweight the checks; that is still a finding |

---

## A17. Pitch story

> "Mytron (B) buys raw head-cam footage from factories (A) and sells labelled data to robotics companies (C). Today that labelling is slow and a lot of footage is unusable. Our pipeline runs on a laptop. It tracks both hands through blur, gloves and occlusion, fixes its own mistakes, and puts a green, yellow or red light on every segment of footage with a reason, never on the worker. Green data becomes training datasets and benchmark clips for C, and training modules for A's new workers. On our hand-labelled test set we find X% of hands (baseline Y%), and accuracy on green segments is G% vs R% on red, so the light works. Annotators only review P% of frames."

---

## A18. Sources

- Mytron brief PDF (local only, not in the repo)
- [MyTron Labs: official site](https://www.mytronlabs.com/main)
- [MyTron Labs LLP: Internshala](https://internshala.com/company/mytron-labs-llp-1770816357/)
- [Scroll.in: factory workers' data used to train robots](https://scroll.in/article/1092960/how-big-tech-is-harnessing-the-data-of-indian-factory-workers-to-train-robots)
- [DPDP Act brought into force: Hogan Lovells](https://www.hlc.com/en/publications/indias-digital-personal-data-protection-act-2023-brought-into-force-)
- [PIB: DPDP Rules 2025](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf)
- [MediaPipe releases](https://github.com/google-ai-edge/mediapipe/releases)
- [rtmlib](https://github.com/Tau-J/rtmlib)
- [WiLoR](https://gittrend.io/repo/rolpotamias/WiLoR)
- [Ultralytics YOLO](https://docs.ultralytics.com/yolo/)
- [SAM 3](https://docs.ultralytics.com/models/sam-3)
- [Gemini video understanding](https://ai.google.dev/gemini-api/docs/interactions/video-understanding)
- [Gemini free tier 2026](https://dev.to/hassann/gemini-api-free-tier-in-2026-limits-models-and-when-you-get-billed-4081)
- [100DOH hand_object_detector](https://github.com/ddshan/hand_object_detector)
- [Hands23](https://github.com/EvaCheng-cty/hands23_detector)
- [EgoHandICL (ICLR 2026)](https://arxiv.org/html/2601.19850)
- [Industrial egocentric HOI detection (2025)](https://arxiv.org/pdf/2507.13326)

---

# PART B: Teammates' research

> Paste here. Sections `B1, B2…`, ideas `B-H1`, `B-D1`, `B-M1`… Reference Part A IDs where you agree or disagree.

_(empty)_

---

# SECTION C: Combined decisions (fill together)

| Decision | Choice | Decided by / time |
|---|---|---|
| Primary problem statement | PS5 on PS1 (fallback PS1 at H+14) | |
| Track owners (A10) | | |
| Repo name + URL | | |
| Product shown in the live demo (M1 / M2 / M3) | | |
| Laptop specs for efficiency slide | | |
| Gemini model in use | | |
| Ideas committed (IDs) | ★ items + … | |
| Ideas dropped (IDs) | worker flagging (A5.4) + … | |

## Open questions

1. Is MediaPipe's left/right really mirrored on these clips? (H1)
2. Which clips are the demo clips? Label those first.
3. Ask the Mytron mentors: do they already pay A for footage, and what do C's ask for most (contact? grasp? benchmarks?)
4. Does a "task" repeat across clips? Benchmark and Work Modules work best on repeated tasks.
