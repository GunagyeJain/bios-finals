# Demo script (2:00)

Follows `../05-solution/app-flow.md` §3, shortened to 2 minutes and without Work Modules (cut). Use it for the
demo video (organisers' Drive only, never public) and as the core of the live 5-minute demo.
Demo clips: `MTL-SKL00089-005`, `MTL-SKL00089-006`, `mytronlabs-000003-002`. App: `streamlit run app/Home.py`,
light theme, browser zoom 100 %. Numbers: read them off the app on the day, never from memory.

| Time | Click | Say |
|---|---|---|
| 0:00 | Title slide | "Factories record hours of head-camera video. We turn it into graded, robot-ready hand data, on a laptop CPU." |
| 0:10 | **Library** | "Every clip, every second graded green, yellow or red. Here are the three demo clips with their light share and hands found." |
| 0:25 | Click row **MTL-SKL00089-005** → **Clip review** | "The rendered clip: both hands tracked with IDs and left and right." |
| 0:35 | Toggle **Baseline / Ours** at a fast or blurred moment | "Same second, plain MediaPipe versus ours: [say what the app shows, e.g. the hand kept through the blur]." |
| 0:55 | Click a **red** block on the light strip | "A red second always says why: here [read the reason]. A reason, not a guess." |
| 1:10 | **Steps** tab | "Steps come from grab and release moments, captioned from a fixed verb list. Each cycle is checked against the factory's reference cycle: this one is flagged [read the alert]." |
| 1:30 | **Safety** tab | "Fingertips close to a moving machine part, with the time and the hand." |
| 1:40 | **Export** → light **green** → **Build dataset** → open the datasheet | "One button: green seconds only, faces blurred, in the layout robot teams already load, with a datasheet." |
| 1:52 | **Metrics** | "Measured on frames we labelled ourselves: baseline versus ours, accuracy per light colour, and speed on this laptop." |
| 2:00 | End | |

## Fallbacks
- App slow or down: play the backup screen recording of this exact path (Gunagye's and Shefali's laptops).
- A tab is empty for a clip: say "not processed for this clip" and move to the next tab; never fake it.

## Recording the video
- Screen-record at 1080p; cut to 2:00 or less in total.
- Only blurred renders and exports on screen; skip any moment with a readable screen or document.
- Upload only to the organisers' Drive folder; delete local copies when the event ends.
