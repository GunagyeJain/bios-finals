# Business and legal: slide content

_Owner: Bhavyam. Ready to paste into slides 5 and 6 of `slides.md`. Sources: plan §A4 and §A11 (`../03-ideation/bhavyam/bhavyam-plan-discussion.md`). We are not lawyers: every legal point below is a question for an advisor, not a conclusion._
Rules: no market sizes, prices or customer claims, because we have no evidence for any. No real frames. Numbers only from the Metrics page.

## Slide 6: Business and next steps
**Title:** One pipeline, three products. Legal checks come first.

| Product | Buyer | State today |
|---|---|---|
| Robot training dataset: green seconds, hands, contacts, steps, faces blurred | Robotics teams | **Built**, exported in the demo |
| Benchmark clips: human reference for a task, with steps and timings | Robotics teams | Designed. Needs a task card for each clip and a held-out set never sold for training |
| Training videos for new workers | The factory | Designed, **cut from this build** |

Why it can work: the factory gets something back from its own footage, so it has a reason to keep recording.

Before any launch, an advisor must answer:
1. **Who may resell the footage?** The factory, its workers and the data company all have a stake. Nothing is sold until the contract allows it.
2. **Did workers consent to this use?** Recording, labelling, selling and robot training are different purposes.
3. **What do buyers see?** Processes, machines and documents can be trade secrets, and a buyer may be a competitor.
4. **Can we ship these tools?** Ultralytics is AGPL-3.0 unless licensed commercially.

Next technical steps: quality light while recording, a hand model for gloves, screen and document blur, 3D hand trajectories for simulators.

## Slide 5: legal and consent limits (one block next to "what failed")
- We grade footage, never workers. No per-worker score exists anywhere in the system.
- Faces are blurred in exports, but the blur is not perfect: very small faces and some side views can be missed. Screens and documents are not blurred. A person must review anything before it leaves the building.
- All event footage is deleted when judging ends.

## Speaker notes (30 seconds)
"The robot dataset is the product we built. The same pipeline could also serve benchmark clips and factory training videos, but we did not build those. The hard part of this business is not the code. It is whether the data company may resell the footage, and whether workers agreed to that purpose. We would not sell anything until a legal advisor answers those questions."

## If a judge asks
**Is this legal in India today?**
We do not know, and that is why it is a launch condition. India's DPDP Rules were notified in November 2025 and phase in. Most duties, including notice and consent, apply about 18 months later, around May 2027. ([PIB](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf), [Hogan Lovells](https://ca.hoganlovells.com/en/publications/indias-digital-personal-data-protection-act-2023-brought-into-force-), [AZB Partners](https://www.azbpartners.com/bank/indias-digital-personal-data-protection-act-phased-rollout-and-key-compliance-milestones/))
A consent notice must state the data and the purpose in plain language and explain how to withdraw. So "we recorded you for training" may not cover "we sold it to a robotics company". (assumption: our reading, to confirm with an advisor)

**What if a worker withdraws after a dataset is sold?**
That is an open question. Our design answer: every exported episode names its source clip, so that clip can be traced. Removing it from a copy a buyer already holds would need a contract term. (assumption: not legal advice)

**Aren't you training robots to replace these workers?**
That is a fair concern and we do not dismiss it. Consent should name this use plainly, and revenue sharing is worth exploring. Training videos would help current workers, but we have not built them.

**Why would a factory pay for video of its own work?**
It would pay for the work on top: steps cut automatically, captions, the clearest example picked. That is a service, not data. (assumption: untested with a real factory)

**Could a buyer's robot cheat on a benchmark?**
Yes, if the same clips were also sold for training. So benchmark clips need a held-out set, licensed for evaluation only.

**Do your tools allow commercial use?**
Not automatically. Ultralytics is AGPL-3.0 with a paid enterprise option ([licence](https://ultralytics.com/license)). We did not confirm YOLOE's own terms, so that needs checking. Gemini's terms also need checking, especially what free-tier inputs are used for.

**Could people be identified despite the blur?**
Possibly: from a body, a voice or a badge, and through any face we miss. Blur reduces the risk and does not remove it, so buyer licences should forbid re-identification.
