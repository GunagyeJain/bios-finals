import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from egovision.io.video import H264Writer

spec = importlib.util.spec_from_file_location("validate_export", Path(__file__).parents[1] / "scripts" / "validate_export.py")
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)

N = 6


def rows(episode=0, task=0):
    out = []
    for i in range(N):
        row = {"frame_index": i, "timestamp": i / 15, "episode_index": episode, "task_index": task, "step_index": 0, "light": "green"}
        for side, present in (("left", True), ("right", False)):
            row |= {f"{side}.present": present, f"{side}.kp2d": [1.0] * 42 if present else None,
                    f"{side}.kp3d": [0.1] * 63 if present else None, f"{side}.score": 0.9 if present else None,
                    f"{side}.source": "mediapipe" if present else None,
                    f"{side}.contact": "none", f"{side}.object": ""}
        out.append(row)
    return out


def write_parquet(root, episode, data):
    path = root / "data" / "chunk-000" / f"episode_{episode:06d}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(data).to_parquet(path, index=False)


def write_video(root, episode, n=N):
    with H264Writer(root / "videos" / "chunk-000" / "egocentric" / f"episode_{episode:06d}.mp4", 15, (64, 48)) as vw:
        for _ in range(n):
            vw.write(np.zeros((48, 64, 3), dtype=np.uint8))


def write_jsonl(path, items):
    path.write_text("".join(json.dumps(i) + "\n" for i in items), encoding="utf-8")


@pytest.fixture
def export(tmp_path):
    root = tmp_path / "demo"
    (root / "meta").mkdir(parents=True)
    write_parquet(root, 0, rows())
    write_video(root, 0)
    (root / "meta" / "info.json").write_text(json.dumps(
        {"fps": 15, "total_episodes": 1, "total_frames": N, "total_tasks": 1, "features": {}, "light": "green",
         "source_clips": ["clipx"], "pipeline_version": "0.1.0"}), encoding="utf-8")
    write_jsonl(root / "meta" / "episodes.jsonl", [
        {"episode_index": 0, "clip": "clipx", "t_start": 0.0, "t_end": 0.4, "n_frames": N, "task": "pick bolt",
         "light_share": 1.0, "grip_types": [], "steps": []}])
    write_jsonl(root / "meta" / "tasks.jsonl", [{"task_index": 0, "task": "pick bolt"}])
    (root / "datasheet.md").write_text("# data\n", encoding="utf-8")
    return root


def failed(root):
    return {k for k, v in V.validate(root).items() if v}


def test_good_export_passes_every_check(export, capsys):
    assert failed(export) == set()
    assert V.main([str(export)]) == 0
    assert "FAIL" not in capsys.readouterr().out


def change(export, **cols):
    data = rows()
    for name, fn in cols.items():
        for i, r in enumerate(data):
            fn(r, i)
    write_parquet(export, 0, data)


def test_red_frame_fails(export):
    change(export, a=lambda r, i: r.update(light="red" if i == 2 else "green"))
    assert failed(export) == {"no red frames"}


def test_yellow_frame_fails_a_green_export_only(export):
    change(export, a=lambda r, i: r.update(light="yellow"))
    assert failed(export) == {"no red frames"}
    info = json.loads((export / "meta" / "info.json").read_text())
    (export / "meta" / "info.json").write_text(json.dumps({**info, "light": "yellow"}))
    assert failed(export) == set()


def test_timestamps_must_increase(export):
    change(export, a=lambda r, i: r.update(timestamp=0.1))
    assert failed(export) == {"timestamps increase per episode"}


def test_frame_index_must_run_from_zero(export):
    change(export, a=lambda r, i: r.update(frame_index=i + 1))
    assert failed(export) == {"timestamps increase per episode"}


def test_wrong_keypoint_length_fails(export):
    change(export, a=lambda r, i: r.update({"left.kp2d": [1.0] * 40}))
    assert failed(export) == {"keypoint shapes"}


def test_points_on_an_absent_hand_fail(export):
    change(export, a=lambda r, i: r.update({"right.kp2d": [1.0] * 42}))
    assert failed(export) == {"keypoint shapes"}


def test_null_kp3d_on_a_present_hand_is_allowed(export):
    change(export, a=lambda r, i: r.update({"left.kp3d": None}))
    assert failed(export) == set()


def test_missing_column_fails(export):
    write_parquet(export, 0, [{k: v for k, v in r.items() if k != "left.score"} for r in rows()])
    assert failed(export) == {"columns"}


def test_video_shorter_than_parquet_fails(export):
    write_video(export, 0, N - 2)
    assert failed(export) == {"video frames = parquet rows"}


def test_episode_without_video_fails(export):
    next((export / "videos").rglob("*.mp4")).unlink()
    assert failed(export) == {"files match episodes"}


def test_unknown_task_index_fails(export):
    write_parquet(export, 0, rows(task=3))
    assert "tasks and episodes consistent" in failed(export)


def test_task_text_must_match(export):
    write_jsonl(export / "meta" / "tasks.jsonl", [{"task_index": 0, "task": "place nut"}])
    assert failed(export) == {"tasks and episodes consistent"}


def test_info_counts_must_match(export):
    info = json.loads((export / "meta" / "info.json").read_text())
    (export / "meta" / "info.json").write_text(json.dumps({**info, "total_frames": 99}))
    assert failed(export) == {"counts in info.json"}


def test_unknown_contact_state_fails(export):
    change(export, a=lambda r, i: r.update({"left.contact": "held"}))
    assert failed(export) == {"allowed values"}


def test_missing_folder_fails_cleanly(tmp_path, capsys):
    assert V.main([str(tmp_path / "nothing")]) == 1
    assert "FAIL  layout" in capsys.readouterr().out
