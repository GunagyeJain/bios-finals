"""A4 · owner: Abhijay. GPU job, run on the RTX laptop or Colab, not part of `run`:
    python -m egovision.hands.wilor --clip factory_001
In: hands.jsonl flags  Out: wilor.jsonl ({frame, t, hands:[Hand dicts with source="wilor"]}).
Share wilor.jsonl through the private team Drive folder; refine.py merges it when present.
Environment: python scripts/setup_wilor.py
"""
from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from dataclasses import dataclass

import cv2
import numpy as np

from egovision import config
from egovision.hands import cleanup, params
from egovision.io.frames import frames
from egovision.schema import ClipPaths, FrameHands, Hand, read_hands, read_meta, write_hands


@dataclass(frozen=True)
class Request:
    frame: int
    t: float
    id: int
    side: str
    bbox: tuple[float, float, float, float]
    reason: str  # missing | flagged


def select(rows: list[FrameHands], step: int, fps: float) -> list[Request]:
    """Sampled frames only. A hand is sent when flagged low_conf/disagree, or when MediaPipe had nothing
    there inside a live track: gap-filled (source interp), or absent with the track back within TRACK_KEEP_S."""
    out: list[Request] = []
    seen: dict[int, list[tuple[int, float, Hand]]] = defaultdict(list)
    for fr in rows:
        for h in fr.hands:
            seen[h.id].append((fr.frame, fr.t, h))
            if fr.frame % step:
                continue
            if h.source == "interp":
                out.append(Request(fr.frame, fr.t, h.id, h.side, tuple(h.bbox), "missing"))
            elif {"low_conf", "disagree"} & set(h.flags):
                out.append(Request(fr.frame, fr.t, h.id, h.side, tuple(h.bbox), "flagged"))
    for tid, obs in seen.items():
        for (fa, ta, a), (fb, tb, b) in zip(obs, obs[1:]):
            if fb - fa <= 1 or tb - ta > params.TRACK_KEEP_S:
                continue
            for f in range(fa + 1, fb):
                if f % step == 0:
                    w = (f - fa) / (fb - fa)
                    box = tuple((1 - w) * x + w * y for x, y in zip(a.bbox, b.bbox))
                    out.append(Request(f, f / fps, tid, a.side, box, "missing"))
    return sorted(out, key=lambda r: (r.frame, r.id))


def crop_box(bbox, rescale: float = params.WILOR_RESCALE) -> tuple[float, float, float]:
    """Square crop around the box: centre x, centre y, side."""
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2, (y1 + y2) / 2, rescale * max(x2 - x1, y2 - y1, 1.0)


def make_patch(img: np.ndarray, bbox, side: str, size: int = params.WILOR_PATCH) -> np.ndarray:
    """BGR square crop resized to the model input, zero padded, mirrored for left hands (the model
    only knows right hands). Blurred before shrinking to avoid aliasing, as WiLoR does."""
    cx, cy, s = crop_box(bbox)
    half = s / 2
    x1, y1 = int(round(cx - half)), int(round(cy - half))
    n = max(int(round(s)), 2)
    h, w = img.shape[:2]
    patch = np.zeros((n, n, 3), dtype=img.dtype)
    ax1, ay1, ax2, ay2 = max(x1, 0), max(y1, 0), min(x1 + n, w), min(y1 + n, h)
    if ax2 > ax1 and ay2 > ay1:
        patch[ay1 - y1:ay2 - y1, ax1 - x1:ax2 - x1] = img[ay1:ay2, ax1:ax2]
    if side == "left":
        patch = patch[:, ::-1]
    factor = n / size / 2
    if factor > 1.1:
        patch = cv2.GaussianBlur(patch, (0, 0), (factor - 1) / 2)
    return cv2.resize(patch, (size, size), interpolation=cv2.INTER_LINEAR)


def to_hand(joints: np.ndarray, cam: np.ndarray, req: Request, width: int, height: int) -> Hand:
    """One model output → contract Hand. Same camera maths as WiLoR's demo: crop camera to full image,
    then project. kp3d is re-centred on the joints' mean to sit in the same frame as MediaPipe's."""
    joints = np.array(joints, dtype=float)
    s, tx, ty = float(cam[0]), float(cam[1]), float(cam[2])
    if req.side == "left":
        joints[:, 0] *= -1
        tx *= -1
    cx, cy, box = crop_box(req.bbox)
    focal = params.WILOR_FOCAL / params.WILOR_PATCH * max(width, height)
    bs = box * s + 1e-9
    tz = 2 * focal / bs
    t = np.array([2 * (cx - width / 2) / bs + tx, 2 * (cy - height / 2) / bs + ty, tz])
    cam_pts = joints + t
    kp2d = (focal * cam_pts[:, :2] / cam_pts[:, 2:3] + np.array([width / 2, height / 2])).tolist()
    kp3d = (joints - joints.mean(axis=0)).tolist()
    return Hand(side=req.side, bbox=cleanup.bbox_of(kp2d), score=params.WILOR_SCORE, kp2d=kp2d, kp3d=kp3d,
                id=req.id, source="wilor")


def _load_model(device: str):
    """Built directly from local files: nothing here may fetch MANO from anywhere but the user's own
    registered download."""
    import torch
    from wilor_mini.models.wilor import WiLor

    mano = params.WILOR_DIR / "MANO_RIGHT.pkl"
    ckpt = params.WILOR_DIR / "wilor_final.ckpt"
    mean = params.WILOR_DIR / "mano_mean_params.npz"
    for f in (mano, ckpt, mean):
        if not f.exists():
            raise SystemExit(f"missing {f}\nMANO_RIGHT.pkl: register at https://mano.is.tue.mpg.de and copy it here. "
                             "Others: python scripts/setup_wilor.py")
    model = WiLor(mano_model_path=str(mano), mano_mean_path=str(mean), focal_length=params.WILOR_FOCAL,
                  image_size=params.WILOR_PATCH)
    model.load_state_dict(torch.load(ckpt, map_location="cpu", weights_only=False)["state_dict"], strict=False)
    return model.eval().to(device)


def run(clip: str, device: str = "cuda") -> dict:
    import torch

    p = ClipPaths(clip)
    meta = read_meta(p.meta)
    w, h, step = meta["width"], meta["height"], meta.get("step", config.FRAME_STEP)
    reqs = select(list(read_hands(p.hands)), step, meta["fps"])
    by_frame: dict[int, list[Request]] = defaultdict(list)
    for r in reqs:
        by_frame[r.frame].append(r)
    model = _load_model(device)

    results: dict[int, list[Hand]] = defaultdict(list)
    batch: list[tuple[Request, np.ndarray]] = []

    def flush() -> None:
        if not batch:
            return
        x = torch.from_numpy(np.stack([b[1] for b in batch])).to(device, dtype=torch.float32)
        with torch.inference_mode():
            out = model(x)
        joints, cams = out["pred_keypoints_3d"].float().cpu().numpy(), out["pred_cam"].float().cpu().numpy()
        for (req, _), j, c in zip(batch, joints, cams):
            results[req.frame].append(to_hand(j, c, req, w, h))
        batch.clear()

    t0 = time.time()
    for i, _, img in frames(p.video, step=step):
        for r in by_frame.get(i, ()):
            batch.append((r, make_patch(img, r.bbox, r.side)))
            if len(batch) >= params.WILOR_BATCH:
                flush()
    flush()
    took = time.time() - t0

    tmp = p.wilor.with_suffix(".tmp")
    write_hands(tmp, (FrameHands(f, f / meta["fps"], [cleanup.rounded(x) for x in results[f]]) for f in sorted(results)))
    tmp.replace(p.wilor)
    sampled = len(range(0, meta["n_frames"], step))
    s = {"hands_sent": len(reqs), "frames_sent": len(by_frame), "share_of_frames": round(len(by_frame) / max(sampled, 1), 4),
         "reasons": {k: sum(r.reason == k for r in reqs) for k in ("missing", "flagged")},
         "hands_per_s": round(len(reqs) / max(took, 1e-6), 1),
         "device": torch.cuda.get_device_name(0) if device == "cuda" else device}
    (p.dir / "wilor_stats.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
    print(f"  {clip}: {s}")
    return s


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="egovision.hands.wilor")
    ap.add_argument("--clip", required=True)
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args()
    run(a.clip, a.device)
