# Right-front hair-plate deficit: cross-connectome check against BANC — design (V1)

Designed 2026-11-03, after the released-posture test was merged (PR #314).

**Status:** preregistered in f1a147e (protocol sha 856fe70b…) and run once:
INCONCLUSIVE_INTEGRITY (I3: 21.7 % of BANC SNpp45 rows were excluded). No labels were
assigned. The run also showed that the assumption that BANC `SNpp45` equals MaleCNS
`SNpp45` does not hold. See `RF_HAIR_PLATE_CROSS_CONNECTOME_RESULTS.md`. The design below
is unchanged.

## Why this question

The right-front leg is the main input-side block in the coxa track:

- `joint_RFCoxa` is BLOCKED_BY_INPUT. In D3 the RF hair plates fire at saturation, but RF
  coxa MNs barely respond (0.55 Hz).
- Without RF, the loop is left-sided. Two left legs cannot support a bilateral posture
  question.
- The drive-asymmetry analysis (`COXA_DRIVE_ASYMMETRY_RESULTS.md`) traced the deficit to
  the connectome:
  - Fewer SNpp45 neurons: 5 RF against 7 LF via the ventral prothoracic nerve, plus one
    left ProLN neuron excluded in Step A.
  - Much smaller RF neurons: 320–378 raw output synapses each, against mostly 680–1,320
    for LF.
  - Engine choices explain only 9 % of the deficit.
- Twice the question **"real anatomy or under-traced reconstruction?"** was left open,
  because one connectome cannot answer it.

A second, independent connectome is already in the repository, committed with
provenance in the distal-tarsus work:

| File | sha256 | Contents |
|---|---|---|
| `docs/evidence/distal-tarsus-reference-v1/banc_888_meta.feather` | 86ccf5df… | BANC v888, the female brain-and-nerve-cord connectome (Bates et al., Nature 2026) |

BANC metadata includes the cell type (`SNpp45` is typed), entry nerve, side, neuromere,
proofread flag, L2 cable length and volume. **This check needs no download and no
external request.**

## Question

Does BANC show the same right-front versus left-front SNpp45 deficit as MaleCNS, in neuron
count and in neuron size?

- **If it does,** the RF weakness in our model is plausibly real anatomy, or at least not
  specific to MaleCNS.
- **If it does not,** the deficit is specific to the MaleCNS animal or its reconstruction.
  One more animal cannot separate individual variation from tracing incompleteness, and
  the label says so.

## Data and leg assignment (fixed)

**BANC**

- **Rows:** `cell_type == 'SNpp45'`, exact.
- **Primary leg rule** mirrors Step A (`hair_plate_identity.NERVES`). The `nerve` value
  must be exactly one of:
  - `<side>_ventral_prothoracic_nerve` → T1 (MaleCNS `VProN`);
  - `<side>_mesothoracic_leg_nerve` → T2 (`MesoLN`);
  - `<side>_metathoracic_leg_nerve` → T3 (`MetaLN`).
- The side comes from the nerve name. The `side` column is a cross-check, and any
  disagreement is reported.
- Rows with any other nerve value, including multi-nerve strings, are excluded and listed,
  as Step A did.
- **Sensitivity count (reported, not labelled):** all SNpp45 rows whose nerve names a
  single prothoracic nerve of one side. This mirrors adding back the excluded left ProLN
  neuron on the MaleCNS side.

**MaleCNS (the model's connectome)**

- **Counts:** per-leg counts from Step A (`evidence/hair-plate-identity-v1/run/result.json`).
- **Size:** per-neuron total raw output synapses, from the cached connectome with the
  Step A loader (`.cache/malecns-v1`).
- **Limit:** BANC metadata has no output-synapse totals, and the local MaleCNS metadata
  has no cable length. So size is compared as **within-dataset right/left ratios**, never
  as raw values across datasets.

## Measures

For each dataset and each leg (T1–T3, left and right):

- the SNpp45 count `n`;
- the size per neuron: L2 cable (µm) in BANC, and raw output synapses in MaleCNS;
- the median size and the summed size.

These give, per segment, the right − left count difference and the right/left ratios of
median and summed size.

**Reported only:**
- BANC volume ratios;
- the proofread flag of each T1 neuron;
- the excluded rows;
- the T2 and T3 right/left values in both datasets. These show how much bilateral
  difference is normal in each animal.

## Integrity (all required, else `INCONCLUSIVE_INTEGRITY` with no labels)

1. **I1 Sources.** The BANC file sha equals 86ccf5df… and the provenance record. The Step A
   result sha matches its committed file.
2. **I2 Typing.** BANC has at least one SNpp45 row in each of the six legs under the
   primary rule.
3. **I3 Exclusions bounded.** At most 20 % of BANC SNpp45 rows are excluded by the
   primary rule.
4. **I4 MaleCNS reproduction.** The cached connectome gives the Step A per-leg counts
   exactly (7, 5, 12, 11, 8, 9).
5. **I5 Size fields present.** Every included BANC T1 row has a finite, positive
   `l2_cable_length_um`.

## Labels (decided by these rules only; BANC T1)

**Q_COUNT** uses d = n(T1 right) − n(T1 left).

| Label | Rule |
|---|---|
| `COUNT_DEFICIT_REPLICATED` | d ≤ −2 |
| `COUNT_SYMMETRIC` | \|d\| ≤ 1 |
| `COUNT_REVERSED` | d ≥ +2 |

**Q_SIZE** uses r = median cable(T1 right) / median cable(T1 left).

| Label | Rule |
|---|---|
| `SIZE_DEFICIT_REPLICATED` | r ≤ 0.67 |
| `SIZE_SYMMETRIC` | 0.85 ≤ r ≤ 1/0.85 |
| `SIZE_REVERSED` | r ≥ 1.5 |
| `SIZE_INDETERMINATE` | otherwise |

**Q_RF (overall)**

| Label | Rule |
|---|---|
| `RF_DEFICIT_REPLICATED` | both COUNT and SIZE replicated |
| `RF_DEFICIT_NOT_REPLICATED` | COUNT_SYMMETRIC (or REVERSED) and SIZE_SYMMETRIC (or REVERSED) |
| `RF_PARTIAL` | otherwise |

**The bars.**
- The count bar matches the MaleCNS difference (−2).
- The size bar 0.67 is the bar used throughout the coxa track. The MaleCNS per-neuron
  output ratio is far below it.
- The symmetric band (±15 %) is fixed here, before any BANC per-leg value is seen.

## What each outcome means (declared now)

**RF_DEFICIT_REPLICATED**
- Two animals of different sex show the same deficit. That favours real anatomy, or a
  bias shared by both reconstruction pipelines, over a MaleCNS-only tracing gap.
- `joint_RFCoxa` stays BLOCKED_BY_INPUT, now documented as a likely property of the
  fly.
- The coxa track should not try to "fix" RF input. A real biological asymmetry would also
  be a scientific finding in its own right.

**RF_DEFICIT_NOT_REPLICATED**
- The deficit is specific to MaleCNS: individual variation or under-tracing. One
  comparison cannot say which.
- Any use of this would be a **separately designed and versioned engineering
  question**. An example is a labelled RF-input substitution that is never presented as
  the reconstruction.
- No weights change because of this result. Whether to design that question is the
  user's decision.

**RF_PARTIAL**
- Recorded as is. No follow-up is implied.

In every case:
- motor coverage stays 20/42 admitted, +2 conditional;
- `COXA_COORDINATE_STATUS.md` gets one evidence line for `joint_RFCoxa`, with no status
  change.

## Predictions (expectations, not criteria)

- **Q_COUNT: COUNT_SYMMETRIC is somewhat more likely.** The other segments differ by only
  one neuron between sides in MaleCNS (12/11, 8/9), and hair-plate sensilla should be
  bilaterally fixed.
- **Q_SIZE: SIZE_SYMMETRIC is more likely.** A 2–3× per-neuron size deficit confined to
  one leg looks more like under-traced arbors than biology.
- **Q_RF: overall low confidence.** BANC's own typing could miss neurons too, and that
  would be visible as exclusions or an unproofread flag.

## Limits

- **Two animals only** (one male MaleCNS, one female BANC). This can show replication or
  non-replication. It cannot establish population anatomy.
- **Size proxies differ by dataset** (cable vs output synapses), so sizes are compared
  only as within-dataset ratios.
- **Typing dependence.** An SNpp45 neuron that BANC failed to type is invisible here. The
  sensitivity count and exclusions bound the nerve-rule part only.
- **Structural only.** No simulation, and nothing about function, is tested.

## Build and run plan (on approval)

1. **Protocol.** Write `docs/evidence/rf-hair-plate-banc-v1/protocol.json` with the rules,
   bars, file hashes and expected Step A counts.
2. **Code.** Write `malecns_backend/embodiment/rf_hair_plate_banc.py`. It reuses the
   `hair_plate_identity` loader, NERVES and side rule. It is read-only.
3. **Tests.** Write `tests/test_rf_hair_plate_banc.py`. It uses synthetic tables to cover
   the nerve-name mapping, exclusions, label boundaries and integrity faults.
4. **Commit and hash-lock, then run once.** The run takes seconds. Write the results
   document, add the one-line status evidence, then update the handoff and roadmap.
