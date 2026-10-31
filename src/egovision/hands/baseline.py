"""A1 · owner: Abhijay. Task: docs/06-plan/tasks/abhijay.md

MediaPipe Hand Landmarker, VIDEO mode, untouched output.
In: ClipPaths(clip).video  Out: ClipPaths(clip).hands_baseline (every FRAME_STEP-th frame).
"""
from __future__ import annotations

import argparse
import time
from collections import Counter
from typing import Iterator

import cv2

from egovision import config
from egovision.hands import params
from egovision.io.frames import frames
from egovision.schema import ClipPaths, FrameHands, Hand, read_hands, write_hands

COLORS = {"left": (255, 0, 0), "right": (0, 165, 255)}  # BGR: left blue, right orange


def to_frame_hands(res, frame: int, t: float, w: int, h: int) -> FrameHands:
    """MediaPipe result → contract format. Sides stay as MediaPipe labels them."""
    hands = []
    for pts, hd, wpts in zip(res.hand_landmarks, res.handedness, res.hand_world_landmarks):
        kp = [[p.x * w, p.y * h] for p in pts]
        xs, ys = zip(*kp)
        hands.append(Hand(side=hd[0].category_name.lower(), score=hd[0].score,
                          bbox=[min(xs), min(ys), max(xs), max(ys)], kp2d=kp,
                          kp3d=[[p.x, p.y, p.z] for p in wpts]))
    return FrameHands(frame, t, hands)


def _detect(clip: str) -> Iterator[FrameHands]:
    import mediapipe as mp
    from mediapipe.tasks import python as mpp
    from mediapipe.tasks.python import vision

    opts = vision.HandLandmarkerOptions(
        base_options=mpp.BaseOptions(model_asset_path=str(params.MODEL_PATH)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=params.NUM_HANDS,
        min_hand_detection_confidence=params.MIN_DETECTION_CONF,
        min_tracking_confidence=params.MIN_TRACKING_CONF)
    with vision.HandLandmarker.create_from_options(opts) as lm:
        for i, t, img in frames(ClipPaths(clip).video, step=config.FRAME_STEP):
            h, w = img.shape[:2]
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            yield to_frame_hands(lm.detect_for_video(mp_img, int(t * 1000)), i, t, w, h)


def run(clip: str) -> None:
    p = ClipPaths(clip).mkdir()
    if not params.MODEL_PATH.exists():
        raise FileNotFoundError(f"{params.MODEL_PATH}: download it from {params.MODEL_URL}")
    counts: Counter[int] = Counter()

    def counted() -> Iterator[FrameHands]:
        for fr in _detect(clip):
            counts[len(fr.hands)] += 1
            yield fr

    # Written to a temp name first: the CLI treats an existing output as a finished stage.
    tmp = p.hands_baseline.with_suffix(".tmp")
    t0 = time.time()
    write_hands(tmp, counted())
    tmp.replace(p.hands_baseline)
    n = sum(counts.values())
    shares = " ".join(f"{k}h={counts[k] / max(n, 1):.1%}" for k in range(params.NUM_HANDS + 1))
    print(f"  {clip}: {n} frames, {n / max(time.time() - t0, 1e-6):.1f} FPS, {shares}")


def preview(clip: str) -> None:
    """Draws the raw baseline on the clip; skipped frames repeat the last result."""
    from mediapipe.tasks.python.vision import HandLandmarksConnections as C

    p = ClipPaths(clip)
    rows = {fr.frame: fr for fr in read_hands(p.hands_baseline)}
    cap = cv2.VideoCapture(str(p.video))
    fps, w, h = cap.get(cv2.CAP_PROP_FPS) or 30.0, int(cap.get(3)), int(cap.get(4))
    cap.release()
    out = cv2.VideoWriter(str(p.dir / "preview_baseline.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    last = None
    for i, _, img in frames(p.video):
        last = rows.get(i, last)
        for hand in (last.hands if last else []):
            color = COLORS[hand.side]
            pts = [(int(x), int(y)) for x, y in hand.kp2d]
            for c in C.HAND_CONNECTIONS:
                cv2.line(img, pts[c.start], pts[c.end], color, 2)
            for pt in pts:
                cv2.circle(img, pt, 3, color, -1)
            cv2.putText(img, f"{hand.side} {hand.score:.2f}", (int(hand.bbox[0]), max(int(hand.bbox[1]) - 6, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        out.write(img)
    out.release()
    print(f"  wrote {p.dir / 'preview_baseline.mp4'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="egovision.hands.baseline")
    ap.add_argument("--clip", required=True)
    ap.add_argument("--preview", action="store_true", help="also write preview_baseline.mp4")
    ap.add_argument("--force", action="store_true", help="re-run detection even if the output exists")
    a = ap.parse_args()
    if a.force or not ClipPaths(a.clip).hands_baseline.exists():
        run(a.clip)
    if a.preview:
        preview(a.clip)
