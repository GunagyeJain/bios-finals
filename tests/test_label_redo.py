import numpy as np

from egovision import config
from egovision.eval import label_tool as lt

POINTS = [[100, 100], [80, 60], [90, 50], [100, 48], [108, 52], [114, 60]]


def _session(monkeypatch, tmp_path, redo=0):
    monkeypatch.setattr(config, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(config, "EVAL_LABELS", tmp_path / "labels")
    monkeypatch.setattr(lt, "FRAMES_DIR", tmp_path / "frames")
    monkeypatch.setattr(lt, "clip_info", lambda clip: (640, 360, 9000, 30.0, 2))
    monkeypatch.setattr(lt, "frame_image", lambda clip, f: np.zeros((360, 640, 3), np.uint8))
    return lt.Session("clipA", "shefali", 5, False, redo)


def _label_all(s):
    while (f := s.next_frame()) is not None:
        d = lt.FrameDraft(f)
        for x, y in POINTS:
            d.click(x, y)
        d.set_side("right")
        d.toggle_tag("glove")
        s.save(d)


def test_redo_reopens_first_n_in_labelling_order_with_saved_hands(monkeypatch, tmp_path):
    _label_all(_session(monkeypatch, tmp_path))
    s = _session(monkeypatch, tmp_path, redo=3)
    first3 = [f for f in s.todo if f in s.done][:3]
    assert s.redo == first3 and s.next_frame() == first3[0]
    d = s.draft(first3[0])
    assert d.hands[0].points == POINTS and d.hands[0].side == "right" and d.tags == ["glove"]
    for x, y in [[400, 200], [380, 160], [390, 150], [400, 148], [408, 152], [414, 160]]:
        d.click(x, y, s.radius)                     # far from the saved hand: the missing hand
    d.set_side("left")
    s.save(d)
    saved = next(f for f in s.data["frames"] if f["frame"] == first3[0])
    assert [h["side"] for h in saved["hands"]] == ["right", "left"]
    assert all(h["prefill"] is None and h["edited"] is False for h in saved["hands"])
    assert s.redo == first3[1:]


def test_redo_x_keeps_the_frame_and_resumes_after_restart(monkeypatch, tmp_path):
    _label_all(_session(monkeypatch, tmp_path))
    s = _session(monkeypatch, tmp_path, redo=2)
    first = s.next_frame()
    s.skip(first)                                   # x on a redo frame: keep it as saved
    assert first not in s.skipped and first in s.done
    again = _session(monkeypatch, tmp_path)         # restart without --redo: one frame still pending
    assert len(again.redo) == 1 and again.next_frame() == again.redo[0]
    again.skip(again.redo[0])
    assert again.next_frame() is None and not again.redo_file.exists()


def test_redo_keeps_prefill_and_edited_of_saved_hands():
    saved = [{"points": POINTS, "side": "left", "prefill": "rtmlib", "edited": True}]
    d = lt.FrameDraft.with_suggestions(4, saved, None)
    assert d.hands[0].prefill == "rtmlib" and d.hands[0].edited
    h = lt.web_hand({"points": POINTS, "side": "left", "sug": 0}, saved, None)
    assert h.prefill == "rtmlib" and h.edited
