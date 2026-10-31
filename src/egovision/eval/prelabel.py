"""Suggested points for the label tool. `python -m egovision.eval.prelabel --clip X --labeller NAME [--n 40]`
Writes outputs/prelabels/<clip>__<labeller>.json (git-ignored, coordinates only); the label tool shows them
as hollow points the labeller checks, moves or clears.

Model: rtmlib `Hand` (RTMDet hand detector + RTMPose hand, ONNX, CPU). Never MediaPipe or our own
hands*.jsonl: labels are ground truth for the metrics. rtmlib is also the pipeline's recovery model (B1,
`source="rtmlib"`), so each saved hand records `prefill` and `edited`, and the metrics report prefilled
hands next to the manual --shared set (which never gets suggestions).
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np

from .label_tool import N_POINTS, frame_image, frame_order, prelabels_path

KP = (0, 4, 8, 12, 16, 20)       # wrist + 5 tips, MediaPipe / RTMPose hand order
MIN_SCORE = 0.3                  # mean score of those 6 points; below = no suggestion
SIDE_MARGIN = 0.15               # |wrist x - hand centre x| under 15 % of the hand width → side unsure
MODEL = "rtmlib"


def guess_side(points: list[list[float]]) -> str | None:
    """Head-cam view: the right hand enters from the lower right, so its wrist sits right of the
    hand's own centre (left hand: left of it). Too close to call → None."""
    xs = [p[0] for p in points]
    width = max(xs) - min(xs)
    dx = points[0][0] - sum(xs) / len(xs)
    if width <= 0 or abs(dx) < SIDE_MARGIN * width:
        return None
    return "right" if dx > 0 else "left"


def hands_from_model(bboxes, keypoints, scores, max_hands: int = 2) -> list[dict]:
    """rtmlib output → up to `max_hands` suggestions {points, side, score}, best first.
    rtmlib returns one whole-image pose when the detector finds no box: that is noise, so no box → []."""
    if bboxes is None or len(bboxes) == 0:
        return []
    out = []
    for kp, sc in zip(np.asarray(keypoints), np.asarray(scores)):
        score = float(np.mean(sc[list(KP)]))
        if score < MIN_SCORE:
            continue
        points = [[round(float(kp[k][0]), 1), round(float(kp[k][1]), 1)] for k in KP]
        out.append({"points": points, "side": guess_side(points), "score": round(score, 3)})
    out.sort(key=lambda h: -h["score"])
    out = out[:max_hands]
    if len(out) == 2 and out[0]["side"] and out[0]["side"] == out[1]["side"]:
        for h in out:                                  # two hands can't share a side: leave both to the labeller
            h["side"] = None
    return out


def run(clip: str, labeller: str, n: int) -> dict:
    from rtmlib import Hand
    labeller = labeller.strip().lower()
    frames = frame_order(clip, labeller, n, shared=False)
    model = Hand(backend="onnxruntime", device="cpu")
    found: dict[str, list[dict]] = {}
    for i, frame in enumerate(frames, 1):
        img = frame_image(clip, frame)
        if img is None:
            continue
        bboxes = model.det_model(img)
        hands = []
        if len(bboxes):
            keypoints, scores = model.pose_model(img, bboxes=bboxes)
            hands = hands_from_model(bboxes, keypoints, scores)
        if hands:
            found[str(frame)] = hands
        print(f"\r{i}/{len(frames)} frames, {len(found)} with suggestions", end="", file=sys.stderr)
    print(file=sys.stderr)
    assert all(len(h["points"]) == N_POINTS for hs in found.values() for h in hs)
    out = prelabels_path(clip, labeller)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {"clip": clip, "labeller": labeller, "model": MODEL, "frames": found}
    out.write_text(json.dumps(data) + "\n", encoding="utf-8")
    print(f"{clip}: suggestions for {len(found)}/{len(frames)} frames → {out}")
    return data


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m egovision.eval.prelabel", description=__doc__.split("\n")[0])
    ap.add_argument("--clip", required=True)
    ap.add_argument("--labeller", required=True, help="same name you label with")
    ap.add_argument("--n", type=int, default=40, help="same --n you label with")
    a = ap.parse_args(argv)
    run(a.clip, a.labeller, a.n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
