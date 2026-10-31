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
BLUR_WIDTH = 480       # sharpness needs more pixels: keeps 19 % after a 15 px blur, 160 px keeps 62 %
SAMPLE_STEP = 3        # frames between samples, 10 per second at 30 fps
DARK_PIXEL = 40        # gray level under this counts as a dark pixel
CLIPPED_PIXEL = 245
DARK_SOFT = 0.5        # share of dark pixels
DARK_HARD = 0.85
CLIPPED_SOFT = 0.3
BLUR_SOFT = 0.5        # Laplacian variance as a share of the clip's median second; about 3 % of seconds on all clips
BLUR_HARD = 0.25       # about 0.2 % of seconds
SPEED_SOFT = 3.5       # median optical flow, small-frame px per sample; about the fastest 5 % of seconds
FROZEN_DIFF = 0.3      # mean gray change per sample; below this all second = frozen
HANDS_SOFT = 0.6       # share of frames with a hand
HANDS_HARD = 0.3
EDGE_MARGIN = 3        # px from the frame edge
EDGE_SOFT = 0.5        # share of hand frames with a hand cut by the edge
HAND_Y_MIN = 0.25      # mean hand height, 0 top, 1 bottom
HAND_Y_MAX = 0.9
AGREEMENT_SOFT = 0.6

FEEDBACK_MIN_RUN_S = 5  # a problem's longest stretch is named from this length up
