"""Plug-in functions called by hands/refine.py · owner: Bhavyam (B1, B2).
Signatures are fixed. rtmlib and MediaPipe load on first use, so importing this module stays cheap.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from egovision.hands import params as hand_params
from egovision.hands.baseline import to_frame_hands
from egovision.recovery import params as P
from egovision.schema import TIPS, Hand

WRIST_AND_TIPS = (0, *TIPS)


@lru_cache(maxsize=1)
def _pose():
    from rtmlib import Hand as RtmHand
    from rtmlib import RTMPose

    m = RtmHand.MODE["lightweight"]
    return RTMPose(m["pose"], model_input_size=m["pose_input_size"], backend="onnxruntime", device="cpu")


@lru_cache(maxsize=1)
def _detector():
    from rtmlib import Hand as RtmHand
    from rtmlib import RTMDet

    m = RtmHand.MODE["lightweight"]
    return RTMDet(m["det"], model_input_size=m["det_input_size"], backend="onnxruntime", device="cpu")


@lru_cache(maxsize=1)
def _landmarker():
    from mediapipe.tasks import python as mpp
    from mediapipe.tasks.python import vision

    opts = vision.HandLandmarkerOptions(
        base_options=mpp.BaseOptions(model_asset_path=str(hand_params.MODEL_PATH)),
        running_mode=vision.RunningMode.IMAGE, num_hands=hand_params.NUM_HANDS,
        min_hand_detection_confidence=P.ROI_MIN_CONF, min_hand_presence_confidence=P.ROI_MIN_CONF)
    return vision.HandLandmarker.create_from_options(opts)


def grow_box(bbox: list[float], scale: float, w: int, h: int, min_size: float = 0.0) -> list[int]:
    """Square box around `bbox`, `scale` times its longer side, inside a w x h frame."""
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    half = max(bbox[2] - bbox[0], bbox[3] - bbox[1], min_size / scale) * scale / 2
    return [max(0, int(cx - half)), max(0, int(cy - half)), min(w, int(cx + half) + 1), min(h, int(cy + half) + 1)]


def to_full(points: list[list[float]], roi: list[int], upscale: float) -> list[list[float]]:
    """Crop pixels of an upscaled ROI -> pixels of the full frame."""
    return [[roi[0] + x / upscale, roi[1] + y / upscale] for x, y in points]


def _bounds(kp: list[list[float]]) -> list[float]:
    xs, ys = zip(*kp)
    return [min(xs), min(ys), max(xs), max(ys)]


def _roi_mediapipe(img: np.ndarray, frame: int, t: float, side: str, last: Hand, roi: list[int]) -> Hand | None:
    """Re-run MediaPipe on the enlarged crop; take the detection nearest the hand we lost."""
    import mediapipe as mp

    crop = img[roi[1]:roi[3], roi[0]:roi[2]]
    big = cv2.resize(crop, None, fx=P.ROI_UPSCALE, fy=P.ROI_UPSCALE, interpolation=cv2.INTER_CUBIC)
    h, w = big.shape[:2]
    res = _landmarker().detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(big, cv2.COLOR_BGR2RGB)))
    found = []
    for hand in to_frame_hands(res, frame, t, w, h).hands:
        kp = to_full(hand.kp2d, roi, P.ROI_UPSCALE)
        found.append(Hand(side=side, bbox=_bounds(kp), score=hand.score, kp2d=kp, kp3d=hand.kp3d, source="roi"))
    if not found:
        return None
    wrist = np.array(last.kp2d[0])
    return min(found, key=lambda x: np.linalg.norm(np.array(x.kp2d[0]) - wrist))


def nearest_box(boxes, roi: list[int], last: Hand) -> list[float] | None:
    """Detector boxes in crop pixels -> the one closest to `last` in full-frame pixels, if within reach."""
    centre = np.array([(last.bbox[0] + last.bbox[2]) / 2, (last.bbox[1] + last.bbox[3]) / 2])
    size = max(last.bbox[2] - last.bbox[0], last.bbox[3] - last.bbox[1], 1.0)
    best, best_d = None, P.RTM_REACH * size
    for x1, y1, x2, y2 in boxes:
        box = [float(x1 + roi[0]), float(y1 + roi[1]), float(x2 + roi[0]), float(y2 + roi[1])]
        d = float(np.hypot((box[0] + box[2]) / 2 - centre[0], (box[1] + box[3]) / 2 - centre[1]))
        if d < best_d:
            best, best_d = box, d
    return best


def _roi_rtmlib(img: np.ndarray, side: str, last: Hand) -> Hand | None:
    """rtmlib's pose returns 21 points even with no hand there, and its score cannot tell the two
    apart on these clips, so its own detector decides. A wide crop keeps that detector honest."""
    h, w = img.shape[:2]
    roi = grow_box(last.bbox, P.RTM_ROI_SCALE, w, h, P.ROI_MIN_SIZE)
    box = nearest_box(_detector()(img[roi[1]:roi[3], roi[0]:roi[2]]), roi, last)
    if box is None:
        return None
    kp, scores = _pose()(img, bboxes=[grow_box(box, P.AGREE_BOX, w, h)])
    pts = [[float(x), float(y)] for x, y in kp[0]]
    return Hand(side=side, bbox=_bounds(pts), score=float(np.mean(scores[0])), kp2d=pts, kp3d=None, source="rtmlib")


def recover_missing(img: np.ndarray, frame: int, t: float, side: str, last: Hand | None) -> Hand | None:
    """B2 + B1: try ROI re-detect (crop around `last`) then rtmlib. Return a Hand with source "roi"
    or "rtmlib", or None if nothing found. An rtmlib hand never seeds another rtmlib
    hand: refine feeds each result back as `last`, so a false one could walk on through a whole gap."""
    if last is None:
        return None
    h, w = img.shape[:2]
    roi = grow_box(last.bbox, P.ROI_SCALE, w, h, P.ROI_MIN_SIZE)
    found = _roi_mediapipe(img, frame, t, side, last, roi)
    if found is None and last.source != "rtmlib":
        found = _roi_rtmlib(img, side, last)
    return found


def agreement(img: np.ndarray, hand: Hand) -> float | None:
    """B1: 0..1 agreement between `hand` and rtmlib on the same box. None = not computed."""
    h, w = img.shape[:2]
    kp, _ = _pose()(img, bboxes=[grow_box(hand.bbox, P.AGREE_BOX, w, h)])
    return agreement_score(hand.kp2d, kp[0], hand.bbox)


def agreement_score(a: list[list[float]], b, bbox: list[float]) -> float:
    """1 when wrist and tips coincide, 0 when they sit AGREE_ZERO hand sizes apart on average."""
    size = max(bbox[2] - bbox[0], bbox[3] - bbox[1], 1.0)
    dist = np.mean([np.hypot(a[i][0] - b[i][0], a[i][1] - b[i][1]) for i in WRIST_AND_TIPS])
    return round(float(max(0.0, 1.0 - dist / size / P.AGREE_ZERO)), 3)
