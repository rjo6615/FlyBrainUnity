# Synthetic split-coupling V1: retained integrity failure and roadmap

2026-10-25. Fresh branch from origin/newBrain c665480 (merged PR #273).
Protocol/fixture/runner/tests committed a0a501308335be788e2813ae21c968de7ef4c60a
BEFORE one nine-case campaign. No repeat, threshold change, shortened window,
solver/gain/drive/seed tuning or reclassification after outcomes.

## Outcome: numerical checks pass; the V1 experiment is NOT accepted

The original verdict is **INTEGRITY_FAILURE**. All nine native sample-window
activation/position/velocity numerical budgets pass, as do both predeclared pulse
grid-refinement tests. However, the three PULSE cases fail V1's solver-integrity
guard. That failure remains in the unchanged raw record and original evaluator.
Neither a successful evidence review nor passing unit tests changes that verdict.

| External interval | PULSE maximum position error | PULSE maximum velocity error | Normalized E | Original solver guard |
|---:|---:|---:|---:|---|
| 100us | 1.87500000e-7 | 1.32577981e-4 | .132577981 | FAIL |
| 50us | 9.48254397e-8 | 6.12092629e-5 | .061209263 | FAIL |
| 25us | 5.30977412e-8 | 2.89579314e-5 | .028957931 | FAIL |

These errors use SYNTHETIC units, not biological tolerances. Budgets were position
1e-5,velocity1e-3,activation.01 with declared bounds. E=max(q_error/1e-5,v_error/1e-3).
Refinement requires fine E<=.75*coarse E+1e-12; both comparisons pass. All native
timestamps over the entire10ms window are retained, not just endpoints. No
production timestep is selected. Numerical agreement does not rescue integrity.

## What actually ran

Four independent fixed-base native hinge rotors with constant inertias[1,2,3,4],
no actuators/native activation/contact/geoms/passive mechanics, zero gravity.
Source muscle activation is a separate external vector advanced using the existing
pure Radau solver and native source derivative, with source parameters unchanged.
Frozen source force coefficients and the existing R_G projection are explicitly
reinterpreted in synthetic units, constant across this fixture's motion. This is
not source/FlyGym finite-angle force registration or a physical muscle-length law.

At each100/50/25us interval, old activation determines held total tension/torque;
native Euler alone advances q/v/time; only after body advancement and owned-force
clearing is the external solver terminal state committed. Reference DOP853
integrates the SAME continuous synthetic equations independently, not native
mj_step. Three conditions per grid: RELAX_ZERO, FLOOR_BASELINE and PULSE on
outgoing[2,5)ms. Matched baseline/pulse histories are exact through2ms inclusive.

Actual campaign:3 native models,2100 synthetic body mj_step calls,2112 explicit
mj_forward calls (3mass checks+9initial+2100post-clear),0 resets or explicit native
step1/step2/Euler/RK/implicit calls outside mj_step internals,0 CNS/FlyGym runs.
All before/applied/cleared force buffers and body/external states, Radau nodes,
reference states/nodes, costs and operation counts are retained. Source/fixture/
upstream locks and mass matrices verify. All native ownership/time/update/force
checks pass. Native compiler/internal integrator work is outside Python counters.

The foreign sentinel generalized force.125 and body z-torque.25 stay exactly
preserved. Only the three owned projected force entries are added and cleared.
Independent equations and native semi-implicit updates agree within the declared
1e-9. Tests inject body failures before and after native advancement: the adapter
retains uncertain physical state, latches failed, does not commit external state,
clears only verified owned forces and rejects retry. No rollback claim.

## Why the exact solver guard failed

The native body state and committed external activation follow the intended
single-owner update. Every committed activation is BIT-IDENTICAL to the stored
solver terminal state and internal final node. V1 additionally required its
separately computed dense-output polynomial at that endpoint to be bit-identical.

| Grid | Nonidentical dense endpoints | Maximum absolute dense/terminal difference |
|---:|---:|---:|
| 100us PULSE | 1 | 4.33680869e-19 |
| 50us PULSE | 2 | 1.38777878e-17 |
| 25us PULSE | 11 | 1.11022302e-16 |

All six nonpulse cases have zero such differences. These14 observed differences
explain the only failing per-case guard. The guard I implemented assumed identity
between two separately computed representations. No tolerance was added and no
guard removed after observing the discrepancies; the experiment stays failed.

Source inspection supports a floating-point/interpolation explanation: installed
SciPy1.18.1 Radau stores y_new=y+Z[-1], but builds dense output from Q=Z.T@P and
evaluates a separate polynomial plus y_old. The official API describes Radau dense
output as a cubic collocation polynomial. This is a diagnosis, not authorization
to accept the failed record or automatically substitute a chosen tolerance.

Installed scipy/integrate/_ivp/radau.py raw SHA256
232f08010ccaa736e16ca34afc888c69365352df58fffbf7aecba6f863a456c6 is retained in
failure-review.json. Reference: [SciPy solve_ivp / Radau](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html).

## Preserved evidence and review boundary

Complete original LFS record docs/evidence/lf-synthetic-coupling-v1/run/validation.json:
25551077bytes, raw SHA256
12805789411e5b7b2aa9dbaea0f4e18e5075671a9945501970d9e952f99d822e.
All nine cases and failed pulse guards remain intact. The original runner and its
acceptance evaluator remain unchanged from the prospective campaign commit.

A separate read-only lf_synthetic_coupling_review module verifies the exact raw
record/source locks, reproduces the ORIGINAL failed evaluation and reports the
endpoint diagnostics. It does not correct acceptance, run native code, integrate
or repeat the experiment. failure-review.json is descriptive postmortem evidence,
not a second experimental protocol or a passing replacement record.

The original runner's --report intentionally rejects failed integrity; use the
separate failure-review command below to inspect this preserved negative result.
Exit0 from that command means the failed record is authentic and reproducible,
not that the coupling experiment passed. This separation avoids making negative
scientific outcomes impossible to review without changing their classification.

## Implementation checks

- Before campaign:14 passed /11 saved-output tests deselected in28.20s. Includes
  real native single-step force timing, exact foreign-buffer clearing, duplicate/
  tampered ownership rejection and injected before/after-native-step failures.
- Continuous FLOOR_BASELINE reference independently matches analytic constant-
  torque rotor q/v solution within1e-12. This is a native-derivative/analytic
  synthetic reference check, not biological validation.
- Postmortem tests retain the exact failed guard and require committed state to
  match authoritative solver terminal state; they do not modify V1 acceptance.
  Corruption tests were explicitly strengthened for an already-failed record:
  each corruption must produce a NEW evaluation difference, rather than pass
  vacuously because the original global verdict is already failed. All9 focused
  corruption checks passed /18 deselected in3.28s.
- Preflight/failure review tests prohibit native model/data/forward/step/muscle
  derivative, Radau/DOP853 and FlyGym/CNS initialization. Exact Windows Git Bash
  failure-review command executed successfully, retaining INTEGRITY_FAILURE.
- **215 tests passed in154.89s**:27 synthetic/negative-review checks plus188 prior
  native-isolation/contract/integrator/transient/pose-force/force-reference/crosswalk/
  binding/admission checks. The9 focused stronger corruption checks above also
  passed after their assertion was improved. Automated checks passing does not
  change the scientific INTEGRITY_FAILURE outcome.
- No dependency, production/neural/source-physiology change, new admission or Unity
  run. Prior raw scientific prerequisites remain separately false.

## Roadmap checkpoint after this run

| Stage | Current position |
|---|---|
| Motor mapping | **20/42 admitted**, new admissions0 |
| Previous source/native gates | Prior source-reference, activation and native-isolation results preserved |
| Synthetic coupling | Full numerical budgets/refinement and force ownership checks pass, but V1 remains INTEGRITY_FAILURE |
| Immediate next task | Independently specify/test terminal-state versus dense-output endpoint semantics before a new acceptance protocol |
| Later transfer gate | Physical units/geometry/velocity/length review, original raw prerequisites, individual binding and neural conversion |
| Moving-fly behavior | Muscle-force coupling, causal balance and walking remain unestablished |

Next work must use source/API evidence and independent endpoint-contract tests,
not tune an epsilon to these14 observed residues. A new protocol or corrected
implementation must be separately versioned before new outcomes, preserving this
failed campaign. Do not jump directly to source-to-FlyGym force transfer or reuse
the zero-DOF adapter on a moving body. No Unity run is needed yet.

## Changed files and purpose

- .gitattributes: LFS scientific record and exact fixture-byte policy.
- docs/LF_SYNTHETIC_COUPLING_V1.md: prospective model, conditions, ownership and acceptance.
- docs/fixtures/lf-synthetic-coupling-v1.xml: explicit four-rotor synthetic mechanics.
- malecns_backend/embodiment/lf_synthetic_coupling.py: restricted adapter, independent
  reference, counted campaign and ORIGINAL unchanged acceptance evaluator.
- tests/test_lf_synthetic_coupling.py: native/analytic/ownership/failure/negative-record checks.
- docs/evidence/lf-synthetic-coupling-v1/run/validation.json: complete failed campaign via LFS.
- malecns_backend/embodiment/lf_synthetic_coupling_review.py: static negative-result verifier/diagnostics.
- docs/evidence/lf-synthetic-coupling-v1/failure-review.json: descriptive postmortem summary.
- docs/LF_SYNTHETIC_COUPLING_RESULTS.md: outcomes, limits, validation and roadmap.
- docs/LEG_MAPPING_STATUS.md and docs/PROJECT_HANDOFF.md: retained failure checkpoint and next gate.

## Windows Git Bash after merging

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
git lfs pull --include="docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather,docs/evidence/lf-pose-force-v1*/run/validation.json,docs/evidence/lf-activation-transient-v1/run/validation.json,docs/evidence/lf-activation-integrator-v1/run/validation.json,docs/evidence/lf-native-isolation-v1*/run/validation.json,docs/evidence/lf-synthetic-coupling-v1/run/validation.json"
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m malecns_backend.embodiment.lf_synthetic_coupling_review --report docs/evidence/lf-synthetic-coupling-v1/run/validation.json
code docs/LF_SYNTHETIC_COUPLING_RESULTS.md
```

Expected: SYNTHETIC RECORD VERIFIED: INTEGRITY_FAILURE (unchanged; experiment NOT
accepted). All nine numerical checks PASS, three PULSE solver guards FAIL with
the recorded dense differences. Production20/42,0newadmissions and next endpoint
semantics task. This is the intended failed-record review, not another experiment.
Do not use the original --execute/--report runner to repeat or obtain a pass.

Optional tests (fresh scratch path):

```bash
"$PY" -m pytest -q -p no:cacheprovider --basetemp="$PWD/.pytest-tmp-synthetic-manual-v1" tests/test_lf_synthetic_coupling.py tests/test_lf_native_isolation.py tests/test_lf_actuation_contract.py tests/test_lf_activation_integrator.py tests/test_lf_activation_transient.py tests/test_lf_pose_force.py tests/test_lf_force_reference.py tests/test_lf_anatomical_crosswalk.py tests/test_lf_proximal_binding_review.py tests/test_remaining_leg_admission_audit.py
# Expected215 passed, including tests preserving the scientific INTEGRITY_FAILURE.
```
