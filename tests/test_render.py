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
    render("fixture_001", redact=lambda img, keep=None: img)
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
