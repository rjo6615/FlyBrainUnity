# Milestone 4B-2: simultaneous six-tibia causal experiment

`python -m malecns_backend.embodiment.six_tibia_causal` runs two fresh,
same-seed 500 ms experiments. Each experiment has one MaleCNS runtime and one
body. All six validated 4B-1 chordotonal populations feed that shared runtime,
and six independent observer/filter/decoder states read the authoritative
annotation-derived motor populations. The closed run applies each decoder's
output; the control computes the same outputs but applies zero neural
contribution. All non-tibia position actuators remain measured-position holds.

Use `--json PATH` to write the compact summary. High-frequency samples remain
in memory and are deliberately not committed. The command requires the normal
MaleCNS artifacts and a compatible FlyGym installation; unit tests use mock
brain/body implementations without inventing experimental results.

## Causal interpretation

The analyzer first verifies closed/control equivalence before the first applied
motor contribution. It then enforces the order motor spike → decoded output →
applied output → physical divergence → sensory-rate divergence → CNS-spike
divergence → mapped-motor divergence. A contradiction yields `INVALID`.
`S0`–`S7` are engineering causal stages, not biological behavior or walking
scores. Body pose/contact differences are descriptive only.

## Provenance and safeguards

Angles are `PHYSICS_MEASURED`; chordotonal rates are
`MODELED_TRANSDUCTION`; MaleCNS propagation is `CONNECTOME_DERIVED`; motor
identity is `ANNOTATION_DERIVED`; offsets are `MODELED_MOTOR_DECODING`; and
range/slew limits are `ENGINEERING_CONSTRAINT`. There is no gait, CPG,
behavior/posture controller, engineered cross-leg coupling, descending drive,
training, or tuning. Existing neural, sensory, motor-decoder, timestep, seed,
mapping, and actuator constants are unchanged.
