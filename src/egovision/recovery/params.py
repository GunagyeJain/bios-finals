"""Module-local thresholds and constants. Only this module's owner edits this file."""
ROI_SCALE = 4.0        # crop side, in hand sizes; MediaPipe needs context: 64 % of hidden hands found at 4x, 28 % at 2x
ROI_MIN_SIZE = 96.0    # px; a tiny last box still gets a usable crop
ROI_UPSCALE = 1.0      # 2x added no recall
ROI_MIN_CONF = 0.4
RTM_ROI_SCALE = 6.0    # detector crop; narrower crops invent hands: 43 % false at 3x, 14 % at 6x
RTM_REACH = 1.5        # hand sizes from the last box
AGREE_BOX = 1.4        # hand box +- 20 %
AGREE_ZERO = 0.5       # hand sizes of mean wrist+tip distance at which agreement reaches 0
