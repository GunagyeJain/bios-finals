"""S3 · owner: Shefali. Task: docs/06-plan/tasks/shefali.md

Reference cycle per factory + alignment.
In: steps.csv of every clip in the same factory  Out: alerts_steps.csv (schema.ALERT_COLS).
"""
from egovision.stages import NotBuilt


def run(clip: str) -> None:
    raise NotBuilt("S3")
