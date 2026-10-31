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
    assert "fixture_001" in page and "grabs" in page


def test_empty_state_without_index(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "INDEX_DB", tmp_path / "none.db")
    monkeypatch.syspath_prepend(str(APP))
    at = _run("Home.py")
    assert not at.exception and "No clips indexed yet" in _html(at)


def test_export_page_previews_episodes(indexed):
    at = _run("pages/2_Export.py")
    assert not at.exception
    assert "Episodes" in _html(at) and at.button[0].label == "Build dataset"


def test_metrics_page_flags_synthetic_numbers(indexed):
    at = _run("pages/4_Metrics.py")
    assert not at.exception
    page = _html(at)
    assert "synthetic fixture numbers" in page and "Left/right correct" in page


def test_player_payload_links_videos_and_packs_the_timeline(indexed, tmp_path, monkeypatch):
    import player
    from egovision.index import query
    monkeypatch.setattr(player, "STATIC", tmp_path / "static")
    d = query.clip_data("fixture_001")
    p = player.payload("fixture_001", d, 30.0, 3.0)
    ours = next(v for v in p["views"] if v["key"] == "ours")
    assert ours["url"].startswith("/app/static/media/fixture_001/render.mp4?v=")
    assert (tmp_path / "static" / "fixture_001" / "render.mp4").exists()
    assert [v["url"] for v in p["views"] if v["key"] in ("2f", "5f")] == [None, None]   # robot views not rendered
    assert len(p["segments"]) == 3 and len(p["hands"]) == 90 and p["robot"]["2f"] == ["2f", "generic"]


def test_player_html_embeds_data_safely(indexed, monkeypatch, tmp_path):
    import player
    monkeypatch.setattr(player, "STATIC", tmp_path / "static")
    captured = {}
    monkeypatch.setattr(player.components, "html", lambda html, **kw: captured.setdefault("html", html))
    from egovision.index import query
    d = query.clip_data("fixture_001")
    d["steps"].loc[0, "caption"] = "</script><script>alert(1)</script>"
    player.player("fixture_001", d, 30.0, 3.0)
    html = captured["html"]
    assert html.count("</script>") == 1 and "/*DATA*/" not in html and "requestAnimationFrame" in html
