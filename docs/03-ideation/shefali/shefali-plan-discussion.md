# Idea: RealWork, real work sorted for the right robot

**Author:** Shefali · **Status:** draft · **Track:** PS5 Open innovation (built on PS1 hand tracking)

## One-liner
A tool that checks factory footage before it is sold: is this real work or "camera work", how good is each part, and which kind of robot can learn from it.

## The problem nobody listed
Mytron records workers doing manual tasks and turns the footage into data that teaches robots (assumption: confirm with organisers).

**Workers know they are training their replacement.** Some slow down, cut corners or do the task differently when the camera is on. Mytron ends up selling footage of how people act on camera, not how they really work, and the robot learns the wrong way to do the job.

Nothing in the problem statement mentions this, and no one is measuring it today (assumption).

Two smaller problems sit on top:
- Not every minute is equally useful. Some repetitions are clean, some are fumbled, some have the hands out of view.
- Most factory robots have a two-finger gripper, not a human hand. A buyer with gripper robots can only use part of the footage, and nobody knows which part.

## How it works
Factory work repeats. Real work has a steady rhythm. Faking it breaks that rhythm. We measure that from the hands alone.

1. **Track the hands** in every frame (21 points per hand, left and right).
2. **Split the clip into repetitions** of the task, using the path the hands follow each round.
3. **Score each repetition** on four things:
   - Rhythm: does it take a normal amount of time compared to the others?
   - Pauses: are there odd stops in the middle of the task?
   - Smoothness: is the movement smooth, or hesitant and jerky?
   - Visibility: are both hands clearly in view the whole time?
4. **Grade it:**
   - **Gold:** the cleanest repetitions. Sold as premium examples.
   - **Silver:** normal, real work. The bulk a robot learns from. Keep all of it.
   - **Red:** fake, fumbled or hands not visible. Cut it.
5. **Tag it by robot type**, using only finger positions:
   - **2-finger:** simple pinch grabs (thumb and index only). For standard gripper robots.
   - **5-finger:** three or more fingers, or fingers moving while holding. For humanoid robot hands.
   - **Generic:** reaching, moving parts, step order. Useful to any robot.
6. **Output:** a report per clip, a colour-coded timeline under the video, and the gold clips saved with their hand data.

It grades the footage, never the person. No worker is named or scored.

## USP (why this stands out)
- **It finds a problem Mytron did not ask about.** Most teams will improve hand tracking or build the listed examples. We show them a hidden risk in what they sell.
- **It is human.** It starts from how workers feel, not from a model.
- **It runs on the hands alone.** No object detector, no paid API. A normal laptop is enough.
- **It makes hand-tracking accuracy matter** (30 of 100 judging points): every score depends on the finger points being right.
- **It turns one pile of footage into several products**: gold, silver, and per-robot sets.

## Why Mytron would want it
1. **Stop paying for useless footage.** Bad footage is caught soon after recording, not months later.
2. **Stop paying to label junk.** Labelling is mostly done by hand today (problem statement, p.1). Red footage can be skipped.
3. **Protect their name.** If a robot trained on faked work fails, the buyer blames the data. We catch it before it ships.
4. **Charge more for better data.** Gold examples sell at a premium; silver stays the cheaper bulk tier.
5. **Sell the right data to the right buyer.** Gripper companies get 2-finger footage; humanoid companies get 5-finger footage.
6. **Stand out from competitors.** Other companies sell factory footage too (Build AI, Mecka). A quality grade with every dataset is something they can show buyers.
7. **A fair-treatment story.** Big tech gets asked how the workers behind AI data are treated. A tool that grades footage, not people, and can support paying workers for good footage, gives Mytron a clean answer.

**Pitch line:** *"Mytron sells real work. We make sure that is what they are selling."*

## ML / tech
- Model / approach: MediaPipe Hand Landmarker for hand points (upgrade to WiLoR on Colab if time allows); One-Euro smoothing; simple, explainable rules for rhythm, pauses, smoothness and grip type. No training needed.
- Data: the 20 event clips (480p on laptops). Plus our own test clip: one of us wears a phone on their head and does a simple task twice, once normally and once slowed down or sloppy on purpose. Our own footage, no faces.
- Stack: Python, OpenCV, NumPy, pandas; a simple web page or Streamlit view for the timeline and report.
- Runs on: any team laptop, CPU only. See `../../01-team/hardware.md`.

## How we prove it works
- **Real vs fake test:** the tool must tell our normal take from our faked take.
- **Grip labels:** we label about 50 grabs by hand and report how many the tool got right.
- **Hand tracking:** share of frames with hands found, and frames per second, on the demo clips.
- Every number in the slides is measured by us. No made-up figures.

## Risks
| Risk | Likelihood | Fallback |
|---|---|---|
| Clip looks uneven for an innocent reason (hard part, broken tool, new worker) | High | Red and yellow are "check this", never a verdict. A human decides. Say this openly. |
| Some clips do not repeat a task | Medium | Score fixed-length windows instead of repetitions |
| Fingers hidden by tools or gloves give wrong grip labels | Medium | Mark low-confidence grabs as "unsure"; show these failure cases honestly |
| Judges read it as worker surveillance | Medium | Grade footage, not people. No names, no per-worker ranking. |
| We do not know what robots Mytron's buyers use | Medium | Ask at the event. If mostly grippers, lead with the 2-finger set. |

## Demo plan (what judges see in 3 minutes)
1. The problem in one line: "workers know they are training their replacement."
2. Our own test: normal take vs faked take, and the tool tells them apart.
3. A demo clip with the gold / silver / red timeline under it.
4. Best vs worst repetition playing side by side.
5. The per-clip report: minutes of gold, silver, red, and 2-finger / 5-finger / generic.
6. Hand-tracking numbers and the failure cases we found.

## Future scope
- **Live warning while recording:** tell the worker straight away if the camera slips or the hands leave the frame.
- **Worker report:** each worker sees how much of their footage was good, so pay can follow quality, not just hours.
- **Fumble and recovery finder:** robots rarely see how to recover from a mistake. Those moments could be a premium set.
- **Off-task filter:** cut nose scratches, glove fixes and camera adjustments so robots do not learn them.
- **Freshness check:** compare new footage with old footage of the same task and flag old methods the factory no longer uses.
- **Export for robot teams:** package graded clips in formats robot teams already use (for example LeRobot).
- **Mix of workers:** warn when one person makes up too much of a task's footage, so robots do not learn one person's habits.

## Effort (24 h hack, ends 1 Nov 11:00)
Suggested split based on hardware; change as needed.
| Part | Who | Hours |
|---|---|---|
| Hand tracking, smoothing, accuracy numbers | Abhijay / Bhavyam | 6 |
| Repetition split and quality score | Gunagye | 6 |
| Grip type tags (2-finger / 5-finger / generic) | Bhavyam | 4 |
| Timeline view, report, demo video, slides | Shefali | 6 |
| Own test recording and hand labels | All | 2 |

## Score
See `../scoring.md`.
