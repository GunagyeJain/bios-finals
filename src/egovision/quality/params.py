"""Module-local thresholds and constants. Only this module's owner edits this file."""
from .. import config

YUNET_MODEL = config.ROOT / "models" / "face_detection_yunet_2023mar.onnx"
YUNET_URL = ("https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/"
             "face_detection_yunet_2023mar.onnx")
FACE_SCORE = 0.6       # below the detector's usual 0.9: a false blur costs less than a leaked face
FACE_NMS = 0.3
FACE_TOP_K = 500
FACE_PAD = 0.2         # share of the face size added on each side
BLUR_MIN_KERNEL = 15   # px
