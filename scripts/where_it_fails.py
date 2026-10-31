"""Writes docs/07-pitch/where-it-fails.md from the labels and final hands, so no number is typed by hand.
    python scripts/where_it_fails.py
Needs hands.jsonl for the labelled clips; quality.csv adds fast-head and dark seconds. Times only, no footage."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from egovision import config
from egovision.eval import metrics as M
from egovision.schema import QUALITY_COLS, ClipPaths, read_csv, read_hands, read_meta

OUT = config.ROOT / "docs" / "07-pitch" / "where-it-fails.md"
EDGE_PX = 5.0
MODES = {
    "overlap": ("Hands overlapping or holding each other",
                "Voting and the same-side split keep the two sides apart when both hands are found. A hand hidden behind the "
                "other stays missing: we report it rather than invent it."),
    "edge": ("Hand cut off by the frame edge",
             "Hands touching the edge carry the `edge` flag, and the Data Health light marks stretches with `edge_cut`, "
             "so buyers can filter them out."),
    "gloves": ("Gloves",
               "No glove-specific model: the low detection thresholds are the only help. WiLoR was meant for this and was cut."),
    "dark": ("Dark frames",
             "The Data Health light flags dark seconds, and red seconds are never exported."),
    "fast": ("Fast motion and blur",
             "Gaps up to 5 frames are interpolated and marked `interp`, and two-way smoothing removes lag. "
             "The light flags fast head motion. A heavily blurred hand is often still missed."),
}


@dataclass
class Mode:
    tally: M.Tally = field(default_factory=M.Tally)
    base: M.Tally = field(default_factory=M.Tally)
    examples: dict[str, float] = field(default_factory=dict)


def reasons_at(rows: list[dict], t: float) -> set[str]:
    for r in rows:
        if float(r["t_start"]) <= t < float(r["t_end"]):
            return set(filter(None, r["reasons"].split(";")))
    return set()


def modes_of(hand: dict, tags: list[str], reasons: set[str], width: int, height: int) -> list[str]:
    x1, y1, x2, y2 = hand["bbox"]
    out = []
    if "overlap" in tags:
        out.append("overlap")
    if x1 <= EDGE_PX or y1 <= EDGE_PX or x2 >= width - 1 - EDGE_PX or y2 >= height - 1 - EDGE_PX:
        out.append("edge")
    if "glove" in tags:
        out.append("gloves")
    if "dark" in tags or "dark" in reasons:
        out.append("dark")
    if "blur" in tags or "fast_head" in reasons:
        out.append("fast")
    return out


def failed(hand: dict, pred: list) -> bool:
    pairs = M.match([hand], pred)
    return not pairs or hand["side"] != pred[pairs[0][1]].side or bool((pairs[0][2] > M.PCK_THRESHOLD).any())


def side_split(label_hands: list[dict], ours: list, base: list) -> dict[str, list[int]]:
    """Left/right on our found hands: [correct, total], split by whether the baseline found that hand too."""
    known = {i for i, _, _ in M.match(label_hands, base)}
    out = {"both": [0, 0], "new": [0, 0]}
    for i, j, _ in M.match(label_hands, ours):
        group = out["both" if i in known else "new"]
        group[0] += label_hands[i]["side"] == ours[j].side
        group[1] += 1
    return out


def collect(clips: list[str]) -> tuple[dict[str, Mode], int, M.Tally, dict[str, list[int]]]:
    modes: dict[str, Mode] = defaultdict(Mode)
    total, overall = 0, M.Tally()
    sides = {"both": [0, 0], "new": [0, 0]}
    for clip in clips:
        p = ClipPaths(clip)
        meta = read_meta(p.meta)
        ours = {f.frame: f.hands for f in read_hands(p.hands)}
        base = {f.frame: f.hands for f in read_hands(p.hands_baseline)}
        quality = read_csv(p.quality, QUALITY_COLS) if p.quality.exists() else []
        for frame, label in sorted(M.merged_labels(M.load_labels(clip)).items()):
            t = frame / meta["fps"]
            pred = ours.get(frame, [])
            overall.add(label["hands"], pred)
            for key, (ok, n) in side_split(label["hands"], pred, base.get(frame, [])).items():
                sides[key][0] += ok
                sides[key][1] += n
            for hand in label["hands"]:
                total += 1
                for name in modes_of(hand, label.get("tags", []), reasons_at(quality, t), meta["width"], meta["height"]):
                    m = modes[name]
                    m.tally.add([hand], pred, count_preds=False)
                    m.base.add([hand], base.get(frame, []), count_preds=False)
                    if failed(hand, pred):
                        m.examples.setdefault(clip, t)
    return modes, total, overall, sides


def pct(v) -> str:
    return "n/a" if v is None else f"{100 * v:.0f} %"


def mmss(t: float) -> str:
    return f"{int(t // 60)}:{int(t % 60):02d}"


def render(modes: dict[str, Mode], total: int, overall: M.Tally, clips: list[str], sides: dict[str, list[int]]) -> str:
    all_r = overall.result()
    rank = sorted(MODES, key=lambda k: -(modes[k].tally.labels - modes[k].tally.matched) if k in modes else 1)
    lines = ["# Where it fails", "",
             f"_Generated {datetime.now():%Y-%m-%d %H:%M} by `scripts/where_it_fails.py` from {total} hand-labelled hands on "
             f"{len(clips)} clips. Do not edit by hand; re-run the script._", "",
             f"All labelled hands, final pipeline: {pct(all_r['detection_recall'])} found, {pct(all_r['pck_0.2'])} of points on found "
             "hands within 20 % of the box. Labelled frames lean towards hard moments on purpose, and a hand can count in "
             "several rows.", "",
             f"Left/right on found hands: {pct(all_r['lr_accuracy'])} overall, {pct(sides['both'][0] / sides['both'][1] if sides['both'][1] else None)} "
             f"on hands the baseline also finds ({sides['both'][0]}/{sides['both'][1]}), "
             f"{pct(sides['new'][0] / sides['new'][1] if sides['new'][1] else None)} on the newly found ones "
             f"({sides['new'][0]}/{sides['new'][1]}).", "",
             "| Failure mode | Labelled hands | Share | Found: baseline → ours | Points OK on found hands |", "|---|---:|---:|---:|---:|"]
    for k in rank:
        m = modes.get(k)
        if not m:
            lines.append(f"| {MODES[k][0]} | 0 | 0 % | not measured | not measured |")
            continue
        r, b = m.tally.result(), m.base.result()
        lines.append(f"| {MODES[k][0]} | {r['labels']} | {pct(r['labels'] / total)} | {pct(b['detection_recall'])} → "
                     f"{pct(r['detection_recall'])} | {pct(r['pck_0.2'])} |")
    for k in rank:
        title, doing = MODES[k]
        m = modes.get(k)
        lines += ["", f"## {title}", ""]
        if not m:
            lines += ["No labelled frame shows this, so we have no accuracy number for it. That is a gap in the check, not "
                      "proof that it works.", "", f"**What we do:** {doing}"]
            continue
        examples = ", ".join(f"`{c}` at {mmss(t)}" for c, t in sorted(m.examples.items())) or "none among the labelled frames"
        lines += [f"**Example failures:** {examples}.", "", f"**What we do:** {doing}"]
    return "\n".join(lines) + "\n"


def main() -> int:
    clips = [c for c in M.labelled_clips() if ClipPaths(c).hands.exists()]
    if not clips:
        print("no labelled clip has hands.jsonl on this laptop")
        return 1
    modes, total, overall, sides = collect(clips)
    OUT.write_text(render(modes, total, overall, clips, sides), encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
