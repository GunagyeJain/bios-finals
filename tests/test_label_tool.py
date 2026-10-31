import json

import pytest

from egovision import config
from egovision.eval import label_tool as lt


def _hand(d: lt.FrameDraft, side: str, x0: float = 100, y0: float = 100) -> None:
    for k in range(lt.N_POINTS):
        d.click(x0 + 10 * k, y0 + 5 * k)
    d.set_side(side)


def test_pick_frames_is_deterministic_and_on_step():
    hard = list(range(100, 200))
    a = lt.pick_frames(40, 3000, hard, seed=7, step=2, min_gap=30)
    assert a == lt.pick_frames(40, 3000, hard, seed=7, step=2, min_gap=30)
    assert len(a) == len(set(a)) == 40
    assert all(f % 2 == 0 and 0 <= f < 3000 for f in a)


def test_pick_frames_hard_share():
    hard = list(range(0, 3000, 2))[:300]
    picks = lt.pick_frames(40, 30000, hard, seed=1, step=2)
    assert sum(f in hard for f in picks) >= 24          # 60 % of 40


def test_pick_frames_few_hard_and_short_clip():
    assert len(lt.pick_frames(40, 3000, [10, 12], seed=1, step=2, min_gap=30)) == 40
    assert lt.pick_frames(40, 20, [], seed=1, step=2, min_gap=30) == list(range(0, 20, 2))


def test_labelling_order_puts_picks_first_then_backups():
    order = lt.labelling_order(10, 5000, [], seed=3, step=2, min_gap=30)
    assert len(order) == len(set(order)) > 10
    assert set(order[:10]) == set(lt.pick_frames(10, 5000, [], 3, 2, 30))


def test_box_pads_15_percent_and_clips():
    assert lt.box_from_points([[100, 100], [200, 150]], 640, 360) == [85.0, 92.5, 215.0, 157.5]
    assert lt.box_from_points([[0, 0], [639, 359]], 640, 360) == [0.0, 0.0, 639.0, 359.0]


def test_draft_needs_six_points_and_a_side():
    d = lt.FrameDraft(10)
    assert d.problem() is None                          # no hands is a valid label
    d.click(1, 1)
    assert "5 clicks missing" in d.problem()
    for _ in range(5):
        d.click(5, 5)
    assert "press l or r" in d.problem()
    d.set_side("left")
    assert d.problem() is None


def test_draft_rejects_two_hands_same_side_and_a_third_hand():
    d = lt.FrameDraft(0)
    _hand(d, "left")
    _hand(d, "left", 300)
    assert "same side" in d.problem()
    d.set_side("right")
    assert d.problem() is None
    assert d.click(1, 1) is False


def test_undo_removes_points_then_hand():
    d = lt.FrameDraft(0)
    _hand(d, "right")
    d.click(400, 400)
    d.undo()
    assert len(d.hands) == 1 and d.hands[0].complete
    for _ in range(6):
        d.undo()
    assert d.hands == []
    d.undo()                                            # nothing left: no error


def test_label_json_matches_schema_and_resumes(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EVAL_LABELS", tmp_path)
    path = lt.labels_path("factory_003", "shefali")
    data = lt.load_labels(path, "factory_003", "shefali")
    d = lt.FrameDraft(812)
    _hand(d, "right")
    d.toggle_tag("glove")
    d.toggle_tag("blur")
    lt.save_labels(path, data, d.to_label(854, 480))
    lt.save_labels(path, data, lt.FrameDraft(100).to_label(854, 480))
    saved = json.loads(path.read_text())
    assert path.name == "factory_003__shefali.json"
    assert set(saved) == {"clip", "labeller", "frames"}
    assert [f["frame"] for f in saved["frames"]] == [100, 812]
    f = saved["frames"][1]
    assert f["tags"] == ["blur", "glove"]               # fixed order, whatever the key order
    h = f["hands"][0]
    assert set(h) == {"side", "bbox", "wrist", "tips"}
    assert h["side"] == "right" and h["wrist"] == [100, 100] and len(h["tips"]) == 5
    again = lt.load_labels(path, "factory_003", "shefali")
    assert again == saved


def test_save_replaces_same_frame(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EVAL_LABELS", tmp_path)
    path = lt.labels_path("c", "x")
    data = lt.load_labels(path, "c", "x")
    lt.save_labels(path, data, lt.FrameDraft(5).to_label(100, 100))
    d = lt.FrameDraft(5)
    _hand(d, "left", 10, 10)
    lt.save_labels(path, data, d.to_label(100, 100))
    assert len(json.loads(path.read_text())["frames"]) == 1


def test_validate_rejects_bad_label():
    with pytest.raises(AssertionError):
        lt.validate_label({"frame": 1, "tags": ["smoke"], "hands": []})


def test_shared_frames_same_for_everyone(tmp_path, monkeypatch):
    monkeypatch.setattr(lt, "SHARED_DIR", tmp_path / "shared")
    monkeypatch.setattr(config, "OUTPUTS", tmp_path / "outputs")
    a = lt.shared_frames("factory_009", 9000, 30.0, 2)
    assert len(a) == lt.SHARED_N
    assert lt.shared_frames("factory_009", 9000, 30.0, 2) == a
    assert json.loads((tmp_path / "shared" / "factory_009.json").read_text())["frames"] == a
