# Numbers for the slides

_Generated 2026-11-01 00:09 by `scripts/pitch_numbers.py` from metrics.json and the index. Do not type numbers by hand; re-run the script._

## Hand tracking: 152 hand-labelled frames, 3 clips

| Metric | Baseline (MediaPipe) | Ours |
|---|---:|---:|
| Hands found | 41.2 % | 68.2 % |
| Detections that are real hands | 87.8 % | 90.5 % |
| Left/right correct | 96.7 % | 92.9 % |
| Keypoints within 20 % (misses count) | 34.9 % | 49.8 % |
| Keypoints within 20 % (found hands only) | 85.0 % | 73.0 % |
| Side swaps per minute | 57.3 | 2.5 |
| Jitter (px) | 9.4 | 6.2 |

Per clip:

| Clip | Labels | Hands found | Side swaps / min |
|---|---:|---:|---:|
| MTL-SKL00089-005 | 40 | 38.6 % → 68.6 % | 77.0 → 3.7 |
| MTL-SKL00089-012 | 40 | 60.0 % → 88.0 % | 49.7 → 2.3 |
| mytronlabs-000003-002 | 72 | 32.1 % → 56.9 % | 50.7 → 2.0 |

## Dataset

- 9 clips processed, 0.5 h of footage, 3 factories.
- Usable (green) share of graded seconds: 68.6 %.
- 703 grabs: a 2-finger robot can copy 32.3 %, a 5-finger robot 98.3 %, 1.7 % can't tell.
