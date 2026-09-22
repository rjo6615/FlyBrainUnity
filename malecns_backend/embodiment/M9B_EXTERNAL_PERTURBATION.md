# M9B — MaleCNS response to calibrated external perturbation

## Frozen design (not executed)

M9B preregisters a **four-condition 2×2 factorial**: `A_P` (motor enabled,
perturbed), `A_C` (motor enabled, zero force), `B_P` (motor disabled,
perturbed), and `B_C` (motor disabled, zero force). The existing M7D/M8 runtime
supports the two interventions orthogonally: the decoder is always evaluated,
while B zeros only its eleven contributions immediately before physical
application; force presence is selected by integer outgoing-transition index.
This design therefore adds no embodiment semantics and permits the
perturbation-specific contrasts `(A_P-A_C)` and `(B_P-B_C)` and their
difference. Raw post-500-ms A/B divergence alone is not perturbation
attribution.

Each fresh seed-1 condition lasts 1500 ms: a 500-ms independently recorded
baseline, force on transitions 5000–5199 (20 ms), and 980 ms after force. The
physics cadence is 0.1 ms (15,000 transitions and 15,001 states); MaleCNS uses
its frozen 0.5-ms cadence (3,000 updates). Perturbed conditions receive exactly
`[0, 1.024, 0]` in world/native MuJoCo units at authoritative Thorax COM and
zero torque. Controls receive exact zero force. Scheduling never uses an
accumulated timestamp.

## Frozen interfaces and initialization

The admitted motor inventory is six tibiae (`LF:5`, `LM:12`, `LH:19`, `RF:26`,
`RM:33`, `RH:40`, all sign +1) and five femora (`LF:3`, `LM:10`, `LH:17`,
`RM:31`, `RH:38`, all sign −1). Only the six tibiae are admitted modeled
proprioceptive inputs. Contact is physical telemetry and is not neural input.
Decoder filtering, gains, saturation, slew limits, and bounds remain the exact
M7D/M8 semantics.

Initialization remains FlyGym 1.2.1 / MuJoCo 3.2.7, static tripod, position
`[0,0,0.6045752232266313]`, orientation `[0,0,0]`, position control, adhesion
disabled, the exact 42 corrected baseline targets, no settling, and the
inherited calibration surface. No locomotion, reference, coordination,
stabilization, assistance, reward, RL, or AI controller is present.

## Provenance, telemetry, and claims

Preflight verifies raw SHA-256 and byte sizes of the canonical M9A-3 Attempt-3
manifest, report, and preregistration, and verifies the manifest's raw-artifact
records. It requires schema `M9A-3-MATCHED-CONTROL-PHYSICS-ONLY-CALIBRATION.3`,
`COMPLETE`, and the preregistered lowest qualifying `1.024` selection with the
frozen body, frame, direction, torque, timing, and cadence.

The raw schema preserves physical pose/orientation/up vector, velocities, 42
joints and commands, eleven isolated contributions, contacts, distal tarsi,
force, and fall/rollover state, plus neural sensory encoding/delivery, CNS
summary, mapped activity, observer/decoder outputs, and pre-/post-zero vectors.
Initialization equivalence is exact; physical equality at 500 ms is expressly
not required. Analyses are trajectory- and time-resolved, not a single score.
Only the conservative classifications frozen in the preregistration are
allowed. Stronger functional interpretations are outside M9B.

## Commands

Zero-transition Windows preflight only:

```powershell
python -m malecns_backend.embodiment.m9b_external_perturbation --windows-preflight
```

The separate `--run-windows` path is the explicit scientific execution entry
point and must not be invoked during implementation/preflight. Canonical raw,
report, and manifest publishing uses exclusive creation and refuses any
existing evidence namespace.
