"""Pipeline stage registry. Order matters. Entry points are imported lazily so one module's
missing dependency never breaks another person's stage. Owner: Gunagye."""
from __future__ import annotations

import importlib
from dataclasses import dataclass


class NotBuilt(Exception):
    """Raised by a stub stage. The CLI skips it with a message instead of crashing."""


@dataclass(frozen=True)
class Stage:
    name: str
    entry: str      # "module:function", function signature: run(clip: str) -> None
    output: str     # attribute of schema.ClipPaths that marks the stage as done
    owner: str
    task: str

    def load(self):
        mod, fn = self.entry.split(":")
        return getattr(importlib.import_module(mod), fn)


STAGES: list[Stage] = [
    Stage("hands_baseline", "egovision.hands.baseline:run", "hands_baseline", "Abhijay", "A1"),
    Stage("hands", "egovision.hands.refine:run", "hands", "Abhijay", "A2-A4"),
    Stage("quality", "egovision.quality.light:run", "quality", "Bhavyam", "B3"),
    Stage("contact", "egovision.contact.run:run", "contacts", "Gunagye", "G2"),
    Stage("steps", "egovision.steps.caption:run", "steps", "Shefali", "S2"),
    Stage("order", "egovision.steps.order:run", "alerts_steps", "Shefali", "S3"),
    Stage("safety", "egovision.safety.run:run", "alerts_safety", "Bhavyam", "B5"),
    Stage("render", "egovision.products.render:run", "render", "Gunagye", "G6"),
]
BY_NAME = {s.name: s for s in STAGES}
