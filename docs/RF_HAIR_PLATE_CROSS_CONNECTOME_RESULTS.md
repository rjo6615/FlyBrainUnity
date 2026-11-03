# RF hair-plate cross-connectome check against BANC — results (V1)

2026-11-03. One run of the preregistered protocol after commit f1a147e (protocol sha
856fe70b…). It is data only and read-only, and took seconds. The result
(`evidence/rf-hair-plate-banc-v1/run/result.json`, sha dfdd5445…) and the console log are
committed. Nothing was retried or changed after the run.

## Integrity: INCONCLUSIVE_INTEGRITY — no labels

| Check | Result |
|---|---|
| I1 Sources (BANC 86ccf5df… = provenance; Step A result; annotations) | pass |
| I2 Typing (≥ 1 BANC SNpp45 per leg) | pass |
| **I3 Exclusions ≤ 20 %** | **fail: 36 of 166 rows (21.7 %)** |
| I4 MaleCNS reproduces Step A counts (7/5/12/11/8/9) | pass |
| I5 Cable length present for BANC T1 rows | pass |

By the protocol, Q_COUNT, Q_SIZE and Q_RF are **not assigned**. The question of whether
the RF deficit is anatomy or reconstruction stays open. `joint_RFCoxa` stays
BLOCKED_BY_INPUT, and coverage stays 20/42 admitted, +2 conditional.

## Why it failed (examined after the run; descriptive only)

**1. The excluded rows are prothoracic, and they are not side-balanced.**

| Nerve of the 36 excluded rows | Rows |
|---|---:|
| `right_prothoracic_leg_nerve` | 22 |
| `left_prothoracic_leg_nerve` | 10 |
| `left_prothoracic_accessory_nerve` | 3 |
| `left_dorsal_prothoracic_nerve` | 1 |

All 36 are proofread.

**2. The same type name covers different populations in the two connectomes.** This is a
design flaw. The design assumed that BANC `SNpp45` names the same population as MaleCNS
`SNpp45`. The counts show it does not:

| Leg | MaleCNS n | BANC n (primary rule) |
|---|---:|---:|
| T1 left / right | 7 / 5 | 8 / 4 |
| T2 left / right | 12 / 11 | 48 / 37 |
| T3 left / right | 8 / 9 | 24 / 9 |

- In T2, BANC has about 4× as many neurons under this name, so its type label is broader.
- The rule also counts 22 left versus 26 right for all single prothoracic nerves
  (sensitivity count). The direction of any T1 count difference therefore depends
  entirely on how each dataset assigns hair-plate afferents to the ventral prothoracic
  nerve versus the prothoracic leg nerve.

**3. The numbers that would have fed the labels do not match each other.** These are not
labels and support no conclusion.
- Primary rule, T1: count difference −4, median-cable ratio 0.76 (in the indeterminate
  band), summed-cable ratio 0.41.
- The sensitivity count reverses the direction of the count difference.
- BANC also shows large asymmetries in other segments under the primary rule (T3: 24 vs
  9), while MaleCNS does not. So this rule produces noise rather than a comparable
  measure.

**MaleCNS (reproduced, consistent with earlier analyses).**
- RF/LF median output-synapse ratio 0.39 (358 vs 918 synapses).
- Summed ratio 0.29.
- T2 and T3 ratios 1.81 and 0.67.

## What this means

- The preregistered integrity bar caught a real problem, although it was not the one it was
  written for.
- Comparing type-name counts across connectomes is not valid here. BANC's SNpp45 label and
  its nerve assignments are not equivalent to MaleCNS's.
- A defensible cross-check needs neuron-level identity, not type names. One option uses
  BANC's own `malecns_match` / `manc_match` columns, or a connectivity criterion.
- Any such check is a separately versioned question (V2) with new preregistered rules. It
  is not a rerun of V1 with the bar moved. None has been designed, and the decision is the
  user's.

## Limits

- Two animals.
- The size proxies differ (BANC cable length vs MaleCNS output synapses).
- Structural only.
- The post-hoc tables above are diagnostic, and no conclusion rests on them.

## Files and checks

- `malecns_backend/embodiment/rf_hair_plate_banc.py` (read-only analysis).
- `tests/test_rf_hair_plate_banc.py`: 11 synthetic tests. They passed, together with the 4
  Step A tests (15 in total).
- `docs/evidence/rf-hair-plate-banc-v1/{protocol.json,run/result.json,run/console.txt}`.
- `.gitattributes`.
- Docs: the design, this file, the status line, the handoff and the roadmap.

```bash
cd "$HOME/Documents/FlyBrainUnity" && PYTHONPATH="$PWD" "$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" -m malecns_backend.embodiment.rf_hair_plate_banc --cache .cache/malecns-v1 --output .cache/rf-hair-plate-banc-repro.json
```

Expected output, in seconds: `INCONCLUSIVE_INTEGRITY`, with only I3 false.
