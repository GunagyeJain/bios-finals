"""A3 · owner: Abhijay. Sanity checks, gap fill, One-Euro and flags on one track. Pure functions, no video."""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from egovision.hands import params
from egovision.schema import FrameHands, Hand

# MediaPipe finger chains: wrist → tip
FINGERS = ((0, 1, 2, 3, 4), (0, 5, 6, 7, 8), (0, 9, 10, 11, 12), (0, 13, 14, 15, 16), (0, 17, 18, 19, 20))

Obs = tuple[int, float, Hand]  # frame, t, hand of one track, sorted by frame


def bbox_of(kp2d: list[list[float]]) -> list[float]:
    xs, ys = zip(*kp2d)
    return [min(xs), min(ys), max(xs), max(ys)]


def _bone_lengths(h: Hand) -> np.ndarray:
    """Length of each finger, wrist to tip along its bones. Steadier than single bones."""
    p = np.asarray(h.kp3d)
    return np.array([np.linalg.norm(np.diff(p[list(f)], axis=0), axis=1).sum() for f in FINGERS])


def mark_sanity(track: list[Obs], width: int) -> list[Obs]:
    """Flags impossible bone lengths and wrist jumps and lowers their score."""
    with_3d = [h for _, _, h in track if h.kp3d is not None]
    median = np.median([_bone_lengths(h) for h in with_3d], axis=0) if with_3d else None
    out: list[Obs] = []
    for i, (f, t, h) in enumerate(track):
        bad = False
        if median is not None and h.kp3d is not None:
            ratio = _bone_lengths(h) / np.maximum(median, 1e-6)
            bad = bool((ratio < params.BONE_RATIO_MIN).any() or (ratio > params.BONE_RATIO_MAX).any())
        if i:
            _, pt, ph = track[i - 1]
            dt = t - pt
            if 0 < dt <= params.SPEED_MAX_DT_S:
                bad = bad or math.dist(h.kp2d[0], ph.kp2d[0]) / dt / width > params.MAX_WRIST_SPEED
        if bad:
            h = replace(h, score=h.score * params.SANITY_SCORE_SCALE, flags=sorted({*h.flags, "sanity"}))
        out.append((f, t, h))
    return out


def _lerp(a: list[list[float]], b: list[list[float]], w: float) -> list[list[float]]:
    return ((1 - w) * np.asarray(a) + w * np.asarray(b)).tolist()


def fill_gaps(track: list[Obs], fps: float) -> list[Obs]:
    """Linear interpolation across up to MAX_GAP_FRAMES missing frames; longer gaps stay empty."""
    out: list[Obs] = []
    for i, (f, t, h) in enumerate(track):
        out.append((f, t, h))
        if i + 1 == len(track):
            break
        nf, _, nh = track[i + 1]
        if nf - f - 1 > params.MAX_GAP_FRAMES:
            continue
        for g in range(f + 1, nf):
            w = (g - f) / (nf - f)
            kp3d = _lerp(h.kp3d, nh.kp3d, w) if h.kp3d is not None and nh.kp3d is not None else None
            kp2d = _lerp(h.kp2d, nh.kp2d, w)
            out.append((g, g / fps, replace(h, kp2d=kp2d, kp3d=kp3d, bbox=bbox_of(kp2d), score=min(h.score, nh.score),
                                            source="interp", agreement=None, flags=[])))
    return out


class OneEuro:
    """One-Euro filter over an array of coordinates: more smoothing when slow, less lag when fast."""

    def __init__(self, min_cutoff: float, beta: float, d_cutoff: float):
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff
        self.x: np.ndarray | None = None
        self.dx: np.ndarray | None = None

    @staticmethod
    def _alpha(cutoff, dt: float):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x: np.ndarray, dt: float) -> np.ndarray:
        if self.x is None:
            self.x, self.dx = x, np.zeros_like(x)
            return x
        a_d = self._alpha(self.d_cutoff, dt)
        self.dx = a_d * (x - self.x) / dt + (1 - a_d) * self.dx
        a = self._alpha(self.min_cutoff + self.beta * np.abs(self.dx), dt)
        self.x = a * x + (1 - a) * self.x
        return self.x


def _filter() -> OneEuro:
    return OneEuro(params.ONE_EURO_MIN_CUTOFF, params.ONE_EURO_BETA, params.ONE_EURO_D_CUTOFF)


def smooth(track: list[Obs]) -> list[Obs]:
    """One-Euro per coordinate. The filter restarts after a gap so it never drags across one."""
    out: list[Obs] = []
    f2, f3, prev_f, prev_t = _filter(), _filter(), None, 0.0
    for f, t, h in track:
        if prev_f is None or f - prev_f - 1 > params.MAX_GAP_FRAMES:
            f2, f3 = _filter(), _filter()
        dt = max(t - prev_t, 1e-3)
        kp2d = f2(np.asarray(h.kp2d, dtype=float), dt).tolist()
        kp3d = h.kp3d
        if kp3d is not None:
            kp3d = (f3(np.asarray(kp3d, dtype=float) * params.KP3D_FILTER_SCALE, dt) / params.KP3D_FILTER_SCALE).tolist()
        out.append((f, t, replace(h, kp2d=kp2d, kp3d=kp3d, bbox=bbox_of(kp2d))))
        prev_f, prev_t = f, t
    return out


def add_flags(h: Hand, width: int, height: int) -> Hand:
    flags = set(h.flags)
    if h.score < params.LOW_CONF:
        flags.add("low_conf")
    if h.agreement is not None and h.agreement < params.DISAGREE:
        flags.add("disagree")
    m = params.EDGE_PX
    x1, y1, x2, y2 = h.bbox
    if x1 <= m or y1 <= m or x2 >= width - m or y2 >= height - m:
        flags.add("edge")
    return replace(h, flags=sorted(flags))


def clean_track(track: list[Obs], fps: float, width: int, height: int) -> list[Obs]:
    obs = smooth(fill_gaps(mark_sanity(track, width), fps))
    return [(f, t, add_flags(h, width, height)) for f, t, h in obs]


def rounded(h: Hand) -> Hand:
    """Keeps hands.jsonl small: 0.01 px, 0.01 mm."""
    return replace(h, score=round(h.score, 4), bbox=[round(v, 2) for v in h.bbox],
                   kp2d=[[round(v, 2) for v in p] for p in h.kp2d],
                   kp3d=None if h.kp3d is None else [[round(v, 5) for v in p] for p in h.kp3d])


def assemble(tracks: dict[int, list[Obs]], n_frames: int, fps: float) -> list[FrameHands]:
    """One row per video frame, hands in stable id order."""
    rows: list[list[Hand]] = [[] for _ in range(n_frames)]
    for tid in sorted(tracks):
        for f, _, h in tracks[tid]:
            if 0 <= f < n_frames:
                rows[f].append(rounded(h))
    return [FrameHands(i, i / fps, hands) for i, hands in enumerate(rows)]
