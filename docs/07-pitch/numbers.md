# Numbers for the slides

_Generated 2026-11-01 05:44 by `scripts/pitch_numbers.py` from metrics.json and the index. Do not type numbers by hand; re-run the script._

## Hand tracking: 152 hand-labelled frames, 3 clips

| Metric | Baseline (MediaPipe) | Ours |
|---|---:|---:|
| Hands found | 41.2 % | 66.1 % |
| Detections that are real hands | 87.8 % | 90.0 % |
| Left/right correct | 96.7 % | 95.5 % |
| Keypoints within 20 % (misses count) | 34.9 % | 49.5 % |
| Keypoints within 20 % (found hands only) | 85.0 % | 74.5 % |
| Side swaps per minute | 57.3 | 4.7 |
| Jitter (px) | 9.4 | 6.2 |

Per clip:

| Clip | Labels | Hands found | Side swaps / min |
|---|---:|---:|---:|
| MTL-SKL00089-005 | 40 | 38.6 % → 68.6 % | 77.0 → 8.7 |
| MTL-SKL00089-012 | 40 | 60.0 % → 80.0 % | 49.7 → 2.0 |
| mytronlabs-000003-002 | 72 | 32.1 % → 56.9 % | 50.7 → 4.0 |

## Dataset

- 40 clips processed, 2.0 h of footage, 4 factories.
- Usable (green) share of graded seconds: 58.7 %.
- 3,990 grabs: a 2-finger robot can copy 44.5 %, a 5-finger robot 99.2 %, 0.8 % can't tell.
