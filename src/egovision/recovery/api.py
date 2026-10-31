"""Plug-in functions called by hands/refine.py · owner: Bhavyam (B1, B2).
Signatures are fixed. Defaults are no-ops so Abhijay's pipeline runs before these exist.
"""
from __future__ import annotations

import numpy as np

from egovision.schema import Hand


def recover_missing(img: np.ndarray, frame: int, t: float, side: str, last: Hand | None) -> Hand | None:
    """B2 + B1: try ROI re-detect (crop around `last`, upscale, CLAHE) then rtmlib. Return a Hand
    with source "roi" or "rtmlib", or None if nothing found."""
    return None


def agreement(img: np.ndarray, hand: Hand) -> float | None:
    """B1: 0..1 agreement between `hand` and rtmlib on the same box. None = not computed."""
    return None
