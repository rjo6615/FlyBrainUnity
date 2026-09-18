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

## First-attempt provenance failure diagnostic

The first Windows attempt is preserved under an immutable diagnostic name as scientific non-result metadata
in `interface_output/tactile_motor_closed_loop_100ms_first_attempt_provenance_failure.json`.
It failed during provenance verification, before FlyGym was imported or either
condition entered simulation. Consequently it is **not** a scientific run and
contains no trajectory. A manually initiated second Windows execution is
acceptable for that reason only.

The M5D-4C implementation lock targets the single repository-relative file
`malecns_backend/embodiment/tactile_motor_matched_control.py`. The lock value
`0d75267b0203d9ad97e69bf9f75d57fdc5057beec682d925176479c00e8a2bc8`
was recorded when M5D-4D was introduced and is the SHA-256 of that file after
canonical CRLF/CR-to-LF conversion. It is not a multi-file or AST digest. The
same canonical-LF source-lock method was already used by the earlier M5D
provenance chain.

The Windows-observed raw digest
`967afaf2f6cde59956cee5b3c3c2d3a1c49ce5d007d7b8d92924615bf66d5048`
is exactly the SHA-256 of the same 12,742-byte LF file checked out with its 243
line endings converted to CRLF (12,985 bytes). Canonicalizing those bytes to LF
restores the locked digest. The authoritative M5D-4C artifact raw digest remains
`15e83fa88aa3e7a6206ea7bb736cd1ec446874dcf44079e0b79bcbf39c594901`.
The cause is therefore `LINE_ENDING_ONLY_MISMATCH`; no M5D-4C implementation,
scientific, control, or parameter semantics changed. The correction applies
canonical-LF hashing only to the implementation text; the authoritative JSON
artifact remains protected by its exact raw-byte lock, and every earlier lock
continues to fail closed.

Run the next attempt manually on Windows from the repository root:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.tactile_motor_closed_loop_audit --live --duration-ms 100.0 --seed 1 --json malecns_backend\embodiment\interface_output\tactile_motor_closed_loop_100ms.json
```
