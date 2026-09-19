# M6A: Whole-Leg Motor Mapping Audit

## Scope and terminal result

**Terminal classification: `WHOLE_LEG_MOTOR_AUDIT_COMPLETE`.**

M6A is a deterministic, read-only anatomical/interface audit. It projects the
locked M4A mapping and M5A interface inventory; it does not initialize or step
physics, actuate a joint, modify MaleCNS dynamics, add an encoder or decoder,
or run a locomotion experiment. An annotation-backed candidate association is
not a claim of demonstrated biological function. Connectivity was not used as
mapping or directional evidence.

The machine-readable authority is
`interface_output/whole_leg_motor_mapping_audit.json` (`M6A.0`). It contains
every actuator, candidate and body-ID list, original annotation metadata,
forward and reverse mappings, physical-axis evidence, classifications,
breakdowns, limitations, and locked provenance.

## Inputs and fail-closed checks

The audit regenerates M4A and M5A in memory and verifies their historical
constraints before classifying anything. It requires M4A totals of `EXACT=7`,
`SUPPORTED=37`, `AMBIGUOUS=15`, `UNMAPPED=303`, and `MISSING=25`; the M5A
summary of 42 physical joints, tiers `1/5/15/21`, 6 activation-eligible, 38
motor-mapped, and 6 sensory/both-mapped; and the exact seven-joint order on all
six legs. A disagreement terminates as `ANNOTATION_AUDIT_FAILURE` or
`ACTUATOR_ORDER_FAILURE`, rather than producing a partial scientific result.

The three generated historical JSON inputs are SHA-256 locked as raw bytes.
The two implementation sources needed to check the established interface and
decoder semantics are locked after canonical-LF normalization. The JSON lists
each expected and observed digest. Any mismatch terminates as
`PROVENANCE_FAILURE`. Optional `--live` inspection uses M5A's read-only compiled
MuJoCo adapter inspection and fails if live FlyGym ordering differs; it never
calls reset or step. The committed artifact uses the locked physical inventory
because FlyGym is not required for deterministic regeneration.

## Physical actuator inventory

The authoritative order is repeated for each of `LF`, `LM`, `LH`, `RF`, `RM`,
and `RH`:

| Offset | Canonical joint class |
|---:|---|
| 0 | Coxa |
| 1 | Coxa_roll |
| 2 | Coxa_yaw |
| 3 | Femur |
| 4 | Femur_roll |
| 5 | Tibia |
| 6 | Tarsus1 |

Thus the inventory is exactly **6 legs × 7 actuators = 42**, at global indices
0–41. Every JSON physical record also includes its M5 tier/eligibility and
six-tibia membership.

## Classification method

Candidate-level `EXACT`, `SUPPORTED`, `AMBIGUOUS`, `UNMAPPED`, and `MISSING`
retain the historical M4A definitions and reasons. M6A separately assesses:

* **motor mapping status** — `VALIDATED`, `SUPPORTED`, `AMBIGUOUS`, or
  `UNMAPPED`;
* **decoder readiness** — the five requested readiness values, without using
  correlations, connectivity, body motion, or a desired command to invent a
  sign;
* **directional structure** — based only on exact annotation terms and explicit
  `dir` values; and
* **physical-axis uniqueness** — reverse mappings expose a population that is
  a candidate for more than one FlyGym actuator rather than treating each use
  as independently validated.

An explicit pair requires both annotation signs. A single direction is
`MAGNITUDE_ONLY`; M6A never manufactures its antagonist by negation. The six
existing tibiae are the only `VALIDATED_EXISTING` decoders. A non-tibia
actuator enters Tier B only when it has an annotation-backed, unique physical
association, both explicit signs, and no shared-population conflict.

## Quantitative result

| Measure | Count |
|---|---:|
| Physical actuators | 42 |
| Actuators with an annotation-backed motor candidate | 38 |
| Actuators with a unique motor mapping | 26 |
| Actuators with ambiguous mapping | 12 |
| Actuators with explicit, non-ambiguous directional information | 26 |
| Directionally resolvable future decoders (excluding validated tibiae) | 14 |
| Magnitude-only | 6 |
| Insufficient evidence | 4 |
| Shared populations spanning physical axes | 6 |
| Tier A | 6 |
| Tier B | 14 |
| Tier C | 18 |
| Tier D | 4 |

The JSON provides complete breakdowns by leg, canonical joint class,
left/right side, and thoracic segment. Low coverage and unresolved evidence are
retained rather than optimized away. The motor-population inventory contains
all 102 uniquely named annotation-backed leg motor populations plus all 285
`unmappedMotor` records. The former includes tarsus2/adhesion annotations for
which the 42-action physical inventory has no corresponding actuator and the
LM accessory tibia population excluded by the locked decoder; these are
inventoried without silently promoting them to forward associations. The
`unmappedMotor` records remain unresolved because their annotation does not
defensibly name a corresponding leg joint and segment.

## Physical-axis ambiguity and shared populations

Six annotation populations span two candidate axes:

| Population | Candidate actuators |
|---|---|
| Pleural remotor/abductor MN T1 left | LF Coxa, LF Coxa_roll |
| Pleural remotor/abductor MN T1 right | RF Coxa, RF Coxa_roll |
| Pleural remotor/abductor MN T2 left | LM Coxa, LM Coxa_roll |
| Pleural remotor/abductor MN T2 right | RM Coxa, RM Coxa_roll |
| Pleural remotor/abductor MN T3 left | LH Coxa, LH Coxa_roll |
| Pleural remotor/abductor MN T3 right | RH Coxa, RH Coxa_roll |

These are unresolved physical-axis decomposition conflicts. Consequently, all
12 affected Coxa/Coxa_roll actuators are Tier C, and none is eligible for M6B.
The reverse mapping records exact body IDs and candidate classification for
each association so a future implementation cannot silently double-drive the
population.

## Six-tibia regression

The regression passes at immutable indices **LF 5, LM 12, LH 19, RF 26, RM
33, RH 40**. Population names, body IDs, mapping confidence, and locked
biological-association digests are checked through M5A. Existing semantics are
reported, not reimplemented: explicit annotation signs are combined as the
per-neuron mean for each direction by the existing `IsolatedMotorDecoder`.
Every validated tibia remains Tier A. A mismatch terminates as
`SIX_TIBIA_REGRESSION_FAILURE`.

## Rule-based M6B scope

The following **14** actuators satisfy all five M6B eligibility rules. This is
an evidence-based list, not permission to activate them in M6A and not a
ranking for locomotion:

* `joint_LFCoxa_yaw`, `joint_LFFemur`, `joint_LFTarsus1`
* `joint_LMCoxa_yaw`, `joint_LMFemur`
* `joint_LHCoxa_yaw`, `joint_LHFemur`
* `joint_RFCoxa_yaw`, `joint_RFFemur`, `joint_RFTarsus1`
* `joint_RMCoxa_yaw`, `joint_RMFemur`
* `joint_RHCoxa_yaw`, `joint_RHFemur`

Tier B means ready for a future isolated motor validation only. No decoder was
created or experimentally validated for these actuators here.

## Reproduction

```bash
python -m malecns_backend.embodiment.whole_leg_motor_mapping_audit --check
pytest -q tests/test_whole_leg_motor_mapping_audit.py
```

To regenerate the committed projection after an intentional, reviewed update
to its locked authorities, update the provenance locks and run with `--write`.
Do not update a lock merely to suppress a provenance failure.
