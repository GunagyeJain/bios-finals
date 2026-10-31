import cv2
import numpy as np
import pandas as pd

from egovision import config
from egovision.products import overlay


def test_render_writes_both_videos_at_processed_fps(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(config, "FIXTURE_DIR", tmp_path / "videos")
    from egovision.fixtures import make
    from egovision.products.render import render
    p = make("fixture_001", seconds=2)
    p.render.unlink()                                          # the fixture ships a stand-in copy
    render("fixture_001", redact=lambda img, keep=None: img, skin=None)
    for path in (p.render, p.render_baseline):
        cap = cv2.VideoCapture(str(path))
        assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 30      # 2 s at 15 processed frames per second
        assert int(cap.get(cv2.CAP_PROP_FOURCC)).to_bytes(4, "little") in (b"avc1", b"h264")


def test_strip_marks_the_playhead_and_colours_by_light():
    img = np.zeros((100, 200, 3), np.uint8)
    seg = pd.DataFrame({"t_start": [0.0, 1.0], "t_end": [1.0, 2.0], "light": ["green", "red"]})
    overlay.strip(img, seg, 2.0, 0.5)
    bottom = img[-3, :, :]
    assert tuple(bottom[150]) == overlay.BGR["red"] and tuple(bottom[20]) == overlay.BGR["green"]
    assert img[-overlay.STRIP_H - 3:, 50].max() == 255           # white playhead at t = 0.5 s


def test_hands_drawn_only_where_keypoints_are():
    from egovision.schema import Hand
    img = np.zeros((200, 200, 3), np.uint8)
    kp = [[100.0 + i, 100.0 + i] for i in range(21)]
    overlay.hands(img, [Hand(side="left", bbox=[100, 100, 120, 120], score=0.9, kp2d=kp, id=3)], 1.0, {})
    assert img[100:121, 100:121].any() and not img[:50, :50].any()


def test_skin_regions_go_to_the_hand_that_touches_them():
    from egovision.products import arms
    from egovision.schema import Hand
    mask = np.zeros((200, 300), bool)
    mask[50:150, 20:120] = True                                 # wearer's forearm + hand
    mask[50:150, 200:280] = True                                # a coworker's arm, no tracked hand on it
    hand = Hand(side="right", bbox=[40, 60, 100, 120], score=0.9, kp2d=[[60.0 + i, 80.0] for i in range(21)])
    out = arms.by_hand(mask, [hand], 1.0)
    assert set(out) == {"right"} and out["right"][100, 50] and not out["right"][100, 240]


def test_touching_arms_are_split_by_the_nearer_hand():
    from egovision.products import arms
    from egovision.schema import Hand
    mask = np.zeros((100, 300), bool)
    mask[40:60, 10:290] = True                                  # two forearms touching: one region
    left = Hand(side="left", bbox=[10, 40, 60, 60], score=0.9, kp2d=[[20.0 + i, 50.0] for i in range(21)])
    right = Hand(side="right", bbox=[240, 40, 290, 60], score=0.9, kp2d=[[260.0 + i, 50.0] for i in range(21)])
    out = arms.by_hand(mask, [left, right], 1.0)
    assert out["left"][50, 30] and not out["left"][50, 270] and out["right"][50, 270]
    assert not (out["left"] & out["right"]).any()
