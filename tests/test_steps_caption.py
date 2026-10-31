import json
from types import SimpleNamespace

import pytest

from egovision import config
from egovision.schema import STEP_COLS, read_csv
from egovision.steps import caption as cap
from egovision.steps import params as P


def _c(t0, t1, hand="right", obj="screwdriver", state="portable"):
    return {"t_start": str(t0), "t_end": str(t1), "hand": hand, "object_name": obj, "state": state}


def test_event_windows_merge_short_and_split_long():
    wins = cap.event_windows([_c(1, 4), _c(4.5, 6, "left", "press"), _c(7, 50)])
    assert wins[:3] == [(1.0, 4.5), (4.5, 6.0), (6.0, 7.0)]
    rest = wins[3:]                                    # 7 → 50 s split into windows of at most 20 s
    assert rest[0][0] == 7.0 and rest[-1][1] == 50.0 and len(rest) == 3
    assert all(b - a <= P.MAX_WIN_S + 1e-6 for a, b in wins)


def test_event_windows_ignore_none_state_and_need_two_events():
    assert cap.event_windows([_c(1, 3, state="none")]) == []
    assert cap.event_windows([]) == []


def test_fixed_windows_cover_the_clip():
    wins = cap.fixed_windows(180.0)
    assert wins[0][0] == 0 and wins[-1][1] == 180.0 and len(wins) == round(180 / P.FALLBACK_WIN_S)


def test_contact_hint_picks_largest_overlap():
    contacts = [_c(0, 2, "left", "hinge"), _c(1, 9, "right", "drill")]
    assert cap.contact_hint(contacts, 1, 5) == {"hand": "right", "object": "drill"}
    assert cap.contact_hint(contacts, 20, 25) == {"hand": "", "object": ""}


def test_clean_answer_forces_the_verb_list():
    a = cap.clean_answer({"verb": "Screw", "object": "  Hinge  Pin ", "hand": "RIGHT", "caption": "x"})
    assert a == {"verb": "other", "object": "hinge pin", "hand": "right", "caption": "x"}


class FakeModels:
    def __init__(self, answers):
        self.answers, self.calls = list(answers), 0

    def generate_content(self, model, contents, config):
        self.calls += 1
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a
        return SimpleNamespace(text=json.dumps(a))


class RateLimited(Exception):
    code = 429


ANSWER = {"verb": "fasten", "object": "screw", "hand": "right", "caption": "right hand fastens the screw"}


def test_ask_gemini_backs_off_on_429():
    client = SimpleNamespace(models=FakeModels([RateLimited(), RateLimited(), ANSWER]))
    waits = []
    assert cap.ask_gemini(client, b"video", "prompt", sleep=waits.append) == ANSWER
    assert waits == [P.BACKOFF_S, 2 * P.BACKOFF_S]


def test_ask_gemini_does_not_retry_other_errors():
    client = SimpleNamespace(models=FakeModels([ValueError("bad request")]))
    with pytest.raises(ValueError):
        cap.ask_gemini(client, b"video", "prompt", sleep=lambda s: None)
    assert client.models.calls == 1


@pytest.fixture
def fixture_clip(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(config, "FIXTURE_DIR", tmp_path / "videos")
    monkeypatch.setattr(config, "GEMINI_CACHE", tmp_path / "cache")
    monkeypatch.setattr(cap, "cut_window", lambda clip, t0, t1, path: path.write_bytes(b"mp4"))
    from egovision.fixtures import make
    return make("fixture_001")


def test_run_writes_steps_caches_and_falls_back(fixture_clip):
    # fixture contacts → windows 1-4.5, 4.5-6, 6-7, 7-10; the third call fails for good
    models = FakeModels([ANSWER, ANSWER, ValueError("blocked"), ANSWER])
    stats = cap.run("fixture_001", client=SimpleNamespace(models=models), sleep=lambda s: None)
    assert stats == {"windows": 4, "cached": 0, "calls": 4, "failed": 1}
    rows = read_csv(fixture_clip.steps, STEP_COLS)
    assert [r["source"] for r in rows] == ["gemini", "gemini", "contact", "gemini"]
    assert rows[2]["verb"] == "other" and rows[2]["caption"] == ""
    assert rows[0]["verb"] == "fasten" and rows[0]["start_s"] == "1.0" and rows[0]["end_s"] == "4.5"

    again = FakeModels([ANSWER])                       # only the failed window is asked again
    stats = cap.run("fixture_001", client=SimpleNamespace(models=again), sleep=lambda s: None)
    assert stats["cached"] == 3 and again.calls == 1


def test_run_without_key_uses_contacts(fixture_clip, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    stats = cap.run("fixture_001")
    rows = read_csv(fixture_clip.steps, STEP_COLS)
    assert stats["calls"] == 0 and {r["source"] for r in rows} == {"contact"}
    assert rows[0]["object"] == "screwdriver" and rows[0]["hand"] == "right"


def test_run_falls_back_to_fixed_windows_without_contacts(fixture_clip, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    fixture_clip.contacts.unlink()
    cap.run("fixture_001")
    rows = read_csv(fixture_clip.steps, STEP_COLS)
    assert float(rows[-1]["end_s"]) == pytest.approx(12.0) and len(rows) == round(12 / P.FALLBACK_WIN_S)
