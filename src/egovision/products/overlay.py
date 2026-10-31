"""G6 · owner: Gunagye. Drawing for render.mp4: hand skeletons by side with track id, a contact label,
a header with time and light, and the clip's light strip with a playhead. Colours match the app."""
from __future__ import annotations

import cv2
import numpy as np
import pandas as pd

BGR = {"green": (130, 162, 68), "yellow": (65, 164, 217), "red": (111, 86, 229), "none": (48, 44, 44)}
HAND = {"left": (214, 138, 74), "right": (243, 242, 242)}
WORD = {"green": "Usable", "yellow": "Check", "red": "Unusable"}
INK, PANEL = (255, 255, 255), (23, 18, 19)
FONT = cv2.FONT_HERSHEY_SIMPLEX
STRIP_H = 8
BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12),
         (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)]


def _label(img: np.ndarray, text: str, org: tuple[int, int], color=INK, scale: float = 0.45) -> None:
    """Text on a dark plate so it reads on any footage."""
    (w, h), base = cv2.getTextSize(text, FONT, scale, 1)
    x, y = max(0, org[0]), max(h + 4, org[1])
    cv2.rectangle(img, (x - 3, y - h - 4), (x + w + 3, y + base + 1), PANEL, -1)
    cv2.putText(img, text, (x, y), FONT, scale, color, 1, cv2.LINE_AA)


def hands(img: np.ndarray, hand_list: list, scale: float, held: dict[str, str]) -> None:
    """Skeleton per hand in its side colour, 'L 3' at the wrist, 'holds <object>' above the hand."""
    for h in hand_list:
        col = HAND[h.side]
        pts = [(int(round(x * scale)), int(round(y * scale))) for x, y in h.kp2d]
        for a, b in BONES:
            cv2.line(img, pts[a], pts[b], col, 2, cv2.LINE_AA)
        for pt in pts:
            cv2.circle(img, pt, 3, col, -1, cv2.LINE_AA)
        _label(img, f"{h.side[0].upper()} {h.id if h.id >= 0 else ''}".strip(), (pts[0][0] + 6, pts[0][1] + 16), col)
        if h.side in held:
            top = min(p[1] for p in pts)
            _label(img, f"holds {held[h.side]}", (min(p[0] for p in pts), top - 8), col)


def header(img: np.ndarray, t: float, light: str | None, reasons: str, view: str) -> None:
    m, s = divmod(t, 60)
    word = WORD.get(light, "Not graded") if light else "Not graded"
    text = f"{int(m)}:{s:04.1f}  {word}" + (f" - {reasons.replace(';', ', ')}" if reasons else "")
    _label(img, text, (28, 24))
    cv2.rectangle(img, (12, 13), (22, 23), BGR.get(light or "none", BGR["none"]), -1)
    (w, _), _ = cv2.getTextSize(view, FONT, 0.45, 1)
    _label(img, view, (img.shape[1] - w - 12, 24), (190, 189, 189))


def strip(img: np.ndarray, segments: pd.DataFrame, duration: float, t: float) -> None:
    """The clip's light across the bottom edge, white playhead at t."""
    h, w = img.shape[:2]
    y0 = h - STRIP_H
    img[y0:] = BGR["none"]
    for r in segments.itertuples():
        x0, x1 = int(w * r.t_start / duration), int(w * r.t_end / duration)
        img[y0:, x0:max(x0 + 1, x1)] = BGR.get(r.light, BGR["none"])
    x = min(w - 1, int(w * t / duration))
    cv2.line(img, (x, y0 - 4), (x, h - 1), INK, 2)


def arms(img: np.ndarray, side_masks: dict[str, np.ndarray], alpha: float = 0.35) -> None:
    """Tint each hand's skin region (hand + forearm) in its side colour, with a 2 px outline."""
    for side, mask in side_masks.items():
        if not mask.any():
            continue
        col = np.array(HAND[side], np.float32)
        img[mask] = (img[mask] * (1 - alpha) + col * alpha).astype(np.uint8)
        contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(img, contours, -1, HAND[side], 2, cv2.LINE_AA)
