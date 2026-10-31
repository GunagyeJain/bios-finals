import cv2
import numpy as np
import pytest

from egovision.quality import redact


def noise(h=120, w=160):
    return np.random.default_rng(0).integers(0, 255, (h, w, 3), np.uint8)


def test_blur_only_touches_the_box_and_leaves_input_alone():
    img = noise()
    before = img.copy()
    out = redact.blur_boxes(img, [[40, 30, 100, 90]])
    assert np.array_equal(img, before)
    assert out[30:90, 40:100].std() < img[30:90, 40:100].std() / 4
    mask = np.ones(img.shape[:2], bool)
    mask[30:90, 40:100] = False
    assert np.array_equal(out[mask], img[mask])


def test_keep_box_is_never_blurred_even_inside_a_face():
    img = noise()
    out = redact.blur_boxes(img, [[40, 30, 100, 90]], keep=[[60.5, 50.5, 80.2, 70.2]])
    assert np.array_equal(out[50:71, 60:81], img[50:71, 60:81])
    assert not np.array_equal(out[30:50, 40:100], img[30:50, 40:100])


def test_boxes_past_the_frame_are_clipped_or_ignored():
    img = noise()
    out = redact.blur_boxes(img, [[-30, -30, 20, 20], [200, 200, 300, 300]], keep=[[150, 110, 400, 400]])
    assert out.shape == img.shape
    assert not np.array_equal(out[:20, :20], img[:20, :20])


def test_no_boxes_returns_the_frame_unchanged():
    img = noise()
    assert redact.blur_boxes(img, []) is img


def test_redact_frame_pads_detector_output_and_keeps_hands(monkeypatch):
    class FakeYuNet:
        def setInputSize(self, size):
            assert size == (160, 120)

        def detect(self, img):
            return 1, np.array([[50, 40, 40, 40, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.9]], np.float32)

    monkeypatch.setattr(redact, "_yunet", lambda: FakeYuNet())
    img = noise()
    assert redact.face_boxes(img)[0] == pytest.approx([42, 32, 98, 88])
    out = redact.redact_frame(img, keep=[[42, 32, 60, 88]])
    assert np.array_equal(out[32:88, 42:60], img[32:88, 42:60])
    assert out[32:88, 61:98].std() < img[32:88, 61:98].std() / 4


def test_no_face_leaves_frame_unchanged(monkeypatch):
    class Empty:
        def setInputSize(self, size):
            pass

        def detect(self, img):
            return 1, None

    monkeypatch.setattr(redact, "_yunet", lambda: Empty())
    img = noise()
    assert redact.redact_frame(img) is img


def test_yunet_finds_real_faces_on_this_opencv():
    if not redact.params.YUNET_MODEL.exists():
        pytest.skip("model not downloaded")
    ultralytics = pytest.importorskip("ultralytics")
    img = cv2.imread(str(ultralytics.ASSETS / "zidane.jpg"))           # stock photo shipped with the package
    assert len(redact.face_boxes(cv2.resize(img, (854, 480)))) >= 2
    assert redact.face_boxes(np.zeros((120, 160, 3), np.uint8)) == []


def test_preview_writes_a_readable_video(tmp_path, monkeypatch):
    from egovision import config
    video = tmp_path / "videos" / "fixture_009.mp4"
    video.parent.mkdir()
    vw = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), 10, (160, 120))
    for _ in range(5):
        vw.write(noise())
    vw.release()
    monkeypatch.setattr(config, "FIXTURE_DIR", video.parent)
    monkeypatch.setattr(config, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(redact, "face_boxes", lambda img: [])
    out = tmp_path / "preview.mp4"
    redact.preview("fixture_009", out)
    cap = cv2.VideoCapture(str(out))
    assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 5
    cap.release()
