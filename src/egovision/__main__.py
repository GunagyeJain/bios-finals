"""CLI. `python -m egovision --help`. Owner: Gunagye."""
from __future__ import annotations

import argparse
import sys
import time

from . import config
from .schema import ClipPaths
from .stages import BY_NAME, STAGES, NotBuilt


def run_clip(clip: str, only: str | None, force: bool) -> bool:
    """Runs the stages in order. A crashing stage is reported and ends this clip (later stages need its
    output); the caller goes on with the next clip. Returns False if a stage failed."""
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
        except Exception as e:  # report and keep going: one bad clip must not stop `run --all`
            print(f"  {st.name:15s} FAIL {e.__class__.__name__}: {e}")
            return False
    return True


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
    v = sub.add_parser("preview", help="browser-playable H.264 copy of clips that have no render yet")
    gv = v.add_mutually_exclusive_group(required=True)
    gv.add_argument("--clip")
    gv.add_argument("--all", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "run":
        clips = config.all_clips() if a.all else [a.clip]
        failed = []
        for c in clips:
            print(f"[{c}]")
            if not run_clip(c, a.stage, a.force):
                failed.append(c)
        if failed:
            print(f"{len(failed)} clip(s) had a failing stage: {', '.join(failed)}")
            return 1
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
    elif a.cmd == "preview":
        from .io.video import h264_preview
        for c in (config.all_clips() if a.all else [a.clip]):
            p = ClipPaths(c)
            if p.render.exists() or p.preview.exists():
                continue
            print(f"[{c}] {h264_preview(p.video, p.preview)}")
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
