# M7B-A5 neural expected-count repair

## Input validation provenance

**M7B LOCAL TEST VALIDATION #2**

- Result: **31 PASSED / 1 FAILED**
- Scientific result: **NONE**
- Canonical analysis: **NOT RUN**

This was a local validator/test bookkeeping failure, not canonical Attempt #4.
The failing synthetic test replaced the neural clock with 10,000 values while
retaining the fixture's default 26-value physics clock.  Consequently,
`physics_time_ms[5::5]` contained 5 values and the noncanonical validation path
derived an expected count of 5, so sample-count validation correctly preceded
provenance validation for that internally inconsistent fixture.

The validator now names and derives both the expected neural clock and its
count directly from the validated physics-clock subset.  Focused tests use the
frozen 50,001-sample clock dimensions to distinguish 9,999- and 10,001-value
length failures, a 10,000-value ideal independent clock provenance failure,
the accepted exact 10,000-value physics subset, and wrong-index provenance.

No canonical evidence, scientific runtime, telemetry generation, scientific
parameter, or preregistration file was changed or executed.
