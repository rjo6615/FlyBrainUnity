# Complementary motor-command group v1 — results and review

Protocol, scientific runner and boundary tests were committed at `939459a` before
new scientific execution, on a fresh branch from latest `origin/newBrain`
`2b1111e4dad1e8a39b1c359270f3b438ff257460` (merged PR #262). See
[the prospective specification](COMPLEMENT_COMMAND_DISSECTION_V1.md).

**All integrity checks passed. Complementary-group replay reduced disturbance-
relative orientation departure while increasing absolute peak tilt and peak
velocity errors. Sustained recovery was not achieved.** No neural parameter,
channel selection, force or acceptance rule was changed after outcomes.

## Measured outcomes

Each fresh arm completed 20000 physics transitions / 4000 neural updates /
20001 states. C_C exactly reproduced the complete archived undisturbed physical/
contact/encoder trajectory and all neural records, with zero command changes.
Initial/model identity, pre-push history through 500 ms, common full-window RNG,
exact 14-channel inventory, every applied/proposed boundary, six-foot attribution
and planned force passed. All 28 nonselected coordinates stayed exactly native.
C_P changed 14720 outgoing actions, first at transition 5280 (528.0 ms, first
affected state 528.1 ms). Both baselines qualified; the pulse resolved and relative
bands were exited. All listed post-force metrics use the unchanged fixed window.

| Measure | Complement only | Tibia only | Full closed loop | All-command yoke |
|---|---:|---:|---:|---:|
| Peak orientation deviation (deg) | 6.094436 | 9.881202 | 12.798550 | 1.447819 |
| Mean orientation deviation (deg) | 2.337358 | 3.725524 | 5.763657 | 0.453098 |
| Orientation integral (deg s) | 3.459178 | 5.513539 | 8.529557 | 0.670550 |
| Peak root-position deviation (model mm) | 0.202228 | 0.372466 | 0.466834 | 0.048897 |
| Peak height error (model mm) | 0.080224 | 0.130421 | 0.195270 | 0.024744 |
| Peak linear-velocity error (model mm/s) | 19.454490 | 11.774171 | 11.501194 | 10.009844 |
| Peak world angular-velocity error (rad/s) | 7.866206 | 8.090276 | 6.950711 | 6.838539 |
| States below three ground contacts | 10 | 15 | 19 | 3 |
| Minimum ground contacts | 2 | 2 | 2 | 2 |
| Rollover / low-height states | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Peak absolute tilt (deg) | 14.781105 | 9.667409 | 7.323098 | 9.947980 |
| Sustained recovery within two seconds | No | No | No | No |

Deviation/error is pushed minus the corresponding undisturbed control. Tilt,
contact counts and rollover/low-height observations describe the pushed body
itself. Every recovery status is NOT_RECOVERED_IN_WINDOW. No metric is combined
into a favorable composite score.

The prospective primary label is SELECTIVE_YOKING_REDUCES_RESPONSE, with peak/
mean differences versus full closed loop -6.704114/-3.426299 deg. Descriptive
differences versus tibia-only are -3.786765/-1.388166 deg, and versus all-command
yoke +4.646617/+1.884260 deg. These are coupled policy comparisons, not additive
or independent channel effects and not percentages explained.

Full closed loop has the lowest observed absolute peak tilt of the tested
policies, while having the largest orientation departure from its moving
undisturbed control. This supports a motor-application contribution to posture
under this modeled pulse, while the overall tradeoffs and lack of recovery
preclude a general balance/gait claim. Baseline active actuation remains in every
yoked trial; fully passive support was not tested. No intent is established.

| Selected channel | Outgoing transitions with applied/proposed command difference |
|---|---:|
| LF Femur | 14475 |
| LM Femur | 14675 |
| LH Femur | 13265 |
| RM Femur | 14695 |
| RH Femur | 14605 |
| LF Femur_roll | 14720 |
| LM Femur_roll | 13870 |
| LH Femur_roll | 8830 |
| RF Femur_roll | 1210 |
| RM Femur_roll | 14675 |
| RH Femur_roll | 14205 |
| RF Femur | 14575 |
| LF Tarsus1 | 14310 |
| RF Tarsus1 | 0 |

Preserve RF Tarsus1 zero command-intervention exposure, as well as the earlier
RF tibia null. Neither establishes silent neurons or an individual causal role.
These are command-difference counts, not spike counts or channel-effect rankings.

Next: separately preregister a time-aligned analysis of the four frozen group
contexts using existing saved root poses, world tilt, velocities, contacts and
commands. Explain how absolute posture and disturbance-relative metrics differ;
declare any vector-valued interaction estimand before calculating it. No new
physics is needed for that analysis. Use it to choose the next roadmap step
without neural tuning, outcome-ranked channel searches or new runs until benefit.

## Intervention and evidence

Select the 14-motor complement of the six previously tested tibias, using exact
v3/M11 mapping and a fixed inventory rule rather than activity/effect ranking:
six femurs, six femur-roll channels, LF/RF Tarsus1. At each physical transition,
only those coordinates use the archived undisturbed tactile-enabled commanded
action. Other 28 coordinates, including all six tibias, retain their current
native proposals exactly. All CNS, sensory, readout and decoder computation stays
active. Baseline active actuation remains; this is not a fully passive body.

Fresh order is unpushed C_C then pushed C_P. Same two-second window, seed, Thorax
pulse, support/collisions, physiology, encoders and metrics as preceding work.
Reuse the validated yoke/kernel and M11 helpers; no competing physics loop,
scripted controller, neural tuning, adaptive selection or retry. C_C validates
the new selective boundary through exact full-control reproduction. All previous
comparison records are hash/source/evaluation-verified and reused without new
duplicate scientific runs. Ordinary live tactile delivery stays disabled.

Physical `commanded_joints` is the actual applied action; per-state
`proposed_joints` and neural `motor_telemetry.commanded_joint_targets` retain
native proposals. Full raw records, source/raw/compressed hashes, environment,
pre-execution commit and all checks are under
`docs/evidence/complement-command-dissection-v1/`. Previous raw evidence, failed/
adverse findings and hashes remain unchanged. Full inherited audits stay visible;
only their source-set requirement is explicitly superseded by the enlarged set.
The historical no-force rejection remains visible in pushed arms and is replaced
only by the unchanged exact planned-force audit. All other strict checks remain.

Raw/gzip bytes: C_C 288859194 / 73174873; C_P 290340587 / 73732066.
Environment: FlyGym 1.2.1 / MuJoCo 3.2.7 / NumPy 2.0.2. These were actual coupled
CNS/physics experiments, once per condition, distinct from synthetic tests.

## Manual Git Bash commands

After the user merges this PR, stop previous replay publishers with Ctrl+C:

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
git lfs pull --include="docs/evidence/**"
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
"$PY" -m malecns_backend.live.complement_command_replay --manifest docs/evidence/complement-command-dissection-v1/manifest.json --condition BOTH --speed 0.1
```

The merge-style pull preserves known unpublished local commits without opening
the message editor. LFS include pattern was verified against actual nested evidence
paths. Validation may take several minutes; it recomputes saved checks and does
not initialize CNS or run physics. Once RECORDED appears, enter Play in the existing
`FlyBrainUnity/Assets/Scenes/LiveFly.unity` scene, with one publisher on port 8765.

C_P (14 complementary motors replayed, six tibias closed-loop) and original ON_P
(all 20 closed-loop) alternate for about 20 wall seconds each. Tactile remains
enabled. Pulse starts at saved 500 ms, about five wall seconds into each clip.
REPLAY RESET is saved time zero, not a physical jump. Ctrl+C stops; --once is one
cycle; --condition ALL includes C_C, earlier tibia-only T_P and all-command-yoked
Y_P. Measured poses use the existing shared replay loop/output-only protocol;
no Unity scene/controller changes or agent Unity Editor validation.

Safe regression/dry checks from this checkout:

```bash
"$PY" -m pytest -q -p no:cacheprovider tests/test_complement_command_dissection.py
"$PY" -m malecns_backend.live.complement_command_dissection --output-dir complement-dissection-dry-review
echo $? # 1 / NOT_RUN; directory must be new, existing outputs are refused
"$PY" -m pytest -q -p no:cacheprovider tests/test_complement_command_dissection.py tests/test_tibia_command_dissection.py tests/test_tactile_motor_yoke.py tests/test_tactile_recovery.py tests/test_m9b_external_perturbation.py tests/test_matched_tactile_delivery.py tests/test_live_contact_context.py tests/test_six_foot_contact_calibration_v2.py tests/test_six_foot_contact_calibration.py tests/test_tactile_targeted_contact_calibration.py tests/test_live_contact_readiness.py tests/test_live_cli.py tests/test_live_headless.py tests/test_live_motor_diagnostics.py tests/test_live_pose_transport.py tests/test_tactile_propagation.py
"$PY" -m pytest -q -p no:cacheprovider tests/test_tactile_contact.py
```

The separate legacy suite retains 6 passed / 1 unchanged metadata artifact-hash
failure (expected a8f8c045..., actual c8fdd337...). No lock/artifact refresh or
historical source change. Synthetic tests are distinct from actual CNS/physics;
the archived test rechecks full evidence and real TCP measured-pose delivery.
One pulse/seed/window and engineering metrics do not establish intention,
biological balance/gait, fully passive support or individual-channel function.
Group effects can be non-additive; do not assign fractions explained or individual
causal roles from differences in peak norms. Preserve the earlier RF tibia null.

Actual checks: 297 focused tests plus 9 subtests passed in 472.02 s, excluding
only the not-yet-produced new archive. The final independent new/upstream archive,
analysis and real TCP test passed in 176.84 s: **298 tests total plus 9 subtests**.
It rechecked full source/raw/compressed hashes and saved evaluations and sent
actual C_P/T_P/ON_P/Y_P endpoint poses over a local socket. The new module alone
has 23 passing tests; the full manual matrix above yields 298 plus 9 subtests.
The separate legacy suite remains 6 passed / 1 unchanged historical metadata
hash failure. Real dry CLI returned 1 / NOT_RUN; replay --help imported and showed
all documented choices; whitespace checks passed. No duplicate scientific runs,
dependency changes, neural tuning, weakened acceptance or agent Unity Editor run.
