# Activation endpoint ownership contract v1

Prospective implementation/reference specification, 2026-10-25; baseline
origin/newBrain5d92fc5 (merged PR #274). Commit this contract, wrapper, manifest
and tests before the fixed reference check. Do not tune an epsilon to the old14
dense discrepancies, change its guard, edit/reclassify its evidence or repeat it.
No native MuJoCo/FlyGym/CNS experiment, neuron/force/timing/acceptance changes.

## Source/API distinction

SciPy solve_ivp returns solution values in y at its returned t, and a separate
sol object for continuous interpolation. Radau's sol is a cubic collocation
polynomial. Installed1.18.1 stores y_new=y+Z[-1]; dense output separately forms
Q=Z.T@P and evaluates its polynomial plus y_old. Equality of the mathematical
endpoint does not supply a bitwise identity contract between these arithmetic
paths. Pin local radau.py/ivp.py hashes and NumPy/SciPy versions before checks.

The existing integrate_interval already returns the authoritative terminal vector
as after and also returns dense samples. Leave that validated function and every
historical caller unchanged. Add a separately named wrapper with explicit sample
roles. It must delegate once to the existing integrator with the same inputs,
native derivative and solver settings; no alternative physiology or new solver.

## Explicit sampling contract (no tolerance or near-time snapping)

Validate finite shapes, ordered requested offsets in[0,duration], successful
solver status, time endpoints and solver internal state chain. Require after to
be BIT-IDENTICAL to the stored internal terminal vector; likewise initial must
match the stored first vector. Never select a dense vector for state commit.

Create a deep copy with:
- after unchanged as authoritative solver terminal state;
- interpolated_samples retaining EVERY original dense sample unchanged;
- samples selecting the original supplied initial state ONLY at offset==0,
  after ONLY at offset==duration, and the untouched dense sample at other times;
- sample_kinds explicitly INITIAL_STATE / SOLVER_TERMINAL_STATE / DENSE_INTERPOLANT.

Use exact offset comparisons. A representable time immediately below duration
(nextafter(duration,0)) remains an interpolated interior sample. No np.isclose,
epsilon, clipping, smoothing, source parameter or solver-tolerance modification.
Record dense-versus-selected differences as diagnostics, never suppress the
original interpolated value. The wrapper does not commit state or advance time;
the future body adapter still needs its own single-owner transition contract.

## Independent fixed check inventory and acceptance

The checks MUST NOT derive their vectors, cases or pass limits from the previous
synthetic trajectories. Check the old archive raw hash and preserve its failure
only as a separate provenance condition, not as a source of test inputs.

1. Constructed return-object counterexample (NOT an ODE/physics simulation):
   duration.25, initial[2,-3,.5,1], terminal[7,-11,13,-17], offsets0,.125,
   nextafter(.25,0),.25. Dense samples deliberately differ substantially at BOTH
   boundaries and have distinct interior vectors. Require exact endpoint selection,
   interior preservation (including near-end time), unchanged dense record, no
   mutation, exact authoritative state and role tags. This proves policy without
   fitting a tolerance to tiny historical floating-point residues.
2. Actual SciPy Radau plumbing against an analytic LINEAR MOCK law
   a'=(u-a)/tau, tau[.001,.002,.003,.004], initial[.2,.4,.6,.8],
   held control[.9,.7,.5,.3]. Two fixed durations .0001 and .001 seconds, offsets
   0,duration/2,nextafter(duration,0),duration. Same existing Radau settings
   rtol1e-9/atol1e-12. Compare all samples and terminal state against the exact
   exponential solution with absolute error<=1e-8, fixed before outcomes. This is
   solver/API implementation validation, NOT native muscle physiology or biology.

All structural/role/non-mutation checks must pass exactly; both analytic checks
must pass and call the existing solver exactly once each. Retain all raw dense
samples and solver records/costs. Native model/forward/step/CNS counts0. The report
classification is ENDPOINT_CONTRACT_VERIFIED_COUPLING_NOT_REVALIDATED when these
checks pass; otherwise ENDPOINT_CONTRACT_FAILED. No historical numerical or
scientific acceptance threshold changes. Save exclusively, preserve failures.
Saved review re-evaluates records/source locks/analytic solutions without invoking
the solver, model/native derivative or CNS. Unit tests also reject malformed and
inconsistent source return objects, missing/failed solver state, and nonfinite data.

## What this can and cannot authorize

This establishes API/data ownership semantics only. The old synthetic coupling
record remains INTEGRITY_FAILURE with its exact original hash/evaluator. Do not
rewrite historical samples, claim a passing corrected campaign or connect the
wrapper to production in this update. Next: separately specify a corrected
synthetic coupling implementation/protocol that consumes explicit endpoint roles,
retains dense diagnostics and keeps exact terminal-state commit checks plus all
physical error/force/timing budgets. Commit it BEFORE any new outcomes.

Current production20/42; no new admission or independent balance/walking evidence.
Before a meaningful new Unity muscle-interface run: supported coupled numerics,
source/body physical units and geometry/velocity/length transfer, exact anatomical/
neural conversion and unresolved raw prerequisites, followed by a bounded headless
experiment. No reliable calendar estimate follows from these gate counts.

Current stable appearances can include engineered position control on unadmitted
coordinates. Neural contribution and independent balance need matched disturbance/
control comparisons under explicitly declared assistance; a visual replay alone
does not establish either. The present milestone is a trustworthy LF proximal
muscle-force interface, one part of progressing toward42 supported coordinates
and later richer sensory/causal balance/locomotion work.20/42 is not overall project
completion. The current pipeline is unchanged; no new Unity behavior is expected.

References: [SciPy solve_ivp return values and Radau dense output](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html),
[SciPy Radau source](https://github.com/scipy/scipy/blob/v1.18.1/scipy/integrate/_ivp/radau.py).
