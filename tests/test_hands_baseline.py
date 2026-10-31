from types import SimpleNamespace as NS

from egovision.hands.baseline import to_frame_hands
from egovision.schema import FrameHands, N_KP


def fake_result(label="Left", score=0.9):
    pts = [NS(x=0.1 + k * 0.01, y=0.5 - k * 0.01, z=0.0) for k in range(N_KP)]
    world = [NS(x=k * 0.001, y=0.0, z=-0.01) for k in range(N_KP)]
    return NS(hand_landmarks=[pts], hand_world_landmarks=[world],
              handedness=[[NS(category_name=label, score=score)]])


def test_converts_normalised_points_to_pixels():
    h = to_frame_hands(fake_result(), 4, 0.1, 640, 480).hands[0]
    assert h.kp2d[0] == [0.1 * 640, 0.5 * 480]
    assert h.bbox == [0.1 * 640, (0.5 - 0.2) * 480, (0.1 + 0.2) * 640, 0.5 * 480]


def test_keeps_raw_label_score_and_world_points():
    h = to_frame_hands(fake_result("Right", 0.7), 4, 0.1, 640, 480).hands[0]
    assert (h.side, h.score, h.source, h.id) == ("right", 0.7, "mediapipe", -1)
    assert h.kp3d[2] == [0.002, 0.0, -0.01]


def test_no_hands_gives_empty_frame_that_round_trips():
    empty = NS(hand_landmarks=[], hand_world_landmarks=[], handedness=[])
    fr = to_frame_hands(empty, 8, 0.2, 640, 480)
    assert fr.hands == []
    assert FrameHands.from_dict({"frame": 8, "t": 0.2, "hands": []}) == fr
