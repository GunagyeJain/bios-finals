"""Smoke test: the app pages render on the fixture index without exceptions."""
from pathlib import Path

import pytest

from egovision import config

APP = Path(__file__).resolve().parents[1] / "app"


@pytest.fixture
def indexed(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(config, "FIXTURE_DIR", tmp_path / "videos")
    monkeypatch.setattr(config, "INDEX_DB", tmp_path / "outputs" / "index.db")
    monkeypatch.syspath_prepend(str(APP))
    from egovision.fixtures import make
    from egovision.index.build import build
    make("fixture_001", seconds=3)
    build()


def _run(page: str, **state):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP / page), default_timeout=30)
    for k, v in state.items():
        at.session_state[k] = v
    return at.run()


def test_library_renders(indexed):
    at = _run("Home.py")
    assert not at.exception
    assert [m.label for m in at.metric][:2] == ["Clips", "Green time"]


def test_clip_review_renders_and_shows_moment(indexed):
    at = _run("pages/1_Clip_review.py", clip="fixture_001", t=1.5)
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "This moment · 0:02" in text
    assert any("holds screwdriver" in m.value for m in at.markdown)


def test_empty_state_without_index(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "INDEX_DB", tmp_path / "none.db")
    monkeypatch.syspath_prepend(str(APP))
    at = _run("Home.py")
    assert not at.exception and "No index yet" in at.info[0].value
