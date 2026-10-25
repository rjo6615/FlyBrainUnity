# LF force-reference fixture results

2026-10-25. Fresh branch from origin/newBrain 29a8e3c, merged PR #267. Production
remains 20/42, no new neural admission, decoder, drive, physiological force law,
ordinary tactile change or Unity run. Existing results/local edits remain intact.

## Implemented and verified

The separate reference adapter projects four nonnegative, explicitly supplied
tendon tensions into three generalized torques through the frozen local covectors.
It reuses the existing exact identities, covector verifier and generic DOF
resolver. Broad promotors remain excluded/unassigned because their anatomical
binding is unresolved; no activity ranking or individual tendon assignment.

The native synthetic fixture has a free root, a nonselected hinge, and three LF
reference hinges. Exact native joint/body/hinge metadata resolves DOFs 7/8/9 and
qpos addresses 8/9/10, distinct from logical action indices 2/0/1. Its axes are
X/Y/Z at the exact reference configuration. It has no actuator, contact, tendon,
gravity, damping or friction. The adapter rejects a position-actuated model,
changed pose/velocity/time, foreign force, double apply and unsafe clearing.
It owns only three force entries. This is an instantaneous reference interface,
not a complete muscle or position decoder and not a production fly adapter.

V1.1 protocol/correction committed at **276c4f1 before execution**. All six fixed
conditions ZERO, four separate unit-tendon loads, and MIXED [.25,.5,.75,1] passed.
Each uses fresh data, with baseline/applied/cleared snapshots. The independent
Python API counter observed exactly **18 mj_forward calls and 0 mj_step calls**
across preflight and execution. No time integration or CNS transition occurred.
These are real native MuJoCo 3.2.7 calculations, not mocked physics. Compiler-
internal calculations are not described as only 18 total arithmetic operations.

| Check | Largest observed absolute error | Declared limit |
|---|---:|---:|
| Applied force versus independent R_M/J projection | 8.673617379884036e-18 | 1e-12 fixture torque units |
| Native M*qacc minus applied generalized force | 7.806255641895632e-17 | 1e-10 fixture torque units |
| Virtual work across the local coordinate transform | 4.336808689942018e-19 | 1e-12 fixture work units |

All nonselected applied forces were exactly zero; clearing removed all applied
torque and returned acceleration to zero within the declared tolerance. Poses,
velocities and time stayed unchanged. Nonselected acceleration under load can
result from coupled inertia; it is not treated as force leakage or forbidden.
No threshold, gain, seed, force schedule or acceptance was tuned.

## Preserved v1 boundary failure

Initial protocol/code committed at 8228e84 before v1. Its fixture-array checks
passed, but the strict saved-review test failed: the inherited audit's inventory
path constructs a FlyGym model and initializes native forward dynamics. Those
initialization calls were outside the fixture counter. V1 therefore cannot
substantiate the claimed total-operation count or construction-free preflight/
review. The record is unchanged, with a separately added context audit explaining
this rejection. No CNS/integration transitions were identified; those are distinct
from model construction/non-integrating forward calls.

V1.1 fixes the implementation boundary, not acceptance. A local static replay
uses the original locked protocol builder and v2/v3 metadata derivations without
live enumeration or fabricated physical records. It reuses original source-lock,
identity/alias, remaining-row, recruitment-null, covector and official-source
validators. All 22 remaining rows and all exact LF source records reproduce.
This verifies static current admission metadata, not a newly compiled fly's body.
The strict test now forbids forward dynamics, integration and live enumeration in
preflight/saved review. The separately observed execution counter must equal 18.
Original historical audit/crosswalk implementations/artifacts were not rewritten;
their inventory commands still have the construction side effect documented here.

Full matrix at discovery: **71 passed / 1 failed** (strict saved-review boundary).
After the committed v1.1 correction and justified fixed repeat: **74 passed in
26.60 s** (29 new adapter/fixture tests, 45 existing reference/audit tests).
The two added tests cover independent call-count tampering and preserved/rejected
v1 provenance. Initial development tests had 19 pass / 1 temporary-directory setup
error / 7 deselected; the missing parent directory was created and the affected
test passed. V1.1 development tests then passed 20, with seven saved-output tests
not yet run before the archive existed. No failures were hidden or tests weakened.

Actual v1.1 execute CLI passed; exact saved-review command passed in Windows Git
Bash in 5.04 s with the validated environment. Saved review performs no dynamics.
The full matrix also contains native fixture and legacy model-inventory checks;
these are implementation/reference checks, not a neural recruitment experiment.
Whitespace checks pass. No dependency changes or expensive fly/CNS trial reruns.

## Evidence and limits

- `docs/evidence/lf-force-reference-v1/validation.json`: preserved initial native
  fixture arrays, 143158 bytes, SHA256
  `5f632b45ea9e5e4948a40bed97539a6428706b4fa7385b7e408c8918153a1f9f`.
- `docs/evidence/lf-force-reference-v1/context-audit-v1_1.json`: explicit rejection
  of v1 total-operation/construction-free-review provenance, with discovery trace.
- `docs/evidence/lf-force-reference-v1_1/validation.json`: accepted separately
  versioned fixture evidence, 144328 bytes, SHA256
  `13d025213360dfb79a9ec46444fd86125cb7115693cb2ec01c4320bb066e3943`.

Both native records retain full mass matrices, qacc, poses, applied/other forces,
metadata, exact conditions, source hashes and evaluations. V1.1 saved review
recomputes every numeric check and reference/source identity; it does not claim
to regenerate archived native dynamics from JSON. V1 is rejected by that reviewer.

Only an exact local reference pose is supported. Synthetic tension/length/torque
units are declared test units, not SI or calibrated biological forces. No spike-to-
activation, passive muscle law, physiological peak force or force-to-position
transfer is assigned. Individual neurons remain unbound to model tendons. Original
historical raw prerequisites remain false in CRLF representation and are not
waived by fixture success. No new admission, balance, gait or biological claim.

Next specify pose-dependent mechanics and activation/passive-force/units transfer,
including selective actuator replacement to avoid double actuation in a moving
fly. Declare numerical/application gates and satisfy original raw prerequisites
before a separate neural coupling experiment. Do not attach these constant local
covectors to arbitrary poses or use a larger gain to obtain movement.

## Changed files and purpose

- `docs/LF_FORCE_REFERENCE_V1.md`: prospective fixed fixture protocol/units/checks.
- `docs/LF_FORCE_REFERENCE_V1_1.md`: boundary defect and prospective correction.
- `docs/fixtures/lf-force-reference-v1.xml`: isolated native fixture, no actuators.
- `malecns_backend/embodiment/lf_force_reference.py`: four-tendon reference adapter,
  exact pose/DOF/force ownership guards; no neural decoder.
- `malecns_backend/embodiment/lf_force_static_reference.py`: construction-free reuse
  of original validators/locks and static admission authority.
- `malecns_backend/embodiment/lf_force_reference_validation.py`: explicit execute,
  observed API counts, complete archive/evaluator and dynamics-free saved review.
- `tests/test_lf_force_reference.py`: native/invalid-state checks, strict review
  boundary, tamper rejection and preserved v1 failure.
- The three evidence files listed above: original, context audit and corrected run.
- `docs/LF_FORCE_REFERENCE_RESULTS.md`: findings, validation and manual commands.
- `docs/LEG_MAPPING_STATUS.md` and `docs/PROJECT_HANDOFF.md`: scope/current milestone
  and remaining scientific/engineering gates.

## Git Bash after merging

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
git lfs pull --include="docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather"
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m malecns_backend.embodiment.lf_force_reference_validation --report docs/evidence/lf-force-reference-v1_1/validation.json
code docs/LF_FORCE_REFERENCE_RESULTS.md
```

Expected: FIXTURE VERIFIED; six cases / 18 recorded explicit native fixture forward
calls; zero integration/CNS transitions; current 20/42, no new admission. This reads
saved results without native dynamics. The original raw-prerequisite flag remains
false in this Windows checkout. No Unity run required.

Optional unit/reference checks (fresh temp directory name):

```bash
"$PY" -m pytest -q -p no:cacheprovider --basetemp="$PWD/.pytest-tmp-force-manual-v1_1" tests/test_lf_force_reference.py tests/test_lf_anatomical_crosswalk.py tests/test_lf_proximal_binding_review.py tests/test_remaining_leg_admission_audit.py
# Expected: 74 passed. Includes native fixture implementation tests, no CNS experiment.
```

Optional zero-dynamics preflight: `"$PY" -m
malecns_backend.embodiment.lf_force_reference_validation --preflight`. Do not rerun
archived execution simply to review it; all output namespaces refuse overwrite.
