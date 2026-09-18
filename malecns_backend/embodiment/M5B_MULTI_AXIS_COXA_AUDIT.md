# M5B-2 — broad coxa proprioception / multi-axis interface audit

## Scope and answer

This is a deterministic, read-only interface-model audit. It does not implement
an encoder, drive neurons, initialize or step physics, alter actuator eligibility,
or modify M4A, M5A, or M5B-1. Its conclusion is: **biological association
supported; transduction geometry unresolved**. A scientifically explicit
multi-axis encoder is therefore **not yet defensible from the local evidence**.

## A. Source evidence

The five populations and exact body IDs are:

| Population | IDs | kind / joint | class | type |
|---|---|---|---|---|
| hair plate T1 left | 821165 | `joint_angle` / `coxa_T1_left` | `mechanosensory_proprioceptive` | `SNpp45` |
| hair plate T2 left | 804460, 806080, 806226, 806918, 809024, 811747, 812090, 815449, 821047, 827735, 828976, 829377, 842203, 857165, 909393, 1050496206, 1083604933, 1387178136 | `joint_angle` / `coxa_T2_left` | `mechanosensory_proprioceptive` | `SNpp45`, `SNpp52` |
| hair plate T3 left | 804317, 808380, 812908, 819326, 820056, 821064, 829860, 836247, 856036, 908831, 1074160161, 1177500143 | `joint_angle` / `coxa_T3_left` | `mechanosensory_proprioceptive` | `SNpp45`, `SNpp52` |
| hair plate T2 right | 804352, 806962, 807933, 808641, 810052, 811145, 812847, 814188, 817320, 818516, 820418, 828689, 860479, 875125, 1471062202 | `joint_angle` / `coxa_T2_right` | `mechanosensory_proprioceptive` | `SNpp45`, `SNpp52` |
| hair plate T3 right | 806572, 809505, 810973, 813983, 814980, 816134, 818438, 824273, 830804, 833354, 908258, 908739, 1055052133, 1071635070 | `joint_angle` / `coxa_T3_right` | `mechanosensory_proprioceptive` | `SNpp45`, `SNpp52` |

The source is `malecns_backend/interface_map.json`; mapping provenance is
`ANNOTATION_DERIVED`. Additional retained fields (including category,
superclass, neurotransmitter, instances, sides, source consumers, and complete
bodymap metadata) are emitted in the JSON artifact.

**Explicit source evidence:** these are mechanosensory proprioceptive hair-plate
populations annotated as sensing joint angle at a named coxa segment/side.

**Not specified:** no `dir` or `axis` value, tuning curve, response direction,
range, velocity sensitivity, strain/contact dependence, reference pose, or
mapping from three FlyGym coordinates appears in the local metadata. Describing
a multi-coordinate function is a **modeling possibility**, not a biological
fact. In particular, “broad” does not justify an average.

## B. Physical DOF relationship

| Leg | `Coxa` | `Coxa_roll` | `Coxa_yaw` |
|---|---:|---:|---:|
| LF | 0 | 1 | 2 |
| LM | 7 | 8 | 9 |
| LH | 14 | 15 | 16 |
| RM | 28 | 29 | 30 |
| RH | 35 | 36 | 37 |

The locally available NeuroMechFly MJCF maps these to `coxa`, `coxa_abduct`, and
`coxa_twist`. They are three separately named hinge coordinates declared on the
same coxa body, rather than three nested body segments. That coxa body is below
the thorax and owns the femur child. In its local body frame, `coxa` uses axis
`1 0 0`, abduction uses the omitted/default MuJoCo joint axis `0 0 1`, and twist
uses `0 1 0`. Segment-specific ranges are recorded in the generated JSON. Thus
the model demonstrates a co-located compound rotational articulation. It does
**not** demonstrate what any biological neuron senses.

## C. Representation options

* **A — duplicated scalar:** high duplicate-drive and axis-invention risk. It
  assumes each neuron independently responds to all three coordinates and is
  not supported.
* **B — combined joint state:** avoids repeated writes, but requires an
  unsourced scalar function and normalization. Broad association alone does
  not support implementation.
* **C — vector/subpopulation:** a vector can avoid premature reduction, but the
  present interface would need extension. Assigning components/directions to
  neurons would invent tuning. It is not supported for implementation.
* **D — unspecified/do not model:** preserves the supported association and the
  unresolved geometry without new biological assumptions. This is the only
  option presently supported, and it intentionally unlocks no actuator.

The JSON records biological assumptions, engineering assumptions, both risks,
interface compatibility, and implementation support for every model.

## D. Historical female FlyWire/FlyGym precedent

The old `fly-brain-main/src/sim/senses.js` read tibia angle, only the single
`coxa_<T#_side>` coordinate, and tarsal load. Each broad hair-plate population
received only that coxa scalar: it did not receive multiple coxa signals and
did not separate all coxa axes. It applied a Gaussian population code with
engineered bounds `-0.3` to `1.7` and neuron-index preferred values. The broad
annotation supports a coxa association, but does not justify selecting that
axis, those bounds, or neuron-wise tuning. This is history, not a MaleCNS model
to copy.

## E. Classification and implementability

All five populations are **`BROAD_JOINT_SUPPORTED`**. None is
`MULTI_AXIS_SUPPORTED`, `AXIS_SPECIFIC_SUPPORTED`, or `INSUFFICIENT`.

A future explicit encoder would have to label as engineering choices its
coordinate normalization and reference pose; position versus velocity/strain
dependence; scalar function or vector representation; sign, gain, range,
saturation, and temporal dynamics; and any neuron allocation/tuning. New source
evidence would be required to call those choices biological.

## Reproduce

From the repository root on Windows:

```powershell
py -m malecns_backend.embodiment.m5b_multi_axis_coxa_audit --check --json malecns_backend\embodiment\interface_output\m5b_multi_axis_coxa_audit.json
```
