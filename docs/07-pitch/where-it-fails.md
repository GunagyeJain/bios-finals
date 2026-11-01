# Where it fails

_Generated 2026-11-01 05:44 by `scripts/where_it_fails.py` from 282 hand-labelled hands on 3 clips. Do not edit by hand; re-run the script._

All labelled hands, final pipeline: 66 % found, 75 % of points on found hands within 20 % of the box. Labelled frames lean towards hard moments on purpose, and a hand can count in several rows.

Left/right on found hands: 96 % overall, 99 % on hands the baseline also finds (113/114), 90 % on the newly found ones (65/72).

| Failure mode | Labelled hands | Share | Found: baseline → ours | Points OK on found hands |
|---|---:|---:|---:|---:|
| Hand cut off by the frame edge | 49 | 17 % | 20 % → 47 % | 56 % |
| Hands overlapping or holding each other | 67 | 24 % | 51 % → 70 % | 75 % |
| Fast motion and blur | 33 | 12 % | 6 % → 52 % | 52 % |
| Gloves | 0 | 0 % | not measured | not measured |
| Dark frames | 0 | 0 % | not measured | not measured |

## Hand cut off by the frame edge

**Example failures:** `MTL-SKL00089-005` at 0:16, `MTL-SKL00089-012` at 0:57, `mytronlabs-000003-002` at 0:00.

**What we do:** Hands touching the edge carry the `edge` flag, and the Data Health light marks stretches with `edge_cut`, so buyers can filter them out.

## Hands overlapping or holding each other

**Example failures:** `MTL-SKL00089-005` at 0:16, `MTL-SKL00089-012` at 0:12, `mytronlabs-000003-002` at 0:16.

**What we do:** Voting and the same-side split keep the two sides apart when both hands are found. A hand hidden behind the other stays missing: we report it rather than invent it.

## Fast motion and blur

**Example failures:** `MTL-SKL00089-005` at 0:24, `MTL-SKL00089-012` at 0:52, `mytronlabs-000003-002` at 0:00.

**What we do:** Gaps up to 5 frames are interpolated and marked `interp`, and two-way smoothing removes lag. The light flags fast head motion. A heavily blurred hand is often still missed.

## Gloves

No labelled frame shows this, so we have no accuracy number for it. That is a gap in the check, not proof that it works.

**What we do:** No glove-specific model: the low detection thresholds are the only help. WiLoR was meant for this and was cut.

## Dark frames

No labelled frame shows this, so we have no accuracy number for it. That is a gap in the check, not proof that it works.

**What we do:** The Data Health light flags dark seconds, and red seconds are never exported.
