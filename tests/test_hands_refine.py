import numpy as np
import pytest

from egovision.eval.metrics import jitter, swaps_per_min
from egovision.hands import cleanup, params, tracking
from egovision.hands.refine import apply_mirror, apply_recovery, refine
from egovision.schema import N_KP, FrameHands, Hand

W, H, FPS = 1920, 1080, 30.0


def hand(side, x, y=500.0, score=0.9, s=100.0, kp3d=True):
    kp = [[x + s * (k / (N_KP - 1) - 0.5), y + s * (k / (N_KP - 1) - 0.5)] for k in range(N_KP)]
    kp[0] = [x, y]
    world = [[0.01 * k, 0.0, 0.0] for k in range(N_KP)] if kp3d else None
    return Hand(side=side, bbox=cleanup.bbox_of(kp), score=score, kp2d=kp, kp3d=world)


def rows(*per_frame, step=2):
    return [FrameHands(i * step, i * step / FPS, list(hs)) for i, hs in enumerate(per_frame)]


def tracked(frames):
    return tracking.vote_sides(tracking.split_on_side_change(tracking.assign_ids(frames, W)), W)


# ---------- tracking ----------
def test_same_hand_keeps_id_and_new_hand_gets_another():
    out = tracking.assign_ids(rows([hand("left", 400)], [hand("left", 410), hand("right", 1500)],
                                   [hand("right", 1510), hand("left", 420)]), W)
    ids = [{h.side: h.id for h in fr.hands} for fr in out]
    assert ids[0]["left"] == ids[1]["left"] == ids[2]["left"]
    assert ids[1]["right"] == ids[2]["right"] != ids[1]["left"]


def test_reentry_inside_keep_time_keeps_id():
    gap = [[] for _ in range(20)]  # 1.33 s at step 2
    out = tracking.assign_ids(rows([hand("left", 400)], *gap, [hand("left", 450)]), W)
    assert out[0].hands[0].id == out[-1].hands[0].id


def test_reentry_after_keep_time_gets_new_id():
    gap = [[] for _ in range(40)]  # 2.67 s at step 2
    out = tracking.assign_ids(rows([hand("left", 400)], *gap, [hand("left", 410)]), W)
    assert out[0].hands[0].id != out[-1].hands[0].id


def test_long_gap_does_not_attach_to_the_other_label():
    gap = [[] for _ in range(20)]
    out = tracking.assign_ids(rows([hand("left", 900)], *gap, [hand("right", 950)]), W)
    assert out[0].hands[0].id != out[-1].hands[0].id


def test_one_hand_detected_twice_is_kept_once():
    assert [h.score for h in tracking.dedupe([hand("left", 400, score=0.6), hand("right", 405, score=0.8)])] == [0.8]


# ---------- side voting ----------
def test_single_frame_label_swap_is_voted_away():
    labels = ["left"] * 5 + ["right"] + ["left"] * 5
    out = tracked(rows(*[[hand(s, 400 + i)] for i, s in enumerate(labels)]))
    assert {h.side for fr in out for h in fr.hands} == {"left"}
    assert len({h.id for fr in out for h in fr.hands}) == 1


def test_prior_decides_when_labels_are_tied():
    labels = ["left", "right"] * 4
    out = tracked(rows(*[[hand(s, 1500)] for s in labels]))
    assert {h.side for fr in out for h in fr.hands} == {"right"}


def test_two_hands_alive_together_never_share_a_side():
    both_left = [[hand("left", 400, score=0.9), hand("left", 1500, score=0.6)] for _ in range(6)]
    out = tracked(rows(*both_left))
    assert all({h.side for h in fr.hands} == {"left", "right"} for fr in out)
    assert next(h for h in out[0].hands if h.kp2d[0][0] > 1000).side == "right"


def test_track_that_jumps_to_the_other_hand_is_split_and_each_part_keeps_its_side():
    labels = ["left"] * 60 + ["right"] * 60
    out = tracked(rows(*[[hand(s, 950)] for s in labels]))
    assert out[10].hands[0].id != out[110].hands[0].id
    assert (out[10].hands[0].side, out[110].hands[0].side) == ("left", "right")


def test_conflict_never_flips_against_the_image_order():
    # Strong track on the left, weak one further left: flipping the weak one to right would be wrong.
    frames = [[hand("left", 900, score=0.9), hand("left", 300, score=0.5)] for _ in range(6)]
    out = tracked(rows(*frames))
    assert next(h for h in out[0].hands if h.kp2d[0][0] < 500).side == "left"


def test_mirror_swaps_every_label():
    assert apply_mirror(rows([hand("left", 400)]), True)[0].hands[0].side == "right"
    assert apply_mirror(rows([hand("left", 400)]), False)[0].hands[0].side == "left"


# ---------- recovery plug-ins ----------
def test_recovery_fills_a_hole_with_track_id_and_voted_side():
    tr = tracked(rows([hand("left", 400)], [], [hand("left", 410)]))
    images = [(fr.frame, fr.t, np.zeros((2, 2, 3))) for fr in tr]
    calls = []

    def recover(img, frame, t, side, last):
        calls.append((frame, side))
        return hand("right", 405, score=0.7)

    out = apply_recovery(tr, images, recover=recover, agree=lambda img, h: 0.8)
    assert calls == [(2, "left")]
    assert out[1].hands[0].id == out[0].hands[0].id and out[1].hands[0].side == "left"
    assert out[0].hands[0].agreement == 0.8


def test_plugins_that_find_nothing_change_nothing():
    tr = tracked(rows([hand("left", 400)], [], [hand("left", 410)]))
    out = apply_recovery(tr, [(fr.frame, fr.t, None) for fr in tr], lambda *a: None, lambda *a: None)
    assert [len(fr.hands) for fr in out] == [1, 0, 1]


# ---------- sanity ----------
def test_wrist_jump_is_flagged_and_score_lowered():
    obs = [(i * 2, i * 2 / FPS, hand("left", 400 + (1000 if i == 3 else 0))) for i in range(6)]
    out = cleanup.mark_sanity(obs, W)
    assert "sanity" in out[3][2].flags and out[3][2].score == pytest.approx(0.9 * params.SANITY_SCORE_SCALE)
    assert "sanity" not in out[1][2].flags


def test_impossible_bone_length_is_flagged():
    bad = hand("left", 400)
    bad.kp3d = [[0.1 * k, 0.0, 0.0] for k in range(N_KP)]
    obs = [(i * 2, i * 2 / FPS, hand("left", 400)) for i in range(6)] + [(12, 12 / FPS, bad)]
    assert "sanity" in cleanup.mark_sanity(obs, W)[-1][2].flags


# ---------- gap fill ----------
def test_gap_fill_interpolates_short_gaps_and_marks_source():
    obs = [(0, 0.0, hand("left", 400)), (4, 4 / FPS, hand("left", 440))]
    out = cleanup.fill_gaps(obs, FPS)
    assert [o[0] for o in out] == [0, 1, 2, 3, 4]
    assert out[2][2].source == "interp" and out[2][2].kp2d[0][0] == pytest.approx(420)
    assert out[0][2].source == "mediapipe"


def test_gap_fill_limit_is_exact():
    assert len(cleanup.fill_gaps([(0, 0.0, hand("left", 400)), (6, 0.2, hand("left", 400))], FPS)) == 7
    assert len(cleanup.fill_gaps([(0, 0.0, hand("left", 400)), (7, 0.23, hand("left", 400))], FPS)) == 2


# ---------- One-Euro ----------
def _filtered(signal, dt=1 / 30):
    f = cleanup._filter()
    return np.array([f(np.array([v], dtype=float), dt)[0] for v in signal])


def test_one_euro_reduces_noise_on_a_still_signal():
    noise = np.random.default_rng(0).normal(500, 3, 300)
    assert np.diff(_filtered(noise)).std() < np.diff(noise).std() / 2


def test_one_euro_follows_a_fast_move():
    ramp = np.arange(0, 3000.0, 30)
    assert abs(_filtered(ramp)[-1] - ramp[-1]) < 60


def test_smoothing_restarts_after_a_long_gap():
    obs = [(0, 0.0, hand("left", 400)), (2, 2 / FPS, hand("left", 400)), (100, 100 / FPS, hand("left", 1200))]
    assert cleanup.smooth(obs)[-1][2].kp2d[0][0] == pytest.approx(1200)


# ---------- flags ----------
def test_flags():
    assert "low_conf" in cleanup.add_flags(hand("left", 400, score=0.4), W, H).flags
    assert "edge" in cleanup.add_flags(hand("left", 400, y=20, s=100), W, H).flags
    disagree = hand("left", 400)
    disagree.agreement = 0.3
    assert cleanup.add_flags(disagree, W, H).flags == ["disagree"]
    assert cleanup.add_flags(hand("left", 400), W, H).flags == []


# ---------- whole stage ----------
def test_refine_writes_every_frame_and_stable_sides():
    labels = ["left"] * 10 + ["right"] + ["left"] * 10
    src = rows(*[[hand(s, 400 + i)] for i, s in enumerate(labels)])
    out = refine(src, 42, FPS, W, H)
    assert [fr.frame for fr in out] == list(range(42))
    assert all(len(fr.hands) == 1 and fr.hands[0].side == "left" for fr in out[:41])
    assert out[1].hands[0].source == "interp" and out[2].hands[0].source == "mediapipe"
    assert FrameHands.from_dict({"frame": 0, "t": 0.0, "hands": []}).hands == []


def test_metrics_see_the_improvement_on_a_noisy_track():
    rng = np.random.default_rng(1)
    labels = ["right" if i % 10 == 5 else "left" for i in range(150)]
    src = rows(*[[hand(s, 400 + rng.normal(0, 4), 500 + rng.normal(0, 4))] for s in labels])
    out = refine(src, 300, FPS, W, H)
    assert swaps_per_min(src, 2, 300 / FPS / 60) > 0 and swaps_per_min(out, 2, 300 / FPS / 60) == 0
    assert jitter(out, 2) < jitter(src, 2) / 2
