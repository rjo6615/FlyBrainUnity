# LF native target orientation results V1

2026-10-25; fresh baseline9553c77 (merged PR278). Protocol, implementation and
tests committed **b967c8a33dc644175e06d790855e08459ea0a7cd before ONE campaign**.
No retry, altered pose set, offset fitting, tolerance change or parameter tuning.

**TARGET_ORIENTATION_GEOMETRY_VERIFIED_TRANSFER_BLOCKED**: all15poses and196
native observations pass integrity, joint-limit and declared orientation checks.
This is a measured native kinematic result, not simulated neural behavior.

| Metric | Maximum observed error | Fixed budget |
|---|---:|---:|
| Relative coxa orientation matrix |1.1102230246251565e-15|1e-10|
| Instantaneous target basis |2.220446049250313e-16|1e-10|
| Target-coordinate finite-difference axes |1.4716783347523688e-11|1e-7|
| Native versus modeled Jacobian |2.220446049250313e-16|1e-7|
| Source-to-target chain finite-difference axes |2.1762546045127166e-10|1e-7|

The native zero-pose basis agrees exactly with registered B_G=I (max error0).
Maximum native basis/J condition numbers1.059125888334738/1.598328954562319,
both below the fixed100bound. All196samples, including differences, are in range.
No fitted frame alignment or axis/sign permutation was used.

## What actually ran

One native FlyGym body initialized through the existing locked factory; no source
model was rerun. Exact source poses/axes/map and original source evaluator reused.
Native identity and complete inventory match the accepted isolation context.
The unique Thorax is body3; LF coxa is body13, ancestry13->3->2->1. Selected
yaw/pitch/roll joints1/2/3 use qpos7/8/9, DOFs6/7/8 and actions2/0/1.

- Initialization:7explicit `mj_forward`,3explicit resets,0integration/CNS.
- Probe phase:196explicit `mj_kinematics`,0forward/reset,0integration/CNS.
- All six integration entry points guarded. Whole input states preserved through
  each observation; time, velocities, activation/control and applied buffers zero.
  Model and initialized state identities are unchanged at the end.
- Existing position-actuator parameters remain unchanged. Initializer forwards
  can compute forces; the probes compute only kinematics. Zero unused controls
  are not claimed to suppress a position actuator or demonstrate equilibrium.

New LFS record `evidence/lf-target-orientation-v1/run/validation.json`:
7,931,285bytes; raw SHA256
`5daa911adc01cc42e4f40576a47ff87024497ec23309e3a01645b66815db27c9`.
Every reference/base/target-difference/chain-difference observation is retained.

## Software verification

- Before campaign:37passed/11skipped in43.77s across orientation and source-pose
  tests. The11prospective saved-record checks were explicitly skipped because
  no campaign existed yet. An earlier34pass/3setup errors was a missing parent
  scratch directory; creating that directory resolved it without scientific edits.
- After campaign:71passed in58.58s across orientation, source-pose and native
  isolation tests. Saved-record tests verify all raw-state/identity/API guards and
  rejection of missing poses/samples, time advance, force injection, count/source
  changes, center/shape/body tampering. A synthetic proper-rotation mismatch is
  classified as disagreement, not hidden as a raw-integrity failure.
- Then corrected five synthetic ownership-test fixtures to resolve the actual
  unique Thorax index instead of assuming body1; added a valid-fixture assertion.
  All5passed in0.97s. Runner, evaluator, protocol and recorded campaign unchanged.
- Static preflight is tested with native construction/kinematics/forward/step,
  solver and live-audit entry points forbidden. Reference/mock tests are distinct
  from the one actual native campaign. No new physics integration or CNS run.
- Saved Windows Git Bash replay passed without native execution. Staged
  whitespace and LFS-pointer checks passed.

## Limits and roadmap

The existing modeled finite-angle orientation convention agrees with the native
LF joint/body frames at these15prescribed poses and their declared differences.
This does not establish a general pose envelope, tendon attachment equivalence,
length/velocity transfer, physical force calibration, anatomical neuron binding,
neural activation law, causal balance or gait. Original failed raw prerequisites
remain false; no old hash or failure was changed. Production remains20/42,
new admissions0. No new Unity behavior is introduced.

Next: audit the four selected source tendon routes, exact site/body ownership and
available target attachment/landmark authorities. Identify what is needed for
length/velocity registration, preserving missing correspondences and unresolved
unit lineage. Do not infer target attachment sites from matching names, copy a
path scale or enable force coupling. Physical/anatomical/neural/raw gates remain.

## Windows Git Bash after merging

This reviews saved measurements; it does not rerun the native assay.

```bash
cd ~/Documents/FlyBrainUnity &&
git switch newBrain &&
git pull --no-rebase --no-edit &&
git lfs pull --include="malecns_backend/embodiment/interface_output/integrated_whole_leg_readiness.json,docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather,docs/evidence/lf-pose-force-v1*/run/validation.json,docs/evidence/lf-activation-transient-v1/run/validation.json,docs/evidence/lf-activation-integrator-v1/run/validation.json,docs/evidence/lf-native-isolation-v1*/run/validation.json,docs/evidence/lf-synthetic-coupling-v*/run/validation.json,docs/evidence/lf-target-orientation-v1/run/validation.json" &&
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" &&
"$PY" -m malecns_backend.embodiment.lf_target_orientation \
  --report docs/evidence/lf-target-orientation-v1/run/validation.json
```

Expected: `ORIENTATION EVIDENCE VERIFIED`,
`TARGET_ORIENTATION_GEOMETRY_VERIFIED_TRANSFER_BLOCKED`,15poses/196recorded
kinematics probes,0integration/CNS,20/42 and0new admissions. Counts refer to the
archived campaign; review executes no native calls. Unity can remain closed.
