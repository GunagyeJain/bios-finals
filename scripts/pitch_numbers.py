"""Writes docs/07-pitch/numbers.md from outputs/*/metrics.json and the index, so no slide number is typed by hand.
python scripts/pitch_numbers.py   (run after `python -m egovision.eval.metrics --all` and `python -m egovision index`)"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from egovision import config  # noqa: E402
from egovision.index import query  # noqa: E402

KEYS = [("detection_recall", "Hands found", True), ("detection_precision", "Detections that are real hands", True),
        ("lr_accuracy", "Left/right correct", True), ("pck_0.2_with_misses", "Keypoints within 20 % (misses count)", True),
        ("pck_0.2", "Keypoints within 20 % (found hands only)", True), ("swaps_per_min", "Side swaps per minute", False),
        ("jitter_px", "Jitter (px)", False)]


def fmt(v, share: bool) -> str:
    return "–" if v is None else (f"{100 * v:.1f} %" if share else f"{v:.1f}")


def main() -> int:
    ms = [json.loads(p.read_text(encoding="utf-8")) | {"clip": p.parent.name}
          for p in sorted(config.OUTPUTS.glob("*/metrics.json")) if not p.parent.name.startswith("fixture")]
    w = lambda side, k: (lambda vals: sum(v * n for v, n in vals) / sum(n for _, n in vals) if vals else None)(
        [(m[side][k], m.get("n_labels", 1)) for m in ms if isinstance(m.get(side, {}).get(k), (int, float))])
    lib = query.library()
    lib = lib[~lib["clip"].str.startswith("fixture")]
    k = query.kpis(lib)
    fit = query.robot_fit(query.sql("SELECT grip FROM contacts WHERE clip NOT LIKE 'fixture%'"))
    lines = [f"# Numbers for the slides", "",
             f"_Generated {datetime.now():%Y-%m-%d %H:%M} by `scripts/pitch_numbers.py` from metrics.json and the index. "
             "Do not type numbers by hand; re-run the script._", "",
             f"## Hand tracking: {sum(m.get('n_labels', 0) for m in ms)} hand-labelled frames, {len(ms)} clips", "",
             "| Metric | Baseline (MediaPipe) | Ours |", "|---|---:|---:|",
             *[f"| {lab} | {fmt(w('baseline', key), sh)} | {fmt(w('ours', key), sh)} |" for key, lab, sh in KEYS], "",
             "Per clip:", "",
             "| Clip | Labels | Hands found | Side swaps / min |", "|---|---:|---:|---:|",
             *[f"| {m['clip']} | {m.get('n_labels')} | {fmt(m['baseline'].get('detection_recall'), True)} → "
               f"{fmt(m['ours'].get('detection_recall'), True)} | {fmt(m['baseline'].get('swaps_per_min'), False)} → "
               f"{fmt(m['ours'].get('swaps_per_min'), False)} |" for m in ms], "",
             "## Dataset", "",
             f"- {len(lib)} clips processed, {k['hours']:.1f} h of footage, {lib['factory'].nunique()} factories.",
             f"- Usable (green) share of graded seconds: {fmt(k['green'], True)}.",
             f"- {fit['grabs']:,} grabs: a 2-finger robot can copy {fmt(fit['2f'], True)}, a 5-finger robot "
             f"{fmt(fit['5f'], True)}, {fmt(fit['unsure'], True)} can't tell.", ""]
    out = ROOT / "docs" / "07-pitch" / "numbers.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
