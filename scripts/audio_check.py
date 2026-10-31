"""One-off evaluation (decisions.md, 31 Oct): does loudness rise at contact grabs/releases more than at random
moments? Audio is streamed from the clip into memory and never written to disk; only numbers are kept.

python scripts/audio_check.py MTL-SKL00089-005 [...]   → prints a table, writes outputs/audio_check/results.json
Contacts come from outputs/audio_check/<clip>.contacts.csv if present, else outputs/<clip>/contacts.csv.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from egovision import config  # noqa: E402

RATE, WIN = 16000, 0.05                    # 50 ms RMS windows
AFTER, BEFORE = (-0.2, 0.3), (-1.5, -0.5)  # rise = max dB in AFTER window - median dB in BEFORE window
N_RANDOM, GAP, N_BOOT, SEED = 2000, 1.0, 1000, 7
AUC_MIN, LOW_MIN, CLIPS_MIN = 0.65, 0.55, 2


def loudness_db(clip: str) -> np.ndarray:
    """dB per 50 ms window of the clip's mono audio, read through an ffmpeg pipe (no file written)."""
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(config.video_path(clip)), "-vn", "-ac", "1",
           "-ar", str(RATE), "-f", "s16le", "-"]
    pcm = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.int16).astype(np.float32)
    n = int(RATE * WIN)
    frames = pcm[: len(pcm) // n * n].reshape(-1, n)
    return 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1.0)


def rise(db: np.ndarray, t: float) -> float | None:
    a0, a1 = (int((t + x) / WIN) for x in AFTER)
    b0, b1 = (int((t + x) / WIN) for x in BEFORE)
    if b0 < 0 or a1 >= len(db):
        return None
    return float(db[a0:a1 + 1].max() - np.median(db[b0:b1 + 1]))


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    """P(contact rise > random rise), ties count half (Mann-Whitney U / n1 n2)."""
    ranks = pd.Series(np.concatenate([pos, neg])).rank().to_numpy()
    return float((ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def check(clip: str, rng: np.random.Generator) -> dict:
    snap = ROOT / "outputs" / "audio_check" / f"{clip}.contacts.csv"
    contacts = pd.read_csv(snap if snap.exists() else ROOT / "outputs" / clip / "contacts.csv")
    db = loudness_db(clip)
    duration = len(db) * WIN
    moments = np.concatenate([contacts["t_start"], contacts["t_end"]])
    pos = np.array([r for r in (rise(db, t) for t in moments) if r is not None])
    cand = rng.uniform(2.0, duration - 1.0, N_RANDOM * 3)
    cand = cand[np.min(np.abs(cand[:, None] - moments[None, :]), axis=1) >= GAP][:N_RANDOM]
    neg = np.array([r for r in (rise(db, t) for t in cand) if r is not None])
    boot = [auc(rng.choice(pos, len(pos)), rng.choice(neg, len(neg))) for _ in range(N_BOOT)]
    return {"clip": clip, "contact_moments": len(pos), "random_moments": len(neg), "auc": round(auc(pos, neg), 3),
            "ci_low": round(float(np.percentile(boot, 2.5)), 3), "ci_high": round(float(np.percentile(boot, 97.5)), 3),
            "median_rise_contact_db": round(float(np.median(pos)), 2),
            "median_rise_random_db": round(float(np.median(neg)), 2)}


def main(clips: list[str]) -> int:
    rng = np.random.default_rng(SEED)
    rows = [check(c, rng) for c in clips]
    passed = [r["clip"] for r in rows if r["auc"] >= AUC_MIN and r["ci_low"] >= LOW_MIN]
    verdict = "keep: propose the export tag" if len(passed) >= CLIPS_MIN else "drop: no better than random"
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"rule: AUC >= {AUC_MIN} and CI low >= {LOW_MIN} on >= {CLIPS_MIN} clips · passed {len(passed)} → {verdict}")
    out = ROOT / "outputs" / "audio_check" / "results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"rows": rows, "passed": passed, "verdict": verdict}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
