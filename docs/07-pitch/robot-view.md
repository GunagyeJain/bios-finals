# Robot view: slide content

_Owner: Bhavyam. Numbers copied from `numbers.md` (generated 2026-11-01 05:44, 40 clips). After the final run, re-run `scripts/pitch_numbers.py` and copy them again._
Rules: numbers only from `numbers.md`. No real frames in the deck: draw the gripper and the robot hand.

## Slide text
**Title:** Which of these grabs could a robot copy?

We draw a robot over the worker's hand and colour it by the grab happening right now. Switch between a 2-finger gripper and a 5-finger robot hand in the player.

| Colour | Meaning |
|---|---|
| Green | This robot type can copy this grab |
| Red | It cannot |
| Grey | No grab right now, or we can't tell which grip it is |

**3,990 grabs on 40 clips:** a 2-finger gripper can copy 44.5 %. 0.8 % we can't tell.

**Why a buyer cares:** a robotics team with a gripper can filter the export to grabs its hardware can copy, instead of sorting footage by hand.

## What it does NOT claim
Say these out loud if the slide is shown:
- **It is a drawing, not a simulation.** The robot follows the human pose. Nothing checks reach, force, collisions or whether a real robot would succeed.
- **"Can copy" means the grip type matches.** A grip is `2f` (pinch), `5f` (wrap) or `generic` (a touch on a fixed object). A 2-finger gripper copies `2f` and `generic`; a 5-finger hand copies all three. That table is our choice, not a test with a robot.
- **The 5-finger figure is not a finding.** 99.2 % is 100 % minus the "can't tell" share, because the 5-finger hand is defined as copying every grip type. For the same reason, the 5-finger view is never red. Do not present it as a result.
- **The grab data is not validated.** Grabs have no human labels yet. They come from object boxes the detector scores low (median 0.15 on the 3 demo clips), and the audio cross-check was no better than random. Treat 44.5 % as what our rule outputs, not a measured capability.
- **It grades grabs, never workers.**

## Speaker notes (20 seconds)
"This came from Mytron's feedback. Here the same hand data is drawn as a robot. Green means this robot type could copy the grab, red means it couldn't, and grey means no grab or we can't tell. With a 2-finger gripper, our rule says a little under half of grabs are copyable. That's a rule on grip type, not a robot test, and we haven't checked the grabs against human labels yet."

## If a judge asks
**Did you test this on a robot?**
No. It is a grip-type rule drawn on video. A real test needs a robot or a simulator.

**How do you know the 44.5 % is right?**
We don't yet. It depends on grabs we have not labelled by hand. The next step is to label a sample of grabs and measure them.

**Why is the 5-finger robot almost always green?**
Because we defined it as able to copy every grip type we detect. It shows the limit of the rule. It says nothing about how good a 5-finger hand is.

**Why is a touch on a machine counted as copyable?**
`generic` means a touch with no specific grip, such as pressing or resting on a fixed object. We count it as copyable by both robots, and that is an assumption.

## For the deck and demo (Shefali, Gunagye)
- The demo script has no Robot view beat yet. If it goes in, use the 2-finger view: the 5-finger view has no red.
- Render on the demo laptop: `python -m egovision.products.robot_overlay --clip <clip>`. It writes both views in about one pass.
