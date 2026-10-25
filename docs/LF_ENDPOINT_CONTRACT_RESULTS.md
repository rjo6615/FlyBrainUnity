# Endpoint contract results and next milestone

2026-10-25; fresh origin/newBrain5d92fc5 (merged PR #274). Contract, wrapper,
source manifest and tests committed93e7eb8a6ba3b1d1c0b0607cb9eef6ec34b3f2f4
before one fixed implementation/reference check. No coupled/native/CNS campaign
was repeated. Historical synthetic V1 remains INTEGRITY_FAILURE, unchanged.

## Outcome

**ENDPOINT_CONTRACT_VERIFIED_COUPLING_NOT_REVALIDATED.** The separately named
wrapper delegates exactly once to the unchanged existing Radau interval solver.
It distinguishes authoritative initial/terminal state from interior interpolation:
offset==0 selects the supplied initial vector; offset==duration selects after,
which must exactly equal the stored internal solver terminal vector. All other
offsets retain their dense samples, including nextafter(duration,0).

The wrapper retains EVERY original dense value in interpolated_samples, adds
explicit sample_kinds and returns deep copies without committing activation or
advancing body time. It does not use an epsilon/np.isclose, snap near times, fit a
gain, clamp activation, replace a solver/ODE or change source constants/tolerances.
The old integrator, coupling runner, original guard and failed raw data are intact.

## Independent checks actually executed

The constructed return-object case deliberately has large, finite discrepancies
between boundary interpolants and authoritative states, with distinct interior
vectors. It is NOT an ODE or physics simulation. Exact boundary selection and
interior/near-end preservation pass, retaining all source values. Thus policy is
tested independently of the old14 tiny coupling discrepancies and their sizes.

Two actual SciPy Radau solves use a LINEAR MOCK derivative with a known exponential
solution; this is numerical/API plumbing, NOT native muscle physiology or biology.
The existing solver settings remain rtol1e-9/atol1e-12. Each case calls the solver
once. All requested samples, roles, terminal states and internal nodes are retained.

| Duration | Maximum analytic sample error | Terminal analytic error | Predeclared limit |
|---:|---:|---:|---:|
| .0001s | 1.97091510e-11 | 1.07691633e-14 | 1e-8 |
| .001s | 6.87648827e-11 | 1.40554235e-13 | 1e-8 |

Both endpoint/interior analytic checks pass. Their actual dense/terminal residues
are0; the constructed counterexample, not a requirement that every real solve
must differ, verifies the selection distinction. No native model/forward/body
step, CNS, force application or Unity run occurred in this reference check.

Installed SciPy1.18.1/NumPy2.0.2 and radau.py/ivp.py raw source identities were
pinned before outcomes in input-manifest.json. SciPy's API distinguishes y values
from the sol interpolation object; source inspection shows separate arithmetic
for terminal state and Radau cubic dense output. References:
[solve_ivp API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html),
[Radau source](https://github.com/scipy/scipy/blob/v1.18.1/scipy/integrate/_ivp/radau.py).

## Evidence and implementation validation

New ordinary-Git record docs/evidence/lf-endpoint-contract-v1/run/contract.json:
24186 canonical LF bytes, canonical SHA256
1f79cb1435fbc149c3691d800f6106bc985fbb53de5e6a672f349306ce72908d.
Text normalization applies; scientific old LFS records are unchanged. Preflight
checks the old raw record SHA256
12805789411e5b7b2aa9dbaea0f4e18e5075671a9945501970d9e952f99d822e and confirms
its INTEGRITY_FAILURE plus unchanged historical integrator/protocol/evaluator.
It does not use historical trajectory vectors or errors to generate these cases.

Development first reported14 passes,1 malformed-input-test failure and7 saved tests
deselected: constructed after/internal terminal lists aliased the same buffer, so
the test's mutation changed both consistently. Independent constructed buffers
fixed that test fixture before the prospective check; no endpoint rule or solver
setting changed. Then15 development checks passed/7deselected in.68s.

Tests cover exact endpoint roles, near-end interior preservation, deep copies,
malformed state/status/time/dense values, one delegation, analytic accuracy,
exclusive error output, historical failure preservation, source locks, and static
saved review. Saved review forbids native model/data/forward/step/muscle derivative,
FlyGym/CNS initialization and the numerical solver. It recomputes saved records
and analytic values without repeating the reference check or a physics experiment.

- **73 passed in55.63s**:22 new endpoint checks plus24 existing activation-integrator
  and27 synthetic-coupling/negative-review checks. This focused regression includes
  predecessor native fixture implementation tests, separate from the new two
  linear-mock solver checks. The old failed scientific classification is preserved.
- Exact Windows Git Bash saved review passed in.89s, no solver/native work. Whitespace
  and staged canonical record identity checked. No broad unrelated experiments
  were repeated.
No dependencies, neural/source physiology, mappings or production controls changed.

## Roadmap and limits

Current20/42 admitted, newly admitted0. This resolves the API ownership/sampling
question only. It does NOT revalidate synthetic coupling or retroactively accept
V1. The wrapper is not wired into any historical or production consumer.

Immediate next task: separately specify a corrected synthetic coupling adapter/
protocol consuming explicit initial/terminal/interior roles, while retaining raw
interpolated diagnostics, exact authoritative state commit, all force/time ownership
and physical numerical budgets. Commit before any new coupled outcomes; preserve
failed V1. Then address source-to-body physical/neural transfer prerequisites.

The project milestone is a trustworthy LF proximal muscle-force interface on the
path toward42 supported coordinates, richer senses and later causal balance/
walking. Position-control assistance remains part of the current runtime, so its
stable appearance does not prove independent neural balance. A meaningful NEW
Unity muscle-interface test still needs coupled validation, supported physical/
anatomical/neural transfer, raw prerequisites and a bounded headless experiment.
No reliable calendar estimate follows. See UNITY_AND_BALANCE_ROADMAP.md for the
short user-facing stage/Unity/balance explanation.

## Changed files and purpose

- docs/LF_ENDPOINT_CONTRACT_V1.md: prospective independent contract/checks.
- docs/evidence/lf-endpoint-contract-v1/input-manifest.json: pinned solver/API sources.
- malecns_backend/embodiment/lf_activation_endpoint.py: separately versioned sample
  roles wrapper, fixed constructed/analytic checks and static evidence review.
- tests/test_lf_activation_endpoint.py:22 contract/reference/identity/error checks.
- docs/evidence/lf-endpoint-contract-v1/run/contract.json: complete reference record.
- docs/LF_ENDPOINT_CONTRACT_RESULTS.md: results, limits, tests and commands.
- docs/UNITY_AND_BALANCE_ROADMAP.md: milestone, Unity readiness and independent-balance scope.
- docs/LEG_MAPPING_STATUS.md and docs/PROJECT_HANDOFF.md: checkpoint and next task.

## Windows Git Bash after merging

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
git lfs pull --include="docs/evidence/lf-synthetic-coupling-v1/run/validation.json"
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m malecns_backend.embodiment.lf_activation_endpoint --report docs/evidence/lf-endpoint-contract-v1/run/contract.json
code docs/LF_ENDPOINT_CONTRACT_RESULTS.md docs/UNITY_AND_BALANCE_ROADMAP.md
```

Expected: ENDPOINT CONTRACT VERIFIED; coupling NOT revalidated; historical V1
remains INTEGRITY_FAILURE. Constructed policy and two LINEAR MOCK checks; no native
physics/CNS. Production20/42,0new admissions and next corrected coupling task.
Saved review does not run the solver. No new Unity behavior is expected yet.

Optional relevant implementation checks (fresh scratch directory):

```bash
"$PY" -m pytest -q -p no:cacheprovider --basetemp="$PWD/.pytest-tmp-endpoint-manual-v1" tests/test_lf_activation_endpoint.py tests/test_lf_activation_integrator.py tests/test_lf_synthetic_coupling.py
# Expected73 passed; includes existing native implementation checks, no new CNS campaign.
```
