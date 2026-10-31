import pytest

from egovision import config
from egovision.schema import QUALITY_COLS, Hand, read_csv, write_csv


@pytest.fixture(scope="module")
def fixture_clip(tmp_path_factory):
    out = tmp_path_factory.mktemp("outputs")
    config.OUTPUTS = out
    config.FIXTURE_DIR = out / "videos"
    from egovision.fixtures import make
    return make("fixture_001", seconds=3)


def test_fixture_outputs_pass_contract(fixture_clip):
    from egovision.contract import check
    assert check("fixture_001") == []


def test_hand_rejects_wrong_keypoint_count():
    with pytest.raises(AssertionError):
        Hand(side="left", bbox=[0, 0, 1, 1], score=1.0, kp2d=[[0, 0]] * 20)


def test_csv_writer_rejects_missing_column(tmp_path):
    with pytest.raises(ValueError):
        write_csv(tmp_path / "q.csv", QUALITY_COLS, [{"clip": "x"}])


def test_csv_reader_rejects_wrong_header(tmp_path):
    (tmp_path / "q.csv").write_text("a,b\n1,2\n")
    with pytest.raises(ValueError):
        read_csv(tmp_path / "q.csv", QUALITY_COLS)


def test_cli_skips_stub_stages(fixture_clip, capsys, monkeypatch):
    from egovision.__main__ import main
    from egovision.stages import NotBuilt

    def stub(clip):
        raise NotBuilt("X1")

    monkeypatch.setattr("egovision.safety.run.run", stub)
    assert main(["run", "--clip", "fixture_001", "--stage", "safety", "--force"]) == 0
    assert "not built yet" in capsys.readouterr().out


def test_cli_reports_a_crashing_stage_and_returns_1(fixture_clip, capsys, monkeypatch):
    from egovision import stages
    from egovision.__main__ import main

    def boom(clip):
        raise RuntimeError("disk full")
    monkeypatch.setattr(stages.Stage, "load", lambda self: boom)
    assert main(["run", "--clip", "fixture_001", "--stage", "quality", "--force"]) == 1
    assert "FAIL RuntimeError: disk full" in capsys.readouterr().out
