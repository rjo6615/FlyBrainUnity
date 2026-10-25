# LF force-reference v1.1: construction-free reference replay

Prospective correction, 2026-10-25. Commit this specification and correction before
the separately archived v1.1 repeat. The six tensions, fixture XML, exact-pose
restriction, projection, numerical checks/tolerances, force ownership and admission
boundary in `LF_FORCE_REFERENCE_V1.md` remain unchanged.

## Preserved v1 and discovered defect

V1 protocol/code committed at 8228e84, then all six fixture conditions passed their
recorded array checks. Its 143158-byte validation.json remains unchanged at
`docs/evidence/lf-force-reference-v1/validation.json`, SHA256
5f632b45ea9e5e4948a40bed97539a6428706b4fa7385b7e408c8918153a1f9f.
However, the strict saved-review test failed: the inherited audit calls
`_windows_m7d_corrected_spontaneous_adapter._protocol`, then `old._inventory`, then
`enumerate_live_actuators`. That path constructs a FlyGym model and initializes
forward dynamics. Its native calls were outside the fixture's 18-call counter.

Thus v1 is retained as fixture-array evidence with **rejected total-operation /
construction-free-review provenance**. It does not substantiate a zero-dynamics
preflight/review or an overall count of only 18 explicit forward calls. No evidence
of CNS transitions or time integration was found, and no old source or result is
rewritten. Earlier reports' zero-integration/CNS claims are distinct from model
construction/forward-dynamics claims; the latter should not be inferred from them.
Original historical audit/crosswalk code and artifacts remain untouched.

## Corrected reference loading

The new local static loader directly reuses the original snapshot, frozen_record,
neuron codec, resolve_population/inspect_lf/row_record validators and crosswalk
extractor. It checks the same saved canonical sources, original raw freezes,
every identity/alias/null/covector, all 22 remaining rows and all official source
rows. It obtains the 42-row admission metadata from the original locked
`build_live_protocol`, then unchanged v2/v3 derivations with an explicitly empty
physical-record list. It never calls the live inventory enumerator. This checks
static admission metadata, not a newly compiled fly's physical bindings. Native
fixture bindings are verified separately in the execution phase as before.

The strict preflight/review test now forbids mj_forward, mj_step and live actuator
enumeration. Do not weaken that test or hide construction behind a counter.
Saved v1.1 review verifies archived numeric evidence without dynamics. Execution
alone compiles the synthetic fixture and makes its 18 explicit mj_forward calls;
compiler-internal calculations are not characterized as 18 total arithmetic calls.
Schema is lf-force-reference-validation-v1.1, evidence directory
`docs/evidence/lf-force-reference-v1_1/`. No new physics parameters or acceptance
thresholds. Repeating the fixed fixture is justified only by this implementation
boundary correction; it is not a search for a behavioral pass.

Historical raw scientific prerequisites remain separately reported and unresolved
in CRLF representation. The static loader does not satisfy or supersede them.
Production remains 20/42; no new neural muscle law, individual tendon binding,
physiological force scale or moving-fly use is established.

## Git Bash after merge

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
git lfs pull --include="docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather"
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m malecns_backend.embodiment.lf_force_reference_validation --report docs/evidence/lf-force-reference-v1_1/validation.json
code docs/LF_FORCE_REFERENCE_RESULTS.md
```

Expected on success: FIXTURE VERIFIED; six cases / 18 recorded explicit native
fixture forward calls; zero integration/CNS transitions, current 20/42. The review
itself performs no dynamics. V1 is retained and is not accepted by the v1.1 reviewer.

Execution also wraps the Python mj_forward entry point across preflight and the
complete fixture campaign, delegating every call to the unchanged native function.
Its separately observed call count must equal 18. The mj_step entry point is
guarded: any attempted call fails before integration and makes validation fail.
Both functions are restored in a finally block. This counts Python API calls, not
compiler-internal calculations; it is instrumentation, not mocked physics.
