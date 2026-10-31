"""Shared data contract. Formats: docs/05-solution/data-schema.md. Owner: Gunagye; announce edits in chat."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

from . import config

N_KP = 21
TIPS = (4, 8, 12, 16, 20)
SIDES = ("left", "right")
HAND_SOURCES = ("mediapipe", "roi", "rtmlib", "wilor", "interp")
HAND_FLAGS = ("low_conf", "disagree", "sanity", "edge")

QUALITY_COLS = ["clip", "t_start", "t_end", "light", "reasons", "blur", "brightness",
                "hands_visible", "edge_cut", "agreement", "frozen"]
CONTACT_COLS = ["clip", "t_start", "t_end", "hand", "state", "object_name", "object_id",
                "confidence", "grip"]
STEP_COLS = ["clip", "step_idx", "start_s", "end_s", "verb", "object", "hand", "caption",
             "source", "cycle_idx"]
ALERT_COLS = ["clip", "t_start", "t_end", "kind", "severity", "hand", "detail"]
LIGHTS = ("green", "yellow", "red")
CONTACT_STATES = ("none", "portable", "fixed")
VERBS = ("pick", "place", "fasten", "insert", "press", "cut", "inspect", "adjust", "carry", "other")


@dataclass
class Hand:
    side: str
    bbox: list[float]
    score: float
    kp2d: list[list[float]]
    kp3d: list[list[float]] | None = None
    id: int = -1
    source: str = "mediapipe"
    agreement: float | None = None
    flags: list[str] = field(default_factory=list)

    def __post_init__(self):
        assert self.side in SIDES, self.side
        assert len(self.kp2d) == N_KP, len(self.kp2d)
        assert self.source in HAND_SOURCES, self.source


@dataclass
class FrameHands:
    frame: int
    t: float
    hands: list[Hand] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps({"frame": self.frame, "t": round(self.t, 4),
                           "hands": [asdict(h) for h in self.hands]})

    @staticmethod
    def from_dict(d: dict) -> "FrameHands":
        return FrameHands(d["frame"], d["t"], [Hand(**h) for h in d.get("hands", [])])


class ClipPaths:
    """Every file path for one clip. Use these, never build paths by hand."""

    def __init__(self, clip: str):
        self.clip = clip
        self.dir = config.OUTPUTS / clip
        self.video = config.video_path(clip)
        self.meta = self.dir / "meta.json"
        self.hands_baseline = self.dir / "hands_baseline.jsonl"
        self.hands = self.dir / "hands.jsonl"
        self.wilor = self.dir / "wilor.jsonl"
        self.quality = self.dir / "quality.csv"
        self.objects = self.dir / "objects.jsonl"
        self.contacts = self.dir / "contacts.csv"
        self.steps = self.dir / "steps.csv"
        self.alerts_steps = self.dir / "alerts_steps.csv"
        self.alerts_safety = self.dir / "alerts_safety.csv"
        self.render = self.dir / "render.mp4"
        self.render_baseline = self.dir / "render_baseline.mp4"
        self.metrics = self.dir / "metrics.json"

    def mkdir(self) -> "ClipPaths":
        self.dir.mkdir(parents=True, exist_ok=True)
        return self

    def hands_input(self) -> Path:
        """Best hand file available: final if built, else baseline. Lets downstream work start early."""
        return self.hands if self.hands.exists() else self.hands_baseline


# ---------- readers / writers ----------
def write_hands(path: Path, frames: Iterable[FrameHands]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for fr in frames:
            f.write(fr.to_json() + "\n")


def read_hands(path: Path) -> Iterator[FrameHands]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield FrameHands.from_dict(json.loads(line))


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def read_jsonl(path: Path) -> Iterator[dict]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def write_csv(path: Path, cols: list[str], rows: Iterable[dict]) -> None:
    """Writes exactly `cols`; a missing or extra key is an error (keeps the contract honest)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="raise")
        w.writeheader()
        for r in rows:
            missing = set(cols) - set(r)
            if missing:
                raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
            w.writerow(r)


def read_csv(path: Path, cols: list[str]) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        if r.fieldnames != cols:
            raise ValueError(f"{path.name}: columns {r.fieldnames} != contract {cols}")
        return list(r)


def write_meta(path: Path, meta: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def read_meta(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
