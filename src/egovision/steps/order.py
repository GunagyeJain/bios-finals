"""S3 · owner: Shefali. Task: docs/06-plan/tasks/shefali.md

Reference cycle per factory + alignment.
In: steps.csv of every clip in the same factory  Out: alerts_steps.csv (schema.ALERT_COLS).

Each step becomes a `verb:object` token (`verb="other"` rows are left out: no caption, nothing to check).
Reference cycle of a factory: the one saved with `save_reference` (outputs/references/<factory>.json),
else found from the factory's clips in clip-name order: the sequence is cut into cycles at every
occurrence of its first token, and the most frequent cycle of REF_MIN_LEN..REF_MAX_LEN tokens wins
(ties: the first full cycle). A factory whose sequence never repeats has no reference.
Cycles of this clip: its tokens cut at every occurrence of the reference's first token; tokens before
the first cut are the tail of a cycle that started in an earlier clip and are not checked.
`cycle_idx` in steps.csv is that cycle number (0, 1, ...); this stage only reports it in `detail`
because steps.csv has one writer (S2).
Each cycle is aligned to the reference by edit distance. A reference token missing from the cycle and
present elsewhere in it is `step_order`; otherwise `step_missing`. A cycle token not in the reference is
`step_extra`. No reference → alerts_steps.csv with the header only, so the stage counts as done.
"""
from __future__ import annotations

import json
from collections import Counter

from egovision import config
from egovision.schema import ALERT_COLS, STEP_COLS, ClipPaths, read_csv, read_meta, write_csv

from . import params as P


# ---------- tokens and cycles ----------
def token(step: dict) -> str | None:
    verb = str(step["verb"]).strip().lower()
    if verb in ("", "other"):
        return None
    return f"{verb}:{' '.join(str(step['object']).lower().split())}"


def label(tok: str) -> str:
    """`fasten:screw` → `fasten screw` for alert text."""
    return tok.replace(":", " ", 1)


def split_cycles(tokens: list[str], start: str) -> tuple[list[str], list[list[str]]]:
    """(lead, cycles): tokens before the first `start`, then one list per cycle beginning with `start`."""
    lead, cycles = [], []
    for t in tokens:
        if t == start:
            cycles.append([t])
        elif cycles:
            cycles[-1].append(t)
        else:
            lead.append(t)
    return lead, cycles


def find_reference(tokens: list[str]) -> list[str] | None:
    """Most frequent cycle (cut at the first token) with a sane length; None if nothing repeats."""
    if not tokens:
        return None
    _, cycles = split_cycles(tokens, tokens[0])
    if len(cycles) < 2:
        return None
    ok = [tuple(c) for c in cycles if P.REF_MIN_LEN <= len(c) <= P.REF_MAX_LEN]
    if not ok:
        return None
    counts = Counter(ok)
    best = max(counts.values())
    return list(next(c for c in ok if counts[c] == best))


# ---------- alignment ----------
def align(ref: list[str], cyc: list[str]) -> list[tuple[str, int | None, int | None]]:
    """Edit-distance alignment. Ops: ('match'|'sub', i_ref, j_cyc), ('del', i_ref, None) = missing in the
    cycle, ('ins', None, j_cyc) = extra in the cycle."""
    n, m = len(ref), len(cyc)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (ref[i - 1] != cyc[j - 1]))
    ops, i, j = [], n, m
    while i or j:
        if i and j and d[i][j] == d[i - 1][j - 1] + (ref[i - 1] != cyc[j - 1]):
            ops.append(("match" if ref[i - 1] == cyc[j - 1] else "sub", i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i and d[i][j] == d[i - 1][j] + 1:
            ops.append(("del", i - 1, None))
            i -= 1
        else:
            ops.append(("ins", None, j - 1))
            j -= 1
    return ops[::-1]


def cycle_problems(ref: list[str], cyc: list[str]) -> list[tuple[str, str, int | None]]:
    """[(kind, token, j_cyc)] for one cycle. j_cyc = index of the cycle step involved (None for missing)."""
    missing, extra = [], []
    for op, i, j in align(ref, cyc):
        if op in ("del", "sub"):
            missing.append(ref[i])
        if op in ("ins", "sub"):
            extra.append((cyc[j], j))
    out = []
    moved = {t for t in missing if t in cyc}
    for t in missing:
        out.append(("step_order", t, cyc.index(t)) if t in moved else ("step_missing", t, None))
    for t, j in extra:
        if t not in moved:                        # a moved step is reported once, as step_order
            out.append(("step_extra", t, j))
    return out


# ---------- files ----------
def factory_of(clip: str) -> str:
    p = ClipPaths(clip)
    if p.meta.exists():
        return read_meta(p.meta)["factory"]
    from egovision.io.frames import factory_of as from_name
    return from_name(clip)


def factory_clips(factory: str) -> list[str]:
    """Clips of the factory that have steps.csv, in clip-name order."""
    return sorted(d.name for d in config.OUTPUTS.iterdir()
                  if (d / "steps.csv").exists() and factory_of(d.name) == factory)


def clip_steps(clip: str) -> list[dict]:
    rows = read_csv(ClipPaths(clip).steps, STEP_COLS)
    return sorted(rows, key=lambda r: float(r["start_s"]))


def reference_path(factory: str):
    return config.OUTPUTS / "references" / f"{factory}.json"


def save_reference(clip_or_factory: str, steps: list[dict] | None = None) -> list[str]:
    """Mark a reference cycle. `save_reference(clip)` (app button): that clip's first full cycle, or all
    its steps if it has no repeat. `save_reference(factory, steps)`: exactly those steps."""
    if steps is None:
        clip = clip_or_factory
        factory = factory_of(clip)
        tokens = [t for t in map(token, clip_steps(clip)) if t]
        _, cycles = split_cycles(tokens, tokens[0]) if tokens else ([], [])
        ref = cycles[0] if len(cycles) >= 2 else tokens
    else:
        factory, ref = clip_or_factory, [t for t in map(token, steps) if t]
    if not ref:
        raise ValueError(f"{clip_or_factory}: no captioned steps to use as a reference")
    path = reference_path(factory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"factory": factory, "tokens": ref}, indent=1) + "\n", encoding="utf-8")
    return ref


def reference_for(factory: str) -> tuple[list[str] | None, str]:
    path = reference_path(factory)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["tokens"], "marked"
    tokens = [t for c in factory_clips(factory) for t in map(token, clip_steps(c)) if t]
    return find_reference(tokens), "found"


def run(clip: str) -> None:
    p = ClipPaths(clip)
    if not p.steps.exists():
        from egovision.stages import NotBuilt
        raise NotBuilt("needs steps.csv (S2) first")
    factory = factory_of(clip)
    ref, how = reference_for(factory)
    rows = []
    if ref:
        steps = [s for s in clip_steps(clip) if token(s)]
        tokens = [token(s) for s in steps]
        lead, cycles = split_cycles(tokens, ref[0])
        k = len(lead)
        for c, cyc in enumerate(cycles):
            span = steps[k:k + len(cyc)]
            t0, t1 = float(span[0]["start_s"]), float(span[-1]["end_s"])
            for kind, tok, j in cycle_problems(ref, cyc):
                at = span[j] if j is not None else None
                verb = {"step_missing": "missing", "step_order": "out of order:", "step_extra": "extra"}[kind]
                rows.append({"clip": clip, "kind": kind, "severity": "warn",
                             "t_start": float(at["start_s"]) if at else t0,
                             "t_end": float(at["end_s"]) if at else t1,
                             "hand": at["hand"] if at else "",
                             "detail": f"cycle {c} {verb} '{label(tok)}'"})
            k += len(cyc)
    write_csv(p.alerts_steps, ALERT_COLS, rows)
    ref_text = " → ".join(map(label, ref)) if ref else "none (no repeating cycle)"
    print(f"{clip}: reference for {factory} ({how if ref else '-'}): {ref_text}; {len(rows)} alerts → {p.alerts_steps}")
