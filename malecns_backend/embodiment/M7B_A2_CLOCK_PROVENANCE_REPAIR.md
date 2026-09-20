# M7B-A2 clock-provenance validation repair

## Attempt provenance

**M7B CANONICAL ANALYSIS ATTEMPT #2**  
**STATUS:** `ABORTED_EVIDENCE_VALIDATION`  
**SCIENTIFIC RESULT:** `NONE`  
**CAUSE:** `ANALYZER CLOCK-PROVENANCE VALIDATION DEFECT`

Attempt #1 used an incorrect neural `t=0` assumption and an overly strict
ideal timestamp check. Attempt #2 corrected the neural origin, but
accumulated-error model treated the neural clock as though it were independently
accumulated at 0.5 ms rather than following the frozen recorder's actual clock
provenance.

No analysis or scientific simulation occurred and no canonical evidence was
modified by either attempt.

## Source-established recorder order

The frozen M7 adapter delegates both conditions to
`_windows_m6c_live_condition.run_condition`. At the start of every loop
iteration, that function reads `physics.data.time * 1000` exactly once into
`now_ms`. The initial iteration therefore observes the initial physics state at
zero. Neural work runs when the loop index is nonzero and divisible by the
five-physics-step stride. After that update completes, `now_ms` is written to
the neural record. The same unchanged `now_ms` is then written to the physics
record. Only after both records are appended does `sim.step` advance the
MuJoCo clock for the next iteration.

Consequently, the physics vector contains the initial state and every
post-transition state, while neural timestamps are exact samples of the same
runtime clock after transitions 5, 10, 15, and so on. In array terms, the
frozen relationship is exactly:

```python
neural_time_ms == physics_time_ms[5::5]
```

There is no independent neural clock.

## Repaired validation

Physics retains all representation, finiteness, monotonicity, count, nominal
origin, endpoint, cadence, and repeated-0.1-ms accumulated-error checks. Neural
retains the corresponding 10,000-sample, float64, finite, monotonic, nominal
0.5-ms origin/cadence/endpoint checks. Its accumulated mathematical bounds are
now sampled from the validated physics-clock bounds, and its provenance is
checked by exact array equality with `physics_time_ms[5::5]`. Exact clock
equality between conditions is also retained.

This is an analyzer-and-test repair only. It does not modify telemetry
generation, canonical raw evidence, manifests, summaries, scientific
parameters, thresholds, model behavior, or preregistration, and it executes no
scientific transition.
