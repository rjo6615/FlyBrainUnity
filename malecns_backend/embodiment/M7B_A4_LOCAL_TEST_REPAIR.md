# M7B-A4 local test-suite repair

## Input validation provenance

**M7B LOCAL TEST VALIDATION #1**

- Result: **27 PASSED / 5 FAILED**
- Scientific result: **NONE**
- Canonical analysis: **NOT RUN**

These five failures were analyzer/test engineering issues discovered before
Attempt #4. They do not increment canonical analysis attempt numbering.

## Isolation-test diagnosis

The only forbidden-token match in `m7_postrun_analysis.py` was `mujoco`, on the
comment line “The frozen recorder reads MuJoCo's clock once at the start of
each loop iteration.” It was a comment/provenance explanation, not an
executable import, executable runtime call, imported dependency, or string.
There were no matches for `flygym`, `brain.step(`, `sim.step(`, or
`_windows_m7`.

Source inspection nevertheless found avoidable transitive coupling: the
analyzer imported `CONDITIONS` and `THRESHOLDS` from the M7 scientific protocol
and runner module. That module does not itself initialize or execute a
simulation on import, and its transitive imports are reduction/provenance code,
not the Windows live adapter. Thus no real simulation or neural runtime was
imported or executable through analyzer import. The coupling was removed by
making the immutable shared values live in the data-only `m7_protocol` module.

The isolation regression now parses imports with the Python AST rather than
rejecting scientific vocabulary in comments. It verifies that analysis uses
the lightweight protocol module, does not import the runner, and neither
imports nor initializes FlyGym or MuJoCo.
