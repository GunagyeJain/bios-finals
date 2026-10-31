import cv2
import numpy as np
import pandas as pd
import pytest

from egovision import config
from egovision.index import query


@pytest.fixture
def indexed(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(config, "FIXTURE_DIR", tmp_path / "videos")
    monkeypatch.setattr(config, "INDEX_DB", tmp_path / "outputs" / "index.db")
    from egovision.fixtures import make
    from egovision.index.build import build
    make("fixture_001", seconds=3)
    build()


def test_library_and_kpis(indexed):
    lib = query.library()
    assert list(lib["clip"]) == ["fixture_001"] and lib["n_alerts"].iloc[0] == 2
    k = query.kpis(lib)
    assert k["clips"] == 1 and k["green"] == pytest.approx(2 / 3) and k["fps"] == 75.0


def test_clip_data_and_hand_lookup(indexed):
    d = query.clip_data("fixture_001")
    assert len(d["segments"]) == 3 and len(d["frame_summary"]) == 90
    hands = query.hand_lookup("fixture_001")
    assert {h["side"] for h in hands[0]} == {"left", "right"}


def test_at_picks_interval_containing_t():
    df = pd.DataFrame({"t_start": [0.0, 1.0, 2.0], "t_end": [1.0, 2.0, 3.0], "light": ["g", "y", "r"]})
    assert list(query.at(df, 1.0)["light"]) == ["y"]
    assert list(query.at(df, 3.0)["light"]) == ["r"]
    assert query.at(df, 5.0).empty


def test_nearest_frame():
    assert query.nearest_frame([0, 2, 4, 6], 30.0, 0.12) == 4
    assert query.nearest_frame([], 30.0, 1.0) is None


def test_flagged_runs_merges_consecutive_frames():
    f = pd.DataFrame({"t": [0.0, 0.1, 0.2, 2.0, 2.1], "flags": ["edge", "edge", "edge", "", "low_conf"]})
    runs = query.flagged_runs(f)
    assert runs[["t_start", "t_end", "flags", "frames"]].values.tolist() == [
        [0.0, 0.2, "edge", 3], [2.1, 2.1, "low_conf", 1]]


def test_h264_writer_roundtrip(tmp_path):
    from egovision.io.video import H264Writer
    path = tmp_path / "v.mp4"
    with H264Writer(path, 30, (64, 48)) as vw:
        for i in range(10):
            vw.write(np.full((48, 64, 3), i * 20, np.uint8))
    cap = cv2.VideoCapture(str(path))
    assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 10
    assert int(cap.get(cv2.CAP_PROP_FOURCC)).to_bytes(4, "little") in (b"avc1", b"h264")


def test_light_runs_merges_touching_segments_longest_first():
    seg = pd.DataFrame({"t_start": [0.0, 1.0, 2.0, 5.0], "t_end": [1.0, 2.0, 3.0, 9.0],
                        "light": ["red", "red", "green", "red"], "reasons": ["dark", "hands_out", "", "dark"]})
    runs = query.light_runs(seg, "red")
    assert runs[["t_start", "t_end", "reasons"]].values.tolist() == [[5.0, 9.0, "dark"], [0.0, 2.0, "dark · hands_out"]]


def test_robot_fit_on_fixture_contacts(indexed):
    fit = query.robot_fit(query.clip_data("fixture_001")["contacts"])   # grips 5f, generic, 2f
    assert fit == {"2f": pytest.approx(2 / 3), "5f": 1.0, "unsure": 0.0, "grabs": 3}


def test_robot_fit_without_contacts_is_none():
    assert query.robot_fit(pd.DataFrame(columns=["grip"]))["2f"] is None
