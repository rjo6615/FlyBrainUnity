# LF native actuator isolation: results and fly roadmap

2026-10-25. Fresh branch from origin/newBrain a50ef0b (merged PR #272). Native
protocol, manifest, runner and tests committed b4efd68 before V1. A separately
specified serialization correction was committed14d3f04 before V1.1. No probe,
gain fitting, tolerance, source physiology, neural parameter or acceptance change.

## Result and exact scope

**V1.1: NATIVE_ISOLATION_VERIFIED_COUPLING_BLOCKED.** All27 forward-only
observations pass the declared checks. Zero selected actuator force and zero
total actuator force on target DOFs are measured in every suppression probe.
Maximum force difference among the other45 actuators is exactly0. Only the three
declared full position-actuator gain/bias rows changed, and exact model identity
was restored before closing the isolated stack. Production is unchanged20/42.

This ran the current validated native FlyGym stack with the existing live/contact
initializer, not a synthetic replacement body. It did NOT advance the fly:34
explicit native forwards (7initializer+27probe),3 native resets and0 calls to
mj_step/mj_step1/mj_step2/mj_Euler/mj_RungeKutta/mj_implicit. No CNS, muscle-force
application or production hook. Native qacc/constraint/sensor outputs can differ
after suppression; qpos/qvel/act/ctrl/time remain exactly as prescribed per probe.

## Current native identity capture

Captured model: nq94,nv93,nu48,na0,nbody72,nsensor175. The exact current target
body is0/LFCoxa, native body ID13. These identities were resolved from the current
compiled model, not copied from a historical fixture.

| Coordinate | Action/actuator ID | Joint ID | qpos index | DOF index | Activation address/count |
|---|---|---:|---:|---:|---|
| LF Coxa_yaw | 2/2 | 1 | 7 | 6 | -1/0 |
| LF Coxa | 0/0 | 2 | 8 | 7 | -1/0 |
| LF Coxa_roll | 1/1 | 3 | 9 | 8 | -1/0 |

Qualified joint/actuator/body names, all42 ordered action associations, all48
actuator transmission/activation/gain/bias/control tables, joint body/address/axis
tables and all175 sensor identities are retained. Existing complete numeric
model/option/name identity hashing and native DOF observers were reused.
The six adhesion actuators have exact body transmissions and zero controls;
they remain separate from motor-coordinate admissions. Source muscle activation
addresses0..3 still do not index this body's empty native act array.

## Fixed comparison and measured forces

Nine fixed inputs: center; +/- .05rad separately on yaw/pitch/roll; +/- velocity
pattern[.1,-.1,.1]rad/s. All nonselected positions stay at captured reset values.
All42 baseline controls use each probe position plus alternating +/-.01rad
offsets. Three arms: BASELINE; CTRL_ZERO_ONLY with only selected controls0;
NEUTRALIZED with only selected gain/bias rows0 and baseline controls unchanged.
These are mechanical diagnostic probes, not neural activity or behavior control.

| Target | Baseline actuator force across probes | CTRL_ZERO_ONLY range | NEUTRALIZED |
|---|---|---|---|
| LF yaw | approximately +.45 | -2.25 to+2.25 | 0 in every probe |
| LF pitch | approximately +.45 | -17.17256510 to-12.67256510 | 0 in every probe |
| LF roll | approximately -.45 | -2.25 to+2.25 | 0 in every probe |

All numbers are native engineered actuator-force units, not calibrated biological
muscle force. At CENTER, ctrl0 leaves pitch force-14.92256510: setting a target
position to zero does not remove its spring. Baseline selected forces are nonzero,
so successful suppression is not a vacuous zero-input result.

For every NEUTRALIZED probe, selected force and target generalized actuation are
exactly0, all45 retained forces exactly match baseline, and generalized force
differences outside the three target DOFs are0. Passive generalized forces and
complete actuator moment matrices match exactly. Native projection agrees with
moment.T@actuator_force within the declared1e-8. Sparse moment records use the
existing validated native CSR conversion and independent saved-CSR evaluator.
State/time and model preservation checks pass with their original criteria.

## V1 export failure preserved; V1.1 correction

V1 reached27 observations and its serialized prefix includes BASELINE,
NEUTRALIZED and RESTORED identities. Strict JSON export then failed on a native
unbounded limit(-inf). The original partial bytes remain unchanged in
docs/evidence/lf-native-isolation-v1/run/validation.json:
2353546bytes, SHA256 d6219a063538b270517ce0f9a9b86ea0bb7a3a135cc37ce93755323f9f9f0e54.
V1's final counters/evaluation were not serialized. Its status is scientifically
inconclusive/SERIALIZATION_FAILED; missing counters are not reconstructed from
expectations. The malformed historical JSON is evidence, not a usable review input.

V1.1 is the one justified repeat after a prospective correction: native nonfinite
metadata is represented by explicit native_nonfinite tags, decoded losslessly
before existing numeric/hash evaluation. No infinite limits are replaced by
arbitrary finite bounds; no fields or probes are dropped. Nonfinite physical
outputs would still fail the unchanged finite-value checks. Strict JSON is
constructed fully before writing. A new round-trip implementation test passes.
The same package manifest, initializer, arms, probes, suppression and criteria
were used. No third campaign or post-outcome adjustment.

Complete V1.1 report docs/evidence/lf-native-isolation-v1_1/run/validation.json:
2455324bytes, raw SHA256 ee3ddfe2e9d298d3b3f269ab04c114d7f3a332ebc68ea20c184deb7b1df2a628.
Both reports are separate LFS records. Preflight also verifies the preserved V1
raw hash. The initial manifest pins196 scientific package files/binaries totaling
62482705bytes: MuJoCo3.2.7,FlyGym1.2.1,dm_control1.0.27,NumPy2.0.2,SciPy1.18.1.
No dependencies or installed source/assets were changed.

## Checks actually run

- **188 tests passed in103.57s**:23 new native-isolation checks plus165 previous
  contract/integrator/transient/pose-force/force-reference/crosswalk/binding/admission
  checks. Existing native fixture implementation tests are included; they are
  separate from the two campaign executions and do not constitute a CNS experiment.
- Development:12 passed /10 saved-output tests deselected in12.97s. After the V1
  export failure, one lossless-encoding test passed /22 deselected in.60s before
  V1.1. The failure and correction are reported above, not hidden as a passing V1.
- New tests check fixed inputs/arm matching, integration-call prohibition/API
  wrapper restoration, lossless metadata, exclusive failure output, current native
  identity preservation, nonvacuity and rejection of corrupted force/state/body/
  sensor/parameter/CSR/counter evidence.
- Preflight and saved-review tests prohibit model/data construction, native reset/
  forward/integration, FlyGym/CNS initialization and numerical solvers. Exact
  Windows Git Bash saved-review command completed successfully with no new native
  campaign. Saved review rechecks locks, complete stored native tables and algebra;
  it does not reconstruct native dynamics from source.
- Whitespace and staged LFS identity checks completed. No Unity run, neuronal
  tuning, muscle coupling or production controller/model changes.

## Roadmap after this run

| Stage | Position |
|---|---|
| Motor coordinate coverage | **20/42 admitted**, new admissions0 |
| Source mechanics/activation | Previous declared fixture/reference checks preserved |
| Native replacement isolation | Verified at all declared fixed inputs; missing historical native tables now captured for this context |
| Immediate next gate | Separately specify a synthetic coupled-state/force-buffer ownership and numerical convergence experiment |
| Before moving-fly muscle coupling | Establish coupled accuracy/timing, physical units/geometry/velocity transfer, original raw prerequisites, individual binding and neural conversion |
| Balance/walking | Later controlled causal tests; neither established by this forward-only audit |

The next synthetic experiment should test the proposed left-endpoint split scheme
and once-only ownership without silently reusing the zero-DOF adapter on a moving
body. Preserve foreign forces, distinguish model mismatch from solver error and
predeclare convergence controls/criteria before outcomes. Use synthetic units
explicitly; do not treat a synthetic numerical pass as source-to-FlyGym biological
force calibration. Keep production disconnected and the current20/42 unchanged.
No Unity run is needed yet. Original raw scientific prerequisites remain false.

## Changed files and purpose

- .gitattributes: separate LFS rules for failed V1 and complete V1.1 records.
- docs/LF_NATIVE_ISOLATION_V1.md: original prospective native experiment.
- docs/LF_NATIVE_ISOLATION_V1_1.md: versioned serialization correction and limits.
- docs/evidence/lf-native-isolation-v1/input-manifest.json: pre-outcome package/assets identity.
- malecns_backend/embodiment/lf_native_isolation.py: native capture/forward probes,
  counted execution, lossless evidence and native-free saved evaluator.
- tests/test_lf_native_isolation.py:23 input/ownership/identity/integrity/encoding tests.
- docs/evidence/lf-native-isolation-v1/run/validation.json: unchanged failed partial export.
- docs/evidence/lf-native-isolation-v1_1/run/validation.json: complete separately versioned evidence.
- docs/LF_NATIVE_ISOLATION_RESULTS.md: results, failed history, checks and roadmap.
- docs/LEG_MAPPING_STATUS.md and docs/PROJECT_HANDOFF.md: checkpoint and next gate.

## Windows Git Bash after merging

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
git lfs pull --include="docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather,docs/evidence/lf-pose-force-v1*/run/validation.json,docs/evidence/lf-activation-transient-v1/run/validation.json,docs/evidence/lf-activation-integrator-v1/run/validation.json,docs/evidence/lf-native-isolation-v1*/run/validation.json"
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m malecns_backend.embodiment.lf_native_isolation --report docs/evidence/lf-native-isolation-v1_1/run/validation.json
code docs/LF_NATIVE_ISOLATION_RESULTS.md
```

Expected: NATIVE ISOLATION EVIDENCE VERIFIED: NATIVE_ISOLATION_VERIFIED_COUPLING_BLOCKED;
27forward-only probes,34recorded forwards,3resets,0integration/CNS,20/42 and raw
prerequisitesFalse. BLOCKED is the intended remaining coupling-readiness result.
Review the V1.1 record; the original V1 partial is preserved as failed evidence.
Saved review performs no native work. No Unity run or campaign repeat needed.

Optional tests (fresh scratch directory):

```bash
"$PY" -m pytest -q -p no:cacheprovider --basetemp="$PWD/.pytest-tmp-native-isolation-manual-v1" tests/test_lf_native_isolation.py tests/test_lf_actuation_contract.py tests/test_lf_activation_integrator.py tests/test_lf_activation_transient.py tests/test_lf_pose_force.py tests/test_lf_force_reference.py tests/test_lf_anatomical_crosswalk.py tests/test_lf_proximal_binding_review.py tests/test_remaining_leg_admission_audit.py
# Expected188 passed; includes existing native fixture checks, no new CNS campaign.
```
