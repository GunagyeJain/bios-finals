import numpy as np
import pytest

from egovision.recovery import api
from egovision.recovery import params as P
from egovision.schema import Hand


def hand(x1=100.0, y1=200.0, x2=200.0, y2=260.0):
    kp = [[x1 + i, y1 + i] for i in range(21)]
    return Hand(side="left", bbox=[x1, y1, x2, y2], score=0.9, kp2d=kp)


def test_to_full_undoes_crop_and_upscale():
    assert api.to_full([[40.0, 10.0]], [300, 100, 400, 200], 2.0) == [[320.0, 105.0]]


def test_crop_to_full_round_trip_lands_on_the_original_pixels():
    roi = api.grow_box([300, 200, 400, 300], 2.0, 1920, 1080)
    point = [350.0, 250.0]
    in_crop = [(point[0] - roi[0]) * 2, (point[1] - roi[1]) * 2]
    assert api.to_full([in_crop], roi, 2.0)[0] == pytest.approx(point)


def test_grow_box_is_square_centred_and_scaled():
    assert api.grow_box([100, 200, 200, 260], 2.0, 1920, 1080) == [50, 130, 251, 331]


def test_grow_box_stays_inside_the_frame():
    x1, y1, x2, y2 = api.grow_box([0, 0, 100, 100], 2.0, 150, 150)
    assert (x1, y1) == (0, 0) and x2 <= 150 and y2 <= 150


def test_grow_box_keeps_a_usable_crop_for_a_tiny_hand():
    x1, y1, x2, y2 = api.grow_box([500, 500, 510, 510], 2.0, 1920, 1080, min_size=96)
    assert x2 - x1 >= 96 and y2 - y1 >= 96


def test_agreement_is_one_when_points_match_and_zero_when_far():
    h = hand()
    assert api.agreement_score(h.kp2d, h.kp2d, h.bbox) == 1.0
    far = [[x + 1000, y] for x, y in h.kp2d]
    assert api.agreement_score(h.kp2d, far, h.bbox) == 0.0


def test_agreement_falls_with_distance_in_hand_sizes():
    h = hand()
    near = [[x + 0.1 * 100, y] for x, y in h.kp2d]
    assert api.agreement_score(h.kp2d, near, h.bbox) == pytest.approx(1 - 0.1 / P.AGREE_ZERO)


def test_agreement_ignores_joints_other_than_wrist_and_tips():
    h = hand()
    other = [list(p) for p in h.kp2d]
    other[2] = [9999.0, 9999.0]
    assert api.agreement_score(h.kp2d, other, h.bbox) == 1.0


def test_recover_without_a_last_hand_is_none():
    assert api.recover_missing(np.zeros((100, 100, 3), np.uint8), 0, 0.0, "left", None) is None


def test_nearest_box_maps_crop_to_full_frame_and_picks_the_closest():
    last = hand(100, 100, 200, 200)
    boxes = np.array([[300, 300, 340, 340], [20, 30, 120, 130]], float)
    assert api.nearest_box(boxes, [100, 100, 500, 500], last) == [120.0, 130.0, 220.0, 230.0]


def test_nearest_box_rejects_a_hand_out_of_reach():
    last = hand(100, 100, 200, 200)
    assert api.nearest_box(np.array([[900.0, 900.0, 950.0, 950.0]]), [0, 0, 1000, 1000], last) is None
    assert api.nearest_box(np.zeros((0, 4)), [0, 0, 1000, 1000], last) is None


def test_no_detector_box_means_no_rtmlib_hand(monkeypatch):
    monkeypatch.setattr(api, "_detector", lambda: lambda crop: np.zeros((0, 4)))
    monkeypatch.setattr(api, "_pose", lambda: pytest.fail("pose must not run without a detected hand"))
    assert api._roi_rtmlib(np.zeros((400, 400, 3), np.uint8), "left", hand()) is None


def test_detected_hand_comes_back_in_full_frame_pixels(monkeypatch):
    pts = np.tile(np.arange(21.0)[:, None], (1, 2))[None] + 100
    monkeypatch.setattr(api, "_detector", lambda: lambda crop: np.array([[100.0, 100.0, 200.0, 200.0]]))
    monkeypatch.setattr(api, "_pose", lambda: lambda img, bboxes: (pts, np.full((1, 21), 0.3)))
    h = api._roi_rtmlib(np.zeros((400, 400, 3), np.uint8), "right", hand())
    assert h.source == "rtmlib" and h.side == "right" and h.kp3d is None
    assert h.bbox == [100.0, 100.0, 120.0, 120.0] and h.score == pytest.approx(0.3)


def test_roi_miss_falls_through_to_rtmlib(monkeypatch):
    calls = []
    monkeypatch.setattr(api, "_roi_mediapipe", lambda *a: calls.append("roi"))
    monkeypatch.setattr(api, "_roi_rtmlib", lambda *a: calls.append("rtmlib"))
    assert api.recover_missing(np.zeros((400, 400, 3), np.uint8), 0, 0.0, "left", hand()) is None
    assert calls == ["roi", "rtmlib"]


def test_an_rtmlib_hand_never_seeds_another_rtmlib_hand(monkeypatch):
    monkeypatch.setattr(api, "_roi_mediapipe", lambda *a: None)
    monkeypatch.setattr(api, "_roi_rtmlib", lambda *a: pytest.fail("rtmlib must not chain"))
    last = hand()
    last.source = "rtmlib"
    assert api.recover_missing(np.zeros((400, 400, 3), np.uint8), 0, 0.0, "left", last) is None
