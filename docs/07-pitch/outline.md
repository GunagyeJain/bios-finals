# Slide outline (6 slides)

Format and rules: problem statement p.15. 5 to 6 slides: problem, approach, results, what failed, what next.
Repo link on slide 1. **Mock-ups we draw ourselves only: no frames, crops or screenshots of the footage.**
Numbers come only from `metrics.json` / measured runs; anything missing stays a visible `[TO FILL]`.
Business and legal content (slides 5 and 6): Bhavyam, from his plan §A14.

| # | Title | On the slide | Criterion (points) |
|---|---|---|---|
| 1 | Raw head-cam video in, robot-ready hand data out | One line on the problem (brief p.1: footage "is mostly labelled by hand, which is slow and expensive"); PS5 on PS1; team; **repo link** | Presentation (10) |
| 2 | One pipeline, every use | Pipeline diagram: hands → light → contacts → steps → order + safety → app + export. The A (factory) → B (Mytron Labs) → C (robotics buyer) strip under it. "Laptop CPU only" badge | Technical approach (15), Innovation (10) |
| 3 | Hands: baseline vs ours | Table: hands found, L/R correct, PCK@0.2, swaps/min, FPS, hardware. Hard cases named (blur, gloves, tools, overlap, re-entry). `[TO FILL from metrics.json]` | Hand accuracy (30), Efficiency (5) |
| 4 | What the app gives a data team | Drawn mock-up of Clip review: light strip with a reason, step timeline with one order alert, safety marker, Export button. Numbers: share of seconds green, accuracy on green vs red `[TO FILL]` | PS results (20), Usefulness (10) |
| 5 | What failed, honestly | 3 biggest failures from A6 with counts `[TO FILL]`; limits: screens not blurred, contacts miss parts the detector misses, step captions need a key and quota; pre-filled labels checked against a hand-only set | Presentation and honesty (10) |
| 6 | Next | What a factory and a robotics team would use first; consent and data-licence checks before any launch; next technical step | Usefulness (10) |

## Mock-up rules
- Draw hands as simple outlines or skeleton lines on a flat background; no factory imagery.
- Use the app's real layout and colours (ui-design.md), filled with made-up shapes, and label it "illustration".
- Charts only from our own numbers.

## Checks before export
- [ ] Repo link on slide 1 is the public submission copy.
- [ ] No real frame, crop or screenshot anywhere (also not in speaker notes).
- [ ] Every number traced to `metrics.json` or a logged run.
- [ ] No em dashes, no filler words.
