"""A5 · owner: Abhijay. `python -m egovision.eval.metrics --clip X` → outputs/<clip>/metrics.json
Compares hands_baseline.jsonl and hands.jsonl against eval/labels/; accuracy per light colour from quality.csv."""
from __future__ import annotations

import math

from egovision.schema import FrameHands, Hand

LINK_SIZES = 1.0     # a hand continues a chain if its wrist moved less than this many hand sizes
STILL_WINDOW = 5     # chain steps either side when deciding a hand is still
STILL_SIZES = 0.25   # net wrist motion across the window, in hand sizes


def _size(h: Hand) -> float:
    return max(h.bbox[2] - h.bbox[0], h.bbox[3] - h.bbox[1], 1.0)


def chains(frames: list[FrameHands], step: int) -> list[list[Hand]]:
    """Links hands across consecutive sampled frames by nearest wrist alone. Ignores ids and sides, so
    the raw baseline and the final file are measured by the same rule."""
    done: list[list[Hand]] = []
    live: list[list[Hand]] = []
    last_frame = None
    for fr in frames:
        if fr.frame % step:
            continue
        if last_frame is not None and fr.frame - last_frame > step:
            done += live
            live = []
        pairs = sorted(((math.dist(c[-1].kp2d[0], h.kp2d[0]), ci, hi) for ci, c in enumerate(live)
                        for hi, h in enumerate(fr.hands)), key=lambda p: p[0])
        used_c, used_h = set(), set()
        for d, ci, hi in pairs:
            if ci in used_c or hi in used_h or d > LINK_SIZES * _size(live[ci][-1]):
                continue
            used_c.add(ci)
            used_h.add(hi)
            live[ci].append(fr.hands[hi])
        done += [c for ci, c in enumerate(live) if ci not in used_c]
        live = [c for ci, c in enumerate(live) if ci in used_c]
        live += [[h] for hi, h in enumerate(fr.hands) if hi not in used_h]
        last_frame = fr.frame
    return done + live


def swaps_per_min(frames: list[FrameHands], step: int, minutes: float) -> float:
    """Side label changes along a continuously visible hand."""
    n = sum(a.side != b.side for c in chains(frames, step) for a, b in zip(c, c[1:]))
    return n / max(minutes, 1e-6)


def pair_order(frames: list[FrameHands], step: int) -> dict[str, int]:
    """Two-hand frames by label: left hand on the image left (right_order), on the image right
    (wrong_order, unless the arms really cross), or both hands given one side (same_side)."""
    out = {"right_order": 0, "wrong_order": 0, "same_side": 0}
    for fr in frames:
        if fr.frame % step or len(fr.hands) != 2:
            continue
        a, b = fr.hands
        if a.side == b.side:
            out["same_side"] += 1
        else:
            left, right = (a, b) if a.side == "left" else (b, a)
            out["right_order" if left.kp2d[0][0] < right.kp2d[0][0] else "wrong_order"] += 1
    return out


def jitter(frames: list[FrameHands], step: int) -> float:
    """Mean frame-to-frame wrist motion in pixels while the hand is still."""
    moves = []
    for c in chains(frames, step):
        for i in range(STILL_WINDOW, len(c) - STILL_WINDOW):
            net = math.dist(c[i - STILL_WINDOW].kp2d[0], c[i + STILL_WINDOW].kp2d[0])
            if net < STILL_SIZES * _size(c[i]):
                moves.append(math.dist(c[i - 1].kp2d[0], c[i].kp2d[0]))
    return sum(moves) / len(moves) if moves else 0.0
