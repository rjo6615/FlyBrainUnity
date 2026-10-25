# Synthetic coupling V2: explicit endpoint ownership

Prospective protocol,2026-10-25. Baseline origin/newBrain7c8d358 (merged PR #275).
Commit this protocol, adapter/runner and tests BEFORE one new nine-case campaign.
This is a separately versioned implementation correction justified by the
independent endpoint contract, not a retry of V1 until it passes. Preserve V1's
raw data, source/evaluator and INTEGRITY_FAILURE. No threshold/window/grid/force/
source-physiology/seed/neural tuning, no automatic retry after V2 outcomes.

## What changes and why

SciPy exposes an authoritative terminal state and separately evaluated dense
interpolation. LF_ENDPOINT_CONTRACT_V1.md independently specifies and tests exact
initial/terminal state selection and unchanged interior interpolation without an
epsilon fitted to old residues. Require the exact canonical endpoint-contract
record1f79cb1435fbc149c3691d800f6106bc985fbb53de5e6a672f349306ce72908d,
recomputed passing evaluation, installed solver source manifest and historical
V1 raw hash12805789411e5b7b2aa9dbaea0f4e18e5075671a9945501970d9e952f99d822e.

A V2 adapter subclasses the restricted V1 SyntheticSplitAdapter. Reuse its
constructor, context guard, exact joint/body/address observer, apply/clear force
ownership, projection, physical-state snapshots and failure latch. Override only
the transition orchestration to call the independently verified endpoint wrapper
instead of the raw interval API. Body update order and all force/state operations
stay the same. No module-global integrator replacement or production hook.

Each interval asks for one sample at offset==dt. That sample MUST be bit-identical
to the authoritative after/internal terminal vector, tagged SOLVER_TERMINAL_STATE.
Keep EVERY raw polynomial value in interpolated_samples, with its own saved
content hash and dense-versus-terminal diagnostic. Neither hide nor bound the old
polynomial residual to obtain a pass. The sample/commit meaning is explicit;
physical error/force/ownership criteria and the exact terminal commit check stay.
The old endpoint wrapper, V1 runner/evaluator and archived outcomes are unmodified.

## Same declared mechanics, conditions and independent reference

Reuse the exact LF_SYNTHETIC_COUPLING_V1.md fixture and equations: four independent
hinge rotors, inertias[1,2,3,4],nq=nv4,nu=na=ngeom0,zero gravity/passive/contact,
synthetic dimensionless units. Source activation derivative/Radau settings and
frozen gain/bias/control floor unchanged; total tension T=-(gain*a+bias), existing
constant R_G projection. No physical source-to-FlyGym registration is implied.

Three grids100/50/25us,whole10ms; RELAX_ZERO,FLOOR_BASELINE,PULSE outgoing[2,5)ms,
same initial states and .125 foreign sentinel generalized force plus .25 body
z-torque. Native body step owns q/v/time once; external activation commits once
after successful body advancement/owned-force clearing. Reject duplicate owners,
stale force buffers and unauthorized force; preserve both foreign buffers. On
body failure retain uncertain native state, latch failed and prohibit retry.

Reuse V1 continuous_reference unchanged: DOP853 with same source law, analytic
continuous rotor dynamics,rtol1e-11/atol1e-13,max_step2.5us,exact control boundaries.
Store all401 reference states and solver nodes/costs. Compare all native timestamps
in the full window against reference slices; no selected window or endpoint-only
acceptance. Retain Radau internal nodes, terminal and raw interpolant data.

Expected operation accounting unchanged:3models,2100synthetic mj_step,2112explicit
mj_forward (3mass+9initial+2100post-clear),0resets/explicitstep1/step2/Euler/RK/
implicit outside native mj_step internals,0CNS/FlyGym runs. Count Python API calls;
compiler/internal native work is outside that count. Failed/partial outputs are
exclusive and retained. No third campaign if V2 fails.

## Unchanged physical/numerical acceptance and added data-role checks

Reuse V1 evaluate unchanged for its mechanical/source/state/force/solver/numerical
checks and pulse refinement. Its top-level schema is V1-specific: V2 requires its
OWN exact schema and reuses the remaining V1 check results without pretending the
new record is V1. Recompute the composite V2 integrity/classification explicitly.
Do not modify V1 or reclassify the historical V1 archive.

All V1 non-schema checks remain required: exact source/fixture identities,
mass/metadata/force preservation, correct controls and state chain, matched prefix
through2ms, native time<=1e-12, force/native-Euler algebra<=1e-9, exact solver
terminal commit and complete finite trajectories/internal nodes.

All9 cases must meet activation error<=.01/bounds[-1e-12,1+1e-12],q_error<=1e-5,
v_error<=1e-3 (synthetic units). Pulse E=max(q_error/1e-5,v_error/1e-3) must satisfy
E50<=.75E100+1e-12,E25<=.75E50+1e-12. No timestep is selected for production.

Additionally require EVERY step's endpoint contract ID, exact terminal sample
role and state source, finite shape(1,4)raw interpolation record and its content
hash. Report raw dense-terminal mismatch counts/maxima for every case, with no
post-outcome tolerance. Preserve all samples even when different. Corruption or
role substitution must fail the V2 evaluator/saved verification.

All integrity/numerical/refinement criteria must pass for
SYNTHETIC_COUPLING_V2_VERIFIED_TRANSFER_BLOCKED. Valid integrity with numerical/
refinement failure remains NUMERICAL_LIMITS_OBSERVED; invalid integrity remains
INTEGRITY_FAILURE. Successful saved review verifies evidence, not biological
transfer. Review constructs no models, solves no ODEs and runs no CNS.

## Roadmap and limits

Production20/42,0newadmissions. V2 is synthetic solver/force-buffer implementation
evidence only, not moving FlyGym muscle application, calibrated biological force,
independent balance or gait. Original raw/anatomical/neural gates remain. No Unity
change in this update. If V2 is accepted, next is a source-to-body transfer
prerequisite review with explicit physical units, finite-angle registration,
length/velocity dependence and missing neural/population binding evidence. Keep
the wrapper disconnected from production pending those gates and bounded headless
evidence. Do not treat API or synthetic correctness as a guaranteed new behavior.
