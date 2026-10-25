# Paired LF endpoint/body-frame results

2026-10-25; baseline a734b56 (merged PR280). V1 protocol/runner committed dc0097b
before its attempt; V1.1 correction committed0155b10 before a separate campaign.
No pose, epsilon, budget, source/target model, neural parameter or physiology change.

## Preserved V1 setup failure

V1 stopped at target mesh bookkeeping before any kinematics probes. Its inspector
compared prefixed compiled mesh names directly with unprefixed XML asset names.
An independent installed dm_control MJCF attachment test demonstrates the prefix
without compiling a model. Source metadata was valid; target initialization ran
7forwards/3resets, but all probe/integration/CNS counts were0. V1 remains
**ENDPOINT_FRAME_INTEGRITY_FAILURE**, with its original protocol/runner/raw record.
Raw631895bytes, SHA256
`4de986daefb60a8528f7fb361cc0dfe0d7120af109140ace52bf4804ca28d598`.

V1.1 uses the existing namespace helper, preserving full raw mesh names plus
terminal components, exact numeric ownership, same full mesh/geom namespace and
all V1 non-schema evaluator checks. Full source model/state equals V1 compilation;
full target model/state equals the original native baseline. This corrects a
reference inspector, not the fly or acceptance budgets. V1 schema still rejects
V1.1 data; V1.1 separately validates its own schema and adds namespace checks.

## V1.1 measured result

**ENDPOINT_FRAME_V1_1_OBSERVER_VERIFIED_TRANSFER_BLOCKED**.
All15poses,105source+106target samples pass integrity, bounds and fixed numeric
criteria. No target attachment, path scale, alignment or muscle sites were created.

| Metric | Maximum observed | Fixed absolute budget |
|---|---:|---:|
| Endpoint world/local reconstruction |4.440892098500626e-16|1e-10|
| Source two-point versus archived tendon lengths |0|1e-10|
| Negative length derivatives versus archived moment arms |1.8889066699667723e-10|1e-7|
| Archived source/target rotations |0|1e-10|
| Compiled geom/body frame reconstruction |3.1086244689504383e-15|1e-10|

Source Thorax/Coxa compiled body IDs2/19, geom IDs1/18. Eight source sites in route
order:4/11 (remotor),8/15 (adductor),6/13 (anterior),7/14 (posterior). Exact compiled
site-body ownership/local position and tendon SITE-wrap order validated. Source
joint/DOF/qpos/actuator/tendon/activation identities and parameters match prior
source authorities. Target bodies3/13, geoms2/12 remain the original native rig.

The source thorax-relative coxa origin at center is approximately
[-.1306,.1995,-.2305]; target approximately[-.160596,.171588,-.230215]. These are
separately recorded native numeric coordinates, not a physical equality, fitted
translation, unit conversion or anatomical correspondence. Compiled geom frames
and mesh preprocessing tables are retained; raw STL frames are not conflated with
compiler-centered mesh frames.

V1.1 executed one source compile and one target initializer (7forwards/3resets),
then211explicit mj_kinematics with0probe forwards/resets and0integration/CNS.
All state velocities/activation/control/applied buffers/time remain zero. Before/
after identities and file/source locks match. V1+V1.1 together had two initializers
(14forwards/6resets),211total kinematics, zero integration/CNS. No additional native
diagnostic campaign was run; the namespace demonstration only constructed MJCF.

New V1.1 LFS record9131610bytes, raw SHA256
`a317d87446c5879b564f21ecd7ffa88572d7b5370e098293c032c695131eae10`.
Both raw records and full observations are retained.

## Checks and limitations

Before V1:29tests passed/12prospective archive tests skipped57.48s. Before V1.1:
14passed/25skipped26.83s; skips distinguish12completed-V1-record tests inapplicable
to an incomplete setup record from13prospective V1.1 tests. An explicit V1 test
asserts its unchanged integrity failure and zero probes. No acceptance check was
removed from either evaluator. Final batch: **70passed/12skipped in89.47s** across
V1/V1.1 endpoint, route-attachment and target-orientation tests. The12skips apply
only to completed-V1-data tamper cases: its setup produced no samples. Its failure
is explicitly tested, and all V1.1 archive checks ran. Windows Git Bash saved replay
passed without native reexecution; whitespace and LFS-pointer checks passed.

The result validates a source endpoint/length-gradient observer and paired frame
context. Velocities were zero: nonzero-velocity muscle physiology and source-to-
target velocity transfer were not measured. Target endpoint correspondence,
physical unit/converter lineage, anatomy/neural conversion and original failed
raw scientific prerequisites remain unresolved. Production20/42,new admissions0;
independent balance/gait and new Unity behavior are not established.

Next: make an explicit target-attachment registration decision from paired frames,
source/target asset evidence and independent anatomical landmarks. Do not infer
endpoints from matching names or choose a transform to make lengths/forces look
good. If no adequate authority exists, keep target correspondence null and state
what additional reference evidence is required before defining a modeled transfer.

## Windows Git Bash after merging

This verifies saved records, with no source clone required or native reexecution.

```bash
cd ~/Documents/FlyBrainUnity &&
git switch newBrain &&
git pull --no-rebase --no-edit &&
git lfs pull --include="malecns_backend/embodiment/interface_output/integrated_whole_leg_readiness.json,docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather,docs/evidence/lf-pose-force-v1*/run/validation.json,docs/evidence/lf-activation-transient-v1/run/validation.json,docs/evidence/lf-activation-integrator-v1/run/validation.json,docs/evidence/lf-native-isolation-v1*/run/validation.json,docs/evidence/lf-synthetic-coupling-v*/run/validation.json,docs/evidence/lf-target-orientation-v1/run/validation.json,docs/evidence/lf-endpoint-frames-v1*/run/validation.json" &&
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" &&
"$PY" -m malecns_backend.embodiment.lf_endpoint_frames_v1_1 \
  --report docs/evidence/lf-endpoint-frames-v1_1/run/validation.json
```

Expected: `ENDPOINT V1.1 EVIDENCE VERIFIED`,
`ENDPOINT_FRAME_V1_1_OBSERVER_VERIFIED_TRANSFER_BLOCKED`;105source/106target
recorded samples; historical V1 setup failure0probes preserved;20/42,0new
admissions. Counts describe archived measurements; review executes no native calls.
