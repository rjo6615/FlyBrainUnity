# Tactile motor-command yoke v1 — results and review

The protocol and scientific runner were committed at `220899c` before execution,
on a fresh branch from `origin/newBrain` at `b1d768e` (merged PR #260).
See [the prospective protocol](TACTILE_MOTOR_YOKE_V1.md).

**Integrity passed; yoking reduced the disturbance-relative orientation response.**
The undisturbed replay reproduced the complete original physical/contact/encoder
trajectory and all 4000 neural records exactly. The pushed replay replaced
14720 proposed action transitions, first at outgoing transition 5280 (528.0 ms;
first affected stored state 528.1 ms). Both fresh arms completed all 20000 physics
transitions / 4000 neural updates / 20001 saved states, with identical initial
state and history through 500 ms, common full-window RNG uniforms, tactile enabled,
exact archived applied commands and intact six-foot attribution. Each force audit
passed: no force in Y_C, exactly 200 Thorax-only nonzero observations in Y_P.

## Measured results

Both baselines qualified, pulses were resolved and relative bands exited. Each
column is the pushed response minus its own undisturbed control, except absolute
tilt/support/rollover/height observations, which describe the pushed body itself.

| Measure | Recorded baseline commands (Y_P vs Y_C) | Closed loop (ON_P vs ON_C) |
|---|---:|---:|
| Peak orientation deviation | 1.447819 deg | 12.798550 deg |
| Mean orientation deviation | 0.453098 deg | 5.763657 deg |
| Orientation integral | 0.670550 deg s | 8.529557 deg s |
| Peak root-position deviation | 0.048897 model mm | 0.466834 model mm |
| Peak height error | 0.024744 model mm | 0.195270 model mm |
| Peak linear-velocity error | 10.009844 model mm/s | 11.501194 model mm/s |
| Peak world angular-velocity error | 6.838539 rad/s | 6.950711 rad/s |
| States with fewer than three ground contacts | 3 | 19 |
| Minimum ground contacts | 2 | 2 |
| Rollover / low-height states | 0 / 0 | 0 / 0 |
| Peak absolute tilt | 9.947980 deg | 7.323098 deg |
| Sustained recovery within two seconds | NOT_RECOVERED_IN_WINDOW | NOT_RECOVERED_IN_WINDOW |

The prospective label is YOKING_REDUCES_RESPONSE. Yoked-minus-closed peak and mean
orientation differences are -11.350731 and -5.310559 degrees. Reused contrast keys
named on_minus_off mean yoked-minus-closed here, as the recorded estimand states.

This supports a causal contribution of disturbance-contingent motor-command
application to the larger orientation departure in this modeled context. It
does **not** show that all closed-loop activity is harmful: closed loop had lower
peak absolute tilt. Nor does it show that a completely passive body would remain
upright: baseline active commands and their mechanical support remain in Y_P.
Neither condition achieved sustained recovery, and no biological balance, intent,
gait or individual-channel function is established. No post-outcome tuning or retry.

Next: separately preregister a focused dissection of the admitted motor-command
changes using the existing M11 intervention infrastructure adapted to this exact
20-motor tactile context, including both disturbed and undisturbed controls.
Choose channels from mapping/provenance and a declared rule before new outcomes;
do not select a winner from exploratory runs or alter neural parameters. Track
absolute tilt and disturbance-relative response separately. Ordinary live tactile
should remain off until its limitations and intervention effects are understood.

## What this control changes

Both fresh arms retain tactile input, CNS computation, sensory encoding and motor
decoding. Immediately before each physical transition, the proposed joint action
is replaced with the exact same-transition command from the archived undisturbed
tactile-enabled trial. This preserves time-varying baseline actuation while
preventing disturbance-contingent commands from changing the applied motor action.
It does not make the body completely passive. No measured joint angle is used as
a command, no interpolation or new controller is introduced, and no physiological,
collision, encoder, gain, seed or pulse parameter is tuned.
The existing M11 contribution-ablation mechanism was inspected; zeroing decoded
contributions is a different intervention from exact full-action replay. This
adapter wraps only this simulation instance's existing step boundary and still
calls the same native simulation and scientific kernel once per transition.

Y_C replays without a push and must exactly reproduce the entire original control.
Y_P receives the same fixed 500..520 ms thorax pulse as prior ON_P. Analysis compares
Y_P against Y_C and the original ON_P against ON_C with unchanged recovery metrics.
The new-source-set equality requirement explicitly supersedes the inherited
source-list check, whose failure remains visible in full raw audits. All other
strict checks, including exact planned forcing and six-foot attribution, remain.

Full fresh gzip JSON traces and the manifest are under
`docs/evidence/tactile-motor-yoke-v1/`. Raw and compressed hashes, source locks,
environment, exact commands, proposed commands, actual forces, neural records and
full evaluation are preserved. No prior results or local user edits are replaced.
Raw/gzip bytes: Y_C 288857382 / 73174215; Y_P 288832991 / 73488681.
Environment: FlyGym 1.2.1 / MuJoCo 3.2.7 / NumPy 2.0.2. These are actual coupled
CNS/physics experiments, distinct from synthetic boundary tests.

## Manual Git Bash checks

After the user merges the PR, update the primary checkout with
`git switch newBrain` and `git pull --no-rebase --no-edit`. This preserves its
unpublished local commits and avoids opening a merge-message editor; a
fast-forward-only pull cannot integrate that known divergent local history.

From this PR checkout (or the primary checkout after the user merges and pulls):

```bash
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
git lfs pull --include="docs/evidence/matched-tactile-v1.json.gz,docs/evidence/tactile-recovery-v1/*.json.gz,docs/evidence/tactile-motor-yoke-v1/*.json.gz"
"$PY" -m pytest -q -p no:cacheprovider tests/test_tactile_motor_yoke.py
"$PY" -m malecns_backend.live.tactile_motor_yoke --output-dir motor-yoke-dry-review
echo $? # 1 / NOT_RUN, directory must be new
```

The archived test recomputes complete saved evidence and sends actual poses over
a real local TCP socket. It does not run CNS/physics. Initial evidence validation
takes time and requires materialized LFS objects.

For Unity review, stop other pose publishers and use the existing
`FlyBrainUnity/Assets/Scenes/LiveFly.unity` scene:

```bash
"$PY" -m malecns_backend.live.tactile_motor_yoke_replay --manifest docs/evidence/tactile-motor-yoke-v1/manifest.json --condition BOTH --speed 0.1
```

Wait for validation and RECORDED, then enter Play. Y_P (undisturbed commands
applied despite the push) and original ON_P (closed-loop commands applied) each
show two simulated seconds over about 20 wall seconds, repeating until Ctrl+C.
Tactile input stays enabled in both. The terminal labels the pulse at saved
500 ms and its end at 520 ms. REPLAY RESET is a return to saved time zero,
not a physical jump. Use `--condition Y_C` for the unpushed transport control or
`--once` for one cycle. No Unity Editor validation was performed by the agent;
the existing output-only protocol and measured poses are reused.

Full focused regression command:

```bash
"$PY" -m pytest -q -p no:cacheprovider tests/test_tactile_motor_yoke.py tests/test_tactile_recovery.py tests/test_m9b_external_perturbation.py tests/test_matched_tactile_delivery.py tests/test_live_contact_context.py tests/test_six_foot_contact_calibration_v2.py tests/test_six_foot_contact_calibration.py tests/test_tactile_targeted_contact_calibration.py tests/test_live_contact_readiness.py tests/test_live_cli.py tests/test_live_headless.py tests/test_live_motor_diagnostics.py tests/test_live_pose_transport.py tests/test_tactile_propagation.py
```

Preserve the documented older tactile-contact artifact hash failure. Neither its
expected hash nor artifact is changed by this protocol. Ordinary live tactile
mode remains disabled. No single pulse, seed or engineering return band proves
biological balance, intent, gait, or the necessity of baseline active actuation.

The initial fresh-Windows-worktree matrix reported 245 passed / 2 failed plus
9 subtests. Both failures were existing raw-byte locks encountering CRLF checkout
conversion. All three relevant original Git blobs matched the unchanged expected
hashes; stripping only CRLF from checkout copies matched too. After scientific
execution ended, five provenance-sensitive checkout files were restored to their
exact original Git blob bytes. `.gitattributes` now preserves those bytes in
future checkouts, including two additional legacy provenance files. Their Git
content and all expected hashes remain unchanged. The separate historical
metadata mismatch still reports 6 passed / 1 failed in `test_tactile_contact.py`
(expected a8f8c045... versus actual c8fdd337..., unchanged origin/newBrain content).
Actual dry CLI returned 1 / NOT_RUN; exclusive output and partial/error behavior
are tested. No scientific retries or duplicate physics runs were performed.

Final full focused matrix: **252 passed, 9 subtests passed in 220.18 s**, including
full new and historical archive/source/hash re-evaluation and real TCP transmission
of actual saved Y_P/ON_P endpoint poses. The two checkout-byte failures are resolved
without changing scientific Git content or expected hashes. Whitespace checks pass.
Manual expectations: 19 tests pass in `test_tactile_motor_yoke.py`; the full command
above yields 252 tests plus 9 subtests. The separate legacy suite remains 6 passed /
1 historical artifact failure. Synthetic boundary tests are not scientific physics.
