# M7B-A1 canonical timestamp-validation repair

## Failure provenance

**M7B CANONICAL ANALYSIS ATTEMPT #1**  
**STATUS:** `ABORTED_EVIDENCE_VALIDATION`  
**SCIENTIFIC RESULT:** `NONE`  
**CAUSE:** `ANALYZER TIME-VECTOR VALIDATION DEFECT`

The analyzer used an absolute `1e-9` comparison between physics time and
`np.arange(len(pt)) * 0.1`; that rejected harmless error accumulated by 50,000
binary64 runtime additions. It also compared neural time to
`np.arange(len(nt)) * 0.5`, incorrectly requiring a neural sample at `t=0`.
No canonical analysis artifact from this attempt is complete.

## Repaired contract

Physics has 50,001 samples: the initial state followed by the states after
50,000 transitions. Its semantic time is `t[i] = i * 0.1 ms`, for
`i = 0..50000`. Neural telemetry has 10,000 samples taken after completed
neural updates, not an initial sample. Its semantic time is
`t[i] = (i + 1) * 0.5 ms`, for `i = 0..9999`.

Each clock must be float64, finite, strictly increasing, have the exact sample
count, correct semantic origin and endpoint, and every difference must match
its frozen timestep. Accumulated-time tolerance is derived from IEEE-754
round-to-nearest: each repeated addition contributes at most half an ULP at
the current clock magnitude, accumulated through the sample, with one ULP for
rounding the independently calculated reference. Cadence tolerance accounts
for the rounding represented by both adjacent timestamps plus one timestep
ULP. Thus the tolerance scales with binary64 precision, clock magnitude, and
run length rather than being chosen to make this archive pass.

The two frozen-protocol conditions use the same deterministic clock mechanism,
so their physics clocks must be exactly equal sample-for-sample, as must their
neural clocks. (Tolerance is needed against an independently calculated ideal,
not between the two identically generated condition clocks.) Validation records
that result and the exact-comparison policy in its evidence metadata.

This repair changes analyzer validation and synthetic tests only. It does not
change or rerun M7, M6C, telemetry generation, timestamps, conditions,
thresholds, interfaces, scientific parameters, or preregistration. No
canonical evidence or completed analysis/report artifact was produced.
