# M5D-5A — Six-tibia proprioceptive activation validation

## Scope

This milestone validates only the modeled sensory path from six measured FlyGym
tibia angles into annotation-backed MaleCNS chordotonal populations. It does not
claim biological proprioception, walking, gait, coordination, CPG activity,
reflexes, or autonomous locomotion. Neural motor output is observed but is never
connected to the body.

## Locked protocol and architecture

The canonical run is a single 100 ms trial pair at seed 1, with 0.1 ms physics
and 0.5 ms neural timesteps. Both conditions use the same initial state,
constant initial joint command, contact environment, unchanged LM Tarsus5
tactile encoder, MaleCNS initialization, and random seeds. Both compute all six
proprioceptive candidate streams. `PROPRIO_DISABLED` withholds their indices at
the established `MaleCNSBrain.external_drive_withheld_indices` boundary;
`PROPRIO_ENABLED` admits them. This gate is the only intervention.

At each neural update, the existing `sensory.SensoryEncoder` receives the actual
measured tibia position. Its unchanged model uses angle range `[-1.35, 1.30]`
rad, normalized angle `(q-lo)/(hi-lo)`, preferred positions `(k+0.5)/n`, Gaussian
width `0.25`, maximum `120 Hz`, no baseline, and a `5 Hz` inclusive cutoff
(`rates <= 5` become zero). Event probability is `rate * 0.5/1000`. Independent
PCG64 streams are derived by `SeedSequence(1).spawn(6)` in LF, LM, LH, RF, RM,
RH order and recreated identically for both conditions.

| Leg | action index / physical source | population | neurons |
|---|---:|---|---:|
| LF | 5 | chordotonal T1 left | 23 |
| LM | 12 | chordotonal T2 left | 80 |
| LH | 19 | chordotonal T3 left | 93 |
| RF | 26 | chordotonal T1 right | 13 |
| RM | 33 | chordotonal T2 right | 83 |
| RH | 40 | chordotonal T3 right | 100 |

Candidate events are delivered only by setting ordinary MaleCNS external drive;
the implementation never writes voltage, conductance, weights, spike counts, or
other neural state. Directly driven indices (392 distinct neurons) are removed
from every downstream divergence and spike metric.

## Evidence and provenance

Classification is fail-closed: provenance, exact physical parity, candidate RNG
parity, and pre-delivery equivalence precede any propagation classification.
Per-leg P0–P7 times remain JSON `null` when absent. Mapped motor divergence (P7)
is observational only. The implementation locks the raw M5D-4E and M5D-4D
artifacts and canonical-LF hashes of both implementation pairs, then invokes the
existing M5D-4E verifier to revalidate M5D-4C and the earlier chain.

The checked-in artifact is intentionally `NOT_RUN`; it contains no fabricated
scientific result. On the validated Windows installation, run exactly:

```powershell
python -m malecns_backend.embodiment.proprioceptive_activation_audit --live --duration-ms 100 --seed 1
```
