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
paths), without resetting or stepping physics. Action-to-actuator association
comes from FlyGym's ordered `_actuators` MJCF elements, the same sequence that
FlyGym binds when applying an action. In this construction the first element's
`name` and pre-attachment `full_identifier` are both
`actuator_position_joint_LFCoxa`. dm_control qualifies names when attaching the
fly, so that element can appear in the compiled table as, for example,
`0/actuator_position_joint_LFCoxa`, while its joint appears as
`0/joint_LFCoxa`. The audit derives (rather than assumes) that slash-delimited
qualification and requires the actuator and transmitted joint to have the same
prefix and exact local identifiers. Compiled `actuator_trntype`/`actuator_trnid`
metadata then identifies the physical joint. If association fails,
the exception reports matching compiled actuator names and IDs, transmission
types and IDs, and joint names and IDs. A mismatch with M4A actuator
names/order fails. The live command also prints the seven discovered physical
joint names for each leg.

The 42 position-control dimensions are six legs times seven distinct physical
hinge DOFs in FlyGym's public order: `Coxa`, `Coxa_roll`, `Coxa_yaw`, `Femur`,
`Femur_roll`, `Tibia`, and `Tarsus1`. In particular, `joint_LFCoxa` is the
first LF coxa hinge; it is not a group containing the separately actuated
`joint_LFCoxa_yaw` and `joint_LFCoxa_roll` hinges.

## M4A action-order correction

The original M4A physical inventory used a manually declared DOF order. M5A
live introspection on the authoritative Windows FlyGym/MuJoCo runtime found 12
mismatches: every leg had `Coxa_yaw` and `Coxa_roll` exchanged. The other 30
action dimensions matched, including all six tibias at LF 5, LM 12, LH 19, RF
26, RM 33, and RH 40. The compiled actuator/transmitted-joint metadata
independently agreed with `fly.actuated_joints`, so M4A now follows that live
contract. This is an inventory/mapping correction made before expanding
actuator activation, not a change to MaleCNS neural dynamics or the existing
six-tibia scientific outputs.

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
confidence against an explicit preserved baseline. A discrepancy raises an
error instead of emitting an audit. Regeneration leaves the aggregate at tier
1: 1, tier 2: 5, tier 3: 15, tier 4: 21, with 6 activation-eligible joints;
the counts do not change because biological evidence remains attached to the
named joint while only the two physical coxa action indices move.

## Commands

Dependency-free committed audit:

```console
python -m malecns_backend.embodiment.full_leg_interface_audit --json malecns_backend/embodiment/interface_output/full_leg_interface_audit.json
```

Real installed FlyGym/MuJoCo metadata introspection (read-only):

```console
python -m malecns_backend.embodiment.full_leg_interface_audit --live --json malecns_backend/embodiment/interface_output/full_leg_interface_audit.json
```
