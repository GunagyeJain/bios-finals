"""B4 · owner: Bhavyam. Blur faces and screens/documents. Fixed signature; default = unchanged
so export (G4) and Work Modules (S4) work before this is built. Never blur inside `keep` boxes."""
from __future__ import annotations

import numpy as np


def redact_frame(img: np.ndarray, keep: list[list[float]] | None = None) -> np.ndarray:
    return img
