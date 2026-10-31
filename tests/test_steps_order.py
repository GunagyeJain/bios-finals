import json

import pytest

from egovision import config
from egovision.schema import ALERT_COLS, read_csv
from egovision.steps import order as o

P, F, X, I = "pick:screwdriver", "fasten:screw", "press:press machine", "inspect:hinge"


def test_find_reference_first_full_cycle():
    assert o.find_reference([P, F, X, P, F, P, F, X, P, F, X]) == [P, F, X]
    assert o.find_reference([P, F, P, F, X, I, P]) == [P, F, X, I]      # first one long enough
    assert o.find_reference([P, F, X, I]) is None                         # one cycle, cut off: no repeat
    assert o.find_reference([P, F, X]) is None                      # no repeat
    assert o.find_reference([P, F, P, F]) is None                   # cycles shorter than REF_MIN_LEN
    assert o.find_reference([]) is None


def test_split_cycles_keeps_lead_apart():
    lead, cycles = o.split_cycles([F, X, P, F, X, P, F], P)
    assert lead == [F, X] and cycles == [[P, F, X], [P, F]]


@pytest.mark.parametrize("cyc, expected", [
    ([P, F, X], []),
    ([P, F], [("step_missing", X)]),
    ([P, X, F], [("step_order", F), ("step_order", X)]),
    ([P, F, I, X], [("step_extra", I)]),
    ([P, I, X], [("step_missing", F), ("step_extra", I)]),
])
def test_cycle_problems(cyc, expected):
    assert sorted((k, t) for k, t, _ in o.cycle_problems([P, F, X], cyc)) == sorted(expected)


def test_order_ignores_other_and_normalises_objects():
    assert o.token({"verb": "other", "object": "x"}) is None
    assert o.token({"verb": "Fasten", "object": "  Hinge   Pin"}) == "fasten:hinge pin"


@pytest.fixture
def fixtures(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(config, "FIXTURE_DIR", tmp_path / "videos")
    from egovision.fixtures import make
    return [make("fixture_001", seconds=3), make("fixture_002", seconds=3)]


def test_fixture_gives_the_known_step_missing(fixtures):
    o.run("fixture_001")
    rows = read_csv(fixtures[0].alerts_steps, ALERT_COLS)
    assert [(r["kind"], r["detail"]) for r in rows] == [("step_missing", "cycle 1 missing 'press press machine'")]
    assert (rows[0]["t_start"], rows[0]["t_end"]) == ("7.0", "10.0")


def test_marked_reference_wins_and_app_button_signature(fixtures):
    path = o.save_reference("fixture_001")                                     # app: save_reference(clip)
    assert path == o.reference_path("fixture") and json.loads(path.read_text())["tokens"] == [P, F, X]
    o.save_reference("fixture", [{"verb": "pick", "object": "screwdriver"}, {"verb": "fasten", "object": "screw"}])
    o.run("fixture_001")                                                       # now [P, F] is the norm
    rows = read_csv(fixtures[0].alerts_steps, ALERT_COLS)
    assert [r["kind"] for r in rows] == ["step_extra"] and "press press machine" in rows[0]["detail"]
    saved = json.loads(o.reference_path("fixture").read_text())
    assert saved["tokens"] == [P, "fasten:screw"]


def test_no_repeat_writes_header_only(fixtures):
    for p in fixtures:
        p.steps.write_text("clip,step_idx,start_s,end_s,verb,object,hand,caption,source,cycle_idx\n"
                           f"{p.clip},0,0,1,pick,bolt,right,x,gemini,\n")
    o.run("fixture_001")
    assert fixtures[0].alerts_steps.read_text().strip() == ",".join(ALERT_COLS)


def _steps(clip, seq):
    lines = ["clip,step_idx,start_s,end_s,verb,object,hand,caption,source,cycle_idx"]
    for k, tok in enumerate(seq):
        verb, obj = tok.split(":")
        lines.append(f"{clip},{k},{2 * k},{2 * k + 2},{verb},{obj},right,x,gemini,")
    return "\n".join(lines) + "\n"


def test_run_reports_each_kind_with_severity(fixtures):
    a, b = fixtures
    a.steps.write_text(_steps(a.clip, [P, F, X, P, F, X]))                    # reference: P F X
    b.steps.write_text(_steps(b.clip, [P, X, F, P, F, I, X, P, F]))
    o.run(b.clip)
    rows = read_csv(b.alerts_steps, ALERT_COLS)
    got = sorted((r["kind"], r["severity"], r["detail"]) for r in rows)
    assert got == [("step_extra", "info", "cycle 1 extra 'inspect hinge'"),
                   ("step_missing", "warn", "cycle 2 missing 'press press machine'"),
                   ("step_order", "warn", "cycle 0 out of order: 'fasten screw'"),
                   ("step_order", "warn", "cycle 0 out of order: 'press press machine'")]
    extra = next(r for r in rows if r["kind"] == "step_extra")
    assert (extra["t_start"], extra["t_end"]) == ("10.0", "12.0")              # the extra step's own time
