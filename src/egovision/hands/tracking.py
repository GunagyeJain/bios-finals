"""A2 · owner: Abhijay. Track IDs (Hungarian match, re-entry) and side voting. Pure functions, no video."""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, replace

import numpy as np
from scipy.optimize import linear_sum_assignment

from egovision.hands import params
from egovision.schema import SIDES, FrameHands, Hand

FORBIDDEN = 1e6


def iou(a: list[float], b: list[float]) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    if w <= 0 or h <= 0:
        return 0.0
    inter = w * h
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def hand_size(h: Hand) -> float:
    return max(h.bbox[2] - h.bbox[0], h.bbox[3] - h.bbox[1], 1.0)


def wrist_distance(a: Hand, b: Hand) -> float:
    return math.dist(a.kp2d[0], b.kp2d[0])


def flip_side(side: str) -> str:
    return "right" if side == "left" else "left"


def dedupe(hands: list[Hand]) -> list[Hand]:
    """One hand detected twice in a frame: keep the higher score."""
    kept: list[Hand] = []
    for h in sorted(hands, key=lambda x: -x.score):
        if all(iou(h.bbox, k.bbox) < params.DUP_IOU for k in kept):
            kept.append(h)
    return kept


@dataclass
class _Track:
    id: int
    last: Hand
    last_t: float


def _cost(tr: _Track, h: Hand, t: float, width: int) -> float:
    gap = t - tr.last_t
    differs = tr.last.side != h.side
    if differs and (gap > params.SIDE_STRICT_AFTER_S or iou(tr.last.bbox, h.bbox) < params.SIDE_SWITCH_IOU):
        return FORBIDDEN
    size = max(hand_size(tr.last), hand_size(h))
    gate = min(size * (params.GATE_SIZES + params.GATE_SIZES_PER_S * gap), params.GATE_MAX_WIDTH * width)
    d = wrist_distance(tr.last, h)
    if d > gate:
        return FORBIDDEN
    return (params.COST_SIDE * differs + params.COST_IOU * (1 - iou(tr.last.bbox, h.bbox))
            + params.COST_DIST * d / gate)


def assign_ids(frames: list[FrameHands], width: int) -> list[FrameHands]:
    """Gives every hand a track id. Labels stay per-frame here; `vote_sides` settles them."""
    tracks: list[_Track] = []
    next_id = 0
    out = []
    for fr in frames:
        tracks = [tr for tr in tracks if fr.t - tr.last_t <= params.TRACK_KEEP_S]
        hands = dedupe(fr.hands)
        matched: dict[int, _Track] = {}
        if tracks and hands:
            cost = np.array([[_cost(tr, h, fr.t, width) for h in hands] for tr in tracks])
            for ti, hi in zip(*linear_sum_assignment(cost)):
                if cost[ti, hi] < FORBIDDEN:
                    matched[int(hi)] = tracks[ti]
        new_hands = []
        for i, h in enumerate(hands):
            tr = matched.get(i)
            if tr is None:
                tr = _Track(next_id, h, fr.t)
                next_id += 1
                tracks.append(tr)
            tr.last, tr.last_t = h, fr.t
            new_hands.append(replace(h, id=tr.id))
        out.append(FrameHands(fr.frame, fr.t, new_hands))
    return out


def split_on_side_change(frames: list[FrameHands]) -> list[FrameHands]:
    """A track whose labels change for good has jumped to the other hand: cut it there, so one
    vote never covers both hands. Short label blips average out and don't cut."""
    labels: dict[int, list[float]] = defaultdict(list)
    for fr in frames:
        for h in fr.hands:
            labels[h.id].append(h.score if h.side == "left" else -h.score)

    pieces: dict[int, list[int]] = {}
    next_id = 0
    for tid, vals in labels.items():
        kernel = np.ones(min(params.SIDE_WINDOW, len(vals)))  # "same" returns the longer of the two
        signs = np.sign(np.convolve(vals, kernel, mode="same"))
        runs: list[list[int]] = []  # [sign, length]
        for s in signs:
            if runs and (s == runs[-1][0] or s == 0):
                runs[-1][1] += 1
            else:
                runs.append([s, 1])
        merged: list[list[int]] = []
        for s, n in runs:
            if merged and (n < params.SIDE_MIN_RUN or s == merged[-1][0]):
                merged[-1][1] += n
            else:
                merged.append([s, n])
        ids: list[int] = []
        for _, n in merged:
            ids += [next_id] * n
            next_id += 1
        pieces[tid] = ids

    pos: dict[int, int] = defaultdict(int)
    out = []
    for fr in frames:
        hands = []
        for h in fr.hands:
            hands.append(replace(h, id=pieces[h.id][pos[h.id]]))
            pos[h.id] += 1
        out.append(FrameHands(fr.frame, fr.t, hands))
    return out


def vote_sides(frames: list[FrameHands], width: int) -> list[FrameHands]:
    """A track's side = score-weighted labels + image-half prior + left-of-the-other-hand, so one
    frame can't swap it. Tracks alive together shouldn't share a side: the one with weaker evidence
    takes the other side, but only if that agrees with where the two sit in the image."""
    votes: dict[int, dict[str, float]] = defaultdict(lambda: dict.fromkeys(SIDES, 0.0))
    xs: dict[int, dict[int, float]] = defaultdict(dict)
    for fr in frames:
        for h in fr.hands:
            votes[h.id][h.side] += h.score
            votes[h.id]["left" if h.kp2d[0][0] < width / 2 else "right"] += params.PRIOR_WEIGHT
            xs[h.id][fr.frame] = h.kp2d[0][0]
        if len(fr.hands) == 2:
            a, b = sorted(fr.hands, key=lambda h: h.kp2d[0][0])
            votes[a.id]["left"] += params.PAIR_WEIGHT
            votes[b.id]["right"] += params.PAIR_WEIGHT

    sides: dict[int, str] = {}
    strongest_first = sorted(votes, key=lambda i: -abs(votes[i]["left"] - votes[i]["right"]))
    for tid in strongest_first:
        side = max(SIDES, key=lambda s: votes[tid][s])
        rivals = [o for o in sides if len(xs[tid].keys() & xs[o].keys()) >= params.CONFLICT_MIN_FRAMES]
        same = [o for o in rivals if sides[o] == side]
        if same and all(sides[o] == side for o in rivals):
            shared = xs[tid].keys() & xs[same[0]].keys()
            is_left = sum(xs[tid][f] - xs[same[0]][f] for f in shared) < 0
            if ("left" if is_left else "right") != side:
                side = flip_side(side)
        sides[tid] = side
    return [FrameHands(fr.frame, fr.t, [replace(h, side=sides[h.id]) for h in fr.hands]) for fr in frames]


def fix_same_side(frames: list[FrameHands]) -> list[FrameHands]:
    """Two hands left with one side after voting can't both be right: when they are clearly apart, the
    one further left in the image is the left hand. Pairs with different sides are left alone."""
    out = []
    for fr in frames:
        if len(fr.hands) == 2 and fr.hands[0].side == fr.hands[1].side:
            a, b = sorted(fr.hands, key=lambda h: h.kp2d[0][0])
            if b.kp2d[0][0] - a.kp2d[0][0] > params.SAME_SIDE_APART * max(hand_size(a), hand_size(b)):
                fr = FrameHands(fr.frame, fr.t, [replace(a, side="left"), replace(b, side="right")])
        out.append(fr)
    return out
