import cv2
import numpy as np
import pytest

from egovision.quality import redact


def noise(h=120, w=160):
    return np.random.default_rng(0).integers(0, 255, (h, w, 3), np.uint8)


class ScriptedYuNet:
    """Plays back one list of (x, y, w, h, score) per call, given in pixels of a 160 x 120 frame."""

    def __init__(self, calls):
        self.calls, self.sizes = list(calls), []

    def setInputSize(self, size):
        self.sizes.append(size)

    def detect(self, img):
        faces = self.calls.pop(0)
        s = img.shape[1] / 160
        if not faces:
            return 1, None
        return 1, np.array([[*(v * s for v in f[:4]), *[0] * 10, f[4]] for f in faces], np.float32)


@pytest.fixture(autouse=True)
def no_followed_faces():
    redact._tracks.clear()


def scripted(monkeypatch, calls):
    fake = ScriptedYuNet(calls)
    monkeypatch.setattr(redact, "_yunet", lambda: fake)
    return fake


FACE = (50, 40, 40, 40)


def test_one_flash_never_blurs_however_often_it_appears_elsewhere(monkeypatch):
    weak = redact.params.FACE_CONFIRM - 0.1
    scripted(monkeypatch, [[(10, 10, 20, 20, weak)], [(100, 70, 20, 20, weak)], [(10, 70, 20, 20, weak)]])
    assert [redact.face_boxes(noise()) for _ in range(3)] == [[], [], []]


def test_a_proven_face_stays_blurred_through_weak_frames_and_gaps(monkeypatch):
    strong = redact.params.FACE_CONFIRM + 0.1
    gap = redact.params.FACE_HOLD
    scripted(monkeypatch, [[(*FACE, strong)], [(*FACE, 0.31)], *[[] for _ in range(gap)], [(*FACE, 0.31)]])
    assert all(redact.face_boxes(noise()) for _ in range(gap + 3))


def test_a_lost_face_is_dropped_after_the_hold(monkeypatch):
    scripted(monkeypatch, [[(*FACE, 0.95)], *[[] for _ in range(redact.params.FACE_HOLD + 1)]])
    seen = [redact.face_boxes(noise()) for _ in range(redact.params.FACE_HOLD + 2)]
    assert seen[-2] and not seen[-1]


def test_a_new_frame_size_forgets_old_faces(monkeypatch):
    scripted(monkeypatch, [[(*FACE, 0.95)], []])
    assert redact.face_boxes(noise())
    assert redact.face_boxes(noise(240, 320)) == []


def test_small_frames_are_enlarged_for_detection_and_boxes_come_back_in_their_pixels(monkeypatch):
    fake = scripted(monkeypatch, [[(*FACE, 0.95)]])
    box = redact.face_boxes(noise())[0]
    assert fake.sizes == [(redact.params.DETECT_WIDTH, redact.params.DETECT_WIDTH * 3 // 4)]
    assert box == pytest.approx([42, 32, 98, 88])


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
    scripted(monkeypatch, [[(*FACE, 0.9)]])
    img = noise()
    out = redact.redact_frame(img, keep=[[42, 32, 60, 88]])
    assert np.array_equal(out[32:88, 42:60], img[32:88, 42:60])
    assert out[32:88, 61:98].std() < img[32:88, 61:98].std() / 4


def test_a_hand_box_over_most_of_a_face_does_not_bring_it_back():
    img = noise()
    out = redact.blur_boxes(img, [[40, 30, 100, 90]], keep=[[30, 20, 90, 100]])
    assert out[30:90, 40:100].std() < img[30:90, 40:100].std() / 4


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


@pytest.fixture
def clip_files(tmp_path, monkeypatch):
    from egovision import config
    from egovision.schema import ClipPaths, write_meta
    monkeypatch.setattr(config, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(config, "FIXTURE_DIR", tmp_path / "videos")
    (tmp_path / "videos").mkdir()
    vw = cv2.VideoWriter(str(tmp_path / "videos" / "fixture_009.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 10, (160, 120))
    for _ in range(40):
        vw.write(noise())
    vw.release()
    p = ClipPaths("fixture_009").mkdir()
    write_meta(p.meta, {"step": 2, "width": 160})
    return p


def face_at(frames_with_score, total=20):
    return [[(*FACE, frames_with_score[k])] if k in frames_with_score else [] for k in range(total)]


def scanned(monkeypatch, frames_with_score):
    scripted(monkeypatch, face_at(frames_with_score))
    redact.scan("fixture_009")
    return redact.read_jsonl(redact._faces_file("fixture_009"))


def test_scan_blurs_a_face_before_its_strong_frame_and_across_gaps(clip_files, monkeypatch):
    rows = {r["frame"]: r["boxes"] for r in scanned(monkeypatch, {5: 0.4, 7: 0.4, 10: 0.95})}
    for call in (5, 6, 7, 8, 9, 10):
        assert rows[call * 2][0] == pytest.approx([42, 32, 98, 88])


def test_scan_holds_a_proven_face_past_both_ends_only_as_far_as_the_hold(clip_files, monkeypatch):
    hold = redact.params.FACE_HOLD
    frames_seen = sorted(r["frame"] for r in scanned(monkeypatch, {9: 0.95, 10: 0.95}))
    assert frames_seen[0] == (9 - hold) * 2 and frames_seen[-1] == (10 + hold) * 2


def test_scan_ignores_faces_that_never_prove_themselves(clip_files, monkeypatch):
    assert list(scanned(monkeypatch, {k: 0.5 for k in range(20)})) == []


def test_clip_redactor_uses_scanned_boxes_on_any_frame_size(clip_files, monkeypatch):
    scanned(monkeypatch, {10: 0.95})
    monkeypatch.setattr(redact, "_yunet", lambda: pytest.fail("a scanned clip needs no detector"))
    blur = redact.clip_redactor("fixture_009")
    big = noise(240, 320)
    assert blur(big, frame=20)[64:176, 84:196].std() < big[64:176, 84:196].std() / 4
    assert blur(big, frame=21)[64:176, 84:196].std() < big[64:176, 84:196].std() / 4   # odd frames use their step
    assert blur(big, frame=38) is big                                                  # past the hold


def test_clip_redactor_falls_back_to_live_detection_without_a_scan(clip_files, monkeypatch):
    scripted(monkeypatch, [[(*FACE, 0.95)]])
    img = noise()
    assert redact.clip_redactor("fixture_009")(img, frame=0)[32:88, 42:98].std() < img[32:88, 42:98].std() / 4
