# M7-A1 compact telemetry repair audit (science not run)

## Attempt provenance

M7 SCIENTIFIC ATTEMPT #1  
STATUS: ABORTED_IMPLEMENTATION_FAILURE  
SCIENTIFIC RESULT: NONE  
COMPLETED CONDITIONS: 0  
CAUSE: COMPACT TELEMETRY SERIALIZATION SHAPE FAILURE

The partial trajectory is not a scientific result and was not recovered,
reduced, classified, or interpreted. The independently created
`ABORTED_IMPLEMENTATION_*.json` remains the provenance record. At repair time,
the repository's canonical output directory contained no `m7_raw.npz`,
`m7_summary.json`, or `m7_manifest.json`; no partial or temporary canonical
file required quarantine.

## Exact root-cause audit

The failure occurred only after collection, when the old list-backed fields
were converted with `np.asarray`. The following inventory describes attempt
#1's 50,001 sampled physics states (initial state plus one state after each of
50,000 physics transitions) and 10,000 neural-update samples. “First mismatch”
means the first location at which the old value departed from its intended
fixed per-sample schema.

| key | samples | intended sample shape | actual unique sample shapes | dtype(s) | scalar | `None` | ragged/nested | first mismatch | meaning |
|---|---:|---|---|---|---|---|---|---|---|
| physics `time_ms` | 50,001 | `()` | `()` | float64 | yes | no | no | none | simulation time |
| physics `qpos` | 50,001 | `(97,)` | `(97,)` | float64 | no | no | no | none | MuJoCo generalized position |
| physics `qvel` | 50,001 | `(93,)` | `(93,)` | float64 | no | no | no | none | MuJoCo generalized velocity |
| physics `joint_position` | 50,001 | `(42,)` | `(42,)` | float64 | no | no | no | none | measured actuator coordinates |
| physics `action` | 50,001 | `(42,)` | `(42,)` | float64 | no | no | no | none | commanded actuator coordinates |
| physics `ctrl` | 50,001 | `(42,)` | `(42,)` | float64 | no | no | no | none | MuJoCo actuator control |
| physics `body_position` | 50,001 | `(3,)` | `(3,)` | float64 | no | no | no | none | body Cartesian position |
| physics `body_orientation` | 50,001 | `(4,)` | `(4,)` | float64 | no | no | no | none | body quaternion |
| physics `contact_forces` | 50,001 | `(30, 3)` | `(30, 3)` | float64 | no | no | fixed nesting | none | FlyGym contact-force observation |
| physics `finite` | 50,001 | `()` | `()` | bool | yes | no | no | none | finite-state flag |
| neural `time_ms` | 10,000 | `()` | `()` | float64 | yes | no | no | none | neural-update simulation time |
| neural `sensory_encoded` | 10,000 | `(6,)` numeric channel summary | outer `(6,)`; inner `(23,)`, `(80,)`, `(93,)`, `(13,)`, `(83,)`, `(100,)` | float64 leaves in Python tuples | no | no | **yes** | sample 0, channel 1 differs from channel 0 | six tibial interfaces, ordered LF/LM/LH/RF/RM/RH |
| neural `delivered_drive_count` | 10,000 | `()` | `()` | int64 | yes | no | no | none | delivered external-drive count |
| neural `aggregate_spikes` | 10,000 | `()` | `()` | int64 | yes | no | no | none | aggregate CNS spike count |
| neural `observer_outputs` | 10,000 | `(11,)` | `(11,)` | float64 | no | no | fixed nesting | none | admitted-channel observer peaks |
| neural `decoder_outputs` | 10,000 | `(11,)` | `(11,)` | float64 | no | no | fixed nesting | none | admitted-channel raw decoder outputs |
| neural `admitted_contributions` | 10,000 | `(11,)` | `(11,)` | float64 | no | no | fixed nesting | none | gated admitted contributions |

Thus the exact and only offending key was `neural_sensory_encoded`. Every
sample was a six-element list, but its six elements were rate vectors for
sensory populations of unequal, anatomically fixed neuron counts. NumPy first
recognized `(10000, 6)` and then rejected the heterogeneous inner dimension.
No field changed shape over simulation time. This was representation-only:
the six runtime vectors retained their same fixed per-interface shapes; the
collector incorrectly represented six semantic channels as if their neuron
axes could be stacked.

## Repair and frozen semantics

Collection now records the peak encoded rate for each of the six interfaces as
one float64 `(6,)` sample. This is exactly the preregistered/reducer quantity:
the former intended reduction was the maximum over time and the inaccessible
common neuron axis, and `max(time, max(neurons, rates))` equals
`max(time, per-interface peak)`. No scientific value is averaged, padded,
truncated, or mixed with another interface, and the sampling cadence is
unchanged.

All fields are preallocated with explicit numeric dtypes and runtime-derived,
initialization-frozen physical shapes. Assignment checks every sample before
storage. A violation immediately raises
`ABORTED_IMPLEMENTATION_TELEMETRY_SCHEMA_FAILURE` with field, expected shape,
observed shape, sample index, and simulation time. V3 preflight allocates only
minimal schema-sized arrays, round-trips the complete payload through compressed
NPZ with `allow_pickle=False`, and executes zero `sim.step()` and zero
`brain.step()` calls.

Neither M7 nor M6C was executed during this repair. The protocol,
preregistration, parameters, interfaces, runtime dynamics, intervention,
condition order, RNG behavior, and M6C default path are unchanged.

Windows V3 preflight command (safe after deploying the repair):

```text
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.m7_spontaneous_locomotion --preflight-windows
```

Future scientific command — **DO NOT RUN YET**:

```text
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.m7_spontaneous_locomotion --run-windows
```
