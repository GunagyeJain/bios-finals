import numpy as np
import pytest

from egovision.hands import cleanup, params
from egovision.hands.refine import merge_wilor, refine
from egovision.hands.wilor import Request, crop_box, make_patch, select, to_hand
from egovision.schema import N_KP, FrameHands, Hand

W, H, FPS = 1920, 1080, 30.0


def hand(side="left", x=400.0, y=500.0, id=0, source="mediapipe", flags=(), score=0.9):
    kp = [[x + 50 * (k / (N_KP - 1) - 0.5), y + 50 * (k / (N_KP - 1) - 0.5)] for k in range(N_KP)]
    kp[0] = [x, y]
    return Hand(side=side, bbox=cleanup.bbox_of(kp), score=score, kp2d=kp, kp3d=[[0.01 * k, 0, 0] for k in range(N_KP)],
                id=id, source=source, flags=list(flags))


def row(frame, *hands):
    return FrameHands(frame, frame / FPS, list(hands))


def req(side="right", bbox=(900.0, 500.0, 1000.0, 600.0)):
    return Request(0, 0.0, 3, side, bbox, "flagged")


# ---------- selection ----------
def test_selects_flagged_and_gap_filled_hands_on_sampled_frames_only():
    rows = [row(0, hand()), row(1, hand(source="interp", flags=["low_conf"])), row(2, hand(source="interp")),
            row(3, hand()), row(4, hand(flags=["low_conf"])), row(6, hand(flags=["disagree"])), row(8, hand(flags=["edge"]))]
    got = {(r.frame, r.reason) for r in select(rows, 2, FPS)}
    assert (2, "missing") in got and (4, "flagged") in got and (6, "flagged") in got
    assert not {f for f, _ in got} & {0, 1, 3, 8}


def test_absent_hand_inside_a_live_track_gets_an_interpolated_box():
    rows = [row(0, hand(x=400)), row(30, hand(x=700))]
    got = {r.frame: r for r in select(rows, 2, FPS)}
    assert sorted(got) == list(range(2, 30, 2))
    assert got[14].reason == "missing" and got[14].id == 0 and got[14].t == pytest.approx(14 / FPS)
    assert (got[14].bbox[0] + got[14].bbox[2]) / 2 == pytest.approx(400 + 300 * 14 / 30, abs=30)


def test_track_gone_longer_than_keep_time_is_not_sent():
    assert select([row(0, hand()), row(90, hand())], 2, FPS) == []


# ---------- crops ----------
def test_patch_is_model_sized_and_mirrored_for_left_hands():
    img = np.zeros((H, W, 3), dtype=np.uint8)
    img[500:600, 900:950] = 255  # left half of the box
    right = make_patch(img, (900, 500, 1000, 600), "right")
    left = make_patch(img, (900, 500, 1000, 600), "left")
    assert right.shape == (params.WILOR_PATCH, params.WILOR_PATCH, 3)
    assert np.array_equal(left[:, ::-1], right)
    assert right[128, 110].max() > 200 and right[128, 146].max() < 50


def test_patch_at_the_image_corner_is_padded_not_crashed():
    img = np.full((H, W, 3), 255, dtype=np.uint8)
    p = make_patch(img, (0, 0, 100, 100), "right")
    assert p[0, 0].max() == 0 and p[255, 255].max() == 255


# ---------- camera maths ----------
def test_wrist_at_origin_projects_to_the_crop_centre():
    r = req()
    joints = np.zeros((N_KP, 3))
    h = to_hand(joints, np.array([1.5, 0.0, 0.0]), r, W, H)
    assert h.kp2d[0] == pytest.approx(list(crop_box(r.bbox)[:2]))


def test_left_hand_comes_back_mirrored():
    joints = np.zeros((N_KP, 3))
    joints[8] = [0.05, 0.0, 0.0]
    cam = np.array([1.5, 0.0, 0.0])
    r_kp = to_hand(joints, cam, req("right"), W, H).kp2d[8][0]
    l_kp = to_hand(joints, cam, req("left"), W, H).kp2d[8][0]
    centre = crop_box(req().bbox)[0]
    assert r_kp > centre and l_kp < centre
    assert r_kp - centre == pytest.approx(centre - l_kp)


def test_to_hand_meets_the_contract_and_centres_world_points():
    joints = np.random.default_rng(0).normal(0, 0.03, (N_KP, 3))
    h = to_hand(joints, np.array([1.5, 0.01, -0.01]), req(), W, H)
    assert (h.source, h.id, h.side, h.score) == ("wilor", 3, "right", params.WILOR_SCORE)
    assert np.mean(h.kp3d, axis=0) == pytest.approx([0, 0, 0], abs=1e-9)


# ---------- merge ----------
def test_merge_replaces_points_and_keeps_id_and_side():
    base = hand(id=7, score=0.3, flags=["low_conf"])
    w = hand(x=410, id=99, source="wilor", score=params.WILOR_SCORE)
    out = merge_wilor([row(0, base)], [row(0, w)])[0].hands
    assert len(out) == 1
    assert (out[0].id, out[0].side, out[0].source) == (7, "left", "wilor")
    assert out[0].kp2d[0][0] == 410 and out[0].score == params.WILOR_SCORE


def test_merge_fills_a_missing_hand_into_its_track():
    out = merge_wilor([row(0, hand(id=7)), row(2), row(4, hand(id=7))], [row(2, hand(id=7, source="wilor"))])
    assert [h.id for h in out[1].hands] == [7]


def test_merge_ignores_a_far_hand_of_an_unknown_track():
    out = merge_wilor([row(0, hand(id=7))], [row(0, hand(x=1500, id=42, source="wilor"))])
    assert [h.id for h in out[0].hands] == [7]


def test_refine_uses_wilor_and_then_clears_its_low_conf_flag():
    src = [row(i * 2, hand(score=0.4)) for i in range(10)]
    wilor = [row(8, hand(x=403, id=0, source="wilor", score=params.WILOR_SCORE))]
    out = refine(src, 20, FPS, W, H, wilor=wilor)
    assert out[8].hands[0].source == "wilor" and "low_conf" not in out[8].hands[0].flags
    assert out[6].hands[0].source == "mediapipe" and "low_conf" in out[6].hands[0].flags
