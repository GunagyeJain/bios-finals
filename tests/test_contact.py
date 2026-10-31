import numpy as np

from egovision.contact import rule


def _hand(tips):
    """21 keypoints: wrist at (0, 100), MCPs on y=50, tips given (5 x [x, y]); joints between."""
    kp = [[0.0, 100.0]]
    mcps = [[-30, 70], [-15, 50], [0, 50], [15, 50], [30, 55]]
    for (mx, my), (tx, ty) in zip(mcps, tips):
        kp += [[mx + (tx - mx) * k / 3, my + (ty - my) * k / 3] for k in range(4)]
    return kp


OPEN_TIPS = [[-60, 40], [-20, -40], [0, -45], [20, -40], [45, -15]]       # fingers stretched
FIST_TIPS = [[-10, 60], [-10, 70], [0, 72], [10, 70], [20, 70]]          # tips back at the palm


def test_tips_in_box_counts_padded_box():
    kp = _hand(FIST_TIPS)
    assert rule.tips_in_box(kp, [-12, 59, 15, 80], pad=0.0) == 4         # pinky tip x=20 is out
    assert rule.tips_in_box(kp, [100, 100, 200, 200], pad=0.15) == 0
    # (21, 70) lies 1 px outside a 0-20 box; 15 % pad (3 px) brings it in
    assert rule.tips_in_box([[21.0, 70.0]] * 21, [0, 60, 20, 80], pad=0.15) == 5


def test_closure_separates_fist_from_open_hand():
    assert rule.closure(_hand(FIST_TIPS)) < 0.6
    assert rule.closure(_hand(OPEN_TIPS)) > 1.0


def test_pick_object_prefers_more_tips_then_portable_then_smaller():
    kp = _hand(FIST_TIPS)
    table = {"id": 1, "name": "table", "kind": "fixed", "bbox": [-100, 0, 100, 200], "score": 0.9}
    tool = {"id": 2, "name": "drill", "kind": "portable", "bbox": [-15, 55, 25, 80], "score": 0.5}
    far = {"id": 3, "name": "box", "kind": "portable", "bbox": [300, 300, 400, 400], "score": 0.9}
    obj, n = rule.pick_object(kp, [table, tool, far])
    assert obj["id"] == 2 and n == 5
    obj, _ = rule.pick_object(kp, [table, far])
    assert obj["id"] == 1
    assert rule.pick_object(kp, [far]) == (None, 0)


def test_pick_object_requires_closure():
    open_kp = _hand(OPEN_TIPS)
    big = {"id": 1, "name": "table", "kind": "fixed", "bbox": [-200, -200, 200, 200], "score": 0.9}
    assert rule.pick_object(open_kp, [big]) == (None, 0)


def _samples(keys, dt=0.1):
    return [(i * dt, k, 1.0) for i, k in enumerate(keys)]


def test_hysteresis_needs_on_frames_to_start():
    assert rule.hysteresis(_samples([7, 7, 7, None] * 3), on=4, off=6) == []
    out = rule.hysteresis(_samples([None, 7, 7, 7, 7, None]), on=4, off=6)
    assert [(round(a, 1), round(b, 1), k) for a, b, k, _ in out] == [(0.1, 0.4, 7)]


def test_hysteresis_bridges_short_gaps_and_ends_after_off_frames():
    keys = [7] * 5 + [None] * 5 + [7] * 5 + [None] * 6 + [7] * 2
    out = rule.hysteresis(_samples(keys), on=4, off=6)
    assert len(out) == 1
    t0, t1, key, conf = out[0]
    assert (round(t0, 1), round(t1, 1), key) == (0.0, 1.4, 7)
    assert conf == 1.0


def test_hysteresis_switches_object_after_old_one_ends():
    keys = [1] * 5 + [2] * 10
    out = rule.hysteresis(_samples(keys), on=4, off=6)
    assert [(k, round(a, 1), round(b, 1)) for a, b, k, _ in out] == [(1, 0.0, 0.4), (2, 0.5, 1.4)]


def test_assign_ids_keeps_id_for_same_name_overlap():
    prev = [{"id": 0, "name": "drill", "bbox": [0, 0, 10, 10]}]
    dets = [{"name": "drill", "bbox": [1, 1, 11, 11]}, {"name": "table", "bbox": [0, 0, 10, 10]}]
    objs, nxt = rule.assign_ids(prev, dets, next_id=1, thr=0.3)
    assert [o["id"] for o in objs] == [0, 1] and nxt == 2


def test_moving_flags_box_that_changes_more_than_background():
    prev = np.zeros((100, 100), np.uint8)
    cur = prev.copy()
    cur[10:30, 10:30] = 80                       # machine box flickers
    cur[60:90, 60:90] = 80                       # hand moves, must be ignored
    flags = rule.moving(prev, cur, [[10, 10, 30, 30], [60, 60, 90, 90]], ignore=[[60, 60, 90, 90]])
    assert flags == [True, False]


PINCH_TIPS = [[-12, 46], [-10, 44], [0, -45], [20, -40], [45, -15]]     # thumb meets index, others straight


def test_grip_pinch_is_2f():
    assert rule.grip([_hand(PINCH_TIPS)] * 6, "portable") == "2f"


def test_grip_fist_is_5f():
    assert rule.grip([_hand(FIST_TIPS)] * 6, "portable") == "5f"


def test_grip_fixed_object_is_generic():
    assert rule.grip([_hand(FIST_TIPS)] * 6, "fixed") == "generic"


def test_grip_open_hand_or_missing_keypoints_is_unsure():
    assert rule.grip([_hand(OPEN_TIPS)] * 6, "portable") == "unsure"
    assert rule.grip([None, None, None, _hand(FIST_TIPS)], "portable") == "unsure"


def test_grip_uses_the_median_over_frames():
    frames = [_hand(PINCH_TIPS)] * 4 + [_hand(FIST_TIPS)] * 2
    assert rule.grip(frames, "portable") == "2f"
