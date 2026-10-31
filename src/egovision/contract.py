"""`python -m egovision check --clip X`: validates every existing output of a clip against the
contract in schema.py. Run it before every checkpoint and before pushing a stage. Owner: Gunagye."""
from __future__ import annotations

from .schema import (ALERT_COLS, CONTACT_COLS, CONTACT_STATES, LIGHTS, QUALITY_COLS, STEP_COLS,
                     ClipPaths, read_csv, read_hands, read_jsonl, read_meta)


def _check_hands(path) -> str:
    n, last = 0, -1
    for fr in read_hands(path):                       # Hand.__post_init__ checks side/kp/source
        assert fr.frame > last, f"frames not increasing at {fr.frame}"
        last, n = fr.frame, n + 1
    return f"{n} frames"


def check(clip: str) -> list[str]:
    p, errors = ClipPaths(clip), []
    checks = {
        "meta": lambda: f"{read_meta(p.meta)['n_frames']} frames @ {read_meta(p.meta)['fps']:.1f} fps",
        "hands_baseline": lambda: _check_hands(p.hands_baseline),
        "hands": lambda: _check_hands(p.hands),
        "wilor": lambda: _check_hands(p.wilor),
        "quality": lambda: _rows(p.quality, QUALITY_COLS, "light", LIGHTS),
        "objects": lambda: f"{sum(1 for _ in read_jsonl(p.objects))} rows",
        "contacts": lambda: _rows(p.contacts, CONTACT_COLS, "state", CONTACT_STATES),
        "steps": lambda: _rows(p.steps, STEP_COLS),
        "alerts_steps": lambda: _rows(p.alerts_steps, ALERT_COLS),
        "alerts_safety": lambda: _rows(p.alerts_safety, ALERT_COLS),
    }
    for name, fn in checks.items():
        if not getattr(p, name).exists():
            print(f"  -    {name}")
            continue
        try:
            print(f"  OK   {name}: {fn()}")
        except Exception as e:  # report and continue so one bad file doesn't hide others
            errors.append(f"{name}: {e}")
            print(f"  FAIL {name}: {e}")
    return errors


def _rows(path, cols, enum_col=None, allowed=()) -> str:
    rows = read_csv(path, cols)
    if enum_col:
        bad = {r[enum_col] for r in rows} - set(allowed)
        assert not bad, f"{enum_col} values {bad} not in {allowed}"
    return f"{len(rows)} rows"
