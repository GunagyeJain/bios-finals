import json

import numpy as np
import pytest

from egovision import config
from egovision.eval import metrics as M
from egovision.schema import N_KP, FrameHands, Hand, write_hands, write_meta

FPS = 30.0


def pred(side="left", x=400.0, y=500.0, off=0.0):
    """A hand of box size 100 whose wrist + 5 tips sit where `label` puts them, shifted by `off`."""
    kp = [[x + off, y + off] for _ in range(N_KP)]
    for i, k in enumerate(M.KP):
        kp[k] = [x + 20 * i + off, y - 20 * i + off]
    return Hand(side=side, bbox=[x, y - 100, x + 100, y], score=0.9, kp2d=kp)


def label(side="left", x=400.0, y=500.0, prefill=None):
    tips = [[x + 20 * i, y - 20 * i] for i in range(1, 6)]
    return {"side": side, "bbox": [x, y - 100, x + 100, y], "wrist": [x, y], "tips": tips, "prefill": prefill, "edited": False}


def frame(hands, tags=()):
    return {"frame": 0, "tags": list(tags), "hands": hands}


def rows(*hands_per_frame):
    return {i * 2: FrameHands(i * 2, i * 2 / FPS, list(h)) for i, h in enumerate(hands_per_frame)}


def labels(*per_frame):
    return {i * 2: {**f, "frame": i * 2} for i, f in enumerate(per_frame)}


def score(r, lab, shared=(), lights=()):
    return M.score_file(r, lab, set(shared), list(lights), FPS)[0]


def test_perfect_prediction_scores_one():
    out = score(rows([pred()]), labels(frame([label()])))
    assert out["detection_recall"] == out["detection_precision"] == out["lr_accuracy"] == out["pck_0.2"] == 1.0


def test_missed_hand_lowers_recall_only():
    out = score(rows([pred()]), labels(frame([label(), label("right", x=1200)])))
    assert (out["detection_recall"], out["detection_precision"]) == (0.5, 1.0)
    assert out["pck_0.2"] == 1.0 and out["pck_0.2_with_misses"] == 0.5


def test_extra_hand_lowers_precision_only():
    out = score(rows([pred(), pred("right", x=1200)]), labels(frame([label()])))
    assert (out["detection_recall"], out["detection_precision"]) == (1.0, 0.5)


def test_no_hands_frame_counts_extra_hand_as_false_positive():
    out = score(rows([pred()]), labels(frame([])))
    assert out["detection_precision"] == 0.0 and out["detection_recall"] is None


def test_wrong_side_is_a_side_error_not_a_miss():
    out = score(rows([pred("right")]), labels(frame([label("left")])))
    assert (out["detection_recall"], out["lr_accuracy"]) == (1.0, 0.0)


def test_swapped_detections_are_matched_by_position():
    out = score(rows([pred("right", x=1200), pred("left", x=400)]), labels(frame([label("left"), label("right", x=1200)])))
    assert out["lr_accuracy"] == 1.0


def test_pck_threshold_is_box_normalised():
    near = score(rows([pred(off=10)]), labels(frame([label()])))  # 14 px on a box of 100 = 0.14
    far = score(rows([pred(off=20)]), labels(frame([label()])))   # 28 px = 0.28
    assert (near["pck_0.2"], far["pck_0.2"]) == (1.0, 0.0)
    assert far["detection_recall"] == 1.0


def test_prediction_too_far_is_a_miss_and_a_false_positive():
    out = score(rows([pred(x=1500)]), labels(frame([label()])))
    assert (out["detection_recall"], out["detection_precision"]) == (0.0, 0.0)


def test_unpredicted_frame_counts_as_no_hands():
    assert score({}, labels(frame([label()])))["detection_recall"] == 0.0


def test_splits_by_tag_light_and_side():
    out = score(rows([pred()], []), labels(frame([label()], ["blur"]), frame([label("right")])),
                lights=[(0.0, 0.05, "green"), (0.05, 1.0, "red")])
    assert out["by_tag"]["blur"]["detection_recall"] == 1.0
    assert out["by_light"]["green"]["detection_recall"] == 1.0 and out["by_light"]["red"]["detection_recall"] == 0.0
    assert out["by_side"]["left"]["detection_recall"] == 1.0 and out["by_side"]["right"]["detection_recall"] == 0.0


def test_shared_manual_and_prefilled_are_reported_apart():
    lab = labels(frame([label()]), frame([label(prefill="rtmlib")]))
    out = score(rows([pred()], [pred(off=20)]), lab, shared=[0])
    assert (out["pck_shared_manual"], out["pck_prefilled"]) == (1.0, 0.0)
    assert M.prefilled_share(lab) == 0.5


def test_manual_hand_outside_the_shared_set_is_not_in_the_shared_number():
    assert score(rows([pred()]), labels(frame([label()])))["pck_shared_manual"] is None


def test_inter_labeller_agreement():
    a = labels(frame([label()]), frame([label("right")]))
    b = labels(frame([label()]), frame([label("left")]))
    out = M.agreement({"a": a, "b": b})
    assert (out["frames"], out["pck_0.2"], out["same_side"], out["same_hand_count"]) == (2, 1.0, 0.5, 1.0)
    assert M.agreement({"a": a}) is None


def test_several_labellers_give_one_label_per_frame():
    out = M.merged_labels({"b": labels(frame([label("right")])), "a": labels(frame([label("left")]))})
    assert out[0]["hands"][0]["side"] == "left"


def test_worst_moments_rank_misses_first():
    out = M.worst_moments(rows([pred()], [pred(off=20)], []), labels(frame([label()]), frame([label()]), frame([label()])), FPS)
    assert [m["frame"] for m in out] == [4, 2]
    assert out[0]["missed"] == 1 and out[1]["bad_points"] == 6


def test_light_lookup_handles_gaps():
    assert M.light_at([(0.0, 1.0, "green")], 0.5) == "green"
    assert M.light_at([(0.0, 1.0, "green")], 1.5) is None


@pytest.fixture
def clip_files(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(config, "EVAL_LABELS", tmp_path / "labels")
    from egovision.schema import ClipPaths
    p = ClipPaths("clipx").mkdir()
    write_meta(p.meta, {"clip": "clipx", "fps": FPS, "n_frames": 8, "step": 2, "width": 1920, "height": 1080})
    r = [FrameHands(i, i / FPS, [pred()]) for i in range(0, 8, 2)]
    write_hands(p.hands_baseline, r)
    write_hands(p.hands, r)
    (tmp_path / "labels").mkdir()
    data = {"clip": "clipx", "labeller": "abhijay", "frames": [{"frame": 2, "tags": [], "hands": [label()]}]}
    (tmp_path / "labels" / "clipx__abhijay.json").write_text(json.dumps(data))
    return p


def test_metrics_file_has_flat_numbers_for_the_index_and_keeps_history(clip_files):
    M.main(["--clip", "clipx", "--note", "first"])
    M.main(["--clip", "clipx", "--note", "second"])
    m = json.loads(clip_files.metrics.read_text())
    assert m["partial"] is True and m["labelled_frames"] == 1
    assert m["detection_recall"] == 1.0 and m["baseline_detection_recall"] == 1.0 and m["pck_0.2"] == 1.0
    assert isinstance(m["swaps_per_min"], (int, float)) and "by_light" in m["hands"]
    assert [h["note"] for h in m["history"]] == ["first", "second"]


def test_summary_pools_counts_over_clips(clip_files):
    M.main(["--all"])
    s = json.loads((config.OUTPUTS / "metrics_summary.json").read_text())
    assert s["clips"] == ["clipx"] and s["hands"]["detection_recall"] == 1.0 and s["partial"] is True


def test_not_partial_with_enough_labels(clip_files, tmp_path):
    frames = [{"frame": i * 2, "tags": [], "hands": []} for i in range(M.FULL_LABELS)]
    (tmp_path / "labels" / "other__abhijay.json").write_text(json.dumps({"clip": "other", "labeller": "abhijay", "frames": frames}))
    M.main(["--clip", "clipx"])
    assert json.loads(clip_files.metrics.read_text())["partial"] is False


def test_box_size_uses_the_longer_side():
    assert M.label_size({"bbox": [0, 0, 10, 40]}) == 40
    assert np.array_equal(M.label_points(label()).shape, (6, 2))
