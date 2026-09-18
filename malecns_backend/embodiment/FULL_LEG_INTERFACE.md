# M5A full-leg sensorimotor interface audit

M5A is a deterministic, read-only inventory. It does **not** activate a joint,
step physics, alter the MaleCNS runtime, or implement locomotion logic.

## Method

The audit calls M4A's `six_leg_audit.generate_map()` rather than introducing a
second annotation parser. Each of M4A's 42 actuator associations becomes one
joint-centric record. Population body IDs are deduplicated and numerically
sorted; candidates are sorted by population name and IDs; actuator records are
sorted by action index. An `unmappedMotor` population is retained in the
unassociated evidence inventory, but is not assigned to a joint without an
annotation-supported association.

The default dependency-free run uses M4A's physical inventory and marks live
MuJoCo addresses unavailable. `--live` constructs the same
`Fly(enable_adhesion=False, control="position")` and `SingleFlySimulation`
stack as the validated body adapter. It reads the compiled model through
`simulation.physics.model` (including the existing `env`/`_env` compatibility
paths), without resetting or stepping physics. Actuator-to-joint association
comes from compiled `actuator_trntype`/`actuator_trnid` metadata rather than a
name substitution. A mismatch with M4A actuator names/order fails.

## Evidence tiers and eligibility

* **Tier 1:** sensory and motor are both `EXACT`.
* **Tier 2:** both are at least `SUPPORTED`, and one or both is not exact.
* **Tier 3:** either side is `AMBIGUOUS` (unless missing evidence forces tier 4).
* **Tier 4:** either side is `MISSING` or `UNMAPPED`.

Only tiers 1 and 2 are marked activation-eligible. This is an engineering
inventory flag, not activation and not a biological confidence score.

## Six-tibia regression

M4B loads its six tibia definitions from the committed M4A map. M5A requires
the regenerated M4A serialization to equal that committed source, then checks
LF, LM, LH, RF, RM, and RH tibia actuator identity, index, candidate names, and
confidence. A discrepancy raises an error instead of emitting an audit.

## Commands

Dependency-free committed audit:

```console
python -m malecns_backend.embodiment.full_leg_interface_audit --json malecns_backend/embodiment/interface_output/full_leg_interface_audit.json
```

Real installed FlyGym/MuJoCo metadata introspection (read-only):

```console
python -m malecns_backend.embodiment.full_leg_interface_audit --live --json malecns_backend/embodiment/interface_output/full_leg_interface_audit.json
```
