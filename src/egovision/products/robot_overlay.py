"""B7 · owner: Bhavyam. Task: docs/06-plan/sprint-3.md

Robot view: a 2-finger gripper or a 5-finger robot hand drawn on each hand, coloured by whether that robot could copy
the current grab. A drawing of the human pose, not a robot simulation.
In: video, hands_input(), contacts.csv  Out: render_robot_2f.mp4, render_robot_5f.mp4.
`python -m egovision.products.robot_overlay --clip X [--mode 2f|5f|both]`
"""
from __future__ import annotations

import argparse
import math
from typing import Callable

import cv2
import numpy as np

from egovision.index.query import ROBOT_CAN_COPY
from egovision.io.frames import frames
from egovision.io.video import H264Writer
from egovision.safety.run import hand_size
from egovision.schema import CONTACT_COLS, ClipPaths, Hand, read_hands, read_meta

from . import overlay
from .render import CRF, WIDTH, _at, _table

MODES = ("2f", "5f")
NAMES = {"2f": "2-finger robot", "5f": "5-finger robot"}
COLOUR = {"copy": overlay.BGR["green"], "cannot": overlay.BGR["red"], "none": (146, 140, 138)}
WORD = {"copy": "can copy", "cannot": "cannot copy", "none": "no grab"}
LINK = 8                 # px, thickness of robot links
EDGE = 2                 # px, dark edge so links read on any footage
GAP_MIN, GAP_MAX = 0.1, 1.0   # jaw gap limits, share of hand size
RAIL_AT, JAW_END = 0.4, 1.1   # along the wrist -> kp 9 line, share of its length


def status(grip: str | None, mode: str) -> str:
    if not grip or grip == "unsure":
        return "none"
    return "copy" if grip in ROBOT_CAN_COPY[mode] else "cannot"


def jaw_gap(hand: Hand) -> float:
    """Thumb tip to index tip in source pixels, limited to what a gripper can open."""
    size = hand_size(hand)
    return float(np.clip(math.dist(hand.kp2d[4], hand.kp2d[8]), GAP_MIN * size, GAP_MAX * size))


def gripper(hand: Hand) -> list[tuple[np.ndarray, np.ndarray]]:
    """Stem, rail and two jaws as line segments in source pixels, pointing wrist -> kp 9."""
    wrist, knuckle = np.array(hand.kp2d[0], float), np.array(hand.kp2d[9], float)
    length = max(float(np.linalg.norm(knuckle - wrist)), 1.0)
    along = (knuckle - wrist) / length
    across = np.array([-along[1], along[0]]) * jaw_gap(hand) / 2
    rail = wrist + RAIL_AT * length * along
    end = wrist + JAW_END * length * along
    return [(wrist, rail), (rail - across, rail + across), (rail - across, end - across), (rail + across, end + across)]


def _links(img: np.ndarray, segments: list, colour: tuple) -> None:
    for width, col in ((LINK + 2 * EDGE, overlay.PANEL), (LINK, colour)):
        for a, b in segments:
            cv2.line(img, a, b, col, width, cv2.LINE_AA)


def _pixels(point, scale: float) -> tuple[int, int]:
    return int(round(point[0] * scale)), int(round(point[1] * scale))


def draw_gripper(img: np.ndarray, hand: Hand, scale: float, colour: tuple) -> None:
    _links(img, [(_pixels(a, scale), _pixels(b, scale)) for a, b in gripper(hand)], colour)


def draw_hand(img: np.ndarray, hand: Hand, scale: float, colour: tuple) -> None:
    pts = [_pixels(p, scale) for p in hand.kp2d]
    _links(img, [(pts[a], pts[b]) for a, b in overlay.BONES], colour)
    for pt in pts:
        cv2.circle(img, pt, LINK // 2 + EDGE, overlay.PANEL, -1, cv2.LINE_AA)
        cv2.circle(img, pt, LINK // 2, colour, -1, cv2.LINE_AA)


DRAW = {"2f": draw_gripper, "5f": draw_hand}


def draw_frame(img: np.ndarray, hands: list[Hand], grips: dict[str, str], scale: float, mode: str) -> None:
    """Nothing on a frame with no hand. With two hands the label names the less copyable one."""
    if not hands:
        return
    states = [status(grips.get(h.side), mode) for h in hands]
    for hand, state in zip(hands, states):
        DRAW[mode](img, hand, scale, COLOUR[state])
    worst = next(s for s in ("cannot", "copy", "none") if s in states)
    overlay._label(img, f"{NAMES[mode]}: {WORD[worst]}", (12, 24), COLOUR[worst])


def render(clip: str, mode: str = "both", redact: Callable | None = None) -> None:
    """One pass writes every requested view, so faces are blurred once."""
    if redact is None:
        from egovision.quality.redact import clip_redactor
        redact = clip_redactor(clip)
    p = ClipPaths(clip)
    meta = read_meta(p.meta)
    step, fps = int(meta["step"]), float(meta["fps"])
    hands = {f.frame: f.hands for f in read_hands(p.hands_input())}
    contacts = _table(p.contacts, CONTACT_COLS, ("t_start", "t_end"))
    contacts = contacts.astype({"confidence": float}).sort_values("confidence")   # strongest wins when rows overlap
    scale = WIDTH / int(meta["width"])
    size = (WIDTH, int(round(int(meta["height"]) * scale / 2)) * 2)
    writers = {m: H264Writer(p.dir / f"render_robot_{m}.mp4", fps / step, size, CRF)
               for m in (MODES if mode == "both" else (mode,))}
    try:
        for i, t, img in frames(p.video, step=step):
            small = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
            now = hands.get(i, [])
            clean = redact(small, keep=[[v * scale for v in h.bbox] for h in now], frame=i)
            grips = {r.hand: r.grip for r in _at(contacts, t).itertuples()}
            for m, writer in writers.items():
                out = clean.copy()
                draw_frame(out, now, grips, scale, m)
                writer.write(out)
    finally:
        for writer in writers.values():
            writer.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="egovision.products.robot_overlay")
    ap.add_argument("--clip", required=True)
    ap.add_argument("--mode", choices=(*MODES, "both"), default="both")
    a = ap.parse_args()
    render(a.clip, a.mode)
