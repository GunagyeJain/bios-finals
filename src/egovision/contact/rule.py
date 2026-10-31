"""Pure contact logic (no video, no model): fingertip-in-box rule, closure, hysteresis, object ids,
moving boxes. Tested in tests/test_contact.py."""
from __future__ import annotations

import numpy as np

from ..schema import TIPS
from . import params as P

PALM = (0, 5, 9, 13, 17)


def pad_box(b: list[float], pad: float) -> list[float]:
    dx, dy = (b[2] - b[0]) * pad, (b[3] - b[1]) * pad
    return [b[0] - dx, b[1] - dy, b[2] + dx, b[3] + dy]


def tips_in_box(kp2d: list[list[float]], bbox: list[float], pad: float = P.PAD) -> int:
    x1, y1, x2, y2 = pad_box(bbox, pad)
    return sum(x1 <= kp2d[i][0] <= x2 and y1 <= kp2d[i][1] <= y2 for i in TIPS)


def closure(kp2d: list[list[float]]) -> float:
    """Mean distance of the four finger tips to the palm centre / palm length. Fist ~0.3, open ~1+."""
    kp = np.asarray(kp2d, float)
    palm = np.linalg.norm(kp[9] - kp[0])
    if palm < 1e-6:
        return float("inf")
    centre = kp[list(PALM)].mean(axis=0)
    return float(np.linalg.norm(kp[[8, 12, 16, 20]] - centre, axis=1).mean() / palm)


def pick_object(kp2d: list[list[float]], objects: list[dict]) -> tuple[dict | None, int]:
    """Object the hand touches: most tips inside, then portable before fixed, then smaller box."""
    if closure(kp2d) > P.CLOSURE_MAX:
        return None, 0
    best, best_key = None, None
    for o in objects:
        n = tips_in_box(kp2d, o["bbox"])
        if n < P.MIN_TIPS:
            continue
        b = o["bbox"]
        key = (-n, o["kind"] != "portable", (b[2] - b[0]) * (b[3] - b[1]))
        if best_key is None or key < best_key:
            best, best_key = (o, n), key
    return best or (None, 0)


def hysteresis(samples: list[tuple[float, object, float]], on: int = P.ON_FRAMES,
               off: int = P.OFF_FRAMES) -> list[tuple[float, float, object, float]]:
    """samples: (t, key or None, score) per frame. A key must hold `on` frames to start a contact,
    and be missing `off` frames to end it. Returns (t_start, t_end, key, mean score)."""
    out = []
    cur, cur_start, last_t, scores, miss = None, 0.0, 0.0, [], 0
    pend, pend_n, pend_start, pend_scores = None, 0, 0.0, []
    for t, key, s in samples:
        if cur is not None and key == cur:
            last_t, miss = t, 0
            scores.append(s)
            pend, pend_n = None, 0
            continue
        if cur is not None:
            miss += 1
            if miss >= off:
                out.append((cur_start, last_t, cur, float(np.mean(scores))))
                cur = None
        if key is None:
            pend, pend_n = None, 0
        elif key == pend:
            pend_n += 1
            pend_scores.append(s)
        else:
            pend, pend_n, pend_start, pend_scores = key, 1, t, [s]
        if cur is None and pend_n >= on:
            cur, cur_start, last_t, scores, miss = pend, pend_start, t, list(pend_scores), 0
            pend, pend_n = None, 0
    if cur is not None:
        out.append((cur_start, last_t, cur, float(np.mean(scores))))
    return out


def iou(a: list[float], b: list[float]) -> float:
    iw = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    ih = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = iw * ih
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def assign_ids(prev: list[dict], dets: list[dict], next_id: int, thr: float = P.TRACK_IOU) -> tuple[list[dict], int]:
    """Greedy IoU match against the previous run: same name + IoU >= thr keeps the id."""
    pairs = sorted(((iou(p["bbox"], d["bbox"]), i, j) for i, p in enumerate(prev)
                    for j, d in enumerate(dets) if p["name"] == d["name"]), reverse=True)
    ids, used = {}, set()
    for v, i, j in pairs:
        if v >= thr and i not in used and j not in ids:
            ids[j] = prev[i]["id"]
            used.add(i)
    out = []
    for j, d in enumerate(dets):
        if j not in ids:
            ids[j], next_id = next_id, next_id + 1
        out.append({**d, "id": ids[j]})
    return out, next_id


def _mask(shape: tuple[int, int], boxes: list[list[float]]) -> np.ndarray:
    m = np.zeros(shape, bool)
    for b in boxes:
        x1, y1 = max(0, int(b[0])), max(0, int(b[1]))
        m[y1:max(y1, int(np.ceil(b[3]))), x1:max(x1, int(np.ceil(b[2])))] = True
    return m


def moving(prev_gray: np.ndarray, gray: np.ndarray, boxes: list[list[float]],
           ignore: list[list[float]] = ()) -> list[bool]:
    """Per box: pixels change clearly more than the background (head motion moves everything).
    `ignore` (hand boxes) is left out of both sides."""
    diff = np.abs(gray.astype(np.int16) - prev_gray.astype(np.int16))
    skip = _mask(diff.shape, list(ignore))
    bg = ~(_mask(diff.shape, boxes) | skip)
    d_out = float(diff[bg].mean()) if bg.any() else 0.0
    flags = []
    for b in boxes:
        inside = _mask(diff.shape, [b]) & ~skip
        d_in = float(diff[inside].mean()) if inside.any() else 0.0
        flags.append(d_in >= P.MOVING_MIN and d_in >= P.MOVING_RATIO * d_out)
    return flags
