"""G3 · owner: Gunagye. Rebuild outputs/index.db from per-clip files (data-schema.md §3).

`python -m egovision index` drops and rebuilds everything except `products` (exports and modules
registered by `register_product`), which survives rebuilds.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from egovision import config
from egovision.schema import (ALERT_COLS, CONTACT_COLS, QUALITY_COLS, STEP_COLS, ClipPaths, read_csv,
                              read_hands, read_meta)

DDL = """
CREATE TABLE IF NOT EXISTS clips (
  clip TEXT PRIMARY KEY, factory TEXT, seq_in_factory INT, video TEXT,
  fps REAL, width INT, height INT, n_frames INT, duration_s REAL,
  is_demo INT, green_share REAL, yellow_share REAL, red_share REAL,
  hands_found_share REAL, processed_at TEXT, pipeline_version TEXT);
CREATE TABLE IF NOT EXISTS segments (
  clip TEXT REFERENCES clips, t_start REAL, t_end REAL, light TEXT,
  reasons TEXT, blur REAL, brightness REAL, hands_visible REAL,
  edge_cut REAL, agreement REAL, frozen INT);
CREATE TABLE IF NOT EXISTS frame_summary (
  clip TEXT, frame INT, t REAL, n_hands INT,
  left_score REAL, right_score REAL, sources TEXT, flags TEXT,
  PRIMARY KEY (clip, frame));
CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY, clip TEXT, t_start REAL, t_end REAL,
  hand TEXT, state TEXT, object_name TEXT, confidence REAL, grip TEXT);
CREATE TABLE IF NOT EXISTS steps (id INTEGER PRIMARY KEY, clip TEXT, step_idx INT, start_s REAL,
  end_s REAL, verb TEXT, object TEXT, hand TEXT, caption TEXT, cycle_idx INT);
CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY, clip TEXT, t_start REAL, t_end REAL,
  kind TEXT, severity TEXT, hand TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, kind TEXT,
  name TEXT, path TEXT, filter_json TEXT, n_items INT, created_at TEXT);
CREATE TABLE IF NOT EXISTS metrics (clip TEXT, key TEXT, value REAL, PRIMARY KEY (clip, key));
CREATE INDEX IF NOT EXISTS idx_seg ON segments(clip, t_start);
CREATE INDEX IF NOT EXISTS idx_alert ON alerts(clip, kind);
"""
PRODUCT_COLS = ["kind", "name", "path", "filter_json", "n_items", "created_at"]


def _connect() -> sqlite3.Connection:
    config.INDEX_DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(config.INDEX_DB)
    db.executescript(DDL)
    return db


def _insert(db: sqlite3.Connection, table: str, cols: list[str], rows: list[dict]) -> None:
    """SQLite column affinity turns the CSV strings into REAL/INT where the DDL says so."""
    if rows:
        db.executemany(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                       [[r[c] for c in cols] for r in rows])


def _seq(clip: str) -> int | None:
    tail = clip.replace("_", "-").rsplit("-", 1)[-1]
    return int(tail) if tail.isdigit() else None


def _shares(quality: list[dict]) -> dict[str, float | None]:
    total = sum(float(r["t_end"]) - float(r["t_start"]) for r in quality)
    if not total:
        return {light: None for light in ("green", "yellow", "red")}
    return {light: sum(float(r["t_end"]) - float(r["t_start"]) for r in quality if r["light"] == light) / total
            for light in ("green", "yellow", "red")}


def _frame_rows(clip: str, path: Path) -> list[dict]:
    rows = []
    for fr in read_hands(path):
        score = {s: max((h.score for h in fr.hands if h.side == s), default=None) for s in ("left", "right")}
        rows.append({"clip": clip, "frame": fr.frame, "t": fr.t, "n_hands": len(fr.hands),
                     "left_score": score["left"], "right_score": score["right"],
                     "sources": ",".join(sorted({h.source for h in fr.hands})),
                     "flags": ",".join(sorted({f for h in fr.hands for f in h.flags}))})
    return rows


def _flat(d: dict, prefix: str = "") -> dict[str, float]:
    """Nested metrics.json → {"ours.pck_0.2": 0.81, "per_light.red.ours.pck_0.2": 0.4, ...}; numbers only."""
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out |= _flat(v, key + ".")
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            out[key] = float(v)
    return out


def _index_clip(db: sqlite3.Connection, p: ClipPaths) -> None:
    meta = read_meta(p.meta)
    clip = p.clip
    quality = read_csv(p.quality, QUALITY_COLS) if p.quality.exists() else []
    frames = _frame_rows(clip, p.hands_input()) if p.hands_input().exists() else []
    shares = _shares(quality)
    mtime = max(f.stat().st_mtime for f in p.dir.iterdir())
    _insert(db, "clips", ["clip", "factory", "seq_in_factory", "video", "fps", "width", "height", "n_frames",
                          "duration_s", "is_demo", "green_share", "yellow_share", "red_share",
                          "hands_found_share", "processed_at", "pipeline_version"],
            [{**meta, "seq_in_factory": _seq(clip), "duration_s": meta["n_frames"] / meta["fps"],
              "is_demo": int(bool(meta.get("is_demo"))), "green_share": shares["green"],
              "yellow_share": shares["yellow"], "red_share": shares["red"],
              "hands_found_share": sum(r["n_hands"] > 0 for r in frames) / len(frames) if frames else None,
              "processed_at": datetime.fromtimestamp(mtime).isoformat(timespec="seconds")}])
    _insert(db, "segments", QUALITY_COLS, quality)
    _insert(db, "frame_summary", list(frames[0]) if frames else [], frames)
    if p.contacts.exists():
        _insert(db, "contacts", [c for c in CONTACT_COLS if c != "object_id"], read_csv(p.contacts, CONTACT_COLS))
    if p.steps.exists():
        _insert(db, "steps", [c for c in STEP_COLS if c != "source"], read_csv(p.steps, STEP_COLS))
    for path in (p.alerts_steps, p.alerts_safety):
        if path.exists():
            _insert(db, "alerts", ALERT_COLS, read_csv(path, ALERT_COLS))
    if p.metrics.exists():
        m = json.loads(p.metrics.read_text(encoding="utf-8"))
        _insert(db, "metrics", ["clip", "key", "value"],
                [{"clip": clip, "key": k, "value": v} for k, v in _flat(m).items()])


def build() -> None:
    """Drop and rebuild the index from every `outputs/<clip>/` with a meta.json; keep `products`."""
    products = []
    if config.INDEX_DB.exists():
        with closing(_connect()) as db:
            products = [dict(zip(PRODUCT_COLS, r)) for r in db.execute(f"SELECT {', '.join(PRODUCT_COLS)} FROM products")]
        config.INDEX_DB.unlink()
    clips = sorted(d.name for d in config.OUTPUTS.iterdir()
                   if d.is_dir() and d.name != config.REFERENCES.name and (d / "meta.json").exists())
    real = [c for c in clips if not c.startswith("fixture")]
    clips = real or clips       # synthetic fixtures only fill an index that has no real clips (tests, empty laptop)
    db = _connect()
    try:
        with db:
            for clip in clips:
                _index_clip(db, ClipPaths(clip))
            _insert(db, "products", PRODUCT_COLS, products)
    finally:
        db.close()
    print(f"{config.INDEX_DB}: {len(clips)} clips, {len(products)} products")


def register_product(kind: str, name: str, path: str | Path, filter: dict, n: int) -> None:
    """Record an export (`dataset`), Work Module (`module`) or `benchmark` so the app lists it."""
    db = _connect()
    try:
        with db:
            _insert(db, "products", PRODUCT_COLS, [{"kind": kind, "name": name, "path": str(path),
                                                    "filter_json": json.dumps(filter), "n_items": n,
                                                    "created_at": datetime.now().isoformat(timespec="seconds")}])
    finally:
        db.close()
