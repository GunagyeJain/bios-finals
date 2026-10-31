# Egocentric Vision Hackathon: Project Plan

**Contributor of this file: Abhijay (member input 1 of 4). This file will be merged with three other members' files. Section 9 lists this contributor's proposals with trade-offs so the merging agent can evaluate them, not just accept them.**

Whoever merges this must read it fully, follow section 2 at all times, and update sections 10 and 11 as work continues.

## 1. Goal

**PRIMARY GOAL: produce high-quality, labelled, quality-scored, privacy-safe training data from head-camera factory video that robotics companies can use to train robots.** When time or effort must be traded off, choose what makes the data more accurate, cleaner, and more useful to a robot-learning team.

**SECONDARY GOAL: insights for the factory itself.** These features are still to be implemented, but only after the primary goal is working and measured (section 6, Tier 2).

Problem statements used: **PS1 (hand tracking)** as the foundation, extended with **PS2 (contacts)**, **PS3 (task timeline)** and the **PS4 bonus (robot-ready 3D hand export)**.

## 2. Hard rules (breaking them means disqualification)

1. Footage is for this hackathon only.
2. **Never commit video files, frames, or screenshots.** Keep footage in `data/` (in `.gitignore`). No footage in the repo, README, notebook outputs, or public slides.
3. Do not post clips, frames, or screenshots on GitHub, LinkedIn, YouTube, or Instagram. Do not show faces, screens, or company documents publicly.
4. Cloud AI APIs are allowed. **Delete every uploaded and local copy when the event ends** (Gemini file storage, Colab, Kaggle, local `data/`).
5. API keys only in environment variables (`GEMINI_API_KEY`), never in code or the repo.
6. All project code is written during the 24 hours. List every library, model, and API in the README.
7. Save every API response to a file; never process a clip twice.
8. Processed demo clips (2 minutes or less in total) go only to the private shared Google Drive folder.

## 3. Data

- 20 real clips, about 3 minutes each, **no labels**: `clips/` (full resolution), `clips_480p/` (laptop version). Some are marked **demo clips**; results must be shown on these.
- Egocentric video: motion blur, occlusion, gloves, harsh lighting, constant camera motion.
- Check the data `README.txt` for resolution, fps, camera details, and whether the worker per clip is known.

## 4. Team and hardware (suggested split, adjust after merging)

| Member | Machine | Suggested role |
|---|---|---|
| A | RTX 3050 laptop | Hand-tracking core: MediaPipe baseline, WiLoR/HaMeR on hard frames |
| B | RTX 2050 laptop | Contacts: object detection, grab/release, later safety flags |
| C | MacBook M4 | Gemini task timeline, merge with contact timestamps |
| D | Lenovo, integrated GPU | Quality score, datasheet, hand-labelling 100 frames, README, slides |

Fallback for heavy models: free Colab or Kaggle GPU. State the hardware used in the README (efficiency is scored against it).

## 5. Pipeline and formats

1. Load clip; pick frames (laptop: 480p, every 2nd or 3rd frame; GPU: every frame).
2. Hand tracking: MediaPipe Hand Landmarker (VIDEO mode); WiLoR/HaMeR on a GPU for hard frames.
3. Clean-up: stable hand IDs, left/right swap fix, One-Euro smoothing, interpolation, fast re-acquisition after re-entry.
4. Contacts: small YOLO plus fingertip rule (2 or more fingertips near an object box, persisting several frames); classify nothing / portable object / fixed surface.
5. Task timeline: Gemini video API with a fixed verb list; grab/release moments sharpen start and end times.
6. Quality score, datasheet, redaction, robot-ready export (Tier 1).
7. Render an annotated demo video.

Formats (keep stable so members can work in parallel; record any change in the progress log):
- `hands.jsonl`, one line per frame: `{"frame":120,"t":4.0,"hands":[{"side":"left","id":0,"bbox":[x1,y1,x2,y2],"score":0.93,"kp2d":[[x,y]x21],"kp3d":[[x,y,z]x21]}]}`
- `contacts.csv`: `clip, t_start, t_end, hand, state, object_name`
- `actions.csv`: `clip, start_s, end_s, verb, object, hand`

Gotchas: MediaPipe left/right assumes a mirrored selfie; head-camera video is not mirrored, so verify and swap if backwards. MediaPipe 3D world points are relative to the hand centre, not the camera. Gemini samples about 1 frame per second by default.

## 6. Features

Build Tier 1 first. Tier 2 is also to be implemented, but only after Tier 1 is working and measured. Within a tier, build in order.

### Tier 1: for robotics data buyers (PRIMARY)
1. **Robot-ready export:** hand trajectories (3D joints over time, consistent hand IDs, timestamps) in a simulator-loadable format such as JSON/NPZ.
2. **Data quality score per clip:** from blur, share of frames with hands detected, lighting, and tracking stability, plus a usable/not-usable flag.
3. **Per-clip labelled datasheet:** task, tools/objects seen, hands-visible percentage, quality score, accuracy numbers, FPS, hardware.
4. **Grab/release and action labels as training annotations:** `contacts.csv` and `actions.csv` in a clean, buyer-friendly format.
5. **Auto-redaction of faces and screens** so the data is privacy-safe to share.

### Tier 2: for the factory (SECONDARY, after Tier 1)
6. **Missing or out-of-order step alerts** against a reference step sequence.
7. **Best-practice extraction:** fastest, cleanest run of a task auto-cut into a short captioned training clip.
8. **Safety flags:** hands near moving machine parts or in risky positions, with timestamps.
9. **Clip comparison view:** time per step and differences between runs (never a ranking of people).

Stretch: natural-language search over clips.

## 7. Evaluation (hand tracking is 30 of 100 points and the tiebreaker)

Judges check frame by frame on the demo clips: every hand found, points on the right joints, left/right never swapped, stable through blur, gloves, occlusion, re-entry. Required numbers:
- Share of frames with hands detected.
- **Hand-label about 100 frames** and report how many the system got right.
- FPS and hardware.
- Before/after for each improvement (smoothing, swap fix, gap filling, WiLoR vs MediaPipe).
- A few failure cases, shown honestly.

Rubric: hand-tracking accuracy 30, results for the chosen problem 20, technical approach 15, usefulness to industry 10, innovation 10, efficiency 5, presentation and honesty 10.

## 8. Timeline and deliverables

| Hours | Goal |
|---|---|
| 0 to 3 | Repo, `.gitignore`, MediaPipe baseline on one clip, first annotated video, first Gemini timeline |
| 3 to 12 | Parallel work on hand quality, contacts, timeline, quality score |
| 12 to 18 | Merge, run all clips, datasheet, export, redaction |
| 18 to 21 | Fix biggest failure, process demo clips, collect numbers; Tier 2 only if Tier 1 is done |
| 21 to 23 | README, 5 to 6 slides, demo video, push before code freeze |
| 23 to 24 | Rehearse |

Deliverables: public GitHub repo (README with setup, the one command that runs the pipeline, laptop or GPU used, all libraries listed, no footage); demo videos of 2 minutes or less in the private Drive folder only; 5 to 6 slides (problem, approach, results, what failed, next steps, repo link on slide 1); 5-minute presentation and demo plus 3 minutes of questions, with every member able to explain any code.

## 9. This contributor's proposals, with trade-offs (for the merging agent to evaluate)

Business assumption behind them: factories are paid to mount head cameras on workers, and the processed footage is sold to robotics companies for robot learning. Raw video is worth little; labelled, quality-scored, privacy-safe data is worth more. This is an unverified assumption, not something the hackathon PDF states.

| Proposal | Benefit | Trade-offs and disadvantages |
|---|---|---|
| **Robotics buyers as the sole primary goal** | One clear focus; matches "teaching robots by watching people", the first use case in the PDF | Judges also score usefulness to industry broadly; a narrower story may look less impressive than a factory dashboard. Buyer needs are assumed, not confirmed (unknown preferred formats, such as HDF5 or LeRobot-style). |
| **Factory features moved to Tier 2** | Protects time for the 30-point accuracy criterion | Tier 2 may never be reached; the demo may look less visual without a dashboard. Consider a minimal Tier 2 demo if time remains. |
| **Robot-ready export** | Directly useful to buyers; covers the PS4 bonus | MediaPipe world landmarks are hand-centred, not in a fixed world frame, and there is no 3D ground truth. Real robot use needs WiLoR/HaMeR or HaWoR (GPU, complex setup). Risk of overclaiming; state limits plainly. |
| **Data quality score** | Cheap; gives buyers a usable/not-usable signal | No ground truth; thresholds are arbitrary unless validated against the 100 hand-labelled frames. A poorly justified score looks weak to judges. |
| **Per-clip datasheet** | Low effort, builds buyer trust, makes results easy to read | Accuracy numbers depend on the manual labelling being done on time. |
| **Actions and grab/release as annotations** | Robot-learning teams use these to segment demonstrations | Gemini sees about 1 fps and may mislabel or vary verbs; needs a fixed verb list and contact-based refinement. Cloud uploads must be deleted afterwards. Free-tier rate limits. |
| **Auto-redaction in Tier 1** | Privacy-safe data is a precondition for selling it; supports the data-use rules | Faces are easy; screens and documents are harder, with false negatives that could still violate the rules. Costs time and compute, and may blur hands or objects if done carelessly. Could be demoted to stretch if time is short. |
| **Dropping the open-innovation tool category** | Removes scope and keeps one problem done well | No standalone tool to demo; the presentation rests on annotated video, datasheets, and numbers. |
| **Four different machines** | Uses all available hardware in parallel | Different OS and GPUs risk environment mismatches. Fix shared formats and a pinned `requirements.txt` early. |

Open questions for the merged plan: who owns the buyer format decision; whether to ask organisers what the company actually does with this data; legal review of worker consent, data ownership, and factory confidentiality before any real deployment.

## 10. Progress log

_The agent updates this after each session: date, who, what was done, what is next._

- [ ] Repo and `.gitignore`
- [ ] MediaPipe baseline on one clip
- [ ] First annotated demo video
- [ ] First Gemini timeline
- [ ] Hand ID, swap fix, smoothing
- [ ] Contacts and grab/release timeline
- [ ] Timeline with contact-refined boundaries
- [ ] Robot-ready export
- [ ] Quality score
- [ ] Datasheet
- [ ] Redaction
- [ ] 100 frames hand-labelled, accuracy computed
- [ ] Tier 2: step alerts, best-practice extraction, safety flags, clip comparison
- [ ] README, slides, demo video

## 11. Team inputs

_Other members' notes go here when merging. The agent treats conflicts as questions to the user, not decisions to make alone._

## 12. Instructions for whoever merges this

1. Read this whole file; follow section 2 without exception.
2. Start with the repo skeleton and a `.gitignore` covering `data/`, `clips/`, `clips_480p/`, `*.mp4`, `*.avi`, `*.mov`, frame outputs, and `.env`; then the MediaPipe baseline on one clip.
3. Build Tier 1 first; start Tier 2 only after Tier 1 is working and measured. Do not start a lower-priority item while a higher one is broken.
4. Keep the section 5 formats stable and log any change.
5. When merging with other members' files, evaluate section 9 critically: keep, change, or drop each proposal based on its trade-offs, and ask the user when unsure.
6. Prefer simple, readable code; every member must be able to explain it.
7. Never print or share frames or footage outside `data/` and the private Drive folder.
8. After each session, update the progress log with open problems and next steps.
