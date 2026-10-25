# LF activation-transient results

2026-10-25. Fresh branch from origin/newBrain f1ba677, merged PR #269. Protocol,
source binding, fixed-length fixture and runner/tests committed at **9b95220
before the nine-condition campaign**. No parameter/timestep/clamp adjustment or
repeat after outcomes. Production remains20/42, new admissions0.

## Outcome: numerical limits observed

All nine conditions completed with implementation integrity verified. **All three
pulse conditions fail the predeclared full-window activation-accuracy criterion.**
The campaign classification is NUMERICAL_LIMITS_OBSERVED, not global numerical
acceptance. Six zero-input/equilibrium cases pass their numerical criteria. No
timestep is selected or authorized for future coupling.

| Timestep | RELAX_ZERO max activation error | FLOOR_BASELINE max error | PULSE max activation error | PULSE max activation | Pulse acceptance |
|---:|---:|---:|---:|---:|---|
| 100 us | 0.000113538137 | 0 | 1.380663692 | 1.999300240 | FAIL: bounds and accuracy |
| 50 us | 0.000036792004 | 0 | 0.559500792 | 0.999999999987 | FAIL: accuracy |
| 25 us | 0.000011788254 | 0 | 0.209847371 | 0.999999959463 | FAIL: accuracy |

Acceptance was maximum absolute error<=0.01 over the complete 10ms window and
activation within [-1e-12,1+1e-12], fixed before outcomes. Native Euler at100us
overshoots normalized activation; compiled source activation limits are disabled
for all four actuators. We did not add a clamp, increase source time constants,
choose another window, or fit a gain. The two finer predeclared grids remain
bounded but still fail accuracy.

Pulse endpoint errors are only .000232091/.000125484/.0000653802, while the full-
window errors above fail. An endpoint-only criterion would hide the large onset
error; the declared full-window decision is retained. Maximum absolute force
errors against the same reference are216.744818/87.833770/32.943091 native force
units (across all four fixed-length actuators). These are source-model numerical
errors, not calibrated biological forces or evidence of damage/behavior.

## What actually ran

The separate fixture has nq=nv=0, four muscle states and fixed world-site tendon
lengths. It reproduces the archived central source forces at activation0/.5/1
within1e-8 with source defaults/parameters/control limits unchanged. It is not a
moving fly or a neural experiment. Static source extraction reused the original
XML hash and accepted pose/source-force evidence; no source asset was changed.

At each of100/50/25us, fresh runs use RELAX_ZERO (a0=0/rawctrl0), FLOOR_BASELINE
(a0=effective floor/rawctrl0), and PULSE (same floor initial state, rawctrl1 on
outgoing [2ms,5ms), rawctrl0 otherwise). All histories and failed outcomes remain.
The independent reference uses the same native mju_muscleDynamics with DOP853,
rtol1e-11/atol1e-13/max_step2.5us, split at exact control transitions. It is an
independent integrator for the same source law, not a second physiological law.
One fine reference per condition is reused across all native grids.

The measured API counts are **2100 native mj_step and2112 explicit mj_forward
calls**. Native activation and time advance; there are **zero body/joint or CNS
transitions**. Compiler-internal validation is outside that explicit API count.
Every after-step force is retained before and after forward refresh. With
actearly=false, force left by mj_step belongs to the pre-integration activation;
the refreshed force belongs to the new activation. Both source affine-force
relations and the exact native Euler state update pass the declared integrity
checks, even when the resulting trajectory fails accuracy.

Matched FLOOR_BASELINE/PULSE histories are exactly equal through2ms inclusive.
The floor baseline remains stationary at0.0001 activation. Passive bias is retained
in both arms; anterior-rotator passive tension remains11.60235359 native units.
The equilibrium floor adds a small active preload, so its total force differs
from the RELAX_ZERO initial passive-only force. Raw zero control is not a
zero-activation equilibrium. RELAX_ZERO is documented as an unmatched relaxation
probe, never used as the matched pulse baseline.

## Checks and evidence

- **115 passed in43.16s**: 16 new transient tests plus99 existing reference/fixture/
  audit tests. Includes actual native single-step force timing, source-parameter
  preservation, an analytic linear mock used only to test reference solver
  boundaries, full-window acceptance recomputation, corruption/output protection
  and strict model/native/reference-integration-free review/preflight.
- Development:7 passed /8 saved-output tests not yet run, then the added native
  timing test passed (15 other tests deselected). No development failure required
  a source or scientific acceptance change.
- Actual nine-condition campaign passed integrity and recorded numerical failures.
  No retries. Exact Windows Git Bash saved-review command passed in5.60s and prints
  all nine numerical decisions, including three PULSE FAIL lines.
- Complete native/reference records: docs/evidence/lf-activation-transient-v1/run/validation.json,
  3799210 bytes, raw SHA256
  539c26fb35d15824d970b482d36af579186e2ed4fe1bf707c03c4e592a90e5fc, in LFS.
- Source binding and generated fixture preserve canonical fixture SHA256
  a728cbcfa19ff517925ea2627a55b01db32ca26dd8a9567d11f70140a6e1903e.
- Full-window plots in transients.png were generated from the archive with
  tools/plot_lf_activation_transient.py and visually inspected. No overshoot was
  clipped; all three pulse and relaxation grids plus shared baseline are displayed.
- Whitespace/LFS identity checks pass. Existing validated packages reused; no
  dependency changes, Unity Editor run, neuron tuning or production modification.

Saved review recomputes recorded timing, force alignment, integrity, complete-
window errors and numerical classifications. It does not rerun native dynamics
or DOP853 reference integration. A verified archive does not accept a failed
numerical timestep. Old raw scientific prerequisites remain separately false in
the recorded Windows checkout; this experiment does not waive them.

## Next engineering gate

The source Euler integration at these predeclared grids is not accepted for pulse
coupling under this protocol. Next separately design a reference-faithful activation
state integrator with explicit ownership/timing and the same source law, time
constants, control floor and passive baseline. Validate it against the independently
integrated source reference, keeping the failed Euler baselines. Do not change
physiology, add a clamp or search timesteps until a pass appears.

This still does not establish neuron-to-activation mapping, individual tendon
binding, SI/FlyGym force units or an anatomical finite-angle current-body mapping.
Selective actuator replacement, force-unit/geometry transfer and original raw
prerequisites remain separate gates before moving-fly neural coupling. No new
motor admission, balance or gait claim follows. Current production20/42.

## Changed files and purpose

- .gitattributes: exact fixture-byte policy and LFS native record rule.
- docs/LF_ACTIVATION_TRANSIENT_V1.md: prospective conditions, timing, reference,
  integrity versus numerical acceptance and limitations.
- docs/fixtures/lf-activation-transient-v1.xml: source-preserving zero-DOF fixture.
- docs/evidence/lf-activation-transient-v1/source-binding.json: exact source
  attributes, frozen lengths/forces and fixture hash before outcomes.
- malecns_backend/embodiment/lf_activation_transient.py: native/reference campaign,
  complete evaluator and dynamics/integration-free saved review.
- tests/test_lf_activation_transient.py: source/timing/solver/boundary/integrity tests.
- docs/evidence/lf-activation-transient-v1/run/validation.json: all nine trajectories
  and numerical failures, retained through LFS.
- tools/plot_lf_activation_transient.py and docs/evidence/lf-activation-transient-v1/transients.png:
  reproducible full-window reference/numerical visualization.
- docs/LF_ACTIVATION_TRANSIENT_RESULTS.md: outcomes, validation and manual commands.
- docs/LEG_MAPPING_STATUS.md and docs/PROJECT_HANDOFF.md: checkpoint and next gate.

## Git Bash after merging

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
git lfs pull --include="docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather,docs/evidence/lf-pose-force-v1*/run/validation.json,docs/evidence/lf-activation-transient-v1/run/validation.json"
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m malecns_backend.embodiment.lf_activation_transient --report docs/evidence/lf-activation-transient-v1/run/validation.json
code docs/LF_ACTIVATION_TRANSIENT_RESULTS.md docs/evidence/lf-activation-transient-v1/transients.png
```

Expected: TRANSIENT EVIDENCE VERIFIED, NUMERICAL_LIMITS_OBSERVED, six zero-input/
baseline PASS lines and **three PULSE FAIL lines**. These are the retained
numerical findings; saved review runs no model/native/reference integration.
Current20/42, no CNS/body-joint transitions or new admission. Historical raw flag
remains false. No Unity run or experiment repeat is needed for review.

Optional tests (fresh temporary directory name):

```bash
"$PY" -m pytest -q -p no:cacheprovider --basetemp="$PWD/.pytest-tmp-transient-manual-v1" tests/test_lf_activation_transient.py tests/test_lf_pose_force.py tests/test_lf_force_reference.py tests/test_lf_anatomical_crosswalk.py tests/test_lf_proximal_binding_review.py tests/test_remaining_leg_admission_audit.py
# Expected:115 passed; includes native activation/fixture implementation checks, no CNS experiment.
```
