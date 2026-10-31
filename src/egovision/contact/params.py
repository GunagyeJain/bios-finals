"""Module-local thresholds and constants. Only this module's owner edits this file."""

# YOLOE vocabulary (text prompts). Edit after the E2 clip notes. Order does not matter.
PORTABLE = ["screwdriver", "wrench", "pliers", "hammer", "drill", "scissors", "knife", "tool",
            "box", "bottle", "bag", "cloth", "fabric", "screw", "bolt", "nut", "wire", "tape",
            "metal part", "plastic part", "pen", "phone", "cup"]
FIXED = ["machine", "sewing machine", "press machine", "lathe", "conveyor belt", "table",
         "workbench", "shelf", "rack", "cabinet", "door", "computer"]

MODEL = "yoloe-11s-seg.pt"  # smallest text-prompt YOLOE; downloaded into models/ on first run
DETECT_EVERY = 5          # YOLOE on every 5th processed frame; boxes held in between
CONF = 0.25
IMGSZ = 640
TRACK_IOU = 0.3           # same name + IoU >= this between runs keeps the object id

# Contact rule (problem statement p.12)
PAD = 0.15                # box padded by 15 % of its width/height on each side
MIN_TIPS = 2              # fingertips inside the padded box
CLOSURE_MAX = 0.9         # rule.closure(): fist ~0.3, power grip ~0.6, open flat hand ~1.0+
ON_FRAMES = 4             # consecutive frames before a contact starts
OFF_FRAMES = 6            # consecutive frames without it before it ends

# Moving machine: mean abs grey difference inside the box vs. outside all boxes (ego-motion)
MOVING_MIN = 6.0          # 0-255 grey levels
MOVING_RATIO = 2.0
