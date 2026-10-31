"""Module-local thresholds and constants. Only this module's owner edits this file."""
NEAR_HAND_SIZES = 0.5   # alert distance, fingertip to box
MIN_NEAR_S = 0.5        # must stay near this long
JOIN_GAP_S = 0.25       # a shorter break does not end a stretch: detection and `moving` both flicker
OBJECT_HOLD_S = 1.0     # objects run on sparse frames; a row stays valid this long
