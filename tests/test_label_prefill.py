import json
import sys
import types

import numpy as np

from egovision import config
from egovision.eval import label_tool as lt
from egovision.eval import prelabel as pl

RIGHT = [[110, 100], [80, 60], [90, 50], [100, 48], [108, 52], [114, 60]]   # wrist right of the hand's centre
LEFT = [[300, 100], [330, 60], [320, 50], [310, 48], [302, 52], [296, 60]]


def _sugs():
    return [{"points": RIGHT, "side": "right"}, {"points": LEFT, "side": None}]


def test_accept_suggestion_as_is():
    d = lt.FrameDraft.with_suggestions(10, _sugs(), "rtmlib")
    assert "press l or r" in d.problem()            # the model was unsure about hand 2
    d.set_side("left")                              # active = last hand
    label = d.to_label(640, 360)
    assert [(h["side"], h["prefill"], h["edited"]) for h in label["hands"]] == [
        ("right", "rtmlib", False), ("left", "rtmlib", False)]   # filling an empty side is not an edit
    assert label["hands"][0]["wrist"] == RIGHT[0]


def test_click_replaces_nearest_suggested_point_and_marks_edited():
    d = lt.FrameDraft.with_suggestions(10, _sugs(), "rtmlib")
    assert d.click(92, 54, radius=20)               # near hand 1's index tip [90, 50]
    assert d.hands[0].points[2] == [92, 54] and d.hands[0].moved == {2} and d.active == 0
    d.set_side("left")                              # flips hand 1's guessed side
    assert d.hands[0].side == "left" and d.hands[0].edited


def test_far_click_starts_a_manual_hand_only_if_room():
    d = lt.FrameDraft.with_suggestions(10, _sugs()[:1], "rtmlib")
    assert d.click(500, 300, radius=20)             # nowhere near: new hand, clicked by hand
    assert len(d.hands) == 2 and d.hands[1].prefill is None and d.hands[1].points == [[500, 300]]
    d.click(91, 51, radius=20)                      # manual hand still open: the click continues it
    assert len(d.hands[1].points) == 2 and d.hands[0].moved == set()
    full = lt.FrameDraft.with_suggestions(10, _sugs(), "rtmlib")
    assert full.click(500, 300, radius=20) is False


def test_clear_removes_a_wrong_suggestion_and_undo_leaves_it_alone():
    d = lt.FrameDraft.with_suggestions(10, _sugs(), "rtmlib")
    d.undo()
    assert len(d.hands) == 2
    d.click(301, 101, radius=20)                    # makes hand 2 active
    d.clear_hand()
    assert len(d.hands) == 1 and d.hands[0].points[0] == RIGHT[0]


def test_web_hand_works_out_edits_against_the_suggestion():
    sugs = _sugs()
    same = lt.web_hand({"points": RIGHT, "side": "right", "sug": 0}, sugs, "rtmlib")
    assert same.prefill == "rtmlib" and not same.edited
    moved = lt.web_hand({"points": [[111, 100]] + RIGHT[1:], "side": "right", "sug": 0}, sugs, "rtmlib")
    assert moved.moved == {0} and moved.edited
    manual = lt.web_hand({"points": RIGHT, "side": "right", "sug": None}, sugs, "rtmlib")
    assert manual.prefill is None and not manual.edited


def test_guess_side_and_model_filtering():
    assert pl.guess_side(RIGHT) == "right" and pl.guess_side(LEFT) == "left"
    assert pl.guess_side([[100, 100]] + [[95 + 2 * k, 50] for k in range(5)]) is None
    kp = np.zeros((2, 21, 2))
    kp[0, list(pl.KP)] = RIGHT
    kp[1, list(pl.KP)] = RIGHT
    sc = np.full((2, 21), 0.9)
    sc[1] = 0.1                                     # second hand too unsure
    assert pl.hands_from_model([], kp, sc) == []    # no detector box: rtmlib's whole-image pose is noise
    hands = pl.hands_from_model([[0, 0, 1, 1]] * 2, kp, sc)
    assert len(hands) == 1 and hands[0]["side"] == "right" and hands[0]["points"] == RIGHT


def _fake_clip(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(config, "EVAL_LABELS", tmp_path / "labels")
    monkeypatch.setattr(lt, "SHARED_DIR", tmp_path / "labels" / "shared")
    monkeypatch.setattr(lt, "clip_info", lambda clip: (640, 360, 9000, 30.0, 2))
    monkeypatch.setattr(lt, "frame_image", lambda clip, f: np.zeros((360, 640, 3), np.uint8))
    monkeypatch.setattr(pl, "frame_image", lambda clip, f: np.zeros((360, 640, 3), np.uint8))
    seen = []

    class FakeHand:
        def __init__(self, **_):
            self.det_model = lambda img: seen.append(1) or [[0, 0, 10, 10]]
            kp = np.zeros((1, 21, 2))
            kp[0, list(pl.KP)] = RIGHT
            self.pose_model = lambda img, bboxes: (kp, np.full((1, 21), 0.9))

    monkeypatch.setitem(sys.modules, "rtmlib", types.SimpleNamespace(Hand=FakeHand))
    return seen


def test_prelabel_covers_exactly_the_tools_frames(monkeypatch, tmp_path):
    _fake_clip(monkeypatch, tmp_path)
    data = pl.run("clipA", "Shefali", 10)
    session = lt.Session("clipA", "shefali", 10, shared=False)
    assert [int(f) for f in data["frames"]] == session.todo
    assert session.prefill == "rtmlib" and session.draft(session.todo[0]).hands[0].prefill == "rtmlib"
    assert session.draft(session.todo[0]).hands[0].side is None     # side guesses stay off: labeller presses L/R
    assert json.loads(lt.prelabels_path("clipA", "shefali").read_text())["model"] == "rtmlib"


def test_shared_frames_never_get_suggestions(monkeypatch, tmp_path):
    _fake_clip(monkeypatch, tmp_path)
    pl.run("clipA", "abhijay", 40)
    shared = lt.Session("clipA", "abhijay", 40, shared=True)
    assert shared.suggestions == {} and shared.prefill is None
    assert all(shared.draft(f).hands == [] for f in shared.todo)
