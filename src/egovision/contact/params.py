"""Module-local thresholds and constants. Only this module's owner edits this file."""

# YOLOE vocabulary (text prompts), from the 4 factories: furniture woodwork (SGF00106), bench
# assembly of plastic parts and tube profiles (SKL00089), polishing at a lapping wheel (000003),
# tiles/stone (000060). Fewer, concrete names detect better than many vague ones.
PORTABLE = ["screwdriver", "pliers", "hammer", "power drill", "angle grinder", "scissors", "knife",
            "tape dispenser", "tape roll", "caliper", "dial gauge", "brush", "bottle", "cable",
            "green plastic part", "plastic part", "metal part", "wooden plank", "wooden frame",
            "aluminium channel", "tile", "box", "cloth"]  # no "phone": green plates got that name
FIXED = ["machine", "polishing wheel", "workbench", "table", "conveyor rollers", "shelf", "rack"]

MODEL = "yoloe-11s-seg.pt"  # smallest text-prompt YOLOE; downloaded into models/ on first run
DETECT_EVERY = 5          # YOLOE on every 5th processed frame; boxes held in between
CONF = 0.10               # 0.25 found a contact candidate in 2-4 of 40 hand frames, 0.10 in 10-15
IMGSZ = 640
TRACK_IOU = 0.3           # same name + IoU >= this between runs keeps the object id
KEEP_RUNS = 1             # an object missed by YOLOE stays for this many more runs (last box)

# Contact rule (problem statement p.12)
PAD = 0.15                # box padded by 15 % of its width/height on each side
MIN_TIPS = 2              # fingertips inside the padded box
CLOSURE_MAX = 1.2         # rule.closure(): fist ~0.3, power grip ~0.6, pinch of a thin plate 1.0-1.3
ON_FRAMES = 4             # consecutive frames before a contact starts
OFF_FRAMES = 6            # consecutive frames without it before it ends

# Moving machine: mean abs grey difference inside the box vs. outside all boxes (ego-motion)
MOVING_MIN = 6.0          # 0-255 grey levels
MOVING_RATIO = 2.0

# Grip per contact interval (F11), from the median over its frames; lengths relative to palm (kp0 → kp9)
PINCH_MAX = 0.35          # thumb tip to index tip: a pinch closes the gap
OTHERS_OPEN_MIN = 0.8     # middle/ring/little tips to palm centre: not wrapped round the object
WRAP_MAX = 0.8            # rule.closure() of a power grip (fist ~0.3, open hand ~1.0+)
MIN_PRESENT = 0.5         # share of the interval's frames that need keypoints, else "unsure"
FIXED_WRAP_MAX = 0.5      # closed hand on a "fixed" box = holding a part YOLOE missed → 5f, not generic
OTHERS_IN_BOX_WRAP = 2    # middle/ring/little tips inside the object box: wrapped round it, not a pinch
