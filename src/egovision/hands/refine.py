"""A2-A4 · owner: Abhijay. Task: docs/06-plan/tasks/abhijay.md

Mirror fix, track IDs, side voting, recovery plug-ins, WiLoR merge, sanity, gap fill, One-Euro.
In: hands_baseline (+ wilor.jsonl if present)  Out: hands.jsonl (every frame).
Calls egovision.recovery.api.recover_missing / agreement (no-op until Bhavyam fills them).
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import replace
from typing import Callable, Iterable

import cv2
import numpy as np

from egovision import config
from egovision.eval.metrics import jitter, pair_order, swaps_per_min
from egovision.hands import cleanup, params, tracking
from egovision.hands.baseline import draw_hands, write_preview
from egovision.io.frames import build_meta, frames
from egovision.io.video import H264Writer
from egovision.recovery import api as recovery
from egovision.schema import ClipPaths, FrameHands, Hand, read_hands, read_meta, write_hands

COMPARE_SECONDS = 10


def apply_mirror(rows: list[FrameHands], mirror: bool) -> list[FrameHands]:
    if not mirror:
        return rows
    return [FrameHands(fr.frame, fr.t, [replace(h, side=tracking.flip_side(h.side)) for h in fr.hands]) for fr in rows]


def apply_recovery(rows: list[FrameHands], images: Iterable[tuple[int, float, np.ndarray]],
                   recover: Callable = recovery.recover_missing, agree: Callable = recovery.agreement) -> list[FrameHands]:
    """Asks the plug-ins about hands missing inside a live track and scores the ones present."""
    frames_of: dict[int, list[int]] = defaultdict(list)
    side_of: dict[int, str] = {}
    for fr in rows:
        for h in fr.hands:
            frames_of[h.id].append(fr.frame)
            side_of[h.id] = h.side
    span = {tid: (fs[0], fs[-1]) for tid, fs in frames_of.items()}
    last: dict[int, tuple[float, Hand]] = {}
    by_frame = {fr.frame: fr for fr in rows}
    out: dict[int, FrameHands] = {}
    for i, t, img in images:
        fr = by_frame.get(i)
        if fr is None:
            continue
        hands = [replace(h, agreement=agree(img, h)) for h in fr.hands]
        present = {h.id for h in hands}
        for tid, (a, b) in span.items():
            if tid in present or not a < i < b or tid not in last:
                continue
            seen_t, prev = last[tid]
            if t - seen_t > params.TRACK_KEEP_S:
                continue
            found = recover(img, i, t, side_of[tid], prev)
            if found is not None:
                hands.append(replace(found, id=tid, side=side_of[tid]))
        for h in hands:
            last[h.id] = (t, h)
        out[i] = FrameHands(i, t, hands)
    return [out.get(fr.frame, fr) for fr in rows]


def merge_wilor(rows: list[FrameHands], wilor: Iterable[FrameHands]) -> list[FrameHands]:
    """WiLoR points replace the matching hand's, keeping its id and voted side. Where that hand was
    missing, the WiLoR hand joins its track if the track still has that id and side."""
    sides = {h.id: h.side for fr in rows for h in fr.hands}
    extra = {fr.frame: fr.hands for fr in wilor}
    out = []
    for fr in rows:
        hands = list(fr.hands)
        for w in extra.get(fr.frame, ()):
            same = [i for i, h in enumerate(hands) if h.side == w.side and
                    tracking.wrist_distance(h, w) <= params.WILOR_MATCH_SIZES * tracking.hand_size(h)]
            if same:
                i = min(same, key=lambda k: tracking.wrist_distance(hands[k], w))
                h = hands[i]
                hands[i] = replace(h, kp2d=w.kp2d, kp3d=w.kp3d, bbox=w.bbox, source="wilor",
                                   score=max(h.score, params.WILOR_SCORE))
            elif sides.get(w.id) == w.side and all(h.id != w.id for h in hands):
                hands.append(w)
        out.append(FrameHands(fr.frame, fr.t, hands))
    return out


def refine(rows: list[FrameHands], n_frames: int, fps: float, width: int, height: int,
           images: Iterable[tuple[int, float, np.ndarray]] = (), wilor: Iterable[FrameHands] = ()) -> list[FrameHands]:
    tracked = tracking.assign_ids(apply_mirror(rows, params.MIRROR), width)
    tracked = tracking.vote_sides(tracking.split_on_side_change(tracked), width)
    tracked = merge_wilor(apply_recovery(tracked, images), wilor)
    tracks: dict[int, list[cleanup.Obs]] = defaultdict(list)
    for fr in tracked:
        for h in fr.hands:
            tracks[h.id].append((fr.frame, fr.t, h))
    done = {tid: cleanup.clean_track(tr, fps, width, height) for tid, tr in tracks.items()}
    return cleanup.assemble(done, n_frames, fps)


def stats(before: list[FrameHands], after: list[FrameHands], n_frames: int, fps: float, step: int) -> dict:
    """Numbers on the same sampled frames for both files."""
    minutes = n_frames / fps / 60
    flags: dict[str, int] = defaultdict(int)
    sources: dict[str, int] = defaultdict(int)
    for fr in after:
        for h in fr.hands:
            sources[h.source] += 1
            for f in h.flags:
                flags[f] += 1
    return {"swaps_per_min": {"baseline": round(swaps_per_min(before, step, minutes), 2),
                              "refined": round(swaps_per_min(after, step, minutes), 2)},
            "jitter_px": {"baseline": round(jitter(before, step), 2), "refined": round(jitter(after, step), 2)},
            "two_hand_frames": {"baseline": pair_order(before, step), "refined": pair_order(after, step)},
            "tracks": len({h.id for fr in after for h in fr.hands}),
            "frames_with_hands": {"baseline": round(sum(bool(f.hands) for f in before) / max(len(before), 1), 4),
                                  "refined": round(sum(bool(f.hands) for f in after) / max(len(after), 1), 4)},
            "sources": dict(sources), "flags": dict(flags)}


def run(clip: str) -> None:
    p = ClipPaths(clip).mkdir()
    meta = read_meta(p.meta) if p.meta.exists() else build_meta(clip)
    fps, n, w, h = meta["fps"], meta["n_frames"], meta["width"], meta["height"]
    step = meta.get("step", config.FRAME_STEP)
    before = list(read_hands(p.hands_baseline))
    images = frames(p.video, step=step) if p.video.exists() else ()
    wilor = list(read_hands(p.wilor)) if p.wilor.exists() else ()
    after = refine(before, n, fps, w, h, images, wilor)
    # Written to a temp name first: the CLI treats an existing output as a finished stage.
    tmp = p.hands.with_suffix(".tmp")
    write_hands(tmp, after)
    tmp.replace(p.hands)
    s = stats(before, after, n, fps, step)
    (p.dir / "hands_stats.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
    print(f"  {clip}: swaps/min {s['swaps_per_min']}, jitter px {s['jitter_px']}, tracks {s['tracks']}")


def compare(clip: str, start_s: float) -> None:
    """Baseline left, refined right, same COMPARE_SECONDS, half size."""
    p = ClipPaths(clip)
    base = {fr.frame: fr for fr in read_hands(p.hands_baseline)}
    final = {fr.frame: fr for fr in read_hands(p.hands)}
    cap = cv2.VideoCapture(str(p.video))
    fps, w, h = cap.get(cv2.CAP_PROP_FPS) or 30.0, int(cap.get(3)), int(cap.get(4))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(start_s * fps))
    i = int(start_s * fps)
    path = p.dir / "compare_baseline_refined.mp4"
    half = (w // 4 * 2, h // 4 * 2)
    last = None
    with H264Writer(path, fps, (half[0] * 2, half[1])) as out:
        for _ in range(int(COMPARE_SECONDS * fps)):
            ok, img = cap.read()
            if not ok:
                break
            last = base.get(i, last)
            left, right = img.copy(), img
            draw_hands(left, last.hands if last else [])
            draw_hands(right, final[i].hands if i in final else [])
            cv2.putText(left, "baseline", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3)
            cv2.putText(right, "refined", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3)
            out.write(np.hstack([cv2.resize(left, half), cv2.resize(right, half)]))
            i += 1
    cap.release()
    print(f"  wrote {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="egovision.hands.refine")
    ap.add_argument("--clip", required=True)
    ap.add_argument("--preview", action="store_true", help="also write preview_refined.mp4")
    ap.add_argument("--compare", type=float, metavar="START_S", help="write a 10 s baseline vs refined video")
    ap.add_argument("--force", action="store_true", help="re-run even if hands.jsonl exists")
    a = ap.parse_args()
    paths = ClipPaths(a.clip)
    if a.force or not paths.hands.exists():
        run(a.clip)
    if a.preview:
        write_preview(a.clip, paths.hands, paths.dir / "preview_refined.mp4")
    if a.compare is not None:
        compare(a.clip, a.compare)
