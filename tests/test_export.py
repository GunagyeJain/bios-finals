import json

import pandas as pd
import pytest

from egovision import config
from egovision.products import episodes as ep


def _seg(lights):
    return pd.DataFrame({"t_start": [float(i) for i in range(len(lights))],
                         "t_end": [float(i + 1) for i in range(len(lights))], "light": lights})


def test_usable_runs_keep_allowed_stretches_of_min_length():
    seg = _seg(["green", "green", "yellow", "green", "green", "green", "red", "green"])
    assert ep.usable_runs(seg, 8.0, "green") == [(3.0, 6.0)]
    assert ep.usable_runs(seg, 8.0, "yellow") == [(0.0, 6.0)]


def test_missing_quality_counts_as_yellow():
    empty = _seg([])
    assert ep.usable_runs(empty, 12.0, "green") == []
    assert ep.usable_runs(empty, 12.0, "yellow") == [(0.0, 12.0)]


def test_split_only_where_both_sides_stay_long_enough():
    assert ep.split((0.0, 10.0), [3.0, 5.0, 8.0], 3.0) == [(0.0, 3.0), (3.0, 10.0)]
    assert ep.split((0.0, 6.0), [1.0, 2.0, 4.0, 4.5], 3.0) == [(0.0, 6.0)]
    assert ep.split((0.0, 9.0), [], 3.0) == [(0.0, 9.0)]


def test_task_from_the_step_with_most_overlap_else_contact():
    steps = pd.DataFrame({"start_s": [0.0, 2.0], "end_s": [2.0, 9.0], "verb": ["pick", "fasten"],
                          "object": ["screw", "panel"]})
    contacts = pd.DataFrame({"t_start": [0.0], "t_end": [5.0], "object_name": ["drill"]})
    assert ep.task_of(0.0, 6.0, steps, contacts) == "fasten panel"
    assert ep.task_of(0.0, 6.0, steps.iloc[0:0], contacts) == "handle drill"
    assert ep.task_of(0.0, 6.0, steps.iloc[0:0], contacts.iloc[0:0]) == "hand activity"


@pytest.fixture
def exported(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(config, "FIXTURE_DIR", tmp_path / "videos")
    monkeypatch.setattr(config, "INDEX_DB", tmp_path / "outputs" / "index.db")
    monkeypatch.setattr(config, "EXPORTS", tmp_path / "exports")
    from egovision.fixtures import make
    from egovision.index.build import build
    from egovision.products.export import export
    make("fixture_001")
    build()
    return export("demo_v1", "yellow", redact=lambda img, keep=None: img)


def test_export_writes_lerobot_layout_without_red_seconds(exported):
    root = config.EXPORTS / "demo_v1"
    assert exported["episodes"] == 2 and exported["red_seconds"] == 0
    info = json.loads((root / "meta" / "info.json").read_text())
    assert info["total_episodes"] == 2 and info["fps"] == 15.0
    eps = [json.loads(line) for line in (root / "meta" / "episodes.jsonl").read_text().splitlines()]
    assert [(e["t_start"], e["t_end"]) for e in eps] == [(0.0, 6.0), (9.0, 12.0)]
    df = pd.read_parquet(root / "data" / "chunk-000" / "episode_000000.parquet")
    assert len(df) == 90 and set(df["light"]) <= {"green", "yellow"}
    assert {"left.kp2d", "right.kp3d", "left.contact", "step_index", "task_index"} <= set(df.columns)
    assert len(df["right.kp2d"].iloc[0]) == 42 and df["timestamp"].iloc[0] == 0.0
    assert (root / "videos" / "chunk-000" / "egocentric" / "episode_000001.mp4").stat().st_size > 0
    assert "Data sheet" in (root / "datasheet.md").read_text(encoding="utf-8")


def test_export_registers_the_dataset(exported):
    from egovision.index import query
    assert query.sql("SELECT kind, name, n_items FROM products").values.tolist() == [["dataset", "demo_v1", 2]]


def test_robot_filter_keeps_only_copyable_grabs():
    clips = pd.DataFrame({"clip": ["c"], "factory": ["f"], "duration_s": [12.0]})
    seg = _seg(["green"] * 12).assign(clip="c")
    contacts = pd.DataFrame({"clip": ["c", "c"], "t_start": [1.0, 7.0], "t_end": [2.0, 8.0], "grip": ["2f", "5f"],
                             "object_name": ["screw", "drill"]})
    steps = pd.DataFrame({"clip": ["c"], "step_idx": [0], "start_s": [6.0], "end_s": [6.0], "verb": ["x"],
                          "object": ["y"], "hand": ["right"]})
    assert len(ep.plan(clips, seg, steps, contacts, "green")) == 2
    only = ep.plan(clips, seg, steps, contacts, "green", robot="2f")
    assert only[["t_start", "t_end"]].values.tolist() == [[0.0, 6.0]]
    assert len(ep.plan(clips, seg, steps, contacts, "green", robot="5f")) == 2
