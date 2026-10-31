"""G2 · owner: Gunagye. Task: docs/06-plan/tasks/gunagye.md

YOLOE objects + fingertip contact rule with hysteresis.
In: video, hands_input()  Out: objects.jsonl, contacts.csv (schema.CONTACT_COLS).
"""
from __future__ import annotations

import contextlib

import cv2

from egovision import config
from egovision.io.frames import frames
from egovision.schema import CONTACT_COLS, SIDES, ClipPaths, read_hands, read_meta, write_csv, write_jsonl
from egovision.stages import NotBuilt

from . import params as P
from . import rule

MODELS_DIR = config.ROOT / "models"


def load_model(names: list[str]):
    """YOLOE with text prompts. Runs inside models/ so the weights and the text encoder that
    ultralytics downloads on first use land there (git-ignored), not in the repo root."""
    from ultralytics import YOLOE

    MODELS_DIR.mkdir(exist_ok=True)
    with contextlib.chdir(MODELS_DIR):
        model = YOLOE(P.MODEL)
        model.set_classes(names, model.get_text_pe(names))
    return model


def detect(model, img, kind: dict[str, str]) -> list[dict]:
    r = model.predict(img, conf=P.CONF, imgsz=P.IMGSZ, agnostic_nms=True, verbose=False)[0]
    out = []
    for box, c, s in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist(), r.boxes.conf.tolist()):
        name = r.names[int(c)]
        out.append({"name": name, "kind": kind[name], "bbox": [round(v, 1) for v in box],
                    "score": round(float(s), 3)})
    return out


def _best_by_side(hands) -> dict:
    by_side = {}
    for h in hands:
        if h.side not in by_side or h.score > by_side[h.side].score:
            by_side[h.side] = h
    return by_side


def run(clip: str) -> None:
    p = ClipPaths(clip)
    if not p.hands_input().exists():
        raise NotBuilt(f"needs {p.hands_input().name} (A1) first")
    step = read_meta(p.meta).get("step", config.FRAME_STEP) if p.meta.exists() else config.FRAME_STEP
    hands = {fr.frame: fr.hands for fr in read_hands(p.hands_input())}
    kind = {n: "portable" for n in P.PORTABLE} | {n: "fixed" for n in P.FIXED}
    model = load_model(list(kind))

    objs, next_id, prev_gray = [], 0, None
    obj_rows, seen = [], {}
    samples = {s: [] for s in SIDES}
    for k, (i, t, img) in enumerate(frames(p.video, step=step)):
        frame_hands = hands.get(i, [])
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if k % P.DETECT_EVERY == 0:
            objs, next_id = rule.assign_ids(objs, detect(model, img, kind), next_id)
            boxes = [o["bbox"] for o in objs]
            flags = (rule.moving(prev_gray, gray, boxes, ignore=[h.bbox for h in frame_hands])
                     if prev_gray is not None else [False] * len(objs))
            objs = [{**o, "moving": f} for o, f in zip(objs, flags)]
            obj_rows.append({"frame": i, "t": round(t, 4), "objects": objs})
        prev_gray = gray
        by_side = _best_by_side(frame_hands)
        for side in SIDES:
            o, n = rule.pick_object(by_side[side].kp2d, objs) if side in by_side else (None, 0)
            if o is not None:
                seen[o["id"]] = o
            samples[side].append((t, o["id"] if o else None, o["score"] * min(1.0, n / 3) if o else 0.0))

    write_jsonl(p.objects, obj_rows)
    rows = [{"clip": clip, "t_start": round(a, 3), "t_end": round(b, 3), "hand": side,
             "state": seen[oid]["kind"], "object_name": seen[oid]["name"], "object_id": oid,
             "confidence": round(conf, 3), "grip": "unsure"}
            for side in SIDES for a, b, oid, conf in rule.hysteresis(samples[side])]
    write_csv(p.contacts, CONTACT_COLS, sorted(rows, key=lambda r: (r["t_start"], r["hand"])))
