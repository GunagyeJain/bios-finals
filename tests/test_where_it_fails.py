import importlib.util
import sys
from pathlib import Path

from egovision.eval import metrics as M
from egovision.schema import N_KP, Hand

spec = importlib.util.spec_from_file_location("where_it_fails", Path(__file__).parents[1] / "scripts" / "where_it_fails.py")
W = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = W    # dataclasses look their module up here
spec.loader.exec_module(W)


def label(bbox=(100.0, 100.0, 200.0, 200.0), side="left"):
    x, y = bbox[0], bbox[3]
    return {"side": side, "bbox": list(bbox), "wrist": [x, y], "tips": [[x + 10 * i, y - 10 * i] for i in range(1, 6)]}


def pred(side="left"):
    kp = [[100.0, 200.0] for _ in range(N_KP)]
    for i, k in enumerate(M.KP):
        kp[k] = [100.0 + 10 * i, 200.0 - 10 * i]
    return Hand(side=side, bbox=[100, 100, 200, 200], score=0.9, kp2d=kp)


def test_modes_come_from_tags_quality_and_box():
    assert W.modes_of(label(), ["overlap", "glove"], set(), 1920, 1080) == ["overlap", "gloves"]
    assert W.modes_of(label(), ["blur"], set(), 1920, 1080) == ["fast"]
    assert W.modes_of(label(), [], {"fast_head", "dark"}, 1920, 1080) == ["dark", "fast"]
    assert W.modes_of(label((0.0, 100.0, 50.0, 200.0)), [], set(), 1920, 1080) == ["edge"]
    assert W.modes_of(label((1800.0, 900.0, 1919.0, 1079.0)), [], set(), 1920, 1080) == ["edge"]
    assert W.modes_of(label(), [], set(), 1920, 1080) == []


def test_failed_covers_missing_wrong_side_and_bad_points():
    assert not W.failed(label(), [pred()])
    assert W.failed(label(), [])
    assert W.failed(label(), [pred("right")])
    bad = pred()
    bad.kp2d[M.KP[3]] = [190.0, 190.0]
    assert W.failed(label(), [bad])


def test_quality_reason_lookup():
    rows = [{"t_start": "0", "t_end": "1", "reasons": "dark;fast_head"}, {"t_start": "1", "t_end": "2", "reasons": ""}]
    assert W.reasons_at(rows, 0.5) == {"dark", "fast_head"}
    assert W.reasons_at(rows, 1.5) == set() and W.reasons_at(rows, 5.0) == set()


def test_unmeasured_mode_says_so_and_examples_are_times():
    mode = W.Mode()
    mode.tally.add([label()], [], count_preds=False)
    mode.base.add([label()], [], count_preds=False)
    mode.examples["clipx"] = 83.0
    overall = M.Tally()
    overall.add([label()], [])
    text = W.render({"overlap": mode}, 1, overall, ["clipx"])
    assert "`clipx` at 1:23" in text and "| Gloves | 0 | 0 % | not measured" in text
    assert "no accuracy number" in text
