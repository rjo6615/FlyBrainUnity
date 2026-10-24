# Tibia command-group dissection v1 — results and review

Protocol, scientific runner and boundary tests were committed at `9f58379`
before scientific execution. The isolated branch starts at latest `origin/newBrain`
`8be2f45728ddd5927bed6a6f21a7bb5da29845db` (merged PR #261). See
[the prospective protocol](TIBIA_COMMAND_DISSECTION_V1.md).

**All integrity checks passed. Tibia-only command yoking reduced disturbance-
relative orientation departure, with adverse tradeoffs in absolute tilt and peak
velocity errors. Neither condition achieved sustained recovery.** No acceptance,
force, channel selection or neural parameter was changed after outcomes.

## Measured outcomes

Both fresh arms completed 20000 physics transitions / 4000 neural updates /
20001 states. T_C reproduced the complete original unpushed physical/contact/
encoder trajectory and all neural records exactly, with no command replacements.
Initial/model identity, pre-push history through 500 ms, full common RNG schedule,
exact selected inventory, all applied/proposed command boundaries, six-foot
attribution and planned forcing passed. T_P replaced 14720 outgoing action
transitions, first at transition 5280 (528.0 ms, first affected state 528.1 ms).
The other 36 coordinates matched their native proposals exactly throughout.

| Measure | Tibia-only yoke | Full closed loop | All-command yoke |
|---|---:|---:|---:|
| Peak orientation deviation | 9.881202 deg | 12.798550 deg | 1.447819 deg |
| Mean orientation deviation | 3.725524 deg | 5.763657 deg | 0.453098 deg |
| Orientation integral | 5.513539 deg s | 8.529557 deg s | 0.670550 deg s |
| Peak root-position deviation | 0.372466 model mm | 0.466834 model mm | 0.048897 model mm |
| Peak height error | 0.130421 model mm | 0.195270 model mm | 0.024744 model mm |
| Peak linear-velocity error | 11.774171 model mm/s | 11.501194 model mm/s | 10.009844 model mm/s |
| Peak world angular-velocity error | 8.090276 rad/s | 6.950711 rad/s | 6.838539 rad/s |
| States below three ground contacts | 15 | 19 | 3 |
| Minimum ground contacts | 2 | 2 | 2 |
| Rollover / low-height states | 0 / 0 | 0 / 0 | 0 / 0 |
| Peak absolute tilt | 9.667409 deg | 7.323098 deg | 9.947980 deg |
| Sustained recovery in fixed window | NOT_RECOVERED_IN_WINDOW | NOT_RECOVERED_IN_WINDOW | NOT_RECOVERED_IN_WINDOW |

Each response/deviation column is relative to its own undisturbed control;
absolute tilt, support and rollover/low-height states describe the pushed body.
All baselines qualified, pulses resolved and relative recovery bands were exited.
The primary label is SELECTIVE_YOKING_REDUCES_RESPONSE: peak and mean differences
versus closed loop are -2.917348 and -2.038133 deg. Relative to all-command yoke,
the descriptive differences are +8.433382 and +3.272426 deg. These are different
coupled interventions, not additive channel contributions or percentages explained.

| Selected channel | Outgoing transitions with applied/proposed command difference |
|---|---:|
| LF tibia | 14385 |
| LM tibia | 14560 |
| LH tibia | 14425 |
| RF tibia | 0 |
| RM tibia | 14695 |
| RH tibia | 14720 |

Keep the RF tibia null exposure. It does not mean its motor neurons never spiked,
and no individual causal contribution for it is established by this group test.
The other motors can compensate, and changing the tibia commands changes later
sensory/neural history. This supports a group-level motor-application effect in
this context, not biological balance or an isolated-channel necessity claim.

Next: separately preregister the complementary group of all other 14 admitted
motor channels, defined by the fixed inventory complement rather than outcome
ranking, with paired disturbed/undisturbed controls. Keep the six tibias closed-
loop. That completes the group-level comparison before interpreting interactions
or planning individual-channel work. Preserve absolute tilt, velocity tradeoffs,
the RF tibia null and both earlier adverse/non-recovery results; no neural tuning.

## What this intervention tests

The six tibia channels were selected together from the existing M11 anatomical
mapping, not ranked by activity or outcomes. Exact action indices LF/LM/LH/RF/RM/RH
are 5/12/19/26/33/40 and must match the current 20-motor inventory. At each physical
transition, only those six command coordinates use the archived undisturbed
tactile-enabled command. The other 36 coordinates retain their native proposed
commands exactly, including the other 14 admitted motors. Neural computation,
tactile/proprioceptive input and all motor decoders stay active.

This extends the preceding full-action yoke to an anatomical group. Existing M11
zero-contribution ablation was inspected but would change the intervention type;
its mapping and effect/classification helpers are reused here. The shared kernel,
existing instance-local yoke, force callback, attribution and recovery metrics
remain in use. No competing physics loop, neural tuning or scripted controller.
The two fresh trials are unpushed T_C then pushed T_P; all old comparisons reuse
their complete verified saved evidence. No unchanged control is rerun solely to
duplicate previous science: T_C validates the new selective action boundary.

Raw physics `commanded_joints` records the actually applied action. Neural
`motor_telemetry.commanded_joint_targets` retains the native decoder proposal;
`proposed_joints` records that proposal at each outgoing physical action boundary.
Keeping these distinct makes the intervention auditable.
M11 helper labels retained inside the raw audit express signed metric differences;
their historical word "ablation" does not mean neurons or baseline commands were
zeroed here. The primary label explicitly describes selective command yoking.

Full fresh traces and source/raw/compressed hashes, environment, pre-execution
commit and complete evaluation are in `docs/evidence/tibia-command-dissection-v1/`.
Raw/gzip bytes are T_C 288858342 / 73174581 and T_P 285601700 / 72863885.
Environment: FlyGym 1.2.1 / MuJoCo 3.2.7 / NumPy 2.0.2. Both were actual coupled
CNS/physics runs, once each, distinct from synthetic implementation tests.
All historical scientific sources, raw evidence and expected locks are preserved.
Only the enlarged source-set check supersedes its inherited version; the full
inherited failure remains visible and every other strict requirement is required.
The old no-force rejection remains visible for pushed arms and is replaced only
by the unchanged exact planned-force audit. Integrity never requires benefit.

## Manual Git Bash checks

After the user merges this PR, update the primary checkout with:

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
git lfs pull --include="docs/evidence/matched-tactile-v1.json.gz,docs/evidence/tactile-recovery-v1/*.json.gz,docs/evidence/tactile-motor-yoke-v1/*.json.gz,docs/evidence/tibia-command-dissection-v1/*.json.gz"
"$PY" -m pytest -q -p no:cacheprovider tests/test_tibia_command_dissection.py
"$PY" -m malecns_backend.live.tibia_command_dissection --output-dir tibia-dissection-dry-review
echo $? # 1 / NOT_RUN; existing output directories are refused
```

The merge-style pull preserves known unpublished local commits without opening
a message editor. The archived test rechecks saved evidence and real TCP poses;
it does not rerun CNS/physics. Use a new directory name for the safe dry command.

For measured-pose Unity review, stop other publishers, keep the existing
`FlyBrainUnity/Assets/Scenes/LiveFly.unity` scene and run:

```bash
"$PY" -m malecns_backend.live.tibia_command_replay --manifest docs/evidence/tibia-command-dissection-v1/manifest.json --condition BOTH --speed 0.1
```

Wait for evidence validation and RECORDED, then enter Play. T_P (six tibias yoked,
other 14 motors closed-loop) and original ON_P (all 20 closed-loop) alternate for
about 20 wall seconds each. Tactile stays enabled. The pulse begins at saved
500 ms, about five wall seconds into a clip at this replay speed. REPLAY RESET
is a return to saved time zero, not a physical jump. Ctrl+C stops, --once performs
one cycle, --condition ALL adds T_C and the earlier all-command-yoked Y_P.
The shared prior replay helper retains its previous CLI and labels; this update
extracts its existing pose-stream loop for reuse. No Unity scene/controller changes
or Unity Editor validation by the agent.

Full focused regression command:

```bash
"$PY" -m pytest -q -p no:cacheprovider tests/test_tibia_command_dissection.py tests/test_tactile_motor_yoke.py tests/test_tactile_recovery.py tests/test_m9b_external_perturbation.py tests/test_matched_tactile_delivery.py tests/test_live_contact_context.py tests/test_six_foot_contact_calibration_v2.py tests/test_six_foot_contact_calibration.py tests/test_tactile_targeted_contact_calibration.py tests/test_live_contact_readiness.py tests/test_live_cli.py tests/test_live_headless.py tests/test_live_motor_diagnostics.py tests/test_live_pose_transport.py tests/test_tactile_propagation.py
"$PY" -m pytest -q -p no:cacheprovider tests/test_tactile_contact.py
```

The separate older tactile-contact suite retains the known metadata-artifact
hash mismatch (expected a8f8c045..., actual c8fdd337...). Do not refresh the hash.
Prior byte-preservation attributes prevent the previously diagnosed Windows CRLF
conversion; no historical scientific file content is changed here. Ordinary live
tactile remains disabled. One group intervention under one seed/pulse/window
cannot prove biological balance, intent, gait, isolated neuron/channel function,
or fully passive support; interactions and compensation remain possible.

Automated checks: 274 focused tests plus 9 subtests passed in 270.32 s, excluding
only the not-yet-produced new archive. After completion, the independent new
archive/reanalysis/actual-TCP test passed in 144.25 s: **275 tests total plus
9 subtests**. It verified full new/upstream hashes/source locks and recomputed
saved evaluations, then transmitted measured T_P/ON_P/Y_P endpoint poses over a
real local socket. Historical replay tests also passed after extracting the shared
stream helper. Synthetic boundary tests do not replace actual scientific evidence.
The separate legacy suite remains 6 passed / 1 unchanged artifact-hash failure.
Actual safe dry CLI returned 1 / NOT_RUN; whitespace checks passed. No scientific
retry, neural parameter change or Unity Editor validation was performed.
Manual expectations: 23 passing tests in the new test module; the full focused
command above yields 275 tests plus 9 subtests, with potentially several minutes
for complete saved-evidence verification. It never initializes a new CNS.
