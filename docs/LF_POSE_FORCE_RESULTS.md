# LF pose/source-force reference results

2026-10-25. Fresh branch from origin/newBrain 0eba000, merged PR #268. Current
production remains 20/42. No neural law/gain/drive/seed, production actuator,
ordinary tactile mode, old source lock or existing result was changed.

## What is implemented

A separately declared rotational correspondence maps source LFCoxa orientation
changes onto intrinsic XYZ target coordinates. At each sampled pose it computes
J=inverse(B_G)*B_M and R_G=inverse(J)^T*R_M, using native source hinge axes and
tendon derivatives. This is an explicit new modeling convention; it matches
rotational changes, not translations, attachment geometry, different inertias or
an actual finite-angle FlyGym body registration. The old local registration and
its limits remain intact.

The source XML matches the original frozen raw hash. All **71 referenced mesh
files / 13961614 bytes** were hashed before measurements in the committed input
manifest and rechecked afterward. No source asset/model/environment modifications.
Validated MuJoCo 3.2.7 compiles the source previously exported with 3.3.2; central
J/R reproduction is checked rather than assumed across those versions.

The fixed 15-pose campaign uses the original default qpos, six individual +/-
.05-rad co​​xa offsets and eight +/- .05-rad corners. Each observes activation
0/.5/1 and six +/-1e-6 derivative probes; two central activation-derivative probes
complete **137 explicit mj_forward calls**. The API counter observes mj_step=0.
All measured data have zero time and velocity, with no integrated trajectory/CNS.
Compiler-internal validation calculations are not claimed to be absent or included
in that explicit API count. All nonselected native muscle/passive contributions
remain recorded; they are not removed to improve force reconstruction.

## Preserved failed v1 and explicit correction

Protocol, code and input locks committed at **51a22f3 before v1**. All 137 calls
completed, but v1 failed: selected moment arms and total-force reconstruction were
wrong, while orientation/Jacobian and direct muscle gain/bias/dynamics checks
passed. MuJoCo stores actuator moments with sparse row descriptors; the code
incorrectly reshaped allocated storage as dense rows. Allocated size alone did
not justify that representation. The native central tendon-length differences
already present in the failed record reproduce the old R_M within 2.765e-11,
isolating the representation defect without a new pose or threshold search.

V1 remains failed and byte-identical in Git LFS. The documented v1.1 correction
was committed at **7b9bbad before the justified fixed repeat**. It calls native
mju_sparse2dense and records raw sparse values/counts/row addresses/column indices
alongside the dense matrix. Saved review independently reconstructs the matrix
with SciPy CSR and checks agreement. Model parameters, pose schedule, epsilon,
numerical criteria and scientific scope are unchanged. No historical failure was
converted to a pass or omitted.

## V1.1 observed results

All fixed poses/conditions and checks pass. The central J and four R_M columns
reproduce the frozen reference within 1e-10. Across all poses:

| Numeric check | Maximum observed absolute error | Declared limit |
|---|---:|---:|
| Native tendon moment versus length derivative | 1.888907e-10 | 1e-7 |
| Native source axes versus rotation derivative | 8.921397e-11 | 1e-7 |
| Pose-map J versus coordinate derivative | 2.220446e-10 | 1e-7 |
| Rotation reconstruction | 1.110223e-15 | 1e-10 |
| Gain*activation+bias versus native selected force | 0 | 1e-8 |
| Muscle dynamics helper versus native act_dot | 0 | 1e-6 |
| All transmissions/forces versus qfrc_actuator | 1.776357e-15 | 1e-8 |
| Virtual work across the declared map | 5.551115e-17 | 1e-9 |

Units are the declared native reference/model units, not calibrated SI or
cross-body force units. Native helper comparisons establish source-code/component
fidelity, not independent biological force-law validation. Finite-difference
geometry checks use a separate measurement path.

The largest absolute J change from the central reference is 0.02433096925. Maximum
absolute R_G component changes by tendon (remotor/adductor/anterior/posterior)
are 0.0062910330 / 0.0025675624 / 0.0033262190 / 0.0035620170 native length units.
These are descriptive maxima over all predeclared poses, not selected gains or a
validated continuous range. They show why the central constants must not simply
be attached to a moving body.

At the central reference, selected tensile magnitudes (-native actuator_force):

| Tendon class | At activation 0 | At activation 1 | Passive component |
|---|---:|---:|---:|
| Pleural remotor/abductor | 0 | 27.39685925 | 0 |
| Sternal adductor | 0 | 12.76448479 | 0 |
| Sternal anterior rotator | 11.60235359 | 18.45632371 | 11.60235359 |
| Sternal posterior rotator | 0 | 156.98596208 | 0 |

Thus zero activation does not mean zero total source force. At raw control zero,
the selected control floor is .0001; at activation zero the recorded derivative
is +2 /s for all four selected actuators, not a zero-activation equilibrium.
At activation .5, raw control 0/1 gives -1562.1875 /s and +4000 /s. The source
parameters are .0001/.0004 seconds for activation/deactivation before native
state-dependent factors. These are existing model choices, not measured MaleCNS
physiology or a recommendation to copy them into the CNS/FlyGym interface. No
activation transient, numerical integration stability or emergent movement was
tested by these instantaneous observations.

## Evidence and actual validation

- Failed v1: docs/evidence/lf-pose-force-v1/run/validation.json, 3222353 bytes,
  raw SHA256 5413ad619c1f8b3fb08b2468c9dc3667cd715365246f7ca933e5ebc10aba6252.
- Accepted v1.1: docs/evidence/lf-pose-force-v1_1/run/validation.json, 4659217 bytes,
  raw SHA256 24332543da1d4b8a1c475bef518c334058cb95c9ecad8c5a4173c0043d0449fe.
- Both full native records are retained through LFS, including all conditions,
  activation/control/force arrays, moment data, source/asset hashes and evaluations.
- **99 passed in 32.86 s**: 25 new pose/source-integrity checks and 74 existing
  force/reference/audit checks. Includes corruption rejection, preserved failed
  v1 identity, sparse-format defect, geometry/virtual work and strict model/dynamics-
  free preflight/review. Matrix includes native fixture implementation/legacy model
  inventory checks; no result is presented as a CNS or behavioral experiment.
- Initial development subset: 12 passed / 7 archived-output tests not yet run /
  one warning from the deliberately rejected gimbal-lock case. Corrected development
  subset: 18 passed / 7 archived-output tests not yet run; expected warning checked.
- Actual corrected execute CLI passes. Exact saved-review CLI passes in Windows
  Git Bash in 5.10 s. Review constructs no model and runs no dynamics; optional
  --model only rechecks external source/assets as bytes.
- Whitespace and LFS object identity checks pass. Existing SciPy and physics
  packages reused; no dependency changes. No Unity Editor run or production change.

## Remaining gates and next task

The new orientation map is not an independently established finite-angle anatomical
registration to FlyGym. Native mass/force units are not independently tied to
the production body or SI. No spike-to-activation relationship, per-neuron tendon
binding or biological peak force is established; broad promotors remain unresolved.
Original raw scientific prerequisites are still false in the recorded CRLF checkout
and are not waived by source-reference success. Admission remains 20/42.

Next separately specify bounded source activation-transient/integration validation
and baseline semantics, with the native control floor and passive preload retained.
Establish force units/physical registration before a current-body application;
do not copy native peak force or time constants as biological calibration. Future
matched arms need identical passive/preload context. Exact selective replacement
of the three co​​xa position actuators must precede torque application while keeping
the other 39 controls intact, rather than disabling production wholesale or double
actuating. No moving-fly neural coupling until these numeric/application and raw
prerequisites pass. Do not tune neural thresholds, gains or drive for movement.

## Changed files and purpose

- .gitattributes: LFS rule for both separately versioned native records.
- docs/LF_POSE_FORCE_V1.md: prospective poses, map convention, force/dynamics scope,
  numeric checks, units and production-replacement boundary.
- docs/LF_POSE_FORCE_V1_1.md: sparse-format defect and pre-repeat correction.
- docs/evidence/lf-pose-force-v1/input-manifest.json: pre-measurement XML/asset locks.
- docs/evidence/lf-pose-force-v1/run/validation.json: preserved failed native run.
- docs/evidence/lf-pose-force-v1_1/run/validation.json: corrected native evidence.
- malecns_backend/embodiment/lf_pose_force.py: rotational map, source-only assay,
  sparse conversion, independent evaluator and dynamics-free review CLI.
- tests/test_lf_pose_force.py: map/source/format/integrity/boundary checks.
- docs/LF_POSE_FORCE_RESULTS.md: complete outcomes, limits and actual validation.
- docs/LEG_MAPPING_STATUS.md and docs/PROJECT_HANDOFF.md: checkpoint and remaining gates.

## Git Bash after merging

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
git lfs pull --include="docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather,docs/evidence/lf-pose-force-v1*/run/validation.json"
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m malecns_backend.embodiment.lf_pose_force --report docs/evidence/lf-pose-force-v1_1/run/validation.json
code docs/LF_POSE_FORCE_RESULTS.md
```

Expected: POSE/FORCE REFERENCE VERIFIED; 15 poses / 137 recorded explicit forward
calls; no integration/CNS; current 20/42 and new admissions 0. This reads saved
evidence without native model construction/dynamics. No Unity run or local
FlyMimic mesh installation is needed for review. Recorded original raw flag remains
false. Rechecking the local source bytes is optional with
`--model "$HOME/Documents/FlyMimic/flymimic/assets/models/best_combined_cvt3.xml"`.

Optional tests (fresh temporary directory name):

```bash
"$PY" -m pytest -q -p no:cacheprovider --basetemp="$PWD/.pytest-tmp-pose-manual-v1_1" tests/test_lf_pose_force.py tests/test_lf_force_reference.py tests/test_lf_anatomical_crosswalk.py tests/test_lf_proximal_binding_review.py tests/test_remaining_leg_admission_audit.py
# Expected: 99 passed. Includes native fixture implementation checks, no CNS experiment.
```
