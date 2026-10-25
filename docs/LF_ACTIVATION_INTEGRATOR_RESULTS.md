# LF activation integrator results and roadmap

2026-10-25. Fresh branch from origin/newBrain a5b8cdd (merged PR #270).
Prospective protocol, integrator, validation runner and tests committed at
e1dadc70ac8758456e8492d4a9b5c83ecbe79bb3 BEFORE the single nine-case campaign.
No solver, tolerance, source parameter, acceptance or external-grid change after
outcomes. No campaign retry. The prior Euler failures and raw evidence are intact.

## Result: integration fidelity at the declared fixture conditions

**All nine cases pass integrity and the predeclared numerical criteria.**
Classification: ALL_NUMERICALLY_ACCEPTED. The implicit Radau integrator advances
the unchanged native muscle law, with rtol=1e-9/atol=1e-12 and adaptive internal
steps capped by the external interval. No clamp or time-constant change.

| External interval | RELAX_ZERO maximum error | FLOOR_BASELINE error | PULSE maximum error | Archived Euler PULSE error |
|---:|---:|---:|---:|---:|
| 100 us | 2.31022463e-13 | 0 | 1.76429649e-10 | 1.380663692 (FAIL) |
| 50 us | 1.62506835e-13 | 0 | 1.24318000e-10 | .559500792 (FAIL) |
| 25 us | 8.40684944e-15 | 0 | 1.82032167e-12 | .209847371 (FAIL) |

Every Radau case is evaluated at all 401 archived 25-us timestamps over the full
10-ms window, as well as its macro states. Bounds are also checked at every
accepted internal solver node. No endpoint-only acceptance or hidden window.
The common acceptance remains maximum absolute activation error<=.01 and bounds
[-1e-12,1+1e-12]. These are sampled checks, not a continuous-time error theorem.

Pulse maximum activations are .9999998555034163/.999999855505455/.9999998555055675.
Maximum force differences against the archived reference are
2.76969781e-8/1.95161809e-8/2.85764949e-10 source force units. That numerical force
comparison is separate from the 1e-8 integrity check of native force against its
own activation*gain+bias relation; those alignment checks pass in every case.
Force units are not calibrated to FlyGym, SI or biological muscle.

## What ran and what was preserved

The existing source-preserving fixed-length fixture has no body/joint DOFs. Its
four native activation addresses and tendon/actuator identities are checked
exactly. The source law, control limits/floor, passive bias, dyn/gain/bias
parameters and fixture bytes remain unchanged. Three activation=0/.5/1 native
forward observations reproduce the original central forces within 1e-8.

The single campaign executed **2100 Radau intervals/activation commits and 4212
explicit native mj_forward calls, zero mj_step**. Activation and fixture time
advance once per interval under the experimental adapter. Native force and
derivative are recorded before/after each commit. Every accepted solver node,
dense sample, status and nfev/njev/nlu count is retained. No production or CNS
execution and no moving-body integration occurred. Compiler-internal validation
is outside the explicit Python API count.

The independent DOP853 solution is reused from the exact prior archive, not
recomputed or revised. Its raw SHA256 remains
539c26fb35d15824d970b482d36af579186e2ed4fe1bf707c03c4e592a90e5fc.
All nine original Euler decisions are preserved and verified. New integrator
evidence is separately archived at docs/evidence/lf-activation-integrator-v1/run/validation.json:
7841130 bytes, SHA256 cd545ca6863b2d2468da067b258d9aac0ecb7f3ab8a953f15c0d6574f62eb49b,
stored through LFS. The full-window comparison.png overlays Radau, the unchanged
reference and all previous Euler curves; the overshoot is visible and unclipped.

FLOOR_BASELINE stays exactly at activation .0001, including passive plus floor-
active preload. Its history matches PULSE exactly through 2 ms inclusive. The
RELAX_ZERO probe remains unmatched, starting at activation zero and relaxing to
the source control floor. Zero raw input does not mean zero activation or force.

## Validation actually performed

- **139 passed in 55.65 s**: 24 new integrator checks plus the prior 115 transient,
  pose-force, force-reference, crosswalk, binding and admission-audit checks.
- Native single-interval tests verify state/time ownership, pre/post force and
  derivative timing, source preservation and prohibition of native mj_step.
  Moving models, clamps and non-bijective activation addresses are rejected.
- An analytic mocked linear derivative tests Radau plumbing only; it is not a
  native muscle or biological validation. Source fixture/native calls and the
  actual campaign are reported separately above.
- Development: 12 checks passed, one test setup errored because the requested
  pytest basetemp parent did not exist, and 11 saved-output checks were deselected.
  Created that scratch parent; the setup-affected test then passed (23 deselected).
  This was a test-directory fix before the campaign, not an experimental retry.
- Preflight passed with no model construction or integration. Exact Windows Git
  Bash saved review executed successfully in 5.61 s. Tests prohibit native model,
  muscle derivative and both solver calls during preflight/saved review.
- Archive-only comparison plot generated with the extended existing plotting
  tool and visually inspected. Existing plot generation remains available without
  the optional integrator overlay. Whitespace and staged LFS identity checked.
- Existing validated environment reused; no dependency changes. No Unity run,
  CNS experiment, neuron/gain tuning or production-controller change.

Saved review recomputes identities, saved context, timing/forces, solver-record
structure, full-window errors and decisions. It does not reconstruct Radau or
DOP853 trajectories; scientific confidence comes from the recorded prospective
campaign and independent numerical comparison, not saved review alone.

## Roadmap checkpoint after this run

| Stage | Where we are | Next concrete requirement |
|---|---|---|
| Motor coordinate coverage | Production remains **20/42**, new admissions **0** | Admission evidence for the remaining 22, including unresolved LF proximal/shared-axis binding |
| Existing body/sensory experiments | Prior matched tactile/perturbation/yoke observations are preserved | Do not generalize those observations to independent balance or gait |
| LF source mechanics | Local source-force/pose checks and this fixed-length activation integrator pass their declared reference checks | Specify the moving-body state-ownership and selective actuator-replacement contract |
| Physical/neural coupling | Not established by this run | Resolve force units/geometry, original raw prerequisites, exact mapping and neural-to-activation interpretation before a moving-fly coupling experiment |
| Balance and walking | Goals, not demonstrated capabilities | Controlled causal tests after a supported, validated interface; no scripted gait substitute |

The immediate next update should **design and statically audit a selective LF
actuator-replacement/state-ownership contract**, enumerating exact target
coordinate, actuator and activation IDs and the controls that must remain intact.
It must prevent existing position actuation and new force actuation from driving
the same coordinates, and prevent native plus external integration from advancing
activation twice. Keep it unconnected to production pending physical/biological
prerequisites. Do not use this numerical pass to admit a coordinate or waive the
original false raw-freeze flags. Production remains 20/42; this is not an overall
percentage of the complete fly project. No Unity run is needed yet.

After every future run, report what ran, what its result establishes/does not
establish, current motor count, the active gate and the next concrete gate.

## Changed files and purpose

- .gitattributes: LFS rule for the separate new report.
- docs/LF_ACTIVATION_INTEGRATOR_V1.md: prospective numerical experiment and limits.
- malecns_backend/embodiment/lf_activation_integrator.py: pure Radau interval solver
  and zero-DOF state/force adapter, with no production hook.
- malecns_backend/embodiment/lf_activation_integrator_validation.py: locked archived
  comparison, nine-case assay, integrity/numerical evaluator and saved review.
- tests/test_lf_activation_integrator.py: analytic/native/boundary/failure/corruption checks.
- docs/evidence/lf-activation-integrator-v1/run/validation.json: all numerical records via LFS.
- tools/plot_lf_activation_transient.py: optional new overlay while retaining Euler history.
- docs/evidence/lf-activation-integrator-v1/comparison.png: full-window visual comparison.
- docs/LF_ACTIVATION_INTEGRATOR_RESULTS.md: findings, limitations, roadmap and commands.
- docs/LEG_MAPPING_STATUS.md and docs/PROJECT_HANDOFF.md: checkpoint/next task and user reporting preference.

## Windows Git Bash after merging

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
git lfs pull --include="docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather,docs/evidence/lf-pose-force-v1*/run/validation.json,docs/evidence/lf-activation-transient-v1/run/validation.json,docs/evidence/lf-activation-integrator-v1/run/validation.json"
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m malecns_backend.embodiment.lf_activation_integrator_validation --report docs/evidence/lf-activation-integrator-v1/run/validation.json
code docs/LF_ACTIVATION_INTEGRATOR_RESULTS.md docs/evidence/lf-activation-integrator-v1/comparison.png
```

Expected: INTEGRATOR EVIDENCE VERIFIED: ALL_NUMERICALLY_ACCEPTED; nine PASS lines;
production20/42, newly admitted0, original raw prerequisites False, and the next
roadmap gate. No Unity run or campaign repeat. Historical Euler PULSE failures
remain failures, even though this separate integration method passes.

Optional implementation tests (fresh temporary path):

```bash
"$PY" -m pytest -q -p no:cacheprovider --basetemp="$PWD/.pytest-tmp-integrator-manual-v1" tests/test_lf_activation_integrator.py tests/test_lf_activation_transient.py tests/test_lf_pose_force.py tests/test_lf_force_reference.py tests/test_lf_anatomical_crosswalk.py tests/test_lf_proximal_binding_review.py tests/test_remaining_leg_admission_audit.py
# Expected: 139 passed; native implementation checks included, no CNS campaign.
```
