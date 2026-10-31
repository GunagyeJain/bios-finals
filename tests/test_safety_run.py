import pytest

from egovision import config
from egovision.safety import run as safety
from egovision.safety import params as P
from egovision.schema import ALERT_COLS, TIPS, ClipPaths, FrameHands, Hand, read_csv, write_hands, write_jsonl
from egovision.stages import NotBuilt

BOX = [500.0, 100.0, 600.0, 200.0]
FPS = 30


def hand(tip_x, tip_y=150.0, size=100.0, side="left"):
    """A hand `size` px wide whose five fingertips all sit at (tip_x, tip_y)."""
    kp = [[tip_x if i in TIPS else tip_x - size, tip_y] for i in range(21)]
    return Hand(side=side, bbox=[tip_x - size, tip_y - 10, tip_x, tip_y + 10], score=0.9, kp2d=kp)


def obj(box=BOX, kind="fixed", moving=True, id=1, name="press"):
    return {"id": id, "name": name, "kind": kind, "bbox": box, "score": 0.8, "moving": moving}


def object_rows(seconds, **kw):
    return [{"frame": i, "t": i / FPS, "objects": [obj(**kw)]} for i in range(0, seconds * FPS, 10)]


def frames(seconds, hands_at):
    return [FrameHands(i, i / FPS, hands_at(i / FPS)) for i in range(seconds * FPS)]


def test_tip_inside_the_box_is_zero_and_outside_is_straight_line_distance():
    assert safety.tip_distance(hand(550), BOX) == 0
    assert safety.tip_distance(hand(480), BOX) == 20
    assert safety.tip_distance(hand(470, 60), BOX) == pytest.approx(50)


def test_distance_uses_the_closest_of_the_five_tips():
    h = hand(100)
    h.kp2d[12] = [490.0, 150.0]
    assert safety.tip_distance(h, BOX) == 10


def test_hand_held_near_a_moving_machine_alerts_once():
    rows = safety.find_alerts("c", frames(3, lambda t: [hand(480)]), object_rows(3))
    assert len(rows) == 1
    r = rows[0]
    assert (r["kind"], r["severity"], r["hand"], r["clip"]) == ("safety", "warn", "left", "c")
    assert r["t_start"] == 0 and r["t_end"] == pytest.approx(3, abs=0.05)
    assert "20 px" in r["detail"] and "press" in r["detail"]


def test_distance_limit_scales_with_hand_size():
    near = hand(460, size=100)            # 40 px away, limit 50
    far = hand(460, size=60)              # 40 px away, limit 30
    assert safety.find_alerts("c", frames(2, lambda t: [near]), object_rows(2))
    assert not safety.find_alerts("c", frames(2, lambda t: [far]), object_rows(2))


def test_a_brief_touch_is_not_an_alert():
    brief = frames(3, lambda t: [hand(480)] if 1.0 <= t < 1.0 + P.MIN_NEAR_S - 0.1 else [hand(100)])
    assert not safety.find_alerts("c", brief, object_rows(3))


def test_half_a_second_is_enough():
    held = frames(3, lambda t: [hand(480)] if 1.0 <= t <= 1.0 + P.MIN_NEAR_S + 0.04 else [hand(100)])
    assert len(safety.find_alerts("c", held, object_rows(3))) == 1


def test_still_machines_and_portable_objects_never_alert():
    fr = frames(2, lambda t: [hand(480)])
    assert not safety.find_alerts("c", fr, object_rows(2, moving=False))
    assert not safety.find_alerts("c", fr, object_rows(2, kind="portable"))


@pytest.mark.parametrize("name", P.NEVER_MOVES)
def test_furniture_never_alerts_even_when_flagged_moving(name):
    assert not safety.find_alerts("c", frames(2, lambda t: [hand(480)]), object_rows(2, name=name))


def test_a_short_gap_joins_and_a_long_gap_splits():
    gap = P.JOIN_GAP_S
    short = frames(4, lambda t: [] if 1.5 <= t < 1.5 + gap / 2 else [hand(480)])
    long_ = frames(4, lambda t: [] if 1.5 <= t < 1.5 + 3 * gap else [hand(480)])
    assert len(safety.find_alerts("c", short, object_rows(4))) == 1
    assert len(safety.find_alerts("c", long_, object_rows(4))) == 2


def test_each_hand_gets_its_own_alert():
    fr = frames(2, lambda t: [hand(480), hand(480, side="right")])
    assert sorted(r["hand"] for r in safety.find_alerts("c", fr, object_rows(2))) == ["left", "right"]


def test_each_machine_gets_its_own_alert():
    rows = [{"frame": i, "t": i / FPS, "objects": [obj(id=1, name="press"), obj(id=2, name="lathe")]}
            for i in range(0, 60, 10)]
    assert sorted(r["detail"].split("'")[1] for r in safety.find_alerts("c", frames(2, lambda t: [hand(480)]), rows)) \
        == ["lathe", "press"]


def test_stale_object_rows_are_ignored():
    rows = [{"frame": 0, "t": 0.0, "objects": [obj()]}]
    late = frames(5, lambda t: [hand(480)] if t > P.OBJECT_HOLD_S + 0.5 else [hand(100)])
    assert not safety.find_alerts("c", late, rows)


def test_frames_before_the_first_object_row_are_ignored():
    assert safety.moving_boxes([{"t": 2.0, "objects": [obj()]}], [2.0], 1.0) == []


def test_no_object_rows_means_no_alerts():
    assert safety.find_alerts("c", frames(1, lambda t: [hand(480)]), []) == []


@pytest.fixture
def outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS", tmp_path)
    return ClipPaths("clip_x").mkdir()


def test_run_writes_a_contract_file_and_a_header_only_file_when_quiet(outputs):
    write_hands(outputs.hands, frames(2, lambda t: [hand(100)]))
    write_jsonl(outputs.objects, object_rows(2))
    safety.run("clip_x")
    assert read_csv(outputs.alerts_safety, ALERT_COLS) == []
    write_hands(outputs.hands, frames(2, lambda t: [hand(480)]))
    safety.run("clip_x")
    assert len(read_csv(outputs.alerts_safety, ALERT_COLS)) == 1


def test_run_waits_for_its_inputs(outputs):
    with pytest.raises(NotBuilt):
        safety.run("clip_x")
    write_hands(outputs.hands, frames(1, lambda t: []))
    with pytest.raises(NotBuilt):
        safety.run("clip_x")
