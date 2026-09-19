# M5D-5B1 pre-intervention contact diagnostic

## Immutable Scientific Run #1

`proprioceptive_closed_loop_100ms.json` was copied byte-for-byte to
`proprioceptive_closed_loop_100ms_scientific_run_1.json`. Its raw SHA-256 is
`a219b17a2796067513e5b250deabf62c0e7c96cc44176d0efa29b1183c0425c8`.
The historical result remains **COMPLETE / PRE_INTERVENTION_DIVERGENCE**. Nothing
in this audit reclassifies the run or gives C10-C12 a causal interpretation.

## Evidence limitation

The live adapter accumulated full rows in memory, but `run_canonical_pair`
passed them to `analyze` and serialized only the reduced report. Consequently,
Scientific Run #1 does **not** contain the raw condition rows requested by this
audit. No rerun was made. The detailed contacts below are corroborating t=0
rows in the already-preserved M5D-4A artifact, produced by the same `_make_live`,
`_pairs`, and `contact_metadata` path. They are recorded explicitly as
corroboration rather than falsely presented as retained Run #1 telemetry.

## t=0 contacts

Each condition has two duplicate solver contacts. Per-contact force/wrench was
not recorded by this contact metadata path (the separate 36x3 contact-force
array is all zeros at this sample).

| condition | index | geom1 id/name/semantic | geom2 id/name/semantic | position | distance | force |
|---|---:|---|---|---|---:|---|
| enabled | 0 | `20`, `0/LHCoxa`, `LHCoxa` | `36`, `0/RHCoxa`, `RHCoxa` | `[-0.2916761852081384, -2.498731083155903e-11, 1.158427759226986]` | `-0.02453605937522539` | not recorded |
| enabled | 1 | `20`, `0/LHCoxa`, `LHCoxa` | `36`, `0/RHCoxa`, `RHCoxa` | same | `-0.02453605937522539` | not recorded |
| disabled | 0 | `20`, `1/LHCoxa`, `LHCoxa` | `36`, `1/RHCoxa`, `RHCoxa` | `[-0.2916761852081384, -2.498731083155903e-11, 1.158427759226986]` | `-0.02453605937522539` | not recorded |
| disabled | 1 | `20`, `1/LHCoxa`, `LHCoxa` | `36`, `1/RHCoxa`, `RHCoxa` | same | `-0.02453605937522539` | not recorded |

The validated M5D-4B semantics treat a geometry pair as unordered, normalize a
valid name with `rsplit("/", 1)[1]`, sort the contact list, retain all numeric
metadata, and retain raw IDs when either name is unresolved. Under that exact
comparison both lists are equal. The diagnosis is **CONTACT_NAMESPACE_ONLY**.

## Initial physical state

Zero-tolerance comparison has no numeric differences: qpos, qvel, qacc, ctrl,
42 actions, six tibia angles, baseline targets, previous-target histories, and
contact-force arrays compare equal. The strongest direct Run #1 evidence is
that qpos/qvel/qacc/contact forces precede `contact_set` in its fail-fast scan,
and C4/C5 place the first action/ctrl differences at 13.5/13.6 ms. Because raw
rows were discarded, baseline/history values cannot be independently printed
from Run #1; this limitation is preserved in the JSON diagnostic.

## Comparator audit and correction

The defect was the call to generic `_equal(a[field], b[field])` for every
pre-intervention field in `proprioceptive_closed_loop.py`. It compared
instance-qualified names literally. M5D-4B already provides
`compare_contact_sets`, which uses exact basename normalization, unordered pair
semantics, deterministic list ordering, fail-closed unresolved IDs, and exact
numeric metadata. M5D-5B now delegates **only** `contact_set` to that validated
comparator. No model or scientific parameter changed.

## C1 and C2

C1 is the first enabled row with a nonzero newly mapped extensor/flexor spike
increment; C2 is the first enabled row with a nonzero decoder raw contribution.
Decoder low-pass carryover can in principle make C2 later than a motor spike,
but it cannot be established here: the report retained neither per-update
observer/decoder values nor motor counts (the per-leg summary fields stayed at
their defaults). LM is only an inference from its unique C4=13.5-ms first
command divergence. Exact requested spike counts, states, activations,
antagonist, and raw/admitted values are therefore **unresolved**, and no C1 or
telemetry fix was made. Manufacturing those numbers would rewrite the evidence.

## Tactile attribution

Run #1 retained no tactile time series or tactile divergence reductions.
Physical source, modeled rate, candidate-event, and delivered-event first
divergences are all unresolved; `first_feedback_channel = UNRESOLVED`. Thus the
22-ms proprioceptive delivery observation cannot uniquely attribute later CNS
divergence. C10-C12 remain non-causal observations.

## Disposition

A Scientific Run #2 is scientifically justified as a *new run* because the
contact comparator defect is proven and corrected. It was not executed here.
Run #2 must also preserve enough raw or reduced tactile and decoder telemetry to
resolve the explicitly documented gaps before any feedback attribution claim.
