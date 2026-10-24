# Live-v3 contact context validation v1

Specified before inspecting this protocol's outcomes, 2026-10-24. Question: in
the unchanged supported live-v3 context, can the existing total Tarsus5 force
proxy be attributed to exact Tarsus5/support contact throughout a fixed sampled
window, with clean positive and negative observations for every foot?

This is an observational transfer prerequisite, not a matched sensory-delivery
experiment or causal calibration. No tactile input is enabled, even on success.
The previous v1 rejection and isolated v2/v2.1 results remain unchanged.

## Fixed execution

Run one fresh existing `create_live_v3_session` for exactly 20000 physics steps
(2 s, dt 0.0001 s), retaining reset plus all steps (20001 states). Use its normal
20-channel neural motor inventory, six tibia proprioceptive populations, frozen
seed, tripod/spawn, position control, static ground and inherited calibration
surface, zero adhesion, gravity, floor/self collisions and explicit pair contact
settings. Reuse `adapter._runtime` and the scientific kernel; add no second neural
or embodiment loop. No surface repositioning, root constraint, collision filtering,
gain/threshold/weight/seed revision, sample selection, early success or retry.
The inherited runtime already verifies the exact corrected reset and surface.

A passive simulation proxy records the factory's reset observation and the exact
observation returned by every step; it does not refresh, forward, reset, call a
neural API, sample RNG or alter the action. Every sample records all detected
contacts with exact geom IDs, contact frame, solver address and local force/torque,
the six body force vectors and telemetry vectors, physics state and commands,
applied-force maxima and an immutable-context fingerprint. Record raw model
identity/ownership tables, actual FlyGym sensor placement bodies, model contact
configuration and support geometry. Observe the ordinary live body; a held-joint
physics smoke test is implementation validation only and cannot satisfy this run.

## Independent attribution

Resolve Tarsus5 body IDs and unique exact Tarsus5 geoms from compiled names and
ownership, then verify their actual 36-row FlyGym contact-sensor placement order.
Require exactly the static world `ground` and inherited calibration surface as
support identities; do not accept a similarly named moving body as ground.

MuJoCo 3.2.7's `mj_contactForce` returns contact-local force then torque. Transform
the first three values with the transpose of the recorded contact frame; subtract
from geom1's owning body and add to geom2's owning body. Sum all solver-active
contacts independently for each Tarsus5 body. Keep floor and calibration-surface
contributions separate, plus all other pairs involving that sensor body. A contact
on another geom of the same body is an unselected source. Do not infer attribution
from a force threshold or structural path. Contacts on other bodies can influence
the mechanics but are not direct sources in this body's external-force array.

Compare reconstructed total linear force to raw `cfrc_ext[body,3:]` with fixed
rtol=1e-10, atol=1e-14 (numerical observer audit, not a sensing threshold). Verify
telemetry exactly equals that vector after FlyGym's float32 conversion. Require
finite vectors, proper orthonormal contact frames, valid unique IDs, zero applied
forces and no connect/weld/flex equality sources; otherwise attribution is
unsupported. Record inactive geometric contacts too; do not silently count them
as force-bearing or discard them for acceptance.

Primary reference for sign/frame and additional external-force sources:
[MuJoCo 3.2.7 mj_rnePostConstraint](https://github.com/google-deepmind/mujoco/blob/3.2.7/src/engine/engine_core_smooth.c#L1850).
API reference:
[mj_contactForce](https://mujoco.readthedocs.io/en/3.2.7/APIreference/APIfunctions.html#mj-contactforce).
The installed FlyGym observer reads named body `cfrc_ext` and casts to float32.

## Acceptance specified before outcomes

Require the archived v2.1 prerequisite hashes, all six saved acceptances and strict
re-evaluation of each leg. Require unchanged source hashes before/after execution,
normal-runtime identity checks, complete fixed schedule, finite physics, exact
sensor/geom/support identities, fixed context and verified passive observation.

For every foot, over **all** 20001 states: no unselected direct contact source,
no force-reconstruction discrepancy, and exact support contact presence equals
telemetry magnitude > the unchanged engineering threshold 1e-12. Require at least
one clean negative state (no contact on that sensor body, magnitude <= threshold)
and at least one clean exact-support positive state (magnitude > threshold).
All detected unselected contacts on that sensor body are ambiguous, even if
inactive or zero force. Other-body collisions are retained and summarized; they
do not themselves invalidate the sensor's direct-source attribution.

Missing coverage is INCONCLUSIVE, integrity failures/disagreements are REJECTED,
and exceptions/interruption preserve the partial trace and prevent acceptance.
Every state is retained; no minimum successful subwindow is selected. This cannot
prove separation or absence of collisions between stored physics states, nor does
observational acceptance establish a matched causal intervention. Even complete
acceptance is limited to this seed, pose, support and two-second trajectory.

## Manual Windows Git Bash commands

In the PR checkout, use the validated environment (absolute path works in a worktree):

```bash
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m pytest -q tests/test_live_contact_context.py tests/test_live_contact_readiness.py tests/test_live_headless.py
"$PY" -m malecns_backend.live.contact_context --output live-contact-context-dry.json.gz
echo $?  # expected 1, NOT_RUN, no admission
```

For the predeclared single experiment or a separately planned independent replication:

```bash
"$PY" -m malecns_backend.live.contact_context --live --output live-contact-context-v1.json.gz
echo $?  # 0 only if every fixed integrity/coverage/attribution check passes; otherwise 1
```

The output is full gzip-compressed JSON, including per-leg checks and raw samples.
Existing output paths must fail before session creation and remain unchanged.
There are no duration/seed/threshold/placement knobs. Do not rerun unchanged failures
to seek a pass. CNS initialization may take minutes; no dependency changes are needed.
