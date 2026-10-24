# Six-foot collision-isolation calibration v2

Protocol specified on 2026-10-24 before running v2 physics. The v1 result remains
rejected: every nominal negative control touched its target. No v1 evidence or
locked source is replaced. This is a different engineering calibration context.

Question: does the existing total Tarsus5 force proxy distinguish an isolated
exact-pair contact from a collision-excluded negative over the entire fixed window?
This does not calibrate sensitivity in ordinary multi-contact live-v3 operation.

For LF, LM, LH, RF, RM, RH, run one fresh control then one fresh positive, seed 0,
0.05 s, dt 0.0001 s, including reset (501 samples each). Use the legacy sensor
ordering, observer, surface dimensions and positive placement (0.0001 penetration
relative to geom_rbound). Hold reset joint targets with adhesion off. No CNS,
encoder delivery, gravity change, root constraint, gain change or retry is used.
The free body can fall; no support is added. Subsequent trajectories may diverge.

Both conditions disable FlyGym explicit floor and self collision pairs at creation
and require compiled npair=0. Set every geom's contype/conaffinity to zero, then
allow only selected Tarsus5 (1/2) and positive surface (2/1). Negative surface is
collision-disabled and parked at the fixed world position (1000000, 0, 0), never
adjusted after outcomes. This deliberately excludes ground, other feet, body and
self collisions in both arms. Masks guarantee exclusion between integration
samples; independently record conservative bounding-sphere separation at every
sample. Separation samples alone do not prove a continuous geometric distance
bound. The topology exclusion, rather than an initial gap, supplies the continuous
negative collision guarantee. Require positive clearance at every negative sample.
No explicit contact pair may override the masks. Record the complete geom identity
table, masks, surface position, reset qpos/qvel, held targets, contact pairs and
force vector at every physics sample. Abort neither arm based on an early failure.

Acceptance (all required, no sample filtering): fixed schema, threshold 1e-12,
full fixed increasing schedules, finite force vectors/magnitudes, exact identities,
matched finite reset qpos/qvel and held commands, unchanged pose on placement,
unchanged masks and static surface, no explicit pairs, independently recomputed
clearance, and no unexpected pair anywhere in either condition. Every negative
sample must have no contact and force <= threshold. At least one positive sample
must have the exact target pair; every such sample must exceed threshold, and
every non-contact positive sample must remain <= threshold. Exact-pair truth is
independent of total-force measurement. Any unexpected collision makes attributing
total force to that pair invalid and rejects the leg, even if force agrees.

Exceptions preserve samples already collected, error text and per-arm status.
All legs/arms are attempted once. Nonfinite values are serialized as null with
locations and rejected. Missing dependencies/dry runs cannot pass. Existing output
files cannot be overwritten. Acceptance does not enable tactile delivery or claim
biological sensing, balance, gait, or transfer to ordinary supported live-v3 bodies.
A later matched delivery experiment still requires its own context and integrity
checks; a positive isolated calibration alone does not authorize that experiment.

## Manual Windows Git Bash checks

From the PR checkout, point PY at the existing validated environment (the absolute
path also works from this isolated worktree):

```bash
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m pytest -q tests/test_six_foot_contact_calibration_v2.py tests/test_six_foot_contact_calibration.py tests/test_tactile_targeted_contact_calibration.py
"$PY" -m malecns_backend.embodiment.six_foot_contact_calibration_v2 --output six-foot-v2-dry.json
"$PY" -m malecns_backend.embodiment.six_foot_contact_calibration_v2 --live --output six-foot-v2-live.json
```

Unit tests must pass. Dry run exits 1, with no accepted feet and NOT_RUN arms.
Live execution records all twelve arms; exit 0 means all six pass the specified
criteria, exit 1 means rejection/incomplete evidence. Neither outcome is promised.
Use a new output filename for each authorized experiment; do not rerun to seek a
pass. Reusing an output path must fail without modifying the existing file.
