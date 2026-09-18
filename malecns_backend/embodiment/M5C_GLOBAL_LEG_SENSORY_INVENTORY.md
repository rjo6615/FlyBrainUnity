# M5C-1 — global leg sensory inventory

## Scope and method

This is a **read-only, annotation-first** inventory.  The search scans all 617
population records in `malecns_backend/interface_map.json`; it does not begin
with the 42 FlyGym actions or restrict discovery to M4A/M5A candidates.  A
population is included only when its source record contains (1) a T1/T2/T3 and
side locus, (2) `kind: joint_angle`, `load`, or `contact`, and (3) a source
mechanosensory/proprioceptive class.  A suggestive population name alone is not
enough.  The JSON retains every body ID, source type/class, raw metadata,
consumer, direction/axis/tuning field, interface association, and decision.

Connectivity was not needed.  The implementation accepts descriptive
connectivity context but deliberately does not pass it into any anatomical
decision.  No mapping, activation eligibility, encoder, runtime, physics,
controller, or locked M4A/M5A/M5B artifact was changed.

## Complete result

The global search found **23 populations and 2,341 distinct neurons**.  The
body-ID sets are disjoint in this inventory.

| Classification | Populations | Neurons | Source basis |
|---|---:|---:|---|
| `JOINT_SPECIFIC` | 11 | 452 | Six chordotonal records explicitly name a tibia joint; five hair-plate records explicitly name a coxa joint. |
| `SEGMENT_SPECIFIC` | 0 | 0 | No additional source-supported segment-only proprioceptor was found. |
| `BROAD_LEG` | 0 | 0 | No included record was localized only to a whole leg. |
| `LOAD_OR_CONTACT` | 12 | 1,889 | Six campaniform records name tarsal force; six tactile records name claw contact. |
| `OTHER_MECHANOSENSORY` | 0 | 0 | Antennal, haltere, and wing/notum populations are mechanosensory but are not leg-associated source records. |
| `UNCERTAIN` | 0 | 0 | — |

Sensory mechanisms are: `joint_angle` **11 populations / 452 neurons**,
`contact` **6 / 1,877**, and `load` **6 / 12**.  Each leg has chordotonal,
tactile, and campaniform populations.  Hair plates exist for LF, LM, LH, RM,
and RH, but the source contains no RF/T1-right hair plate.  Thus LF has 4
populations/177 neurons, LM 4/478, LH 4/501, RF 3/130, RM 4/528, and RH 4/527.

### Population inventory

| Population family | Members | Biological structure | Classification | M5A coverage |
|---|---|---|---|---|
| chordotonal | T1/T2/T3, left/right | source `joint=tibia_T#_side` (femur–tibia angle in the historical model) | `JOINT_SPECIFIC` | 6 used once, at the six Tibia interfaces |
| hair plate | T1/T2/T3 left; T2/T3 right | source `joint=coxa_T#_side` | `JOINT_SPECIFIC`, but not coxa-axis-specific | 5 used and duplicated over three coxa DOFs each |
| campaniform | T1/T2/T3, left/right | source `sensor=force_tarsus_T#_side` | `LOAD_OR_CONTACT` | 6 unused by the 42 position interfaces |
| tactile | T1/T2/T3, left/right | source `site=claw_T#_side` | `LOAD_OR_CONTACT` | 6 unused by the 42 position interfaces |

The machine-readable inventory is the complete per-population report.  In
particular, it preserves `class`, `subclass`, `type`, provenance, consumers,
and every body ID rather than expanding thousands of IDs into this narrative.

## Current-interface coverage

* **Currently used:** 11/23 populations (452/2,341 neurons).  These are the six
  chordotonal and five hair-plate populations.
* **Duplicated across DOFs:** 5/23.  Every available hair plate is associated
  with all three coxa coordinates.  This reports the locked M5A state and does
  not endorse or alter it.
* **Unused:** 12/23 (1,889 neurons): all tactile and campaniform populations.
* **Unrepresentable with the current 42-joint position interface:** 12/23.
  Contact and load are physical observations, not joint-position coordinates.
* **Needs modeled transduction:** 23/23.  Anatomical labels do not themselves
  specify gains, calibration, dynamics, or neuron tuning.  This inventory adds
  none of those assumptions.

The biological structure count is six named tibia joints, five named coxa
joints, six named tarsal-force sites, and six named claw-contact sites.  Counts
by exact structure, side, leg, mechanism, and coverage are serialized in JSON.

## Most interesting unused populations

These are biologically meaningful, but none is a joint-state candidate.

| Population | Leg | Biological structure | Sensor type | Body count | Source specificity | Currently used? | Candidate level |
|---|---|---|---:|---:|---|---|---|
| tactile T1 left | LF | claw_T1_left | contact | 151 | `LOAD_OR_CONTACT` | No | `NOT_JOINT_STATE` |
| campaniform T1 left | LF | force_tarsus_T1_left | load | 2 | `LOAD_OR_CONTACT` | No | `NOT_JOINT_STATE` |
| tactile T2 left | LM | claw_T2_left | contact | 378 | `LOAD_OR_CONTACT` | No | `NOT_JOINT_STATE` |
| campaniform T2 left | LM | force_tarsus_T2_left | load | 2 | `LOAD_OR_CONTACT` | No | `NOT_JOINT_STATE` |
| tactile T3 left | LH | claw_T3_left | contact | 394 | `LOAD_OR_CONTACT` | No | `NOT_JOINT_STATE` |
| campaniform T3 left | LH | force_tarsus_T3_left | load | 2 | `LOAD_OR_CONTACT` | No | `NOT_JOINT_STATE` |
| tactile T1 right | RF | claw_T1_right | contact | 115 | `LOAD_OR_CONTACT` | No | `NOT_JOINT_STATE` |
| campaniform T1 right | RF | force_tarsus_T1_right | load | 2 | `LOAD_OR_CONTACT` | No | `NOT_JOINT_STATE` |
| tactile T2 right | RM | claw_T2_right | contact | 428 | `LOAD_OR_CONTACT` | No | `NOT_JOINT_STATE` |
| campaniform T2 right | RM | force_tarsus_T2_right | load | 2 | `LOAD_OR_CONTACT` | No | `NOT_JOINT_STATE` |
| tactile T3 right | RH | claw_T3_right | contact | 411 | `LOAD_OR_CONTACT` | No | `NOT_JOINT_STATE` |
| campaniform T3 right | RH | force_tarsus_T3_right | load | 2 | `LOAD_OR_CONTACT` | No | `NOT_JOINT_STATE` |

Candidate totals are **HIGH_PRIORITY 0, INVESTIGATE 0, BROAD_ONLY 11, and
NOT_JOINT_STATE 12**.  `BROAD_ONLY` includes the already-used joint-angle
families because they provide no currently-unused source population for an
additional coordinate.  Consequently, the local annotations provide **no
new femur, femur–tibia, tibia–tarsus, tarsus-angle, or trochanter joint-state
population worth a dedicated physical-coordinate correspondence audit**.
Contact/load could be studied separately, but not as a seventh joint actuator.

## Historical female FlyWire/FlyGym cross-check

`fly-brain-main/src/sim/senses.js` historically supplied four relevant modeled
inputs.  This is precedent only, not MaleCNS identity evidence.

| Historical interface | MaleCNS result | Status |
|---|---|---|
| tibia angle → chordotonal Gaussian population code | Six corresponding populations exist and M5A associates them with Tibia | `PRESENT_AND_USED` |
| coxa promotion/remotion angle → hair-plate Gaussian population code | Five corresponding populations exist and M5A uses them broadly; RF is absent | `PRESENT_AND_USED` overall; RF member `NOT_FOUND` |
| tarsal load → campaniform load-proportional drive | Six corresponding populations exist but are absent from the 42 position-interface associations | `PRESENT_BUT_UNUSED` |
| tarsal/leg contact → tactile afferents | Six corresponding populations exist but are absent from the 42 position-interface associations | `PRESENT_BUT_UNUSED` |

The historical Gaussian bounds, index-ordered preferred values, contact subset,
and load gain are modeled transduction, not source biological tuning, and are
not ported here.

## Reproduction

From PowerShell at the repository root on Windows:

```powershell
py -m malecns_backend.embodiment.m5c_leg_sensory_inventory_audit --json malecns_backend\embodiment\interface_output\m5c_leg_sensory_inventory.json
```

The command prints three progress stages, the concise unused-population table,
and the aggregate summary.  The complete inventory uses the locally committed
MaleCNS/bodymap artifact, so no graph download or decode is required.
