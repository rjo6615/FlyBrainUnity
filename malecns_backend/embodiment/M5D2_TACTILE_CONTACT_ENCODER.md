# M5D-2 — six-leg tactile contact encoder

## Scope and scientific status

This milestone implements **contact only**. It does not encode campaniform
load, add an actuator or gait controller, or make a tactile-driven behavioral
claim. The association between each population and claw/contact sensation is
annotation-backed. Force-to-contact-to-rate is a **modeled engineering**
transduction, not a biologically measured transfer function.

## Physical signal

The input remains the validated `(36, 3)` `contact_forces` array in LF, LM,
LH, RF, RM, RH order, with Tibia through Tarsus5 within each leg. All six raw
vectors are retained in every telemetry frame. Only offsets 5, 11, 17, 23, 29,
and 35 (`Tarsus5`) drive contact. M5D-1 found that the biological source says
`claw_T#_side`, while the configured FlyGym placements end at Tarsus5 and no
separate per-claw public observation was locally verified. Thus Tarsus5 is the
most distal and most defensible available physical proxy; proximal rows are
not pooled to increase detections. Magnitudes are Euclidean norms and units
remain **model force units**.

## Calibration and threshold

`--live` records the reset observation and a bounded passive hold of the
measured reset joint positions (default 0.05 s at the runtime's 0.0001 s
timestep). It adds no walking controller and reports count, min, max, mean,
median, 1/5/25/50/75/95/99 percentiles, exact-zero fraction, and nonzero
fraction per leg. The checked-in environment lacks FlyGym, so real calibration
is `NOT_RUN` here.

The default threshold is `1e-12` model force units and contact uses strict
`magnitude > threshold`. This numerical-epsilon value is a **provisional
MODELED_ENGINEERING_PARAMETER**, not a biological threshold. The Windows live
statistics must establish that zero and nonzero observations are cleanly
separated before accepting it; otherwise choose and document a threshold from
that empirical distribution.

## Transduction and spikes

An onset begins a 20 ms linear envelope at 120 Hz, decaying to zero and never
restarting during sustained contact. Release rearms the detector. Duration,
maximum rate, threshold, seed, and enable state are explicit configuration
fields marked modeled engineering choices. Every annotated neuron is eligible;
there is no every-Nth-neuron allocation.

`SeedSequence(seed).spawn(6)` creates one deterministic RNG per population.
Disabled operation performs no draws and neither construction nor encoding
accesses the historical tibia or MaleCNS RNG. Generated candidates enter a
brain only through `set_external_drive`; the encoder never writes membrane
state, connectivity, weights, or neural thresholds.

| Leg | annotation-backed population | size |
|---|---|---:|
| LF | tactile T1 left | 151 |
| LM | tactile T2 left | 378 |
| LH | tactile T3 left | 394 |
| RF | tactile T1 right | 115 |
| RM | tactile T2 right | 428 |
| RH | tactile T3 right | 411 |

## Validation status

The checked-in open-loop report passes zero, equality/subthreshold, first
crossing, sustained contact, bounded expiry, release, and second-onset cases.
Synthetic cases validate encoder mechanics, not biology. Real FlyGym
calibration is pending on the validated Windows installation. Consequently the
fresh-runtime matched-control propagation diagnostic is explicitly `NOT_RUN`;
it must follow acceptance of live calibration and must apply no tactile-derived
motor output. Propagation alone will not establish behavioral significance.

Run the bounded Windows calibration and regenerate the report with:

```powershell
python -m malecns_backend.embodiment.tactile_contact_audit --live --duration-s 0.05 --json malecns_backend/embodiment/interface_output/tactile_contact_audit.json
```
