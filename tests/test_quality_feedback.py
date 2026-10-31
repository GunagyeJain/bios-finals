import pytest

from egovision import config
from egovision.quality import feedback
from egovision.schema import QUALITY_COLS, ClipPaths, write_csv


def seconds(n, **reasons):
    """n one-second rows; reasons maps a reason to the seconds it fails on."""
    return [{"t_start": s, "reasons": ";".join(r for r, secs in reasons.items() if s in secs)} for s in range(n)]


def test_clean_clip_says_so():
    assert feedback.summarise(seconds(10)) == "no capture problems found"


def test_share_of_the_clip_is_reported():
    assert feedback.summarise(seconds(100, hands_out=range(0, 100, 5))) == "hands out of view 20 %"


def test_a_long_stretch_gets_its_times():
    assert feedback.summarise(seconds(100, dark=range(41, 59))) == "dark 18 %, longest 0:41–0:59"


def test_a_short_stretch_gets_no_times():
    assert feedback.summarise(seconds(100, dark=range(41, 41 + 4))) == "dark 4 %"


def test_biggest_problem_comes_first():
    text = feedback.summarise(seconds(10, blur=[1], hands_out=[1, 2, 3]))
    assert text == "hands out of view 30 %; blurry 10 %"


def test_one_second_can_carry_several_reasons():
    assert feedback.summarise(seconds(2, dark=[0], blur=[0])).count("50 %") == 2


def test_every_reason_the_light_can_give_has_a_word():
    from egovision.quality import light
    hard = {"dark_share": 1.0, "clipped_share": 1.0, "frozen": True, "blur_rel": 0.0, "speed": 99.0, "hands_visible": 0.0,
            "edge_cut": 1.0, "hand_y": 0.01, "agreement": 0.0}
    soft = {**hard, "dark_share": 0.6, "frozen": False, "blur_rel": 0.3, "hands_visible": 0.5}
    used = {r for m in (hard, soft) for r in light.judge(m)[1].split(";")}
    assert {"dark", "dim", "frozen", "blur", "hands_out", "hands_partial", "disagree"} <= used
    assert used <= set(feedback.WORDS)


def test_unknown_reason_is_shown_as_it_is():
    assert feedback.summarise(seconds(2, new_check=[0])) == "new_check 50 %"


def test_longest_run_picks_the_longest_and_handles_the_end():
    assert feedback.longest_run([1, 2, 7, 8, 9, 10]) == (7, 11)
    assert feedback.longest_run([3]) == (3, 4)


@pytest.mark.parametrize("s,text", [(0, "0:00"), (65, "1:05"), (179, "2:59")])
def test_clock(s, text):
    assert feedback.clock(s) == text


def test_capture_feedback_reads_quality_csv(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS", tmp_path)
    p = ClipPaths("clip_x").mkdir()
    write_csv(p.quality, QUALITY_COLS, [
        {"clip": "clip_x", "t_start": 0.0, "t_end": 1.0, "light": "red", "reasons": "hands_out", "blur": 1,
         "brightness": 0.5, "hands_visible": 0, "edge_cut": -1, "agreement": -1, "frozen": 0}])
    assert feedback.capture_feedback("clip_x") == "hands out of view 100 %"


def test_datasheet_picks_it_up(tmp_path, monkeypatch):
    from egovision.products import datasheet
    monkeypatch.setattr(config, "OUTPUTS", tmp_path)
    lines = datasheet._feedback(["clip_missing"])
    assert lines == ["- `clip_missing`: feedback unavailable (FileNotFoundError)"]
