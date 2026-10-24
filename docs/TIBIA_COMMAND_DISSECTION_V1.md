# Tibia motor-command dissection v1

Prospective protocol, 2026-10-24. Before new outcomes, select the entire anatomical
tibia group: all six tibia channels in the existing M11 motor mapping, intersected
with and required present in the current 20-motor v3 inventory. Exact action
indices LF/LM/LH/RF/RM/RH are 5/12/19/26/33/40. Selection uses anatomy/mapping,
not prior per-channel effect size, activity, apparent benefit or outcome ranking.
This is a group-level first dissection, not an individual-channel conclusion.

## Fixed experiment

Exactly two fresh conditions, T_C then T_P, seed 1, two seconds / 20000 physics
transitions / 4000 neural updates / 20001 states each. Both retain tactile delivery,
392 proprioceptive and 1877 tactile inputs, the common 2269-slot external RNG
schedule, all 20 decoded motor channels, and normal supported live-v3 physics.
No weights, neural parameters, gains, encoder, mapping, collision, support,
adhesion, decoder, duration or acceptance changes. Ordinary live tactile stays off.

At every outgoing physical transition n, copy the native proposed 42-coordinate
joint action, replacing ONLY indices 5/12/19/26/33/40 with archived undisturbed
ENABLED sample n+1 commanded_joints values. All other 36 coordinates must equal
the native proposal exactly; 14 of those are admitted live motors. Adhesion remains
zero. Record proposed/applied actions and per-channel intervention exposure.
The archived future command schedule is explicitly an open-loop causal control,
not an online stabilizer or controller. Never substitute qpos, ctrl, interpolated
values or zero commands. Keep CNS, readout and decoders active in all channels.

Reuse the existing command-yoke instance boundary and shared kernel. The M11
zero-contribution gate was inspected: zeroing baseline actuation would answer a
different question. Reuse its anatomical inventory and pure effect/classification
helpers, while using the already verified yoke for exact command replacement.
Thus this extends the preceding all-channel yoke to a preselected group rather
than silently changing intervention type to ablation.

T_C has no force and must reproduce the archived ON_C entire physical/contact/
encoder trajectory and all neural records exactly. Compare contact names only
after stripping generated namespace prefixes; require exact IDs/ownership and
every other contact field. Exact initial/model identity, first 500 ms physical
and neural histories and complete uniform RNG schedule must match in both arms.
Any missing source, mismatched action/index/identity, nonfinite evidence,
unplanned forcing or failed context requirement rejects integrity.

T_P uses unchanged world [0,1.024,0] force at exact Thorax COM, zero torque,
outgoing transitions 5000..5199, 200 applied observations, impulse .02048 native
force seconds. Reuse the complete recovery-v1 sparse-force audit and all six-foot
attribution checks. After the push, physical/neural/candidate differences can be
outcomes. All nonselected actions must remain identical to their contemporaneous
native proposals, even after physical feedback diverges.

## Comparisons and fixed interpretation

Verify full archived yoke-v1 and recovery-v1 sources, raw/compressed hashes and
saved evaluations before new execution. Reuse ON_P/ON_C closed loop and Y_P/Y_C
all-command-yoke metrics; do not rerun unchanged controls merely to duplicate data.
Compare T_P minus T_C with ON_P minus ON_C using unchanged recovery-v1 resolution,
world-angular-velocity conversion, bands and 100 ms dwell. Report an additional
descriptive comparison with all-command yoke; do not assume additive channel
effects or assign the residual to the other 14 channels independently.

Use existing M11 ablation_effect for selected-minus-reference metric differences
and classify with inherited inclusive +/-0.25 deg bounds. Primary orientation
label SELECTIVE_YOKING_REDUCES_RESPONSE requires BOTH peak and mean differences
<=-0.25 deg; SELECTIVE_YOKING_INCREASES_RESPONSE requires BOTH >=+0.25 deg;
otherwise MIXED_OR_UNRESOLVED. This explicitly inherits M11's inclusive boundary.
Report height, velocity, contact support, absolute tilt, rollover and recovery
separately. Smaller deviation from a moving control is not synonymous with a more
upright body. No exposure or unqualified baseline limits interpretation. Integrity
never requires a beneficial outcome, recovery or individual channel activity.

No retries, adaptive channel search, force sweep or parameter tuning. Keep null,
partial, rejected and adverse results. This tests an aggregate command-group
intervention under one modeled pulse/seed/window, not intention, biological
balance, gait, isolated tibia necessity/sufficiency or fully passive support.
The other motors may compensate; effects are context-dependent and non-additive.

## Evidence and execution

Commit this protocol, implementation and boundary tests before execution. Reserve
a new output directory exclusively and save every full/partial arm separately as
gzip JSON with raw/compressed hashes, environment, implementation commit and source
locks. Stop following arms after interruption; no overwrite of existing output.
Retain full inherited audits. Only the inherited source-set requirement is
explicitly superseded by equality to the enlarged versioned source set; every
other strict requirement remains. Historical no-force rejection remains visible
and is replaced only by the unchanged exact planned-force requirement.

Git Bash, from this checkout:

```bash
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m pytest -q -p no:cacheprovider tests/test_tibia_command_dissection.py
"$PY" -m malecns_backend.live.tibia_command_dissection --output-dir tibia-dissection-dry
echo $? # 1 / NOT_RUN; existing directories refused
"$PY" -m malecns_backend.live.tibia_command_dissection --live --output-dir docs/evidence/tibia-command-dissection-v1
```

The live command is the single prospective pair, or a separately planned
independent replication, not repeat-until-benefit. Unity review uses measured
saved poses and labels resets, not another scientific run.
