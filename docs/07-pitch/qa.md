# Judge Q&A

Short answers. Any number: read it off the Metrics page on the day.

1. **Who made the labels, and aren't they biased toward your pipeline?**
   Every labelled frame was checked by one of us in our label tool. Points were pre-filled by rtmlib (RTMPose
   hand), which the final pipeline does not use as its result, and each hand records whether it was pre-filled
   and whether we edited it. A shared 30-frame set is fully hand-made, so we can compare accuracy on manual vs
   pre-filled frames and show the suggestions did not bias the numbers.

2. **How do you measure hand accuracy without ground truth?**
   Our own labels: wrist and 5 fingertips plus left/right on frames picked 60 % from hard moments and 40 % at
   random. Metrics: hands found, left/right correct, PCK@0.2, swaps per minute, jitter, FPS.

3. **What did you do beyond the starter code?**
   Track IDs, left/right voting per track, smoothing and gap filling on top of MediaPipe; a per-second quality
   light with reasons; fingertip contact with objects; step captions on grab/release windows; an order check
   per factory; safety alerts; a robot dataset export; and the eval tooling.

4. **Does the quality light mean anything?**
   The Metrics page shows tracking accuracy on green vs red seconds from our labels. If green were not more
   accurate than red, the light would be useless; that comparison is the proof.

5. **What hardware, and how fast?**
   Laptop CPUs only, no GPU. FPS per stage and the hardware are on the Metrics page.

6. **Why Gemini for steps, and what does it see?**
   No step labels exist, so we use a vision-language model with a fixed verb list and a JSON schema. It only
   sees short 480p windows between grab and release, with faces blurred, sent inline (nothing stored in API
   files), and every answer is cached. Without a key the stage still runs and falls back to contacts.

7. **How do you know the right order of steps?**
   Per factory, a reviewer can mark a clip as the reference; otherwise we take the first full repeated cycle.
   Each cycle is aligned to it by edit distance: missing and out-of-order steps are warnings, extra steps
   are info. No repeat, no alerts.

8. **Where does it fail?**
   The top failure cases are on the Metrics page. Known limits: screens and documents are not blurred;
   contacts miss parts the object detector misses; fast hand crossings can still swap sides.

9. **Who would actually use this?**
   A data company's reviewers (which footage is usable and why), robotics teams (hand trajectories, contacts
   and steps in a format they load) and the factory (safety timestamps, and later training videos).

10. **What about privacy and the footage rules?**
    No footage, frames or screenshots in git or in public slides; hooks and CI block media files. Faces blurred
    in exports and API windows. Everything is deleted when the event ends. Selling such data would need
    ownership, consent and licence checks first.
