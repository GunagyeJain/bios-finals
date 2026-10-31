"""CLI. `python -m egovision --help`. Owner: Gunagye."""
from __future__ import annotations

import argparse
import sys
import time

from . import config
from .schema import ClipPaths
from .stages import BY_NAME, STAGES, NotBuilt


def run_clip(clip: str, only: str | None, force: bool) -> None:
    from .io.frames import build_meta

    p = ClipPaths(clip).mkdir()
    if not p.meta.exists() and p.video.exists():
        build_meta(clip)
    for st in ([BY_NAME[only]] if only else STAGES):
        if getattr(p, st.output).exists() and not force:
            print(f"  {st.name:15s} done (exists)")
            continue
        t0 = time.time()
        try:
            st.load()(clip)
            print(f"  {st.name:15s} ok   {time.time() - t0:6.1f}s")
        except NotBuilt as e:
            print(f"  {st.name:15s} skip (not built yet: {st.owner} {st.task}) {e}")


def status(clip: str) -> None:
    p = ClipPaths(clip)
    for name in ["meta", "hands_baseline", "hands", "wilor", "quality", "objects", "contacts",
                 "steps", "alerts_steps", "alerts_safety", "render", "metrics"]:
        print(f"  {'x' if getattr(p, name).exists() else ' '} {getattr(p, name).name}")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):      # Windows consoles default to cp1252; stages print "→", "·"
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="egovision")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run pipeline stages")
    g = r.add_mutually_exclusive_group(required=True)
    g.add_argument("--clip")
    g.add_argument("--all", action="store_true")
    r.add_argument("--stage", choices=list(BY_NAME))
    r.add_argument("--force", action="store_true")
    s = sub.add_parser("status", help="which outputs exist for a clip")
    s.add_argument("--clip", required=True)
    c = sub.add_parser("check", help="validate a clip's outputs against the contract")
    c.add_argument("--clip", required=True)
    sub.add_parser("fixtures", help="write synthetic clips fixture_001/002 with every output")
    sub.add_parser("index", help="rebuild outputs/index.db")
    e = sub.add_parser("export", help="build a robot dataset")
    e.add_argument("--name", required=True)
    e.add_argument("--light", default="green", choices=["green", "yellow"])
    a = ap.parse_args(argv)

    if a.cmd == "run":
        clips = config.all_clips() if a.all else [a.clip]
        for c in clips:
            print(f"[{c}]")
            run_clip(c, a.stage, a.force)
    elif a.cmd == "status":
        status(a.clip)
    elif a.cmd == "check":
        from .contract import check
        return 1 if check(a.clip) else 0
    elif a.cmd == "fixtures":
        from .fixtures import make_all
        make_all()
    elif a.cmd == "index":
        from .index.build import build
        build()
    elif a.cmd == "export":
        from .products.export import export
        try:
            s = export(a.name, a.light)
        except ValueError as e:
            print(e)
            return 1
        print(f"{s['path']}: {s['episodes']} episodes, {s['frames']} frames, {s['seconds']} s, "
              f"{s['tasks']} tasks, {s['red_seconds']:.0f} red seconds")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except NotBuilt as e:
        print(f"not built yet: {e}")
        sys.exit(1)
