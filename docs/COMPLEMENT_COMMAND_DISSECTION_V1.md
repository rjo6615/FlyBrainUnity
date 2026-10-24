# Complementary motor-command group v1

Prospective specification, 2026-10-24, before new scientific outcomes. Select the
exact current v3 inventory minus the six already tested tibias. This fixed rule
selects 14 admitted motor channels: six femurs, six femur-roll channels and two
front Tarsus1 channels. No activity/effect ranking or individual-channel search.

Canonical v3 order/action indices are LF/LM/LH/RM/RH Femur 3/10/17/31/38;
LF/LM/LH/RF/RM/RH Femur_roll 4/11/18/25/32/39; RF Femur 24; LF/RF Tarsus1 6/27.
Require the actual exact names/indices/body-ID/dense-index inventory, disjoint
from the six tibias and together exhaustively equal to all 20 admitted motors.

## Fixed pair and application boundary

Fresh order C_C then C_P, once each; seed 1, two seconds, 20000 physics transitions,
4000 neural updates and 20001 saved states. Tactile delivery and all 20 motor
readouts/decoders remain active, with unchanged 1877 tactile/392 proprioceptive
neurons, common 2269-slot RNG schedule, physiology, encoder, gains, mapping,
collisions, support, adhesion and native scientific kernel. No tuning or retries.

At outgoing transition n, copy the contemporaneous native proposed 42-coordinate
action. Replace ONLY the 14 selected coordinates with archived undisturbed
ENABLED sample n+1 commanded_joints. The other 28 coordinates, including all six
tibias, must remain exactly native proposals. Require finite 42-vectors and zero
adhesion. Record proposed/applied actions and each selected channel's exposure.
Never use measured pose, ctrl, interpolation, zeros or a held starting posture.
This uses the previously recorded future undisturbed command schedule openly as
a causal open-loop engineering control, not an online balancing controller.
Retain ongoing CNS/encoder/readout/decoder computation and its proposal telemetry.

C_C is unpushed and must exactly reproduce the entire archived ON_C physical/
contact/encoder trajectory, all neural records and zero applied/proposed changes.
Strip only generated contact-name namespace prefixes when matching; exact
IDs/ownership and all other contact fields must agree. Require initial/model
identity and full histories through 500 ms, complete common RNG uniforms and all
strict attribution/readout/context checks in both arms. Missing/mismatched source,
identity, action, finite evidence or force rejects integrity, not just positivity.

C_P receives the same exact Thorax-COM world force [0,1.024,0], zero torque,
outgoing transitions 5000..5199 (200 applied observations, impulse .02048 native
force seconds). Reuse existing force callback and complete sparse-wrench audit;
no other body/generalized forcing. Later closed-loop physical/neural/contact and
candidate divergence can be an outcome; all nonselected applied actions must
still equal their own current native proposals.

## References and unchanged interpretation

First verify all complete archived tibia-v1, all-command-yoke-v1, recovery-v1 and
their prerequisites: raw/compressed/source hashes and recomputed evaluations.
Reuse their undisturbed and pushed records, not new duplicate baseline trials.
C_C exists to validate the new selective boundary, not to replicate old science.
Retain original scientific sources, hashes, evidence, nulls and adverse outcomes.

Compare C_P minus C_C primarily with ON_P minus ON_C using unchanged recovery-v1
metrics, world angular velocity, resolution/bands and 100 ms sustained dwell.
As in tibia-v1, use existing M11 signed effect/classification helpers, inclusive
0.25 deg: SELECTIVE_YOKING_REDUCES_RESPONSE requires BOTH peak/mean differences
<=-0.25; INCREASES requires BOTH >=+0.25; otherwise MIXED_OR_UNRESOLVED. Classifier
names inherited from M11 do not mean neurons or baseline contributions are zeroed.
Report descriptive comparisons against tibia-only and all-command yokes, retaining
height, velocity, absolute tilt, support, rollover and recovery separately.

The four group contexts now permit comparison, not an assumption of additive
effects. Do not assign fractions explained from differences in peak/mean norms,
or assign residual response to a channel independently. Other motors can compensate;
state/sensory feedback changes after intervention. No exposure/unqualified baseline
limits interpretation; zero individual-channel exposure is retained, not retuned.
Integrity never requires a beneficial result, recovery or activity in each channel.

This tests one aggregate modeled application intervention under one seed/pulse/
window; it cannot establish intention, biological balance, gait, fully passive
support or individual-channel necessity/sufficiency. Keep the RF tibia's earlier
zero exposure and all prior adverse tilt/velocity/non-recovery findings visible.

## Evidence and execution

Commit protocol, implementation and boundary tests before execution. Reserve a
new directory exclusively; save every complete/partial/error arm as gzip JSON,
with full raw/source/compressed hashes, environment, pre-execution commit and
all checks. Stop later arms after interruption; no force/channel/seed/window
search, overwrite, retry or acceptance changes. Ordinary live tactile stays off.

Reuse the validated yoke/kernel and M11 mapping/classifier. Full inherited audits
remain visible: explicitly supersede only their source-set requirement with the
enlarged versioned source-set equality. All other strict checks remain. Retain the
historical no-force rejection in pushed arms, replaced only by exact planned force.
No Unity scene/controller changes; measured replay labels conditions and resets.

Git Bash from this checkout:

```bash
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m pytest -q -p no:cacheprovider tests/test_complement_command_dissection.py
"$PY" -m malecns_backend.live.complement_command_dissection --output-dir complement-dissection-dry
echo $? # 1 / NOT_RUN; directory must be new
"$PY" -m malecns_backend.live.complement_command_dissection --live --output-dir docs/evidence/complement-command-dissection-v1
```

The live command is this single prospective pair or a separately planned
independent replication, not repeated attempts to obtain benefit.
