"""S2 · owner: Shefali. Task: docs/06-plan/tasks/shefali.md

Gemini captions on grab/release windows, cached in gemini_cache/.
In: video, contacts.csv  Out: steps.csv (schema.STEP_COLS).

Windows run between consecutive grab/release events in contacts.csv (shorter than MIN_WIN_S joins its
neighbour, longer than MAX_WIN_S is split); no contacts.csv → fixed FALLBACK_WIN_S windows. Each window is
cut to a small 480p H.264 clip with faces blurred (quality.redact, hands kept) and sent inline with the
request, so nothing is uploaded to the Files API and there is nothing to delete afterwards. Answers are
cached per (clip, t0, t1, model, prompt); a cached window never calls the API again. A failed or skipped
call keeps the row with `source="contact"`, `verb="other"` and the object/hand from contacts.
`cycle_idx` stays empty here: the order check (S3) owns cycles.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import time
from pathlib import Path

from egovision import config
from egovision.schema import CONTACT_COLS, STEP_COLS, VERBS, ClipPaths, read_csv, read_hands, write_csv

from . import params as P

HANDS = ("left", "right", "both", "none")
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {"verb": {"type": "STRING", "enum": list(VERBS)}, "object": {"type": "STRING"},
                   "hand": {"type": "STRING", "enum": list(HANDS)}, "caption": {"type": "STRING"}},
    "required": ["verb", "object", "hand", "caption"],
}


# ---------- windows ----------
def _merge_short(bounds: list[float]) -> list[float]:
    """Drop inner boundaries that would leave a window shorter than MIN_WIN_S."""
    out = [bounds[0]]
    for b in bounds[1:]:
        if b - out[-1] < P.MIN_WIN_S:
            if len(out) > 1:
                out[-1] = b                   # stretch the previous window
            continue
        out.append(b)
    return out


def _split_long(t0: float, t1: float) -> list[tuple[float, float]]:
    k = max(1, int(-(-(t1 - t0) // P.MAX_WIN_S)))
    step = (t1 - t0) / k
    return [(round(t0 + i * step, 3), round(t0 + (i + 1) * step, 3)) for i in range(k)]


def event_windows(contacts: list[dict]) -> list[tuple[float, float]]:
    """Windows between consecutive grab/release events (every contact start and end)."""
    events = sorted({float(c[k]) for c in contacts if c["state"] != "none" for k in ("t_start", "t_end")})
    if len(events) < 2:
        return []
    bounds = _merge_short(events)
    return [w for a, b in zip(bounds, bounds[1:]) for w in _split_long(a, b)]


def fixed_windows(duration: float) -> list[tuple[float, float]]:
    n = max(1, round(duration / P.FALLBACK_WIN_S))
    step = duration / n
    return [(round(i * step, 3), round((i + 1) * step, 3)) for i in range(n)]


def contact_hint(contacts: list[dict], t0: float, t1: float) -> dict:
    """Hand and object of the contact overlapping the window most, or empty strings."""
    best, best_overlap = None, 0.0
    for c in contacts:
        if c["state"] == "none":
            continue
        overlap = min(t1, float(c["t_end"])) - max(t0, float(c["t_start"]))
        if overlap > best_overlap:
            best, best_overlap = c, overlap
    return {"hand": best["hand"], "object": best["object_name"]} if best else {"hand": "", "object": ""}


def prompt_for(hint: dict) -> str:
    extra = (f"Hint from the hand tracker (may be wrong): the {hint['hand']} hand touches a {hint['object']}."
             if hint["object"] else "")
    return P.PROMPT.format(verbs=", ".join(VERBS), hint=extra).strip()


# ---------- cache ----------
def cache_path(clip: str, t0: float, t1: float, prompt: str) -> Path:
    key = hashlib.sha1(f"{clip}|{t0:.3f}|{t1:.3f}|{P.MODEL}|{prompt}".encode()).hexdigest()
    return config.GEMINI_CACHE / f"{key}.json"


# ---------- video ----------
def cut_window(clip: str, t0: float, t1: float, path: Path) -> None:
    """Window [t0, t1) as a small H.264 clip: CLIP_HEIGHT, CLIP_FPS, faces blurred, hands kept sharp."""
    import cv2

    from egovision.io.video import H264Writer
    from egovision.quality.redact import redact_frame

    p = ClipPaths(clip)
    hands = {f.frame: [h.bbox for h in f.hands] for f in read_hands(p.hands_input())} \
        if p.hands_input().exists() else {}
    cap = cv2.VideoCapture(str(p.video))
    if not cap.isOpened():
        raise FileNotFoundError(p.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    every = max(1, round(fps / P.CLIP_FPS))
    first, last = int(t0 * fps), int(t1 * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    writer, keep = None, []
    try:
        for i in range(first, last):
            ok, img = cap.read()
            if not ok:
                break
            keep = hands.get(i, keep)                   # baseline hands exist on every step-th frame only
            if (i - first) % every:
                continue
            s = P.CLIP_HEIGHT / img.shape[0]
            size = (int(img.shape[1] * s) // 2 * 2, P.CLIP_HEIGHT)
            small = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
            small = redact_frame(small, [[v * s for v in b] for b in keep])
            if writer is None:
                writer = H264Writer(path, fps / every, size, crf=P.CLIP_CRF)
            writer.write(small)
    finally:
        cap.release()
        if writer:
            writer.close()
    if writer is None:
        raise ValueError(f"{clip}: no frames in {t0:.1f}-{t1:.1f} s")


# ---------- Gemini ----------
def make_client():
    """Gemini client from GEMINI_API_KEY, or None (every row then falls back to contacts)."""
    import os
    if not os.environ.get("GEMINI_API_KEY"):
        return None
    from google import genai
    return genai.Client()


_exhausted: set[str] = set()                        # models whose daily quota ran out in this process
_overloaded: set[str] = set()                       # models that kept answering 5xx: tried last from then on


def _code(err: Exception) -> int | None:
    return getattr(err, "code", None) or getattr(err, "status_code", None)


def _daily_quota(err: Exception) -> bool:
    """429 because the model's requests-per-day ran out (retry in hours), not a per-minute limit."""
    text = str(err)
    return _code(err) == 429 and ("PerDay" in text or "per day" in text)


def ask_gemini(client, video: bytes, prompt: str, sleep=time.sleep) -> dict:
    """One answer. Free-tier quotas are per model and small (20 requests a day on Flash), and new models
    are often overloaded (503), so each model gets a few tries with backoff on per-minute 429 and 5xx,
    then the next model in P.MODELS is used; a model out of daily quota is skipped for the rest of the run,
    one that stayed overloaded is tried last until it answers again.
    Raises the last error when every model fails."""
    from google.genai import types
    cfg = types.GenerateContentConfig(response_mime_type="application/json",
                                      response_schema=RESPONSE_SCHEMA, temperature=0)
    parts = [types.Part.from_bytes(data=video, mime_type="video/mp4"), prompt]
    last: Exception | None = None
    usable = [m for m in P.MODELS if m not in _exhausted]
    for model in [m for m in usable if m not in _overloaded] + [m for m in usable if m in _overloaded]:
        for attempt in range(P.MAX_RETRIES):
            try:
                resp = client.models.generate_content(model=model, contents=parts, config=cfg)
                _overloaded.discard(model)
                return {**clean_answer(json.loads(resp.text)), "model": model}
            except Exception as err:                    # noqa: BLE001 (SDK error types vary by version)
                last = err
                if _daily_quota(err):
                    _exhausted.add(model)
                    print(f"  {model}: daily free quota used up, next model")
                    break
                if _code(err) not in (429, 500, 502, 503, 504) or attempt == P.MAX_RETRIES - 1:
                    if _code(err) in (500, 502, 503, 504):
                        _overloaded.add(model)
                    print(f"  {model}: {_code(err) or type(err).__name__}, next model")
                    break
                wait = P.BACKOFF_S * 2 ** attempt
                print(f"  {model}: {_code(err)}, retry in {wait:.0f} s")
                sleep(wait)
    raise last or RuntimeError("every Gemini model is out of daily quota")


def clean_answer(a: dict) -> dict:
    verb = str(a.get("verb", "")).strip().lower()
    hand = str(a.get("hand", "")).strip().lower()
    return {"verb": verb if verb in VERBS else "other",
            "object": " ".join(str(a.get("object", "")).lower().split())[:40],
            "hand": hand if hand in HANDS else "none",
            "caption": " ".join(str(a.get("caption", "")).split())[:200]}


# ---------- stage ----------
def step_row(clip: str, k: int, t0: float, t1: float, answer: dict | None, hint: dict) -> dict:
    if answer is None:
        return {"clip": clip, "step_idx": k, "start_s": t0, "end_s": t1, "verb": "other",
                "object": hint["object"], "hand": hint["hand"], "caption": "", "source": "contact",
                "cycle_idx": ""}
    hand = "" if answer["hand"] == "none" else answer["hand"]
    return {"clip": clip, "step_idx": k, "start_s": t0, "end_s": t1, "verb": answer["verb"],
            "object": answer["object"], "hand": hand, "caption": answer["caption"], "source": "gemini",
            "cycle_idx": ""}


def windows_for(clip: str) -> tuple[list[tuple[float, float]], list[dict]]:
    import cv2
    p = ClipPaths(clip)
    contacts = read_csv(p.contacts, CONTACT_COLS) if p.contacts.exists() else []
    wins = event_windows(contacts)
    if not wins:
        cap = cv2.VideoCapture(str(p.video))
        duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / (cap.get(cv2.CAP_PROP_FPS) or 30.0)
        cap.release()
        wins = fixed_windows(duration)
        print(f"{clip}: no grab/release events, using {len(wins)} fixed {P.FALLBACK_WIN_S:.0f} s windows")
    return wins, contacts


def run(clip: str, client=None, sleep=time.sleep) -> dict:
    """Writes steps.csv. Returns counts (windows, cached, calls, failed) for the checkpoint report."""
    p = ClipPaths(clip).mkdir()
    client = client if client is not None else make_client()
    if client is None:
        print("GEMINI_API_KEY not set: steps fall back to contacts (source=contact)")
    wins, contacts = windows_for(clip)
    stats = {"windows": len(wins), "cached": 0, "calls": 0, "failed": 0}
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for k, (t0, t1) in enumerate(wins):
            hint = contact_hint(contacts, t0, t1)
            prompt = prompt_for(hint)
            cached = cache_path(clip, t0, t1, prompt)
            answer = None
            if cached.exists():
                answer = json.loads(cached.read_text(encoding="utf-8"))
                stats["cached"] += 1
            elif client is not None and stats["calls"] < P.MAX_CALLS_PER_RUN:
                stats["calls"] += 1
                try:
                    video = Path(tmp) / "window.mp4"
                    cut_window(clip, t0, t1, video)
                    answer = ask_gemini(client, video.read_bytes(), prompt, sleep)
                    cached.parent.mkdir(parents=True, exist_ok=True)
                    cached.write_text(json.dumps(answer), encoding="utf-8")
                except Exception as err:                # noqa: BLE001 (keep the stage going; row falls back)
                    stats["failed"] += 1
                    print(f"  {t0:.1f}-{t1:.1f} s: gemini failed ({type(err).__name__}: {str(err)[:120]})")
            rows.append(step_row(clip, k, t0, t1, answer, hint))
            if answer:
                print(f"  {t0:6.1f}-{t1:6.1f} s  {answer['verb']:8s} {answer['object']:20s} {answer['hand']:6s} "
                      f"{answer.get('model', '')}")
    write_csv(p.steps, STEP_COLS, rows)
    print(f"{clip}: {len(rows)} steps → {p.steps}  (models {', '.join(P.MODELS)}; {stats['calls']} windows asked, "
          f"{stats['cached']} cached, {stats['failed']} failed)")
    return stats
