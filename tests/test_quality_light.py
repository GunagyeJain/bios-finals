import cv2
import numpy as np
import pytest

from egovision.quality import light
from egovision.schema import FrameHands, Hand


def good(**over):
    m = {"blur": 400.0, "brightness": 0.5, "dark_share": 0.1, "clipped_share": 0.0, "speed": 0.5,
         "frozen": False, "hands_visible": 1.0, "edge_cut": 0.0, "hand_y": 0.6, "agreement": 0.9}
    return {**m, **over}


def test_clean_second_is_green():
    assert light.judge(good()) == ("green", "")


@pytest.mark.parametrize("over,reason", [
    ({"dark_share": 0.95}, "dark"), ({"frozen": True}, "frozen"), ({"blur": 10.0}, "blur"),
    ({"hands_visible": 0.1}, "hands_out")])
def test_each_hard_fail_is_red(over, reason):
    assert light.judge(good(**over)) == ("red", reason)


@pytest.mark.parametrize("over,reason", [
    ({"dark_share": 0.6}, "dim"), ({"clipped_share": 0.5}, "clipped"), ({"blur": 100.0}, "blur"),
    ({"speed": 9.0}, "fast_head"), ({"hands_visible": 0.5}, "hands_partial"), ({"edge_cut": 0.8}, "edge_cut"),
    ({"hand_y": 0.1}, "camera_angle"), ({"hand_y": 0.97}, "camera_angle"), ({"agreement": 0.3}, "disagree")])
def test_each_soft_fail_is_yellow(over, reason):
    assert light.judge(good(**over)) == ("yellow", reason)


def test_two_soft_fails_stay_yellow_and_three_turn_red():
    assert light.judge(good(speed=9.0, edge_cut=0.8)) == ("yellow", "fast_head;edge_cut")
    assert light.judge(good(speed=9.0, edge_cut=0.8, agreement=0.3))[0] == "red"


def test_hard_reasons_come_first():
    assert light.judge(good(speed=9.0, dark_share=0.95)) == ("red", "dark;fast_head")


def test_unknown_hand_values_skip_their_checks():
    m = good(hands_visible=-1.0, edge_cut=-1.0, hand_y=-1.0, agreement=-1.0)
    assert light.judge(m) == ("green", "")


def hand(y1, y2, x1=100, x2=200):
    kp = [[x1, y1]] * 21
    return Hand(side="left", bbox=[x1, y1, x2, y2], score=0.9, kp2d=kp)


def test_hand_metrics_shares_and_position():
    frames = [FrameHands(0, 0.0, [hand(200, 400)]), FrameHands(1, 0.1, []),
              FrameHands(2, 0.2, [hand(600, 720)]), FrameHands(3, 0.3, [])]
    m = light.hand_metrics(frames, 1280, 720)
    assert m["hands_visible"] == 0.5
    assert m["edge_cut"] == 0.5
    assert m["hand_y"] == pytest.approx((300 / 720 + 660 / 720) / 2)
    assert m["agreement"] == -1.0


def test_hand_metrics_without_data_are_unknown():
    assert set(light.hand_metrics([], 1280, 720).values()) == {-1.0}


def test_hand_metrics_with_no_hand_seen_is_zero_not_unknown():
    m = light.hand_metrics([FrameHands(0, 0.0, [])], 1280, 720)
    assert m["hands_visible"] == 0.0
    assert m["edge_cut"] == -1.0


def test_agreement_is_averaged_over_hands_that_have_it():
    a, b, c = hand(200, 400), hand(200, 400), hand(200, 400)
    a.agreement, b.agreement = 0.8, 0.4
    assert light.hand_metrics([FrameHands(0, 0.0, [a, b, c])], 1280, 720)["agreement"] == pytest.approx(0.6)


def texture(seed=0):
    return cv2.resize(np.random.default_rng(seed).integers(0, 255, (45, 80), np.uint8), (160, 90))


def test_frame_metrics_separate_sharp_from_blurred():
    sharp, soft = texture(), cv2.GaussianBlur(texture(), (15, 15), 0)
    assert light.frame_metrics(sharp, None)["blur"] > 10 * light.frame_metrics(soft, None)["blur"]


def test_frame_metrics_read_dark_and_clipped_pixels():
    m = light.frame_metrics(np.full((90, 160), 10, np.uint8), None)
    assert m["dark"] == 1.0 and m["brightness"] == pytest.approx(10 / 255)
    assert light.frame_metrics(np.full((90, 160), 250, np.uint8), None)["clipped"] == 1.0


def test_frame_metrics_see_a_camera_pan():
    img = texture()
    assert light.frame_metrics(np.roll(img, 6, axis=1), img)["speed"] > 3
    assert light.frame_metrics(img, img)["speed"] < 0.1


def test_segment_is_frozen_only_if_every_sample_is_still():
    still = {"blur": 300.0, "brightness": 0.5, "dark": 0.1, "clipped": 0.0, "speed": 0.0, "diff": 0.0}
    none = {"hands_visible": -1.0, "edge_cut": -1.0, "hand_y": -1.0, "agreement": -1.0}
    assert light.segment([still, still], none)["frozen"]
    assert not light.segment([still, {**still, "diff": 2.0}], none)["frozen"]
    first_only = {k: v for k, v in still.items() if k not in ("speed", "diff")}
    assert not light.segment([first_only], none)["frozen"]
