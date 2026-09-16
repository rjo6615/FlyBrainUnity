# Milestone 3A — MaleCNS sensory/motor interface audit

## Scope and result

This is a source-and-artifact audit, **not an embodiment implementation**. No
MaleCNS dynamics, graph, weights, delays, signs, cache, Unity bridge, or
`fly-brain-interactive` file was changed. The authoritative per-population
inventory is [`interface_map.json`](interface_map.json); it contains every
dense index and resolved 64-bit body ID, annotations, body-map metadata,
source consumers, candidate mappings, confidence, and provenance. This report
keeps the ID lists out of human-facing output.

The most important conclusion is that `fly-brain-main` is a hybrid reference
application. It stimulates genuine annotated sensory neurons and propagates
through the MaleCNS connectome/LIF model, but all physical-to-rate transfer
functions are modeled. Its default locomotor path reads annotated descending
neurons and then uses an engineered gait generator. Its optional `connectome`
mode reads mapped VNC motor-neuron rates, but the muscle-to-joint map remains a
manually authored actuator approximation. Flight, jump choreography, righting,
grooming kinematics, courtship song, and endogenous action selection contain
substantial engineered control. They must not be described as emergent
connectome behavior.

## 1–3. Inventory and bodymap

### Complete category summary

| Category | Addressable populations | Member entries | Distinct addressed neurons | Meaning |
|---|---:|---:|---:|---|
| `muscles` | 170 | 439 | 383 | Motor-neuron groups mapped to named MuJoCo actuators; overlap occurs where one anatomical group is assigned to multiple actuators. |
| `wing` | 7 | 56 | 56 | Power, bilateral amplitude-up/down, and unfold motor groups. |
| `jump` | 1 | 2 | 2 | TTMn. |
| `feeding` | 1 | 26 | 26 | Selected feeding/pump motor types. |
| `sensors` | 151 | 8,154 | 7,745 | Physical sensory channels; bilateral ORN rows can overlap because unknown-side ORNs are included for both antennae. |
| `unmappedMotor` | 0 | 422 declared | 0 | 285 aggregate `(subclass,type,side,n)` inventory rows. The JSON has **no indices or body IDs** for these; they are not addressable mappings. |
| `eyes` | 2 | 4,107 | 4,107 | One retinotopic photoreceptor array per eye. |

Thus the bodymap has 332 addressable populations and 12,317 distinct referenced
neurons, exactly matching the earlier audit. Including the intentionally
non-addressable `unmappedMotor` inventory gives 617 records in the audit JSON.

Every addressable population record in JSON supplies category/name/count,
dense indices, resolved body IDs, unique type/instance/class/superclass/side/NT
annotations, all extra bodymap fields (`actuator`, `dir`, `kind`, `site`,
`joint`, `sensor`, `glomerulus`, `antenna`, `az`, `el`, photoreceptor `kind`),
provenance, and consumers. The top-level source-occurrence inventory records
every textual `bodymap` use found throughout `fly-brain-main` source, scripts,
and documentation.

MaleCNS-wide annotation counts include **1,314 `descending_neuron`** and
**1,846 `ascending_neuron`** superclass neurons. Related direction-bearing
superclasses also exist (`sensory_ascending` 537, `sensory_descending` 12,
`efferent_ascending` 8, `efferent_descending` 4); these should not silently be
folded into the strict DN/AN totals.

## 4, 12. Exact sensory stimulation path

Normal `FlyAgent` operation calls `Senses.update`, optionally
`CompoundEye.update`, clears the previous externally driven indices, and calls
`Brain.setDriveOne(index, rateHz)` for current channels. The brain converts the
requested rate to stochastic external spike drive. Sensory code does **not**
directly change voltage, thresholds, or synaptic weights. The agent executes
two 0.5-ms neural steps per 1-ms body update. Multiple same-step causes are
combined by taking the maximum requested rate for each neuron, not summing.

The separate endogenous module calls `brain.pulse(indices, conductance)` and,
for forward-DN braking, `brain.addG(i, 0, negative_conductance)`. This is modeled
central drive, not sensory transduction and not connectome-derived input.

### Sensory channels and modeled encoders

| Modality / kind | Populations | Entries (distinct) | Reference encoding |
|---|---:|---:|---|
| Olfaction `odor` | 106 | 3,044 (2,635) | Bilateral antenna position; Gaussian static plumes/wind offset and nearby-fly plume; authored odor→glomerulus sensitivities; Hill response; 6 Hz spontaneous + up to 150 Hz evoked; divisive total-drive normalization. |
| Vision `eyes` | 2 | 4,107 | One MuJoCo ray per mapped photoreceptor; log luminance, 300-ms adaptation, `clamp(40 + 90 contrast, 0, 250)` Hz. |
| Tactile leg contact | 6 | 1,877 | Fixed 25% tarsal subset; contact onset/offset burst decays with 15-ms time constant; 180 Hz peak; authored 85% reafference suppression while stepping. Other 75% is obstacle bristle input at 150 Hz. |
| Wing/notum contact | 2 | 655 | Boolean body-side contact → 150 Hz. |
| Proprioceptive joint angle | 11 | 452 | Chordotonal tibia and hair-plate coxa values encoded as ordered Gaussian population codes, 120-Hz peak, fixed ranges/width. The missing right T1 hair-plate channel reflects the artifact, not parser loss. |
| Campaniform load | 6 | 12 | Positive tarsal load → `min(200, 3000*load)` Hz. |
| Haltere/gyro | 2 | 396 | Body angular-speed magnitude above 2 → `min(200, 10*w)` Hz, identically to both sides. |
| JO wind/gravity | 2 | 475 | Relative air speed above 0.5 → `min(150,20*air)` Hz; front contact can force 120 Hz. |
| JO auditory | 2 | 114 | Populations exist, but `Senses.update` supplies no sound/vibration drive. |
| Tarsal taste | 6 | 768 | Contact with authored food/bitter/other-fly regions selects annotated GRN type subsets; Hill-coded sugar/bitter to 150 Hz; pheromone 120 Hz. |
| Labellar taste | 2 | 223 | Mouth height/contact gates sugar/water/bitter annotated subsets, Hill-coded to 180/120/180 Hz. |
| Pharyngeal taste | 2 | 48 | Mapped in bodymap but not driven by `Senses.update`. |
| Thermosensation | 2 | 25 | Authored hot-patch spatial field at antenna; threshold 0.05; `200*heat` Hz. |
| Hygrosensation | 2 | 65 | Populations exist; no reference drive. |

All spatial geometry, plume functions, thresholds, rate constants, fixed subset
selection, and taste/odor dictionaries are **modeled transduction**. Neuron
identities and downstream connections are annotation/connectome-derived.
Stochasticity occurs when a rate becomes external spikes in the LIF brain; the
transduction formulas themselves are deterministic. Channels are generally
bilateral, but haltere and relative-air magnitude lose directional detail.

## 5, 11. Exact output decoding

`Motor.readBrain` differences cumulative **spike counts**, converts increments
to instantaneous Hz, and applies a per-neuron first-order low-pass with default
40-ms time constant. It never reads voltage, conductance, spike maxima, or raw
weights as output.

* **Mapped motor populations:** population mean filtered rate is transformed
  by `1-exp(-rate*ln(2)/17)`. Antenna/proboscis actuators always use this;
  `connectome` mode also mixes signed muscle activations into each leg actuator
  and clamps to MuJoCo control ranges. This is a modeled decoder over a manual
  anatomical actuator map.
* **Default descending mode:** literature-selected DN types receive manual
  weights. Weighted mean forward/backward/groom/left/right rates are decoded.
  Forward has a 4-Hz threshold and exponential scale 12; backward is capped at
  0.35; turning is a left/right difference, low-pass (150 ms walking, 50 ms
  flight), slow baseline-adapted over 4 s, divided by 25, and clamped ±0.6.
  A hand-tuned tripod gait then produces joint positions and adhesion.
* **Grooming:** mean DNg07/08/12 rate divided by 40 must exceed 0.5 and 1.5×
  forward. The resulting 7-Hz front-leg sweep is explicitly choreographed.
* **Jump:** at least four GF spikes in 50 ms, or looming-takeoff DN activity
  above 70 Hz and 3× its 3-s baseline, triggers a timed, hand-authored leg
  program. A software-added GF→TTMn pulse represents an electrical synapse
  absent from the chemical graph.
* **Feeding:** selected motor-neuron population mean uses the same half-17-Hz
  saturation. Ingestion additionally requires geometric food contact and an
  extended proboscis.
* **Wing category:** despite being compiled, `bodymap.wing` is not read by the
  normal flight controller. Flight uses engineered wing cycles and forces.

## 6–8, 13–14. Provenance and engineered behavior

### Provenance boundary

1. MaleCNS identities, annotations, chemical edges, and synapse counts:
   **biological/connectome-derived**.
2. Selecting annotated neurons into sensory and motor groups:
   **annotation-derived**, with compiler rules.
3. Bodymap actuator/direction assignment, visual-axis fitting/remapping, all
   environment-to-Hz equations: **manual/model assumptions**.
4. Propagation after injected spikes: **biological connectivity + modeled LIF**.
5. Spike-rate filtering and neural-to-actuator conversion:
   **modeled motor decoder**.
6. Gait, jump pose sequence, righting, flight aerodynamics/wing cycle, explicit
   behavior selection: **engineered control**.

### Behavioral classification

| Behavior | Class | Evidence-based interpretation |
|---|---|---|
| Forward/back/turn | **B** | Real DN rates contribute, but thresholds, weighted roles, adaptation, and the tripod CPG select/shape body motion. |
| Direct leg actuation in optional `connectome` mode | **B** | Real VNC MN rates drive controls, but muscle grouping, signs, saturating decoder, mixing, and MuJoCo position actuators are authored. |
| Grooming | **B** | DN rate gates a hand-coded 7-Hz front-leg trajectory. |
| Feeding/ingestion | **B** | MN rates affect proboscis/pump and intake, while geometric gating and intrinsic feeding bouts are engineered. |
| GF/loom escape jump | **B** | Neural evidence triggers an engineered timed posture/push program with touch/upright/startup gates. |
| Voluntary takeoff | **C** | Intrinsic probabilistic state logic directly supplies a voluntary flag/drive. |
| Flight | **C** | `Flight` supplies phases, wing kinematics, forces, collision avoidance, and landing; DN turn affects steering only. |
| Righting | **C** | Orientation threshold/timer directly activates an authored wing/leg routine. |
| Courtship chase/song | **B/C** | Neural pIP10/DNp13 score helps gate courtship; target bearing, distance controller, and visible 30-Hz wing flutter are engineered. |
| Rest/exploration/search/approach/avoidance | **C** | `Intrinsic` is an explicit stochastic state machine with bout timers, geometry/taste/heat conditions, and DN conductance biases. |

### Endogenous drives

`Intrinsic` is enabled by default when `FlyAgent` is constructed normally. It
targets identified DNs/MNs but explicitly stands in for missing intrinsic
dynamics and neuromodulatory/action-selection circuitry.

| Drive | Target | Condition/dynamics | Classification |
|---|---|---|---|
| Walk | DNg100/DNg97 | Lognormal walk/stop bouts; OU speed noise (800 ms); pulse 12 with 25% jitter and hunger/arousal scaling | Engineered behavior control with literature motivation |
| Turn/saccade | DNa02/DNa01 by side | Bernoulli timing 0.7/s walking, 0.3/s standing; 120–260 ms; pulse 10 | Literature-derived modeled drive / engineered control |
| Groom | DNg07/08/12 | 20% pause choice; lognormal 2.5-s median; pulse 10 | Engineered behavior control |
| Back/avoid | MDN | bilateral antenna/rearing contact; 350 ms; pulse 14, then turn | Engineered reflex control |
| Brake | all forward-role DNs | stop/groom 6, feed 16; negative excitatory conductance | Engineered state gating |
| Feeding | MN9 plus bodymap feeding MNs | sugar, mouth geometry, hunger and lognormal bout; pulse 10 scaled by hunger | Engineered behavior control |
| Takeoff | DNp02/DNp04 | probabilistic bout end or wall avoidance; 80-ms window; pulse 20 | Engineered behavior control |
| Flight avoidance | side-specific turn DNs | geometric clearance lookahead; pulse 18; otherwise stochastic flight saccades | Engineered behavior control |
| Courtship | forward/turn drive plus external `court` state | pIP10/DNp13 gate, but bearing/distance sets pulses (9/12) and song side | Hybrid neural contribution + engineered control |

Neuromodulation is implemented separately and used as state context; it is a
model, not present as endogenous biophysics in the static connectome. There is
also a 6-Hz ORN spontaneous baseline, which is a modeled sensory baseline, not
an endogenous behavioral state.

## 9. Detailed anatomical output coverage

The 170 muscle rows distinguish T1/T2/T3, left/right, and many antagonistic
functions: trochanter/femur flexion-extension, tibia flexion-extension,
coxa promotion/remotion/abduction/adduction/rotation, femur reduction, tarsal
levation/depression, and long-tendon/claw functions. Individual annotated MN
types are grouped by anatomical type and side; some groups contain multiple
neurons and may feed two actuator rows. Proboscis groups distinguish rostrum,
haustellum, labellum, and retraction. Antennal MN groups are present. Wing
power (DLMn/DVMn) and bilateral steering/folding groups are present separately.
The bodymap does not encode physical muscle moment arms, force constants, or a
one-to-one NeuroMechFly muscle model.

### Candidate target table (not an implementation)

| MaleCNS group | Anatomical target | Reference output | Possible NeuroMechFly target | Confidence |
|---|---|---|---|---|
| T1/T2/T3 leg MN groups | Named leg muscle function, bilateral | Filtered mean spike rate → saturation → signed actuator range | Corresponding coxa/femur/tibia/tarsus joint position actuator | Strong candidate |
| `ltm*` | Long tendon / tarsal-claw function | tarsus2 negative plus adhesion positive | Distal tarsus plus adhesion | Weak candidate; biomechanics missing |
| Antenna MN groups | Bilateral antenna | Direct antenna actuator | None in current old FlyGym bridge | No current match |
| Proboscis/labellum MN groups | Feeding apparatus | Direct rostrum/haustellum/labrum controls | None in current old bridge | No current match |
| `jump` TTMn | Tergotrochanteral jump system | Trigger input plus scripted all-leg jump | No direct TTM muscle actuator; could only inform a future whole-body model | Weak candidate |
| Wing power/steering/folding | Flight apparatus | Not read from bodymap by normal flight | No wing actuator in old walking interface | No current match |
| `feeding` pump set | Pharyngeal/feeding output | Saturated scalar for intake | No direct actuator | No current match |

The full per-row anatomical target, actuator, direction, IDs, and annotations
are in JSON and are preferable to a lossy 170-row Markdown duplication.

## 10. Descending and ascending neurons

MaleCNS provides the desired anatomical substrate: brain ↔ descending/ascending
neurons ↔ VNC circuitry ↔ motor neurons. The strict superclass inventory is
1,314 DNs and 1,846 ANs. Known behavior-associated types selected by the
reference include DNg100, DNg97, DNp09, DNa05/07/01/02, DNp26, MDN,
DNg07/08/12, DNp01 (GF), DNp02/04, pIP10, and DNp13.

However, the default application does **not** wait for downstream VNC MN output
to move the legs: it decodes those DNs into an engineered CPG. Only optional
`mode='connectome'` decodes mapped leg MNs downstream of the VNC, and even that
ends in a modeled muscle decoder. ANs are present in the network but have no
direct body decoder in the reference application.

## 15–18. Existing FlyGym compatibility

The old `fly-brain-interactive` embodiment exposes/uses compound-eye images,
contact-force arrays, end-effector positions, fly position, body-forward
orientation, odor/taste/vibration source geometry, and internally generated
joint phase/angles. Its final motor API sends 42 joint position values (six
legs × seven DOFs) plus six adhesion commands. `BrainBodyBridge` produces
left/right locomotor drives, explicitly selects walking/grooming/escape/feeding/
flight modes with hysteresis, and a preprogrammed stepping controller produces
the joint action. It does not expose a scientifically calibrated muscle API.

The complete compatibility matrix is machine-readable in JSON. In summary:

* **DIRECT:** none. Shared names or physical quantities are not enough to call
  a mapping direct; every candidate requires a transfer function, coordinate
  mapping, anatomical resampling, or actuator model.
* **STRONG CANDIDATES:** chordotonal↔joint angle; hair plate↔coxa angle;
  campaniform↔contact/load; tactile afferents↔contact; photoreceptors↔compound
  eye; ORNs↔odor field; GRNs↔taste/contact; haltere↔angular velocity; annotated
  leg MN groups↔corresponding leg joints.
* **WEAK CANDIDATES:** JO wind/gravity↔relative motion/contact; DN readout↔old
  left/right gait drive; distal long-tendon/claw mapping; TTMn↔whole-body jump.
* **NO CURRENT MATCH:** JO auditory physical sensor, humidity, antenna/proboscis,
  pharyngeal output, and wing muscle actuation. Conversely, old-backend body
  velocity/orientation and generic ground contacts have no single uniquely
  justified MaleCNS target; they must be decomposed into specific receptor
  models rather than injected wholesale.

The old vision, olfactory, gustatory, and somatosensory modules provide reusable
**environment sampling and coordinate-handling concepts**, but their FlyWire
population IDs, layer injection, hard-coded attractive/aversive valence,
bridge-level escape/turn bias, and arbitrary behavior decoder must be replaced
or independently revalidated for MaleCNS. In `fly-brain-main`, odor identity is
an authored glomerular pattern and intensity is a plume/Hill model; valence can
propagate downstream, but courtship and avoidance also add external logic.
Sugar/bitter identities are selected from annotated GRN types, while feeding
state and intake remain externally gated. No claim of emergent valence is
warranted.

## 19–21. Proposed interface architecture (not implemented)

Keep the validated runtime ignorant of embodiment:

```text
Environment / FlyGym observations
  -> SensoryFrame (typed values, units, timestamp, coordinate frame, validity)
  -> MaleCNSInputEncoder (per-modality transducers; index/rate events + provenance)
  -> unchanged MaleCNSBrain
  -> MaleCNSOutputDecoder (windowed spike-count deltas; explicit filters/calibration)
  -> MotorCommand (target type, units, confidence, saturation, provenance)
  -> FlyGym actuator adapter
  -> body/environment feedback
```

`SensoryFrame` should preserve raw joint position/velocity, per-contact force
and geometry, body pose/linear/angular velocity, eye samples with directions,
odor/taste fields, wind, sound/vibration, temperature and humidity. Missing
channels must be marked absent, never synthesized silently.

`MaleCNSInputEncoder` should own only modeled transduction. Each output should
record source observation, target body IDs/dense indices, transfer-function
version, parameters/units, biological annotation evidence, spatial/side map,
random seed/process, and confidence. It should output rates or explicit spike
events through the runtime's existing external-drive API.

`MaleCNSOutputDecoder` should consume monotonically increasing spike counts and
make rate window/filter, population aggregation, gain, threshold, clamp and
fallback behavior explicit. Prefer downstream mapped VNC MNs for body control;
use DN decoding only as a clearly labeled engineered fallback/experiment.
`MotorCommand` should distinguish muscle activation, joint torque/position,
adhesion, feeding, and wing commands rather than collapsing them to a behavior
label.

Recommended provenance carried on every edge:

```text
environment quantity --MODELED_TRANSDUCTION--> annotated receptor activity
 --CONNECTOME_DERIVED + MODELED_LIF--> downstream activity
 --MODELED_MOTOR_DECODER--> biomechanical command
 --ENGINEERED_CONTROL (only if unavoidable and explicitly enabled)--> action
```

## 22. Validation

Run:

```bash
python -m malecns_backend.interface_audit
```

It independently rebuilds the report from `neurons.flyn`, `meta.json`, and
`bodymap.json`, requires byte-equivalent JSON content, resolves every mapped
index, checks per-population duplicate indices, body ID cardinality, available
side metadata, all category/population counts, every recorded source path and
line, and provenance/confidence on every compatibility candidate. Engineered
control cannot simultaneously be labeled connectome-derived. Success ends in
`MALECNS INTERFACE AUDIT PASSED`.

## 23. Plan-changing limitations

1. Do not use the default DN→gait path as evidence of VNC-generated walking.
2. Do not reuse old-backend attractive/aversive or looming escape shortcuts;
   encode the physical stimulus and let MaleCNS propagate it, while separately
   measuring whether neural output is sufficient.
3. Do not call any mapping “direct” yet. The strongest candidates still need
   coordinate, unit, tuning, latency, and biomechanics calibration.
4. The reference app provides no active auditory, humidity, or pharyngeal
   sensory transduction despite mapped populations.
5. The detailed wing bodymap is unused by reference flight; flight cannot be
   validated from that application's animation/aerodynamics.
6. `unmappedMotor` cannot be recovered from bodymap alone. Rebuilding exact IDs
   requires the raw annotation table/compiler inputs.
7. Photoreceptor field directions are useful but inferred and remapped, not
   measured ommatidial optical axes; looming should enter retinotopically and
   must not directly choose escape.

These limitations argue for a sensory-first closed-loop validation, followed
by calibrated VNC motor-neuron decoding, before any behavioral milestone.
