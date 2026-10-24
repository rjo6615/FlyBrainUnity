# Frozen group-context posture analysis v1

Prospective analysis specification, 2026-10-24. Existing scalar peak/mean outcomes
are already known; the new time-aligned curves, peak timing and vector interaction
estimands below are specified before calculation. This is descriptive analysis of
the four frozen command policies, not new independent scientific replication.
No CNS/physics transitions, new force/seed/window, physiological changes, retries,
or retrospective acceptance changes. Preserve every preceding result and lock.

## Inputs and integrity

Use exactly ON_P/ON_C (fully closed-loop), T_P/T_C (six tibias replayed), C_P/C_C
(complementary 14 replayed), Y_P/Y_C (all commands replayed). ON_C is the archived
matched-pair ENABLED arm. Fully verify all upstream raw/compressed/source hashes
and recompute complete frozen evaluations before reducing traces. Require all
preceding integrity checks. Read each exact canonical archive and compare its
hashes again during reduction; retain reference-manifest hashes. Save finite root
position, quaternion, world linear/angular velocity, up_z and exact ground-contact
counts for all 20001 states, time 0..2000 ms at 0.1 ms. No selected samples/arms.
Require all four unpushed root traces/velocities/supports to reproduce ON_C exactly
and all pushed pre-force histories through 500 ms to match their controls.

Commit protocol, implementation and synthetic tests before executing this new
analysis. Reserve a fresh output directory exclusively. Save aligned numeric NPZ
(no pickle/object arrays), full JSON report, plots, raw/source/output hashes and
implementation commit. Preserve partial/error outputs; do not overwrite old data.
No new class of acceptance for balance: analysis integrity is data/provenance only.

## Fixed timeline, posture and orientation

All summaries use the existing cleared-force window: states 5201..20000 inclusive,
520.1..2000.0 ms. All plots show the full 0..2000 ms window and all stored points;
mark 500..520 ms pulse and 520.1 ms analysis start. Do not choose peaks/windows
after looking at curves. Report the earliest sample when a maximum is tied.

Reuse recovery-v1 shortest-arc quaternion distance and its normalized rotation
helper. Rotate local [0,0,1] into world axes to obtain body-up u. Report absolute
tilt acos(clip(u_z,-1,1)) and relative body-up angle acos(clip(u_push dot u_control,
-1,1)), alongside full relative quaternion angle. The latter includes heading
changes; body-up angle excludes pure yaw. Do not subtract angles to infer yaw or
add rotations as vectors. q and -q must produce identical posture metrics.

For each policy report absolute tilt peak/time, relative full-rotation peak/time,
relative up-angle peak/time, absolute tilt at the rotation-error peak and rotation
error at the absolute-tilt peak. Also report control tilt at both times and relative
up-angle at the rotation peak. Recompute the existing complete response summaries
and require equality to saved values; no recovery-band or support-definition edits.

## Predeclared vector interaction

Let a=1 replay tibia commands and b=1 replay complementary commands. Policies
00=ON_P, 10=T_P, 01=C_P, 11=Y_P. Define at each aligned timestamp:

    r_ab = p_pushed_ab - p_unpushed_ab
    I_position = r_11 - r_10 - r_01 + r_00

This signed world-coordinate vector has native model-mm units. Report its full
trace, peak norm/time/xyz, mean norm and signed xyz integral over the fixed post-
force window. Compare peak norm only with inherited .005 model-mm engineering
resolution to label resolved/not-resolved vector nonadditivity. This is not a
statistical significance test or a fraction of motor contribution.

Similarly let d_ab=u_pushed_ab-u_unpushed_ab and I_up=d_11-d_10-d_01+d_00. Report
its xyz trace and peak norm/time/xyz and mean norm; these are dimensionless body-up
vector differences, not rotation angles. Do not assign an angular threshold or
causal single-channel explanation. Group effects include later sensor/neural/
mechanical feedback and compensation. No additive interpretation of peak norms.

## Deliverables and roadmap snapshot

Create full-resolution posture plots (absolute tilt, full relative rotation,
relative body-up angle) and interaction plots (root-response norms, signed root
interaction xyz, signed up-vector interaction xyz), with readable units and policy
labels. No smoothing or plot-dependent scientific selection. Standard plotting
tools only; no generated pose/image substitutions or altered Unity scene.

Snapshot the canonical 42-coordinate model inventory and exact 20 admitted motors
from existing mappings, checking name/index correspondence. Breakdown: six tibias,
six femurs, six femur rolls, two front Tarsus1. Remaining 22 are 18 coxa coordinates
and four middle/hind Tarsus1. This is motor admission, not a claim that biological
mapping is 48% complete. Record current six tibia proprioceptive and six experimental
tactile populations; ordinary live tactile remains disabled. This analysis admits
no additional motor/sensory interface and establishes neither gait nor general
balance, intention, biological physiology, fully passive support or isolated-channel
necessity/sufficiency. Preserve RF tibia/RF Tarsus1 null exposure and all tradeoffs.

Git Bash, from this checkout:

```bash
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m pytest -q -p no:cacheprovider tests/test_group_posture_analysis.py
"$PY" -m malecns_backend.live.group_posture_analysis --output-dir docs/evidence/group-posture-analysis-v1
```

The command only validates/analyzes saved evidence. A later rerun must use a new
directory and is deterministic analysis, not a new CNS/physics experiment.
