# M7B-A3 neural-cadence provenance repair

## Attempt provenance

**M7B CANONICAL ANALYSIS ATTEMPT #3**  
**STATUS:** `ABORTED_EVIDENCE_VALIDATION`  
**SCIENTIFIC RESULT:** `NONE`  
**CAUSE:** `REMAINING ANALYZER NEURAL-CADENCE PROVENANCE DEFECT`

Attempt #3 correctly established that neural timestamps exactly subsample the
shared physics runtime clock. It nevertheless retained a redundant neural
cadence tolerance derived as though neural time were independently advanced by
0.5 ms. Valid canonical telemetry therefore failed evidence validation before
analysis. No analysis or simulation ran, no scientific transition occurred,
and no evidence was modified.

## Exact failure

The rejected check was:

```python
np.abs(np.diff(time) - dt_ms) > (
    2 * np.spacing(np.maximum(adjacent_scale, abs(dt_ms)))
    + np.spacing(dt_ms)
)
```

For the first rejected canonical neural interval, from
`31.499999999999876` ms to `31.99999999999989` ms, the observed interval was
`0.5000000000000142` ms. Its deviation from the nominal `0.5` ms was
`1.4210854715202004e-14` ms, while the expression allowed only
`7.216449660063518e-15` ms. That local ULP expression models one nominal
0.5-ms subtraction; the recorded interval instead spans five successive
binary64 physics-clock advances and then subtracts two recorded timestamps.

## Repaired model

The physics clock is now the only independently validated clock. It retains
the float64, count, finite, monotonic, nominal origin/endpoint, repeated
0.1-ms accumulated-drift, and per-transition cadence checks. Neural telemetry
retains its float64, count, finite, monotonic, and nominal boundary semantics,
but has no independent accumulated-clock or cadence model. Its timing
provenance is established by the stronger exact invariant:

```python
np.array_equal(neural_time_ms, physics_time_ms[5::5])
```

Thus every neural interval is necessarily derived from two validated physics
timestamps separated by five transitions. No independent `+0.5 ms`
accumulation assumption remains.
