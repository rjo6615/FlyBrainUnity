# Milestone 4A: audited six-leg sensorimotor anatomical map

## Scope and non-intervention

This is a read-only anatomical inventory, not a controller. It does not import
FlyGym, initialize physics, decode motor activity, step a simulation, or send an
action. No equation, gain, timing parameter, joint limit, seed, pose, M3D causal
implementation, or Unity asset was changed. The committed JSON is generated
only from the audited `interface_map.json` plus an explicit physical inventory.

## Sources and method

* **Primary biology:** `malecns_backend/interface_map.json`, including all 170
  muscle records, 151 sensor records, and 285 unresolved motor records.
* **Annotation semantics:** `fly-brain-main/public/data/bodymap.json`, its
  compiler, and `fly-brain-main/docs/09-bodymap.md`.
* **Physical body:** the NeuroMechFly 42-position action order already used by
  the validated embodiment, cross-checked against the joint names, classes, and
  exact inherited radian ranges in
  `fly-brain-main/body/flybody/fruitfly.xml`. FlyGym is optional and was not
  installed in the audit environment; no simulation was constructed merely to
  discover metadata.

The inventory finds **42 leg actuators**, **29 leg sensory annotation records**,
and **102 distinct leg motor populations** (126 actuator-association records;
some populations explicitly occur against two bodymap targets). All **285**
`unmappedMotor` records are retained as unresolved rather than assigned a leg.

## Joint matrix

Each cell is `sensory / motor`. `EXACT` means the source explicitly identifies
the required anatomy. `SUPPORTED` records a documented body-model
interpretation. Ambiguity was never promoted by symmetry.

| Leg | Coxa | Coxa yaw | Coxa roll | Femur | Femur roll | Tibia | Tarsus1 |
|---|---|---|---|---|---|---|---|
| LF (T1 left) | AMBIGUOUS / SUPPORTED | AMBIGUOUS / SUPPORTED | AMBIGUOUS / SUPPORTED | MISSING / SUPPORTED | MISSING / SUPPORTED | EXACT / SUPPORTED | MISSING / SUPPORTED |
| LM (T2 left) | AMBIGUOUS / SUPPORTED | AMBIGUOUS / SUPPORTED | AMBIGUOUS / SUPPORTED | MISSING / SUPPORTED | MISSING / SUPPORTED | **EXACT / EXACT** | MISSING / MISSING |
| LH (T3 left) | AMBIGUOUS / SUPPORTED | AMBIGUOUS / SUPPORTED | AMBIGUOUS / SUPPORTED | MISSING / SUPPORTED | MISSING / SUPPORTED | EXACT / SUPPORTED | MISSING / MISSING |
| RF (T1 right) | MISSING / SUPPORTED | MISSING / SUPPORTED | MISSING / SUPPORTED | MISSING / SUPPORTED | MISSING / SUPPORTED | EXACT / SUPPORTED | MISSING / SUPPORTED |
| RM (T2 right) | AMBIGUOUS / SUPPORTED | AMBIGUOUS / SUPPORTED | AMBIGUOUS / SUPPORTED | MISSING / SUPPORTED | MISSING / SUPPORTED | EXACT / SUPPORTED | MISSING / MISSING |
| RH (T3 right) | AMBIGUOUS / SUPPORTED | AMBIGUOUS / SUPPORTED | AMBIGUOUS / SUPPORTED | MISSING / SUPPORTED | MISSING / SUPPORTED | EXACT / SUPPORTED | MISSING / MISSING |

Across the 84 per-joint sensory/motor assessments the totals are **EXACT 7**,
**SUPPORTED 37**, **AMBIGUOUS 15**, and **MISSING 25**. In addition, **303
UNMAPPED** inventory entries comprise 18 non-joint leg sensory channels and 285
unresolved motor annotations. These categories answer different questions and
must not be summed as though each entry were one actuator association.

## Interpretation and unresolved anatomy

* Chordotonal records explicitly name tibia, segment, and side, so all six
  tibia sensory associations are exact. Their sizes are asymmetric: 23/13
  (T1 L/R), 80/83 (T2 L/R), and 93/100 (T3 L/R).
* Hair plates explicitly name the coxa but not which of the body's three coxa
  axes. They therefore remain ambiguous for all three axes. T1 right has no
  hair-plate counterpart at all; all three RF coxa sensory interfaces are
  missing.
* Tactile, taste, and campaniform populations are clearly leg related and are
  preserved, but claw contact/taste or tarsal load cannot defensibly be reduced
  to one position actuator. They remain unmapped.
* Femur and femur-roll motor associations are supported by explicit bodymap
  muscle targets; no source sensor names those joints. Tarsus motor groups exist
  only where explicitly annotated. `tarsus2`/adhesion associations are retained
  separately because the 42-position inventory has no corresponding active
  position channel.
* The many unequal bilateral population sizes are reported in JSON. A matching
  name is not treated as proof of equivalence, and symmetry does not manufacture
  an absent body ID or upgrade confidence.
* Every stored addressable ID is copied as a JSON integer from the audited map,
  is unique inside its source population, and falls within signed 64-bit range.
  The CSR convention remains presynaptic row to postsynaptic target. Shortest
  paths were not computed: reachability is neither required for this anatomical
  association nor evidence of dynamic or functional activation.

## Preserved M3D reference

The reference remains byte/value-equivalent in scientific content:

* `chordotonal T2 left` (80 neurons) → `joint_LMTibia`, action index 12;
* `Ti extensor MN T2 left`: **800911, 801234**;
* `Ti flexor MN T2 left`: **802295, 818295, 823739, 824041, 927808**.

Accessory tibia flexors remain inventoried but were not inserted into the M3D
decoder group. **VALIDATED M3D REFERENCE MAPPING PRESERVED: PASS.**

## Reproduction

Run `python -m malecns_backend.embodiment.six_leg_audit --check` for the matrix,
totals, preserved-reference check, and stale-output check. Use `--write` only to
regenerate the deterministic JSON after an intentional source change.
