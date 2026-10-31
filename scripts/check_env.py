"""Run after setup: python scripts/check_env.py. Prints OK/MISSING per dependency and data path."""
import importlib
import sys

mods = ["numpy", "cv2", "pandas", "pyarrow", "mediapipe", "rtmlib", "onnxruntime", "ultralytics",
        "google.genai", "streamlit", "plotly", "scipy", "egovision"]
bad = 0
print("python", sys.version.split()[0], "(team standard 3.11)")
for m in mods:
    try:
        importlib.import_module(m)
        print(f"OK       {m}")
    except Exception as e:  # report every failure, keep going
        bad += 1
        print(f"MISSING  {m}: {e.__class__.__name__}")
from egovision import config  # noqa: E402
print("clips dir", config.CLIPS_DIR, "found", len(config.all_clips()), "clips")
import os  # noqa: E402
print("GEMINI_API_KEY", "set" if os.environ.get("GEMINI_API_KEY") else "not set (needed by S2 only)")
sys.exit(1 if bad else 0)
