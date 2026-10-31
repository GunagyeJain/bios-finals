"""Module-local thresholds and constants. Only this module's owner edits this file."""
from egovision import config

MODEL_PATH = config.ROOT / "models" / "hand_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
NUM_HANDS = 2
MIN_DETECTION_CONF = 0.4
MIN_TRACKING_CONF = 0.4
MIRROR = False  # MediaPipe labels already match the wearer's hands on these clips; see docs/08-log/decisions.md

# Tracking
DUP_IOU = 0.5               # two detections overlapping this much in one frame are the same hand
TRACK_KEEP_S = 2.0          # a lost track can be picked up again for this long (re-entry)
GATE_SIZES = 1.5            # max wrist jump to the next frame, in hand sizes
GATE_SIZES_PER_S = 2.0      # gate growth per second a track has been lost
GATE_MAX_WIDTH = 0.25       # gate never exceeds this share of the frame width
SIDE_STRICT_AFTER_S = 0.5   # a track lost longer than this only re-attaches to its own label
SIDE_SWITCH_IOU = 0.0       # a label change only stays on the track if the boxes overlap this much
COST_SIDE, COST_IOU, COST_DIST = 0.3, 0.3, 0.4

# Side voting
SIDE_WINDOW = 31            # sampled frames (about 2 s) over which a track's labels are averaged
SIDE_MIN_RUN = 15           # a track only splits for a side change lasting this many sampled frames
PRIOR_WEIGHT = 0.25         # per-frame vote for the image half the wrist is in (labels vote with their score)
PAIR_WEIGHT = 0.5           # per-frame vote when two hands are visible: the one further left votes left
CONFLICT_MIN_FRAMES = 3     # two tracks sharing this many frames should not be the same side

# Sanity
BONE_RATIO_MIN, BONE_RATIO_MAX = 0.6, 1.6   # 3D finger length against the track's median
MAX_WRIST_SPEED = 3.0       # frame widths per second
SPEED_MAX_DT_S = 0.5        # speed is only checked across gaps shorter than this
SANITY_SCORE_SCALE = 0.5

# Gap fill and smoothing
MAX_GAP_FRAMES = 5          # missing video frames filled by linear interpolation
ONE_EURO_MIN_CUTOFF = 1.0
ONE_EURO_BETA = 0.01
ONE_EURO_D_CUTOFF = 1.0
KP3D_FILTER_SCALE = 1000.0  # world points are in metres; filtered in mm so BETA means the same as for pixels

# WiLoR
WILOR_DIR = config.ROOT / "models" / "wilor" / "pretrained_models"   # MANO_RIGHT.pkl, wilor_final.ckpt, mano_mean_params.npz
WILOR_BATCH = 16
WILOR_RESCALE = 2.5         # crop side = this × longer box side (WiLoR's own value)
WILOR_PATCH = 256
WILOR_FOCAL = 5000.0
WILOR_SCORE = 0.7           # WiLoR gives no confidence; hands it re-estimated count as this at least
WILOR_MATCH_SIZES = 1.5     # a WiLoR hand replaces a same-side hand with its wrist this close, in hand sizes

# Flags
LOW_CONF = 0.5
DISAGREE = 0.6
EDGE_PX = 2.0
