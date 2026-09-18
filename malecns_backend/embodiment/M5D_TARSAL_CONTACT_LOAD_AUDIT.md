# M5D-1 — tarsal contact + load physical-interface audit

## Scope and result

This is a **read-only availability audit**. It adds no encoder, neural drive,
mapping, actuator output, controller, physics parameter, or gait behavior. The
non-live artifact does not claim runtime values. FlyGym and MuJoCo were not
installed in the audit environment, so sensor IDs/types/object IDs and actual
initial values remain explicitly `NOT_ESTABLISHED`; `--live` constructs the same
`Fly(enable_adhesion=False, control="position")`, resets once, inspects it, and
never calls `step`.

The result is:

* six contact inputs are `MODELED_TRANSDUCTION_REQUIRED` and
  `PHYSICAL_SIGNAL_READY`;
* six load inputs are `PROXY_ONLY` and `PHYSICAL_PROXY_READY` because external
  contact force is not a direct measurement of campaniform cuticular strain;
* contact state and load magnitude are conceptually separable but are **not
  independent measurements** in the locally evidenced FlyGym interface: both
  are derived from `observation["contact_forces"]`.

## A. Exact biological populations

The complete exact `body_ids` arrays, classes, types, provenance, raw metadata,
and empty direction/tuning/range fields are retained in
`interface_output/m5d_tarsal_contact_load_audit.json`. No tuning was inferred
from these counts or from body-ID ordering.

| Leg | Contact population | IDs | source annotation | Load population | IDs | source annotation |
|---|---|---:|---|---|---:|---|
| LF | `tactile T1 left` | 151 | `kind=contact`, `site=claw_T1_left` | `campaniform T1 left` | 2 | `kind=load`, `sensor=force_tarsus_T1_left` |
| LM | `tactile T2 left` | 378 | `kind=contact`, `site=claw_T2_left` | `campaniform T2 left` | 2 | `kind=load`, `sensor=force_tarsus_T2_left` |
| LH | `tactile T3 left` | 394 | `kind=contact`, `site=claw_T3_left` | `campaniform T3 left` | 2 | `kind=load`, `sensor=force_tarsus_T3_left` |
| RF | `tactile T1 right` | 115 | `kind=contact`, `site=claw_T1_right` | `campaniform T1 right` | 2 | `kind=load`, `sensor=force_tarsus_T1_right` |
| RM | `tactile T2 right` | 428 | `kind=contact`, `site=claw_T2_right` | `campaniform T2 right` | 2 | `kind=load`, `sensor=force_tarsus_T2_right` |
| RH | `tactile T3 right` | 411 | `kind=contact`, `site=claw_T3_right` | `campaniform T3 right` | 2 | `kind=load`, `sensor=force_tarsus_T3_right` |

All tactile records have class `mechanosensory_tactile`; all campaniform records
have class `mechanosensory_proprioceptive`. The sole provenance is the relevant
population record and its `bodymap_metadata` in `interface_map.json`. No record
contains a biological direction, magnitude tuning, threshold, or range.

## B–C. Physical inventory and live boundary

The pinned local target is FlyGym 1.2.1. The runnable interactive configuration
explicitly requests, in `LF, LM, LH, RF, RM, RH` order, `Tibia`, `Tarsus1`,
`Tarsus2`, `Tarsus3`, `Tarsus4`, and `Tarsus5` contact placements. Existing
local consumers document `contact_forces` as shape `(36, 3)`: six 3-D segment
force vectors per leg. `end_effectors` is `(6, 3)` position and does not itself
measure contact or load. Adhesion is a six-element **action**, not measured
contact/load state (and is disabled by the current backend configuration).

The static audit does not invent force units, vector frame, sensor IDs, sensor
types, associated MuJoCo objects, contact pairs, or dynamic ranges. A value is
sampled per returned observation (reset or physics step); M5D takes only the
reset observation in live mode. MuJoCo geom-contact or `cfrc_ext` data may be
available underneath FlyGym, but this repository supplies no verified,
per-claw public mapping for them.

## D–G. Per-leg correspondence and implementability

| Leg | Contact observable | Contact class / readiness | Load observable | Load class / readiness |
|---|---|---|---|---|
| LF | rows 0–5, distal force nonzero | `MODELED_TRANSDUCTION_REQUIRED` / `PHYSICAL_SIGNAL_READY` | force vector/norm rows 0–5 | `PROXY_ONLY` / `PHYSICAL_PROXY_READY` |
| LM | rows 6–11, distal force nonzero | same | force vector/norm rows 6–11 | same |
| LH | rows 12–17, distal force nonzero | same | force vector/norm rows 12–17 | same |
| RF | rows 18–23, distal force nonzero | same | force vector/norm rows 18–23 | same |
| RM | rows 24–29, distal force nonzero | same | force vector/norm rows 24–29 | same |
| RH | rows 30–35, distal force nonzero | same | force vector/norm rows 30–35 | same |

Contact requires distal-row selection and a stated engineering threshold. Load
requires distal selection plus an aggregation and possibly projection onto a
surface normal. Raw direction is three-component; a norm discards direction and
sign. No explicit physical magnitude range is locally available. The physical
layout is symmetric across all six legs; the biological population sizes are
not. A force-derived contact flag and force magnitude can be used separately,
but they are statistically and physically coupled because they share one raw
measurement.

Most importantly, neither availability result supplies a biological transfer
function. Contact force to tactile firing remains modeled transduction, and
external contact force to campaniform firing is only a strain proxy plus modeled
transduction—not a biologically exact encoder.

## F. Historical female implementation (comparison only)

The old browser implementation was a custom MuJoCo female implementation, not
the audited FlyGym body. For contact it read the scalar `touch_claw_<leg>`
sensor, converted `touch>0` to a binary transition, created onset/offset bursts,
decayed them with `exp(-dtMs/15)`, delivered only while burst `>0.05`, and used
`180 * burst * (1 - 0.85 * stepping)` Hz. It allocated every fourth tactile
body ID (order-based, about 25%) to tarsal contact and the rest to obstacle
bristles. There was no stochastic encoding.

For load it took `hypot(x,y,z)` of `force_tarsus_<leg>`, required `load>0`, and
assigned `min(200, 3000*load)` Hz uniformly to every campaniform body ID. There
was no normalization or stochastic encoding. The 15 ms, 0.05, 180 Hz, 0.85,
3000, and 200 Hz values and modulo-four allocation are engineered constants;
none comes from the MaleCNS biological annotations and none is ported by M5D.

## Commands

Non-live deterministic generation:

```bash
python -m malecns_backend.embodiment.m5d_tarsal_contact_load_audit --json malecns_backend/embodiment/interface_output/m5d_tarsal_contact_load_audit.json
```

Exact Windows live command (from the repository root):

```powershell
python -m malecns_backend.embodiment.m5d_tarsal_contact_load_audit --live --json malecns_backend\embodiment\interface_output\m5d_tarsal_contact_load_audit.json
```
