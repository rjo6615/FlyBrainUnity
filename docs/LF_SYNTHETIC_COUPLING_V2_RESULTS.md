# Synthetic coupling V2 results and transfer milestone

2026-10-25. Fresh origin/newBrain7c8d358 (merged PR #275). V2 protocol/adapter/
runner/tests committed c15e80cb2888f841f91f7b639ab70a136d05f873 BEFORE one new
nine-case campaign. No V2 retry, threshold/window/grid/force/source-physiology/
neural/seed change. Historical V1 and its original evaluator remain unchanged.

## Outcome

**SYNTHETIC_COUPLING_V2_VERIFIED_TRANSFER_BLOCKED.** All9cases pass integrity,
activation/position/velocity budgets, exact endpoint roles, force ownership and
both pulse-refinement checks. This clears the declared synthetic coupling
implementation gate. It does NOT establish physical transfer to FlyGym, biological
force calibration, a new motor admission or independent balance. Production20/42.

| Grid | PULSE max position error | PULSE max velocity error | E | V2 result |
|---:|---:|---:|---:|---|
| 100us | 1.87500000e-7 | 1.32577981e-4 | .132577981 | PASS |
| 50us | 9.48254397e-8 | 6.12092629e-5 | .061209263 | PASS |
| 25us | 5.30977412e-8 | 2.89579314e-5 | .028957931 | PASS |

All6nonpulse cases also pass. Unchanged budgets: full-window max q_error<=1e-5,
v_error<=1e-3,activation error<=.01/bounds[-1e-12,1+1e-12]; E=max(q_error/1e-5,
v_error/1e-3). Both E_fine<=.75E_coarse+1e-12 refinements pass. Units are SYNTHETIC,
not biological tolerances. No production timestep is selected.

## What actually changed

V2 subclasses V1's restricted synthetic adapter, reusing constructor, exact native
metadata/context guard, force apply/clear operations and failure latch. Its
transition uses the independently verified endpoint wrapper, not a module-global
integrator replacement. It requests one endpoint sample explicitly labeled
SOLVER_TERMINAL_STATE; sample, after, internal terminal state and committed external
activation are bit-identical. Every raw dense interpolant is retained separately
with a saved content hash. No epsilon or near-time snapping was introduced.

The raw polynomial discrepancies still exist and are preserved:

| PULSE grid | Retained dense mismatches | Maximum difference |
|---:|---:|---:|
| 100us | 1 | 4.33680869e-19 |
| 50us | 2 | 1.38777878e-17 |
| 25us | 11 | 1.11022302e-16 |

They are interpolation diagnostics, not committed state. The V1 exact comparison
and its INTEGRITY_FAILURE are not removed, edited or retroactively passed.
V2 requires its own schema and reuses every non-schema mechanical/source/state/
force/solver/numerical/refinement check from the unchanged V1 evaluator. The V1
top-level schema check still rejects V2; V2 validates its explicit version and
adds role/raw-record integrity checks before forming its own classification.

A read-only whole-trajectory comparison found **zero differences** in physical,
activation, force, time, control, commit-index and phase fields across all2100
V1/V2 transitions. Continuous reference records are exactly equal too. Thus this
implementation correction does not hide a changed simulated trajectory or tuning.

## Actual campaign and retained evidence

Same four independent rotors/inertias[1,2,3,4],zero native actuators/activation/
contacts/passive mechanics/gravity; same frozen source numbers explicitly
reinterpreted in dimensionless synthetic units. Same100/50/25us grids,entire10ms,
RELAX_ZERO/FLOOR_BASELINE/PULSE outgoing[2,5)ms and initial states. Matched prefix
is exact through2ms. Same unchanged DOP853 continuous reference and source native
activation law/Radau settings. No FlyGym moving muscle-force application.

Measured3models,2100synthetic body mj_step,2112explicit mj_forward,0resets or
explicit step1/step2/Euler/RK/implicit calls outside native mj_step internals,
0CNS/FlyGym campaign. Native owns body q/v/time; external activation commits once.
The foreign sentinel generalized force.125 and body z-torque.25 remain intact after
owned projected-force clearing. Native update/force/time checks and diagonal mass
checks pass. Compiler/internal native operations are outside Python API counts.

Complete new LFS record docs/evidence/lf-synthetic-coupling-v2/run/validation.json:
26710381bytes, raw SHA256
49e7443266c0b2a40129cf2600a99a468f3242764afa1a94e48ce55e72a1d891.
All cases, raw interpolants, internal/reference nodes, costs and counters remain.
Original V1 raw hash12805789411e5b7b2aa9dbaea0f4e18e5075671a9945501970d9e952f99d822e
and endpoint-contract canonical hash1f79cb1435fbc149c3691d800f6106bc985fbb53de5e6a672f349306ce72908d
are mandatory preflight locks. Original raw scientific prerequisites remain false.

## Checks and setup limitations actually encountered

- **89 passed in81.68s**:16new V2 checks plus27V1synthetic,22endpoint and24existing
  activation-integrator checks. Includes actual native one-step timing/endpoint
  consumption, before/after-native failure injection, retained foreign forces,
  duplicate ownership rejection and source/evidence corruption checks. These unit
  fixtures are separate from the one nine-case campaign; no new CNS run.
- Development initially1failed,1passed,4setup errors,10saved tests deselected:
  the sparse checkout held an LFS POINTER for historical integrated_whole_leg_readiness.json,
  so its existing strict M6C raw lock correctly failed. Hydrated the original184MB
  artifact from the shared LFS cache; no hash refresh, waiver or code change.
  Then6development checks passed/10deselected in18.75s before the V2 campaign.
- A first full checkout failed for disk space while copying duplicated Unity
  assets; Git removed the incomplete checkout. No scientific run had started.
  The known clean delivered endpoint worktree was converted to sparse checkout
  omitting its duplicated Unity project; all Git/LFS history and non-Unity code/
  evidence remained intact. The new worktree also omits unneeded assets. Primary
  checkout and user local edits were not changed. Sparse layout is local metadata,
  not a repository configuration change in this PR.
- Static preflight/saved-review tests forbid native model/data/forward/step/muscle
  derivative, Radau/DOP853 and FlyGym/CNS initialization. Exact Windows Git Bash
  saved review completed successfully without another campaign.
- Whitespace and staged LFS identities checked. Existing validated environment
  reused; no dependency, source-physiology/neural/gain/seed or production changes.

## Roadmap after this run

| Gate | Position |
|---|---|
| Motor coverage | **20/42 admitted**, newly admitted0 |
| Endpoint and synthetic coupling | Endpoint contract independently verified; V2 now passes declared synthetic coupling checks; V1 remains failed |
| Immediate next task | Source-to-body transfer prerequisite review: physical units/scale, finite-angle geometry/length/velocity behavior, exact population/tendon and neural-activation evidence |
| Before a new Unity muscle-interface run | Resolve those physical/anatomical/neural/raw gates, then perform a separately specified bounded headless experiment |
| Independent balance/walking | Not established; current position-control assistance must be explicit in future causal tests |

The next review should inventory existing source/model evidence and distinguish
unit conventions/reference fidelity from biological calibration. Do not invent a
force scale, infer individual muscle binding from names, tune gain/drive to obtain
movement, or refresh unresolved raw locks. It may identify missing evidence rather
than authorize coupling. Keep production disconnected. No new Unity behavior yet;
the software gate passed, while physical/neural transfer remains the next milestone.

## Changed files and purpose

- .gitattributes: separate LFS rule for V2 evidence.
- docs/LF_SYNTHETIC_COUPLING_V2.md: prospective corrected implementation protocol.
- malecns_backend/embodiment/lf_synthetic_coupling_v2.py: endpoint-aware adapter,
  same-reference campaign, reused mechanical checks and V2 role/evidence evaluator.
- tests/test_lf_synthetic_coupling_v2.py:16 native/ownership/source/corruption tests.
- docs/evidence/lf-synthetic-coupling-v2/run/validation.json: complete new raw evidence.
- docs/LF_SYNTHETIC_COUPLING_V2_RESULTS.md: results, setup limitations and commands.
- docs/UNITY_AND_BALANCE_ROADMAP.md: updated completed software gate and Unity prerequisites.
- docs/LEG_MAPPING_STATUS.md and docs/PROJECT_HANDOFF.md: unchanged count and transfer-review next task.

## Windows Git Bash after merging

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
git lfs pull --include="malecns_backend/embodiment/interface_output/integrated_whole_leg_readiness.json,docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather,docs/evidence/lf-pose-force-v1*/run/validation.json,docs/evidence/lf-activation-transient-v1/run/validation.json,docs/evidence/lf-activation-integrator-v1/run/validation.json,docs/evidence/lf-native-isolation-v1*/run/validation.json,docs/evidence/lf-synthetic-coupling-v*/run/validation.json"
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m malecns_backend.embodiment.lf_synthetic_coupling_v2 --report docs/evidence/lf-synthetic-coupling-v2/run/validation.json
code docs/LF_SYNTHETIC_COUPLING_V2_RESULTS.md docs/UNITY_AND_BALANCE_ROADMAP.md
```

Expected SYNTHETIC_COUPLING_V2_VERIFIED_TRANSFER_BLOCKED and9PASS lines. Original
V1 stays INTEGRITY_FAILURE,allraw dense samples retained,20/42/0newadmissions.
Saved review performs no native body stepping/reference solving/CNS. No Unity
run or campaign repeat is needed.

Optional implementation regression (fresh scratch directory):

```bash
"$PY" -m pytest -q -p no:cacheprovider --basetemp="$PWD/.pytest-tmp-coupling-v2-manual" tests/test_lf_synthetic_coupling_v2.py tests/test_lf_synthetic_coupling.py tests/test_lf_activation_endpoint.py tests/test_lf_activation_integrator.py
# Expected89passed; native fixture implementation tests included, no new CNS campaign.
```
