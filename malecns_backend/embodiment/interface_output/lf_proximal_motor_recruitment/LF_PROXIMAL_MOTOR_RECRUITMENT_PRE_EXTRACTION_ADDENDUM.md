# LF proximal motor recruitment: pre-extraction addendum

**Status: `FROZEN_BEFORE_EXTRACTION_NOT_EXECUTED`**

This addendum freezes the previously missing, outcome-independent M8 source
interval rule. It does not alter the original recruitment preregistration or
the previous M8 assessment. That assessment correctly remains a provenance
failure because this checkout contains a Git LFS pointer rather than the raw
archive.

The authoritative Windows archive identity was supplied from an independent
verification outside this checkout: the expected path is
`malecns_backend/embodiment/interface_output/m8_extended_spontaneous/m8_raw.npz`,
the required byte size is `345584215`, and the required SHA-256 is
`4e39bb83dd4455d56a4d88f717615530602317efaf83a6ed241b13af89dc2a5b`.
Codex did **not** verify those archive bytes. A future extraction utility must
match both size and SHA-256 before opening the archive or reading any scientific
array and must otherwise fail closed.

## Frozen selection and sample convention

From `CORRECTED_SPONTANEOUS_NEURAL_EMBODIMENT`, select the earliest eligible
contiguous 1000-ms interval, intended as `[0,1000)` ms. Copy only exact existing
samples at 1.0-ms cadence from the 0.1-ms physics series: source rows
`0, 10, ..., 9990`, at times `0, 1, ..., 999` ms. This produces exactly 1000
rows by six columns. The columns, in order, are `5, 12, 19, 26, 33, 40` for
`joint_LFTibia`, `joint_LMTibia`, `joint_LHTibia`, `joint_RFTibia`,
`joint_RMTibia`, and `joint_RHTibia`, in radians.

The 1000-sample convention follows the frozen protocol's 1000-ms runtime,
1-ms sensory cadence, left-closed/right-open windows, and total of 2000 neural
steps at 0.5 ms. The selected runtime applies one sensory input for each 1-ms
control interval and advances two neural steps. The original text did not list
timestamps or explicitly distinguish inputs from endpoint states, so this
addendum makes that necessary convention explicit: the state at 1000 ms is an
endpoint, not a 1001st replay input.

No interpolation, smoothing, averaging, synthetic values, timestamp
substitution, or outcome-dependent selection is allowed. Candidate motor
activity must not influence interval selection. M8 neural row `i` corresponds
to physics row `5*(i+1)` at the same 0.5-ms timestamp, but that fact is context
only: the replay contains physical tibial `physical_joint_position` values,
never `neural_sensory_encoded` values.

## Scope and interpretation

The physical angles are FlyGym/MuJoCo measured joint coordinates. Sensory
transduction remains the existing modeled proprioceptive encoder; this does not
establish biological proprioception. Any future candidate “recruitment” means
condition-dependent activity in the current MaleCNS runtime, not biological
motor function.

Only deterministic replay extraction is authorized after pre-open verification
of the authoritative M8 size and SHA-256. Recruitment scientific execution is
not authorized unless every other frozen prerequisite is satisfied. No replay
was created, no M8/physics/neural runtime was run, no candidate outcome was
read, the active 11-channel motor interface was not changed, and no decoder
weight or coordinate sign was assigned.
