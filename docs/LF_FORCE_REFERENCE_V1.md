# LF force-reference adapter v1

Prospective implementation-validation protocol, 2026-10-25. Baseline
origin/newBrain 29a8e3c (merged #267). Commit this protocol, fixture, adapter,
runner and tests before the archived six-case validation. Development unit tests
are implementation checks, not a preregistered biological experiment.

## Scope and reference

Question: can four separately retained LF tendon covectors project known tensile
loads into the correct compiled generalized-force entries, without double
actuation, accumulation, residual force or a sign/basis error?

Reuse the official-source crosswalk reviewer, existing seven-covector verifier,
exact body-ID/dense/alias authority and generic `resolve_dof` observer. The four
class hypotheses, in fixed order, are pleural remotor/abductor, sternal adductor,
sternal anterior rotator and sternal posterior rotator. The broad promotor and its
three alternatives remain unassigned and excluded, based on the atlas's unresolved
binding rather than activity. No individual neuron is bound to a model tendon.

Use the frozen R=-dL/dq and R_G=J^(-T)R_M, basis
[joint_LFCoxa_yaw, joint_LFCoxa, joint_LFCoxa_roll]. Projection is tau_G=R_G*T,
where the columns are the four separate tendons. No extra anatomical sign flip,
normalization, angle conversion, fitted gain or component selection.

## Units, activation and pose boundary

This is a synthetic mechanical fixture, not the fly body. One fixture length unit
is identified with one reference model-length unit solely for coefficient tests;
one fixture force unit is an arbitrary test unit. Torque is fixture force times
reference length, mass/time units are consistent with the synthetic XML. No SI,
biological peak force or force-scale transfer to FlyGym is established.

T is an explicitly supplied, instantaneous nonnegative test tension. There is no
spike-to-activation law, activation dynamics, passive muscle tension, neural drive
or inferred physiological gain. Fixture passive forces are zero. Those terms
remain unassigned for future biological coupling, not implicitly modeled as absent
in the animal. No new rate decoder or observer is added.

Only the exact initial reference configuration is supported: all hinge angles
and velocities zero, root at its initial transform, time zero. The constant
covectors cannot be applied at another pose; there is no claimed finite-angle
range. Reject changed qpos, qvel, time or model metadata before mutation. `project`
alone computes a reference coefficient product, not a pose-dependent action.

## Compiled fixture and isolation

`docs/fixtures/lf-force-reference-v1.xml` has a free root, one nonselected hinge
and the three serial reference hinges. Their action indices 2/0/1 are deliberately
different from joint IDs, qpos addresses and qvel/force DOF addresses. Resolve the
native joint/body/type/address metadata exactly; expected DOFs 7/8/9 and qpos
addresses 8/9/10. Require the native world axes to be X/Y/Z at reference.

Require zero actuators globally (nu=0), zero geoms/contacts, tendons, equality
constraints, gravity, damping and friction. Thus this adapter rejects the current
position-actuated production model instead of adding torque on top of it. No
production runner imports it. Reject pre-existing generalized/body force or a
second apply before clear; own only the three exact DOF entries. `clear` requires
the owned buffer to be intact and clears it without modifying qpos/qvel/time.
Nonselected accelerations may occur through inertia coupling; force isolation
does not require zero motion/acceleration elsewhere.

## Fixed archived conditions and independent checks

Run once, in order: ZERO=[0,0,0,0], REMOTOR=[1,0,0,0], ADDUCTOR=[0,1,0,0],
ANTERIOR=[0,0,1,0], POSTERIOR=[0,0,0,1], MIXED=[.25,.5,.75,1]. Fresh MjData
and adapter for each case. Compile the single fixture once with validated MuJoCo
3.2.7. Each case calls mj_forward at baseline, after apply and after clear: exactly
18 forward-dynamics evaluations, **zero mj_step/integration/CNS transitions**.
Keep every case and all native snapshots, including failures. No retry/sweep.

Checks required for each complete case:

- Independently compute expected torque from inverse(J).T and R_M, not the
  adapter's R_G product; maximum absolute applied-force error <=1e-12 fixture
  torque units. All nonselected applied entries must be exactly zero.
- Virtual work for fixed synthetic dq_M=[.013,-.027,.009] and dq_G=J*dq_M:
  tau_G dot dq_G = (R_M*T) dot dq_M, absolute error <=1e-12 test work units.
- Save native full mass matrix and full qacc. With bias/passive/constraint forces
  zero, require max abs(M*qacc-qfrc_applied) <=1e-10 fixture torque units.
  Do not compare acceleration component signs to torque signs.
- Native actuator/body forces zero, qpos/qvel/time unchanged in all snapshots;
  after clear, generalized force exactly zero and max abs(qacc)<=1e-10 fixture
  acceleration units. All snapshots finite; matrices correctly shaped.
- Exact source/reference hashes before/after unchanged; 20/42 admission unchanged,
  no decoder/sign/gain assigned, four external class hypotheses retained.

These tolerances are declared numerical implementation resolutions, not biological
acceptance. A failed fixture check is preserved and must not be weakened for a
pass. Source/implementation defects require a separately explained version before
repeating archived validation. Unit tests may exercise deliberate invalid inputs.

## Provenance and interpretation

Historical raw freezes remain reported separately. This synthetic fixture uses
the verified unchanged reference content; it does not satisfy or supersede failed
raw scientific prerequisites for later fly/CNS experiments. No old freeze/hash or
checkout is repaired by this update. Archive all raw native matrices, forces,
accelerations and poses. Saved review recomputes numeric checks without rerunning
dynamics; it must not claim it reconstructs native physics from JSON.

Successful result means reference projection/application/clearing work in this
fixture. It establishes neither biological force calibration, individual tendon
binding, a working neural muscle interface, production admission nor balance/gait.
Next is a separately specified pose-dependent force/activation transfer design and
its numerical gates; do not attach constant local covectors to a moving fly.

Primary mechanics references: [MuJoCo 3.2.7 actuation](https://mujoco.readthedocs.io/en/3.2.7/computation/index.html#actuation-model)
and [mj_forward](https://mujoco.readthedocs.io/en/3.2.7/APIreference/APIfunctions.html#mj-forward).
The latter computes forward dynamics without time integration.

## Git Bash after merge

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
git lfs pull --include="docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather"
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m malecns_backend.embodiment.lf_force_reference_validation --report docs/evidence/lf-force-reference-v1/validation.json
code docs/LF_FORCE_REFERENCE_RESULTS.md
```

Expected on success: FIXTURE VERIFIED, 6 cases / 18 recorded native forward calls,
0 integration/CNS transitions, current 20/42, no new admission. No Unity run.
