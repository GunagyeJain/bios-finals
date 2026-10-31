# Data schema

_Code: `src/egovision/schema.py` (dataclasses, column lists, `ClipPaths`). Validate any clip with `python -m egovision check --clip X`. Synthetic examples of every file: `python -m egovision fixtures`._
_Files are the interfaces between people. Change a format only after a heads-up in the team chat + a line in `../08-log/decisions.md`._
Coordinates: pixels of the video in `meta.json`. Keypoints: MediaPipe order (0 wrist; tips 4, 8, 12, 16, 20). Times: seconds (float).

## 1. Per-clip files: `outputs/<clip>/`
| File | Writer | Content |
|---|---|---|
| `meta.json` | io | `{clip, factory, video, width, height, fps, n_frames, step, is_demo, pipeline_version}` |
| `hands_baseline.jsonl` | hands | Raw MediaPipe, never modified |
| `hands.jsonl` | hands | Final hands, one line per frame (below) |
| `quality.csv` | quality | One row per 1 s segment |
| `objects.jsonl` | contact | `{frame, t, objects:[{id, name, kind: portable|fixed, bbox, score, moving}]}` |
| `contacts.csv` | contact | One row per contact interval |
| `steps.csv` | steps | One row per step |
| `wilor.jsonl` | hands (GPU job) | Same shape as `hands.jsonl`, only escalated frames |
| `alerts_steps.csv` | steps | Order alerts (one writer per file) |
| `alerts_safety.csv` | safety | Safety alerts |
| `render.mp4` | products | Annotated H.264 video for the app (git-ignored) |
| `metrics.json` | eval | Numbers for slides |

### 1.1 `hands.jsonl` (one line per frame, every frame after gap fill)
```json
{"frame": 120, "t": 4.0,
 "hands": [{"id": 0, "side": "left", "bbox": [x1, y1, x2, y2], "score": 0.93,
            "kp2d": [[x, y], "...21"], "kp3d": [[x, y, z], "...21"],
            "source": "mediapipe|roi|rtmlib|wilor|interp",
            "agreement": 0.82, "flags": ["low_conf", "disagree", "sanity", "edge"]}]}
```
`kp3d` is MediaPipe world landmarks (metres, around the hand centre, not the camera) or WiLoR joints; `null` if missing.

### 1.2 CSV columns
| File | Columns |
|---|---|
| `quality.csv` | `clip, t_start, t_end, light (green|yellow|red), reasons ("dark;hands_out"), blur, brightness, hands_visible, edge_cut, agreement, frozen` |
| `contacts.csv` | `clip, t_start, t_end, hand, state (none|portable|fixed), object_name, object_id, confidence, grip (2f|5f|generic|unsure)` |
| `steps.csv` | `clip, step_idx, start_s, end_s, verb, object, hand, caption, source (gemini|contact), cycle_idx` |
| `alerts_*.csv` | `clip, t_start, t_end, kind (safety|step_missing|step_order|step_extra), severity (info|warn), hand, detail` |

`contacts.csv`, `steps.csv` columns are a superset of the brief's suggested formats (p.4), so the brief's columns are always present.

## 2. Eval labels: `eval/labels/<clip>__<labeller>.json` (coordinates only, committed; no images)
```json
{"clip": "factory_003", "labeller": "shefali",
 "frames": [{"frame": 812, "tags": ["blur", "glove"],
             "hands": [{"side": "right", "bbox": [..], "wrist": [x, y], "tips": [[x, y], "...5"] }]}]}
```
Frame images used while labelling stay in `eval/frames/` (git-ignored).

## 3. SQLite index: `outputs/index.db`
Built by `python -m egovision index` from the files above (rebuildable, never hand-edited). The app and the exporter read only this + `hands.jsonl`.

```sql
CREATE TABLE clips (
  clip TEXT PRIMARY KEY, factory TEXT, seq_in_factory INT, video TEXT,
  fps REAL, width INT, height INT, n_frames INT, duration_s REAL,
  is_demo INT, green_share REAL, yellow_share REAL, red_share REAL,
  hands_found_share REAL, processed_at TEXT, pipeline_version TEXT);

CREATE TABLE segments (            -- quality.csv
  clip TEXT REFERENCES clips, t_start REAL, t_end REAL, light TEXT,
  reasons TEXT, blur REAL, brightness REAL, hands_visible REAL,
  edge_cut REAL, agreement REAL, frozen INT);

CREATE TABLE frame_summary (       -- one row per frame, from hands.jsonl
  clip TEXT, frame INT, t REAL, n_hands INT,
  left_score REAL, right_score REAL, sources TEXT, flags TEXT,
  PRIMARY KEY (clip, frame));

CREATE TABLE contacts (id INTEGER PRIMARY KEY, clip TEXT, t_start REAL, t_end REAL,
  hand TEXT, state TEXT, object_name TEXT, confidence REAL, grip TEXT);

CREATE TABLE steps (id INTEGER PRIMARY KEY, clip TEXT, step_idx INT, start_s REAL,
  end_s REAL, verb TEXT, object TEXT, hand TEXT, caption TEXT, cycle_idx INT);

CREATE TABLE alerts (id INTEGER PRIMARY KEY, clip TEXT, t_start REAL, t_end REAL,
  kind TEXT, severity TEXT, hand TEXT, detail TEXT);

CREATE TABLE products (id INTEGER PRIMARY KEY, kind TEXT,  -- dataset|module|benchmark
  name TEXT, path TEXT, filter_json TEXT, n_items INT, created_at TEXT);

CREATE TABLE metrics (clip TEXT, key TEXT, value REAL, PRIMARY KEY (clip, key));
CREATE INDEX idx_seg ON segments(clip, t_start);
CREATE INDEX idx_alert ON alerts(clip, kind);
```

## 4. Robot export (hero): `exports/<name>/` (LeRobot-style, git-ignored)
```
exports/<name>/
  meta/info.json          fps, n_episodes, n_frames, feature list + shapes, source clips, pipeline_version
  meta/episodes.jsonl     {episode_index, clip, t_start, t_end, n_frames, task, light_share, grip_types, steps:[...]}
  meta/tasks.jsonl        {task_index, task}            -- task = "verb object" from steps
  data/chunk-000/episode_000000.parquet
  videos/chunk-000/egocentric/episode_000000.mp4        -- faces/screens blurred
  datasheet.md            what, how, numbers, limits, licences, hardware
```
Parquet columns (one row per frame):
`frame_index, timestamp, episode_index, task_index,`
`left.present, left.kp2d (42 floats), left.kp3d (63), left.score, left.source,`
`right.present, right.kp2d, right.kp3d, right.score, right.source,`
`left.contact, right.contact (none|portable|fixed), left.object, right.object,`
`step_index, light`.

**Episode rule:** contiguous green time ≥ 3 s, split at step boundaries if steps exist. Yellow allowed with `--light yellow`. Red never exported.
