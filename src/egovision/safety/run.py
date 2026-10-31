"""B5 · owner: Bhavyam. Task: docs/06-plan/tasks/bhavyam.md

Hand near a moving fixed object (trd.md §5.7). Alerts report a time and a task, never a worker.
In: hands_input(), objects.jsonl  Out: alerts_safety.csv (schema.ALERT_COLS).
"""
from __future__ import annotations

import math
from bisect import bisect_right
from collections import defaultdict

from . import params as P
from ..schema import ALERT_COLS, TIPS, ClipPaths, Hand, read_hands, read_jsonl, write_csv
from ..stages import NotBuilt


def tip_distance(hand: Hand, box: list[float]) -> float:
    """Pixels from the closest fingertip to `box`, 0 if a tip is inside it."""
    x1, y1, x2, y2 = box
    return min(math.hypot(max(x1 - hand.kp2d[i][0], 0, hand.kp2d[i][0] - x2),
                          max(y1 - hand.kp2d[i][1], 0, hand.kp2d[i][1] - y2)) for i in TIPS)


def hand_size(hand: Hand) -> float:
    return max(hand.bbox[2] - hand.bbox[0], hand.bbox[3] - hand.bbox[1], 1.0)


def moving_boxes(rows: list[dict], times: list[float], t: float) -> list[dict]:
    """Moving fixed objects from the latest detection row at `t`; objects run on sparse frames."""
    i = bisect_right(times, t) - 1
    if i < 0 or t - times[i] > P.OBJECT_HOLD_S:
        return []
    return [o for o in rows[i]["objects"] if o["kind"] == "fixed" and o["moving"]]


def intervals(hits: list[tuple[float, float]]) -> list[tuple[float, float, float]]:
    """Sorted (t, distance) hits -> (start, end, closest distance), joined across short gaps,
    keeping only those that last long enough."""
    out: list[list[float]] = []
    for t, d in hits:
        if out and t - out[-1][1] <= P.JOIN_GAP_S:
            out[-1][1], out[-1][2] = t, min(out[-1][2], d)
        else:
            out.append([t, t, d])
    return [(a, b, d) for a, b, d in out if b - a >= P.MIN_NEAR_S]


def find_alerts(clip: str, hand_rows, object_rows: list[dict]) -> list[dict]:
    """One row per hand, object and stretch of time spent near it."""
    times = [r["t"] for r in object_rows]
    hits: dict[tuple[str, int, str], list[tuple[float, float]]] = defaultdict(list)
    for fr in hand_rows:
        boxes = moving_boxes(object_rows, times, fr.t)
        for h in fr.hands if boxes else ():
            for o in boxes:
                d = tip_distance(h, o["bbox"])
                if d <= P.NEAR_HAND_SIZES * hand_size(h):
                    hits[(h.side, o["id"], o["name"])].append((fr.t, d))
    rows = []
    for (side, _, name), got in hits.items():
        for a, b, d in intervals(got):
            rows.append({"clip": clip, "t_start": round(a, 2), "t_end": round(b, 2), "kind": "safety",
                         "severity": "warn", "hand": side,
                         "detail": f"{side} fingertips {d:.0f} px from moving '{name}'"})
    return sorted(rows, key=lambda r: r["t_start"])


def run(clip: str) -> None:
    p = ClipPaths(clip).mkdir()
    if not p.hands_input().exists():
        raise NotBuilt(f"needs {p.hands_input().name} (A1) first")
    if not p.objects.exists():
        raise NotBuilt("needs objects.jsonl (G2) first")
    rows = find_alerts(clip, read_hands(p.hands_input()), list(read_jsonl(p.objects)))
    write_csv(p.alerts_safety, ALERT_COLS, rows)
    print(f"  {clip}: {len(rows)} safety alerts")
