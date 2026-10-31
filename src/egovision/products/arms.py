"""G6 · owner: Gunagye. Hand + forearm masks for render.mp4: MediaPipe's multiclass segmenter finds skin;
each skin region is given to the tracked hand it touches, so a coworker's arm is never painted."""
from __future__ import annotations

import urllib.request
from functools import lru_cache

import cv2
import numpy as np

from egovision import config

MODEL = config.ROOT / "models" / "selfie_multiclass_256x256.tflite"
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/"
             "float32/latest/selfie_multiclass_256x256.tflite")
SKIN = 2              # category "body-skin" (0 background, 1 hair, 2 body-skin, 3 face-skin, 4 clothes, 5 others)
TOUCH_PX = 12         # a region belongs to a hand if one of its keypoints is within this many pixels
MIN_AREA = 400        # px at render size: smaller specks are noise
REACH = 2.0           # a hand's region ends this many hand sizes from its keypoints (hand + forearm)


@lru_cache(maxsize=1)
def _segmenter():
    from mediapipe.tasks import python as mpp
    from mediapipe.tasks.python import vision

    if not MODEL.exists():
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, MODEL.with_suffix(".tmp"))
        MODEL.with_suffix(".tmp").replace(MODEL)
    opts = vision.ImageSegmenterOptions(base_options=mpp.BaseOptions(model_asset_path=str(MODEL)),
                                        output_category_mask=True)
    return vision.ImageSegmenter.create_from_options(opts)


def skin(img: np.ndarray) -> np.ndarray:
    """Boolean skin mask (body skin, not faces) at the image's size."""
    import mediapipe as mp

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    cat = np.squeeze(_segmenter().segment(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
                     .category_mask.numpy_view())
    return cat == SKIN


def by_hand(mask: np.ndarray, hands: list, scale: float) -> dict[str, np.ndarray]:
    """Split a skin mask into connected regions and give each to the side whose keypoints touch it."""
    n, labels = cv2.connectedComponents(mask.astype(np.uint8), connectivity=8)
    near = cv2.dilate(labels.astype(np.uint16), np.ones((2 * TOUCH_PX + 1,) * 2, np.uint8))  # grow labels a bit
    h, w = mask.shape
    claims: dict[str, np.ndarray] = {}
    dist: dict[str, np.ndarray] = {}
    for hand in hands:
        seeds = np.full((h, w), 255, np.uint8)
        ids = set()
        for x, y in hand.kp2d:
            xi, yi = int(round(x * scale)), int(round(y * scale))
            if 0 <= xi < w and 0 <= yi < h:
                seeds[yi, xi] = 0
                if near[yi, xi]:
                    ids.add(int(near[yi, xi]))
        if ids:
            d = cv2.distanceTransform(seeds, cv2.DIST_L2, 3)
            size = np.hypot(hand.bbox[2] - hand.bbox[0], hand.bbox[3] - hand.bbox[1]) * scale
            region = np.isin(labels, list(ids)) & (d <= REACH * size)   # an untracked hand nearby stays unpainted
            claims[hand.side] = claims.get(hand.side, np.zeros_like(mask)) | region
            dist[hand.side] = np.minimum(dist[hand.side], d) if hand.side in dist else d
    if len(claims) == 2:                    # both hands touch one region: each pixel goes to the nearer hand
        shared = claims["left"] & claims["right"]
        left_nearer = dist["left"] <= dist["right"]
        claims["left"] &= ~shared | left_nearer
        claims["right"] &= ~shared | ~left_nearer
    return {side: region for side, region in claims.items() if region.sum() >= MIN_AREA}
