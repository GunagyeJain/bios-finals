"""End of event: delete every local copy of the organisers' footage and everything derived from it,
plus our uploads in the Gemini Files API. Checklist with the steps no script can do:
docs/06-plan/data-deletion.md

python scripts/wipe_event_data.py          # dry run: lists what would go
python scripts/wipe_event_data.py --yes    # deletes (permanently, not to the recycle bin)
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from egovision import config  # noqa: E402  (respects EGO_DATA / EGO_CLIPS / EGO_OUTPUTS)

LOCAL = [config.DATA_DIR, config.CLIPS_DIR, config.OUTPUTS, config.EXPORTS, ROOT / "eval" / "frames",
         config.GEMINI_CACHE]


def wipe_local(delete: bool) -> None:
    for p in dict.fromkeys(LOCAL):
        if p.exists():
            print(f"{'deleting' if delete else 'would delete'} {p}")
            if delete:
                shutil.rmtree(p)


def wipe_gemini(delete: bool) -> None:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("GEMINI_API_KEY not set here: run this on the laptop that called Gemini")
        return
    try:
        from google import genai
        client = genai.Client(api_key=key)
        files = list(client.files.list())
    except Exception as e:  # never hide a failed check: the uploads would stay online
        print(f"Gemini Files API check FAILED ({e}): delete uploads by hand in AI Studio")
        return
    print(f"Gemini Files API: {len(files)} uploaded file(s)")
    for f in files:
        print(f"{'deleting' if delete else 'would delete'} gemini file {f.name} ({f.display_name})")
        if delete:
            client.files.delete(name=f.name)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--yes", action="store_true", help="really delete (default: dry run)")
    a = ap.parse_args()
    wipe_local(a.yes)
    wipe_gemini(a.yes)
    print("Now finish the manual steps in docs/06-plan/data-deletion.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
