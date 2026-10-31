"""Module-local thresholds and constants. Only this module's owner edits this file."""
from egovision import config

MODEL_PATH = config.ROOT / "models" / "hand_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
NUM_HANDS = 2
MIN_DETECTION_CONF = 0.4
MIN_TRACKING_CONF = 0.4
MIRROR = False  # MediaPipe labels already match the wearer's hands on these clips; see docs/08-log/decisions.md
