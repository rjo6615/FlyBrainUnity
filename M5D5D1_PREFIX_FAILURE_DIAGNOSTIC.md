# M5D-5D1 Scientific Run #1 prefix-failure diagnostic

## Scope and read-only disposition

This is an offline reducer only. It neither imports nor invokes either scientific
runner. It does not modify the frozen M5D-5B/M5D-5D artifacts or telemetry and
consumes no scientific run number.

## Fail-closed result in this checkout

**Run status: `FAILED`; classification: `OTHER_DIAGNOSTIC_FAILURE`.** The named
M5D-5D JSON in this checkout is schema `M5D-5D.0` but records `run_status =
FAILED`, `classification = PROVENANCE_FAILURE`, and null milestones. The named
NPZ does not exist. Consequently the diagnostic stops at
`AUTHORITATIVE_JSON_SEMANTICS_MISMATCH`; it does not treat values in this task
request as telemetry, and it makes no scientific conclusion from an
unverifiable input pair. The machine-readable output records the observed JSON
SHA-256.

This is intentionally different from declaring the supplied expected diagnosis
false. Installing the actual frozen `COMPLETE` JSON and its digest-matching NPZ
allows the same script to finish the analysis without running a simulation.

## Exact historical guard reconstruction

The M5D-5D adapter computes `prefix` exactly as:

```text
all(C3,C4,C6,C7,C8,C10,C11 are not None)
and C3 < C4 <= C6 <= C7 <= C8 <= C10 < C11
```

It then computes `replication_guard.passed` as
`pre_intervention_equivalence.passed and prefix`; the classifier emits
`REPLICATION_FAILED_PREFIX` when provenance, physics, RNG, instrumentation, and
pre-equivalence have passed but `prefix` is false.

Using the milestone values supplied in the request (not asserted as verified
telemetry in this checkout), the expanded terms are:

| predicate | evaluation | result |
|---|---|---|
| C3 present | 13.5 is not null | PASS |
| C4 present | 13.5 is not null | PASS |
| C6 present | 13.6 is not null | PASS |
| C7 present | 13.6 is not null | PASS |
| C8 present | 14.0 is not null | PASS |
| C10 present | 22.0 is not null | PASS |
| C11 present | 24.0 is not null | PASS |
| **C3 < C4** | **13.5 < 13.5** | **FAIL (first)** |
| C4 <= C6 | 13.5 <= 13.6 | PASS |
| C6 <= C7 | 13.6 <= 13.6 | PASS |
| C7 <= C8 | 13.6 <= 14.0 | PASS |
| C8 <= C10 | 14.0 <= 22.0 | PASS |
| C10 < C11 | 22.0 < 24.0 | PASS |
| exact pre-intervention equivalence | true == true | PASS (supplied) |
| causal prefix ordered | false == true | FAIL |
| replication guard | true and false == true | FAIL |

Notably, **C1 is not a term in this guard**. The guard therefore does not
require a same-update mapped-motor spike before raw decoder contribution. Its
strict assumption is instead that the first admitted contribution C3 must
precede the first divergent action C4, even though both may be recorded in one
update. If verified telemetry has the supplied values, that is a
`GUARD_SEMANTIC_MISMATCH`, and not a scientific prefix failure or timing/numeric
boundary mismatch.

## Frozen comparison and C1/C13 claims

The checked-in M5D-5B Run #2 reports the supplied sequence (subject to ordinary
binary-float spellings): C2/C3/C4 13.5 ms, C5/C6/C7 13.6 ms, C8 14.0 ms,
C9/C10 22.0 ms, C11 24.0 ms, C12 26.0 ms, with C1/C13 null. Those values match
the values supplied for M5D-5D. If the absent NPZ and replacement COMPLETE JSON
verify, this establishes reproduction of the recorded motor-to-body-to-modeled-
proprioception-to-downstream-CNS causal prefix despite the guard's strict
C3/C4 inequality.

The supplied C1 resolution is coherent: an earlier mapped LM spike can remain
in the 40-ms low-pass observer/decoder and yield decoder output at 13.5 ms with
zero new extensor/flexor spikes at that update. Thus mapped-motor spike time and
decoder-output time are distinct, and C1 may remain null only if no mapped spike
was recorded in the run's milestone window. The exact earlier spike time,
population, body ID, count, instantaneous Hz, and filtered trajectory cannot be
recovered or responsibly stated without the missing NPZ.

C13 must remain `MAPPED_MOTOR_SUBTHRESHOLD_DIVERGENCE`: supplied evidence is
mapped-motor state divergence at 24.5 ms, decoder-state divergence at 39.5 ms,
and no mapped-motor spike divergence within 100 ms. This is not full
closed-loop motor-spike recruitment. The current fail-closed output does not
promote these supplied facts to verified observations.

## Independent pre-intervention check

The historical reducer compares every paired row strictly before C3 over qpos,
qvel, qacc, contact forces/set, six tibia angles, full proprio/tactile records,
delivered sensory events, CNS digest/spikes, mapped motor spikes, observer and
decoder state, raw contribution, motor baseline, previous target, final action,
and ctrl. RNG alignment separately checks draw counters plus every leg's
before/after RNG identity at every row. The new diagnostic refuses to summarize
first divergences until it can open and digest-match the NPZ. Therefore no
field-level equality claim, tolerance relaxation, or fabricated first-divergence
value appears in the failed output.
