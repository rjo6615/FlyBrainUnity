# LF actuation contract: results and fly roadmap

2026-10-25. Fresh baseline origin/newBrain 5a3c8c4 (merged PR #271). Specification,
audit and tests committed at a96a4698ed98d0a597819c345e6cbc8542371cee before
generating the new static record. Historical source and results were preserved.

## Outcome

**STATIC_CONTRACT_VERIFIED_COUPLING_BLOCKED.** The design partition and state
ownership declarations pass the static checks. This is deliberately not a native
force-suppression result or permission to connect muscle forces to production.
The audit generated no model, forward call, integration, solver call, CNS
transition or model/state mutation. Production remains **20/42**, new admissions0.

The existing position-control adapter physically controls all42 joint coordinates,
including the22 not neurally admitted. A neural-admission flag does not remove
the corresponding position spring. The replacement context must therefore be
explicit in all arms of any future matched experiment.

## Exact historical target partition

The target order reuses the existing force-reference basis. These identities
belong to the hash-locked M5A recorded compiled model, not a current native capture.

| Coordinate | Action index | Actuator ID | Joint ID | qpos range | DOF range |
|---|---:|---:|---:|---|---|
| joint_LFCoxa_yaw | 2 | 2 | 1 | [7,8) | [6,7) |
| joint_LFCoxa | 0 | 0 | 2 | [8,9) | [7,8) |
| joint_LFCoxa_roll | 1 | 1 | 3 | [9,10) | [8,9) |

Qualified names are retained in the JSON: 0/joint_* and
0/actuator_position_joint_*. Transmission type0 denotes joint transmission;
joint type3 denotes a hinge, with transmission IDs [joint_id,-1]. These target DOFs6/7/8
are NOT the isolated synthetic force fixture's7/8/9. Never copy fixture addresses
into the fly. The record includes all39 other joint controls: all20 current neural
admissions and19 baseline position controls must be preserved.

A separate later historical signature records nq94/nv93/nu48/na0, all42 position
actuator names plus six adhesion names at recorded name IDs42..47. Those six
adhesion controls remain disabled/constant zero in the design. Their transmission
values are not available in that record. This signature is explicitly NOT asserted
equivalent to M5A: local name/order agreement cannot identify a different compiled
model. Full array hashes are recorded but do not supply their native values.

M5A body IDs and activation addresses are also unavailable, and remain null.
The later signature's na0 establishes that historical model has no native muscle
states. The four SOURCE fixture activation addresses0..3 are retained in their
own scope, with FlyGym activation addresses null and no individual neuron-tendon
assignments. They would describe four separate external states, not data.act
indices in the body model.

## What the design requires before execution

The proposed selective neutralization changes only three full gain/bias rows in
an isolated experimental model, AFTER a current native capture proves the exact
transmissions and fixed-gain/affine-bias semantics. It preserves the other45
actuator rows, all ordering/IDs/sensors and passive/physical configuration.
It does not remove/reindex actuators, globally disable a shared actuator group,
or assume ctrl=0 removes a position spring. No such gain/bias changes were made
by this update.

The proposed split scheme keeps source muscle activations in a separate external
vector. The pure existing Radau solver advances that vector; the native body
stepping path exclusively advances body qpos/qvel/time. Source total tension at
the left endpoint would be projected into ONLY the three resolved LF DOFs and
held for that interval. Commit external activation once after a successful body
step, then clear only the owned force contribution. Preserve unrelated forces;
reject undeclared competing target forces or stale ownership. Stop and retain
state on failure, without claiming native rollback or retry.

This is a design for a first-order coupled scheme. Its moving-body accuracy,
force timing and convergence are untested. The passing zero-DOF Radau result does
not validate this coupling. The zero-DOF advance_fixed_fixture adapter remains
restricted to its fixture and must not be reused to advance the moving fly.

The saved audit lists six unresolved gate groups: current complete native identity/
transmission/force-support tables; native selective-neutralization/preservation;
coupled integration/timing; physical units/geometry/velocity dependence; original
raw scientific prerequisites; and anatomical individual binding/neural conversion.
The original raw prerequisite result remains false. No lock refresh, inferred
biological force scale, new decoder or neural tuning was introduced.

## Evidence and checks actually run

- New record: docs/evidence/lf-actuation-contract-v1/audit.json, **77299 canonical
  LF bytes**, canonical SHA256
  385c57724f1ec3a937ad35bd86cfe76d4cb004b92d7aa52335d010c83bd81fc4.
  It contains all42 rows, scoped source-state identities, proposed ownership,
  blockers and source hashes before/after. Ordinary Git text normalization applies;
  this is not a raw-freeze waiver for any historical artifact.
- Historical M5A, later model signature and accepted integrator record identities
  are checked against predeclared hashes. Existing static mapping/source validators
  rebuild the20/42 admission inventory. Existing integrator saved evaluation is
  reused; neither its numerical campaign nor the failed Euler campaign was rerun.
- **24 new development tests passed /2 saved-review tests deselected in15.61s**,
  before the evidence commit/build. No test or audit failures.
- **165 tests passed in81.58s**: 26 new contract checks plus the prior139 integrator,
  transient, pose-force, force-reference, crosswalk, binding and admission checks.
  The predecessor tests include real native fixture implementation checks; they
  are not a new whole-fly or CNS scientific experiment. The new contract tests
  check historical identities, invalid transmissions/address ranges/aliases,
  preservation, unsafe patch plans and double-owner declarations.
- Static build and saved review run under tests that prohibit FlyGym construction,
  live inventory enumeration, MuJoCo model/forward/step/muscle derivative, CNS
  initialization, transition kernel and both numerical solvers.
- Exact Windows Git Bash saved-review command executed successfully. It rebuilt
  the static result and matched the saved record; no new physics/integration.
- Whitespace and staged canonical record identity checked. Existing environment
  reused, no dependency changes, Unity run or production control/model changes.

## Roadmap checkpoint after this run

| Stage | Current position |
|---|---|
| Motor coverage | **20/42 admitted; no new coordinates this run** |
| Source mechanics and activation | Prior fixed-pose/source-force checks and fixed-length integration pass their declared reference conditions |
| Replacement design | This static contract identifies the three targets,39 retained joint controls, six separately scoped adhesion controls and single-owner rules |
| Immediate next task | Separately specify a current native inventory capture and no-integration selective-neutralization/preservation audit using declared native forward probes |
| Before moving-fly coupling | Resolve coupled numerical/force timing, physical units/registration, original raw prerequisites, individual binding and neural conversion |
| Balance and walking | Remain goals requiring controlled causal evidence; no scripted gait substitute |

The next bounded audit can test native engineering isolation without assuming
biological force calibration or enabling the new force interface. Specify its
conditions, comparison arms and forward-call counts before running it. Preserve
the existing20 admitted channels and all other controls. No Unity run is needed
for this static review. Motor coverage is not overall project completion.

## Changed files and purpose

- docs/LF_ACTUATION_CONTRACT_V1.md: prospective contract, acceptance and limitations.
- malecns_backend/embodiment/lf_actuation_contract.py: source-locked static audit,
  historical identity partition, unsafe-plan rejection and saved review.
- tests/test_lf_actuation_contract.py:26 identity/scope/preservation/ownership tests.
- docs/evidence/lf-actuation-contract-v1/audit.json: complete separately versioned static record.
- docs/LF_ACTUATION_CONTRACT_RESULTS.md: findings, roadmap, checks and commands.
- docs/LEG_MAPPING_STATUS.md: unchanged admission count and native engineering gate.
- docs/PROJECT_HANDOFF.md: verified baseline, latest checkpoint and immediate next task.

## Windows Git Bash after merging

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
git lfs pull --include="docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather,docs/evidence/lf-pose-force-v1*/run/validation.json,docs/evidence/lf-activation-transient-v1/run/validation.json,docs/evidence/lf-activation-integrator-v1/run/validation.json"
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m malecns_backend.embodiment.lf_actuation_contract --report docs/evidence/lf-actuation-contract-v1/audit.json
code docs/LF_ACTUATION_CONTRACT_RESULTS.md docs/LF_ACTUATION_CONTRACT_V1.md
```

Expected: STATIC CONTRACT VERIFIED; coupling BLOCKED. Three historical LF target
rows;39 retained joint controls (20admitted+19baseline) plus six separately scoped
adhesion controls. Current20/42, new admissions0, original raw prerequisitesFalse,
and the next roadmap task. BLOCKED is the required scientific readiness result,
not an execution error or a request for permission. No Unity run or repeat needed.

Optional implementation checks (new scratch path):

```bash
"$PY" -m pytest -q -p no:cacheprovider --basetemp="$PWD/.pytest-tmp-contract-manual-v1" tests/test_lf_actuation_contract.py tests/test_lf_activation_integrator.py tests/test_lf_activation_transient.py tests/test_lf_pose_force.py tests/test_lf_force_reference.py tests/test_lf_anatomical_crosswalk.py tests/test_lf_proximal_binding_review.py tests/test_remaining_leg_admission_audit.py
# Expected:165 passed; includes existing native fixture implementation tests, no new CNS campaign.
```
