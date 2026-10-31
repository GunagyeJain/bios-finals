import cv2
import numpy as np
import pytest

from egovision import config
from egovision.products import overlay, robot_overlay as ro
from egovision.schema import CONTACT_COLS, ClipPaths, Hand, write_csv


def hand(thumb=(100.0, 100.0), index=(130.0, 100.0), wrist=(100.0, 300.0), knuckle=(100.0, 200.0), size=200.0, side="left"):
    kp = [[100.0, 200.0] for _ in range(21)]
    kp[0], kp[4], kp[8], kp[9] = list(wrist), list(thumb), list(index), list(knuckle)
    return Hand(side=side, bbox=[0, 100, size, 300], score=0.9, kp2d=kp)


def blank():
    return np.zeros((400, 400, 3), np.uint8)


@pytest.mark.parametrize("grip,mode,state", [
    ("2f", "2f", "copy"), ("generic", "2f", "copy"), ("5f", "2f", "cannot"),
    ("2f", "5f", "copy"), ("generic", "5f", "copy"), ("5f", "5f", "copy"),
    ("unsure", "2f", "none"), ("unsure", "5f", "none"), (None, "2f", "none"), ("", "5f", "none"),
])
def test_colour_rule_follows_what_each_robot_can_copy(grip, mode, state):
    assert ro.status(grip, mode) == state


def test_colours_match_the_app():
    assert ro.COLOUR["copy"] == (0x82, 0xa2, 0x44) and ro.COLOUR["cannot"] == (0x6f, 0x56, 0xe5)
    assert ro.COLOUR["none"] == (0x92, 0x8c, 0x8a)


def test_jaw_gap_follows_the_pinch_and_stays_in_limits():
    assert ro.jaw_gap(hand()) == pytest.approx(30)
    assert ro.jaw_gap(hand(index=(100.0, 100.0))) == pytest.approx(ro.GAP_MIN * 200)
    assert ro.jaw_gap(hand(index=(390.0, 100.0))) == pytest.approx(ro.GAP_MAX * 200)


def test_gripper_points_from_wrist_to_knuckle_with_jaws_one_gap_apart():
    stem, rail, jaw_a, jaw_b = ro.gripper(hand())
    assert stem[0] == pytest.approx([100, 300]) and stem[1] == pytest.approx([100, 260])
    assert np.linalg.norm(rail[1] - rail[0]) == pytest.approx(30)
    for jaw in (jaw_a, jaw_b):
        d = jaw[1] - jaw[0]
        assert d[0] == pytest.approx(0) and d[1] < 0                 # up the image, as wrist -> knuckle
    assert np.linalg.norm(jaw_a[1] - jaw_b[1]) == pytest.approx(30)  # parallel jaws


def test_gripper_turns_with_the_hand():
    _, _, jaw, _ = ro.gripper(hand(wrist=(50.0, 200.0), knuckle=(250.0, 200.0)))
    d = jaw[1] - jaw[0]
    assert d[0] > 0 and d[1] == pytest.approx(0)


def test_gripper_survives_a_wrist_on_the_knuckle():
    assert all(np.isfinite(p).all() for seg in ro.gripper(hand(wrist=(100.0, 200.0))) for p in seg)


def test_a_frame_with_no_hand_stays_untouched():
    img = blank()
    ro.draw_frame(img, [], {"left": "2f"}, 1.0, "2f")
    assert not img.any()


@pytest.mark.parametrize("mode", ro.MODES)
def test_hand_is_drawn_in_the_status_colour_with_a_label(mode):
    img = blank()
    ro.draw_frame(img, [hand()], {"left": "5f" if mode == "2f" else "2f"}, 1.0, mode)
    want = ro.COLOUR["cannot" if mode == "2f" else "copy"]
    assert (img[:, :, :] == want).all(axis=2).sum() > 100
    assert img[:30, :200].any()                                      # label plate, top left


def test_two_hands_get_their_own_colour_and_the_label_names_the_worse():
    img = blank()
    ro.draw_frame(img, [hand(), hand(wrist=(300.0, 300.0), knuckle=(300.0, 200.0), side="right")],
                  {"left": "2f", "right": "5f"}, 1.0, "2f")
    for colour, x in ((ro.COLOUR["copy"], (0, 200)), (ro.COLOUR["cannot"], (200, 400))):
        assert (img[40:, x[0]:x[1]] == colour).all(axis=2).sum() > 100
    words = []
    real = overlay._label
    overlay._label = lambda _img, text, *a: words.append(text)
    try:
        ro.draw_frame(blank(), [hand(side="left"), hand(side="right")], {"left": "2f", "right": "5f"}, 1.0, "2f")
    finally:
        overlay._label = real
    assert words == ["2-finger robot: cannot copy"]


def test_render_writes_both_views_like_render_mp4_and_passes_hand_boxes_to_redact(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(config, "FIXTURE_DIR", tmp_path / "videos")
    from egovision.fixtures import make
    make("fixture_001", seconds=2)
    p = ClipPaths("fixture_001")
    kept = []

    def stub(img, keep=None):
        kept.append(keep)
        return img

    ro.render("fixture_001", redact=stub)
    assert len(kept) == 30 and any(kept)
    for m in ro.MODES:
        cap = cv2.VideoCapture(str(p.dir / f"render_robot_{m}.mp4"))
        assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 30
        assert int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) == 960
        assert int(cap.get(cv2.CAP_PROP_FOURCC)).to_bytes(4, "little") in (b"avc1", b"h264")
        cap.release()


def test_render_one_mode_without_contacts_writes_only_that_view(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(config, "FIXTURE_DIR", tmp_path / "videos")
    from egovision.fixtures import make
    make("fixture_001", seconds=1)
    p = ClipPaths("fixture_001")
    write_csv(p.contacts, CONTACT_COLS, [])
    ro.render("fixture_001", "5f", redact=lambda img, keep=None: img)
    assert (p.dir / "render_robot_5f.mp4").exists() and not (p.dir / "render_robot_2f.mp4").exists()
