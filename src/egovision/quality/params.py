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

# Data Health light (B3). Pixel checks run on small frames, so they read the same on any clip size.
SMALL_WIDTH = 160
SAMPLE_STEP = 3        # frames between samples, 10 per second at 30 fps
DARK_PIXEL = 40        # gray level under this counts as a dark pixel
CLIPPED_PIXEL = 245
DARK_SOFT = 0.5        # share of dark pixels
DARK_HARD = 0.85
CLIPPED_SOFT = 0.3
BLUR_SOFT = 150.0      # Laplacian variance
BLUR_HARD = 50.0
SPEED_SOFT = 4.0       # median optical flow, small-frame px per sample
FROZEN_DIFF = 0.3      # mean gray change per sample; below this all second = frozen
HANDS_SOFT = 0.6       # share of frames with a hand
HANDS_HARD = 0.3
EDGE_MARGIN = 3        # px from the frame edge
EDGE_SOFT = 0.5        # share of hand frames with a hand cut by the edge
HAND_Y_MIN = 0.25      # mean hand height, 0 top, 1 bottom
HAND_Y_MAX = 0.9
AGREEMENT_SOFT = 0.6
