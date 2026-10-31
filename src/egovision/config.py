"""Paths only. Module thresholds live in each module's own `params.py` (avoids edit conflicts)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("EGO_DATA", ROOT / "data" / "egohack-data"))
CLIPS_DIR = DATA_DIR / "clips_480p"          # laptop path; set EGO_CLIPS for full-res
CLIPS_DIR = Path(os.environ.get("EGO_CLIPS", CLIPS_DIR))
FIXTURE_DIR = ROOT / "data" / "fixture"      # synthetic clip, git-ignored
OUTPUTS = Path(os.environ.get("EGO_OUTPUTS", ROOT / "outputs"))
EXPORTS = ROOT / "exports"
GEMINI_CACHE = ROOT / "gemini_cache"
EVAL_LABELS = ROOT / "eval" / "labels"
INDEX_DB = OUTPUTS / "index.db"
REFERENCES = OUTPUTS / "references"

FRAME_STEP = int(os.environ.get("EGO_STEP", 2))
PIPELINE_VERSION = "0.1.0"


def video_path(clip: str) -> Path:
    """Real clips live in CLIPS_DIR; synthetic ones (name starts with 'fixture') in FIXTURE_DIR."""
    base = FIXTURE_DIR if clip.startswith("fixture") else CLIPS_DIR
    return base / f"{clip}.mp4"


def all_clips() -> list[str]:
    return sorted(p.stem for p in CLIPS_DIR.glob("*.mp4"))
