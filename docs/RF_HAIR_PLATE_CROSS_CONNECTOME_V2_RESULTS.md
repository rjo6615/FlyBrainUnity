# RF hair-plate cross-connectome check by neuron-level match — results (V2)

2026-11-03. One run of the preregistered protocol after commit 8ea584a (protocol sha
9b1ec930…). It is data only and read-only, and took seconds. The result
(`evidence/rf-hair-plate-banc-v2/run/result.json`, sha 23f282bf…) and the console log are
committed. Nothing was retried or changed after the run.

## Integrity: INCONCLUSIVE_INTEGRITY — no labels

| Check | Result |
|---|---|
| I1 Sources and anchors (7/5/12/11/8/9) | pass |
| I2 Bridge version (BANC `malecns_match` IDs in v1.0 annotations) | pass: 100 % |
| **I3 Coverage ≥ 75 % per side** | **fail: LF 5/7 (71 %), RF 3/5 (60 %)** |
| I4 Side consistency | pass: 100 % (22/22) |
| I5 Size field | pass |

Q_COUNT, Q_SIZE and Q_RF are **not assigned**. This is the second inconclusive attempt at
this question. Whether the RF deficit is anatomy or reconstruction is still open.
`joint_RFCoxa` stays BLOCKED_BY_INPUT, and coverage stays 20/42 admitted, +2 conditional.

## What the matches turned out to be (examined after the run; descriptive only)

Neither bridge provides the one-to-one neuron identity that the design assumed.

**1. The MANC bridge (B2) leads to the wrong kind of neuron.** Through `mancBodyid` →
BANC `manc_match`, the left-front anchors reached BANC neurons typed as interneurons:
`IN20A.22A038`, `IN04B101` (twice) and `IN19A082`. None has a nerve. One right-front
anchor reached a BANC neuron typed as a coxa motor neuron (`sternal_anterior_rotator…`,
cable 7,444 µm).

The likely cause is that the MANC IDs in the two sources are not interchangeable here,
for example because they come from different MANC versions. The design had no check that
counterparts were sensory neurons. **That was a design flaw, and it is recorded.**

**2. The direct bridge (B1) matches groups, not neurons.**
- BANC assigns one MaleCNS body ID to a whole group. Nine BANC LF `SNpp45` neurons all
  carry `malecns_match` = 908177, and three RF ones carry 1323625268.
- Most anchors have no B1 match at all: only 1 of 7 LF and 2 of 5 RF.
- So `malecns_match` is a type- or group-level link for these neurons, not a per-neuron
  one.

**3. The B1 counterparts alone repeat V1's pattern.** These are post-hoc numbers, not
labels.
- All B1 counterparts are BANC `SNpp45`: 9 LF and 5 RF, with RF cable medians around
  1,000 µm against LF around 1,350 µm.
- That is a ratio of about 0.74, which is in the indeterminate band.
- These largely overlap V1's type-name rows, so they are not independent evidence.

**4. The context segments are worse.**
- T2 and T3 coverage falls to 22–62 %.
- Anchors without a counterpart: 5 of 12 LM, 7 of 11 RM, 3 of 8 LH and 7 of 9 RH.

## What this means

- The local data cannot answer this question. With the BANC metadata in this
  repository, neither bridge gives neuron-level identity for hair-plate afferents. One is
  group-level and the other reaches non-sensory neurons.
- The data that could settle it is not here. A connectivity-based identity would need
  BANC synapse tables, which are not local. Getting them would mean downloading, and you
  have asked for this project to make no external requests.
- **The recommendation is to stop the RF anatomy-vs-reconstruction thread here.**
  - It ends with two recorded INCONCLUSIVE results.
  - `joint_RFCoxa` remains BLOCKED_BY_INPUT, with its cause localised to the MaleCNS
    connectome (fewer, smaller RF SNpp45 neurons) and its biological status unknown.
  - The project would then move to other coordinates.

## Limits

- Two animals.
- BANC's match annotations are curated by others and not audited here. This run shows
  only that they cannot serve as one-to-one identity for these neurons.
- Structural only.
- The post-hoc tables above are diagnostic, and no conclusion rests on them.

## Files and checks

- `malecns_backend/embodiment/rf_hair_plate_banc_v2.py` (read-only; reuses V1 helpers and
  the Step A rule).
- `tests/test_rf_hair_plate_banc_v2.py`: 10 synthetic tests. They passed together with the
  V1 and Step A tests (25 in total).
- `docs/evidence/rf-hair-plate-banc-v2/{protocol.json,run/result.json,run/console.txt}`.
- `.gitattributes`.
- Docs: the design, this file, the status line, the handoff and the roadmap.

```bash
cd "$HOME/Documents/FlyBrainUnity" && PYTHONPATH="$PWD" "$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" -m malecns_backend.embodiment.rf_hair_plate_banc_v2 --output .cache/rf-hair-plate-banc-v2-repro.json
```

Expected output, in seconds: `INCONCLUSIVE_INTEGRITY`, with only I3 false.
