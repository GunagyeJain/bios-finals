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


def _html(at) -> str:
    return " ".join(e.proto.body for e in at.get("html"))


def test_library_renders_through_the_router(indexed):
    at = _run("Home.py")
    assert not at.exception
    page = _html(at)
    assert "<h1>Library</h1>" in page and "fixture_001" in page and "ev-strip" in page


def test_clip_review_renders_and_shows_moment(indexed):
    at = _run("pages/1_Clip_review.py", clip="fixture_001", t=1.5)
    assert not at.exception
    page = _html(at)
    assert "This moment · 0:01.5" in page and "screwdriver" in page and "Usable" in page


def test_empty_state_without_index(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "INDEX_DB", tmp_path / "none.db")
    monkeypatch.syspath_prepend(str(APP))
    at = _run("Home.py")
    assert not at.exception and "No clips indexed yet" in _html(at)


def test_export_page_previews_episodes(indexed):
    at = _run("pages/2_Export.py")
    assert not at.exception
    assert "Episodes" in _html(at) and at.button[0].label == "Build dataset"
