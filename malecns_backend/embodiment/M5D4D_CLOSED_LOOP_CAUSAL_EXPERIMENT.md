# M5D-4D corrected 100-ms closed-loop causal experiment

## Status

**NOT RUN.** This checkout is not the validated Windows FlyGym/MuJoCo runtime.
The checked-in JSON is deliberately null-valued evidence, not an inferred or
fabricated scientific result. Consequently there is no classification, timing,
causal ordering, or motor-feedback claim yet.

## Frozen protocol and provenance

The one permitted run uses seed 1, 100.0 ms duration, 0.1-ms physics steps and
0.5-ms neural steps. It uses actuator indices LF 5, LM 12, LH 19, RF 26, RM 33,
and RH 40. The experiment imports the actual M5D-4C `MatchedControlPipeline`;
it does not copy its command logic. The condition flag therefore affects only
the admitted contribution. Both conditions continue raw decoding.

The runner verifies byte locks for the authoritative M5D-4C artifact and its
pipeline implementation, verifies the existing M5D-2C through M5D-4B locks,
and fails closed. Prefix validation is based on observed trace events rather
than assigning the expected 14.5/14.6-ms values as results.

## Interpretation policy

Feedback stages are independently recorded. Physical divergence cannot precede
admission; CNS and mapped-motor feedback cannot precede sensory-encoding
divergence. An RNG mismatch cannot earn a feedback classification. These are
claims about the modeled MaleCNS embodiment only—not a biological touch reflex,
natural gait, natural walking, or proof of equivalence to a real fly.

The authoritative first completed artifact must be preserved. There is no
automatic retry or tuning path.

## Exact Windows live command

From the repository root in the validated environment:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.tactile_motor_closed_loop_audit --live --duration-ms 100.0 --seed 1 --json malecns_backend\embodiment\interface_output\tactile_motor_closed_loop_100ms.json
```
