"""Module-local thresholds and constants. Only this module's owner edits this file."""
import os

# Gemini. Newest stable Flash with a free tier, video input and structured output
# (ai.google.dev/gemini-api/docs/models and /pricing, checked 31 Oct 2026). The free tier allows only
# 20 requests a day per model (seen on gemini-3.8-flash), so other free-tier models with video input
# take over when a model is out of quota or overloaded. Cache keys use MODEL whichever model answered.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
FALLBACK_MODELS = ("gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.1-flash-lite", "gemini-3-flash-preview")
MODELS = (MODEL, *[m for m in FALLBACK_MODELS if m != MODEL])
MAX_CALLS_PER_RUN = int(os.environ.get("GEMINI_MAX_CALLS", 40))   # quota guard; the rest fall back to contact rows
MAX_RETRIES = 3            # tries per model before the next one
BACKOFF_S = 4.0            # 4, 8 seconds on per-minute 429 / 5xx

# Windows
MIN_WIN_S = 1.0            # shorter windows join their neighbour
MAX_WIN_S = 20.0           # longer windows are split evenly
FALLBACK_WIN_S = 8.0       # fixed windows when contacts.csv is missing

# Clip sent to Gemini
CLIP_HEIGHT = 480
CLIP_FPS = 5.0
CLIP_CRF = 30

PROMPT = """You see a short first-person video from a factory worker's head camera.
Describe the ONE main manual step the worker's hands do in it.
verb: exactly one of {verbs}. Use "other" if nothing fits or the hands do no work.
object: the main object or part handled, 1 to 3 plain words, lowercase.
hand: which of the worker's hands does it: left, right, both, or none.
caption: one short sentence, present tense, for example "right hand tightens the screw on the hinge".
{hint}"""

# Order check (S3)
REF_MIN_LEN = 3            # reference cycle length, in captioned steps
REF_MAX_LEN = 8
