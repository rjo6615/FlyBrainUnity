# Tactile disturbance and recovery v1 — results

The prospective protocol and scientific implementation were committed at
`ce2dde9613c129c0ea50b4067469786ebf389f34` before execution, from latest
`origin/newBrain` baseline `b0a94c6ba484b301db4cf5fbddc618235fcbba20`.
See [the protocol](TACTILE_DISTURBANCE_RECOVERY_V1.md) for the fixed criteria.

All integrity checks passed. **Continued tactile delivery amplified the orientation
response to this pulse; neither pushed condition recovered within the fixed
two-second window.** This is a preserved adverse functional result, not a failed
implementation to be tuned into a pass. Apparent visual steadiness is insufficient
evidence of useful balance.

## Measured outcomes

Each fresh arm completed 20000 physics transitions / 4000 neural updates and saved
20001 states. Initial states and every physical/neural observation through 500 ms
matched the archived control exactly. Full-window common RNG schedules matched;
withdrawal first affected eligible tactile events at 500.5 ms. OFF_C withheld
49235 eligible events; OFF_P withheld 42944. Each pushed arm had exactly 200
Thorax-only force observations, zero torque and impulse [0, 0.02048, 0] native
force seconds. All six-foot contact attribution checks passed, with no ambiguous
or calibration-surface positive sources.

Both baselines qualified, both pulses resolved, and both relative recovery bands
were exited. Values below compare each pushed arm with its corresponding
phase-matched undisturbed control over the fixed cleared-force window:

| Measure | Continued tactile | Withdrawn tactile |
|---|---:|---:|
| Peak orientation deviation | 12.798550 deg | 3.418028 deg |
| Mean orientation deviation | 5.763657 deg | 1.340016 deg |
| Orientation integral | 8.529557 deg s | 1.983143 deg s |
| Peak root-position deviation | 0.466834 model mm | 0.094719 model mm |
| Peak height error | 0.195270 model mm | 0.033139 model mm |
| Peak linear-velocity error | 11.501194 model mm/s | 9.273767 model mm/s |
| Peak world angular-velocity error | 6.950711 rad/s | 6.367194 rad/s |
| States with fewer than three exact ground contacts | 19 | 0 |
| Minimum exact ground-contact count | 2 | 3 |
| Rollover / low-height states | 0 / 0 | 0 / 0 |
| Peak absolute tilt | 7.323098 deg | 4.616602 deg |
| 100 ms sustained recovery | NOT_RECOVERED_IN_WINDOW | NOT_RECOVERED_IN_WINDOW |

The prospective orientation label is AMPLIFIED_ORIENTATION_RESPONSE_WITH_TACTILE:
peak and mean increased by 9.380522 and 4.423642 degrees, respectively. The peak
root-position difference-in-differences norm was 0.476549 model mm. Orientation
deviation from a moving control is different from absolute tilt, explaining why
the body may still look fairly upright. Nineteen low-support observations are
discrete sampled states, not an asserted single continuous event.

This establishes a modeled disturbance-specific tactile-delivery effect for one
seed, pulse and window. It does not establish beneficial balance, gait, biological
transduction fidelity, or an active motor mechanism independent of passive
mechanics. The engineering recovery bands were fixed before execution; no force,
acceptance, seed, duration or neural parameter was changed afterward. No retries.

Immediate next task: review these recorded pushed/control clips, then separately
preregister a motor-application control to distinguish neural motor application
from passive mechanics and withdrawal effects. Specify replayed motor-command
provenance, matched pre-push state, random schedule and disturbance/control
comparisons before running it. Do not enable ordinary live tactile, tune the
neural model or increase the pulse in response to this adverse result.

## Design and evidence

All four cells share tactile-enabled neural and physical history through 500 ms.
ON_C reuses the verified archived matched-pair ENABLED control. OFF_C, OFF_P and
ON_P are three fresh, fixed two-second trials, run once in that order. OFF cells
withdraw tactile delivery from 500.5 ms. P cells receive the historical M9B
world-axis thorax pulse [0, 1.024, 0] during outgoing transitions 5000..5199.
Each pushed response is compared with its own undisturbed tactile control.

No physiological, encoder, gain, mapping, collision, support or random-seed
parameter was tuned. The existing kernel, input mask and force callback were
reused. The prior no-force context audit is unchanged and its expected forced-arm
rejection remains in the manifest; this version replaces that one requirement
with a complete exact planned-wrench audit. Every other strict check remains.
Ordinary live tactile delivery is still disabled.

Raw fresh arms are preserved separately under `docs/evidence/tactile-recovery-v1/`
as Git LFS gzip JSON; `manifest.json` records full checks, source locks, raw and
compressed hashes, environment, control reference and outcomes. The archived
ON_C record remains `docs/evidence/matched-tactile-v1.json.gz`; no old evidence
was overwritten. Local edits and unpublished primary-checkout commits are preserved.

Fresh archive raw/gzip byte counts: OFF_C 277895240 / 73255319;
OFF_P 278347838 / 73043746; ON_P 271851465 / 72465416. Their complete hashes and
evaluation are in the manifest. Validated environment: FlyGym 1.2.1, MuJoCo 3.2.7,
NumPy 2.0.2. These were actual coupled CNS/physics runs, not mocks.

Automated verification: 232 focused regression tests plus 9 subtests passed;
the final archived-recovery verification/TCP test passed separately (233 total
tests). The latter verified all raw/compressed hashes, recomputed the full saved
analysis and transmitted actual saved endpoint poses through a real local socket.
Synthetic tests exercise force identity/timing/torque/hidden-force defects,
withdrawal timing, full prefix matching, world-frame angular velocity, recovery
dwell and non-recovery, immutable output and partial nonfinite evidence. They are
implementation tests, distinct from the three actual scientific runs. The real
dry CLI returned 1 / NOT_RUN; whitespace checks passed. The separate unchanged
legacy failure is detailed below. No Unity Editor visual validation was executed.

## Manual Git Bash review

From this PR checkout, or the primary checkout after the user merges and pulls:

```bash
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
git lfs pull --include="docs/evidence/matched-tactile-v1.json.gz,docs/evidence/tactile-recovery-v1/*.json.gz"
"$PY" -m pytest -q tests/test_tactile_recovery.py
```

This verifies saved hashes, recomputes full analysis, exercises synthetic defects
and sends actual recorded endpoint poses over TCP. It does not rerun physics/CNS.
Use the existing `FlyBrainUnity/Assets/Scenes/LiveFly.unity` scene, with only one
publisher on port 8765:

```bash
"$PY" -m malecns_backend.live.tactile_recovery_replay --manifest docs/evidence/tactile-recovery-v1/manifest.json --condition PUSHED --speed 0.1
```

Wait for validation and the RECORDED message, then enter Unity Play. OFF_P and
ON_P each show two simulated seconds over about 20 wall seconds, repeating until
Ctrl+C. Terminal labels indicate tactile withdrawal and pulse timing. Each
`REPLAY RESET` returns to saved time zero; the clip transition is not physical
jumping. Watch the motion after the 500 ms pulse and continued ground support;
visual stability alone cannot establish active balance. `--condition ALL` includes
the two undisturbed controls; `--once` stops after one cycle. These are measured
poses over the existing output-only protocol. No Unity scene/controller changes.

Safe dry CLI check, using a fresh directory name:

```bash
"$PY" -m malecns_backend.live.tactile_recovery --output-dir tactile-recovery-dry-review
echo $? # 1, NOT_RUN; existing output directories are refused
```

Full focused regression command:

```bash
"$PY" -m pytest -q tests/test_tactile_recovery.py tests/test_m9b_external_perturbation.py tests/test_matched_tactile_delivery.py tests/test_live_contact_context.py tests/test_six_foot_contact_calibration_v2.py tests/test_six_foot_contact_calibration.py tests/test_tactile_targeted_contact_calibration.py tests/test_live_contact_readiness.py tests/test_live_cli.py tests/test_live_headless.py tests/test_live_motor_diagnostics.py tests/test_live_pose_transport.py tests/test_tactile_propagation.py
"$PY" -m pytest -q tests/test_tactile_contact.py
```

Expected focused result: 233 tests plus 9 subtests pass. The archived-evidence
checks take time and require materialized LFS objects; they do not initialize CNS.

The separate legacy tactile-contact command still reports 6 passed / 1 failed:
expected artifact hash `a8f8c0451f615cd3632ffc2730893ab7aedc3448a9745416bcaf6d4543454090`,
actual `c8fdd337d6c416c45edafdc615a1f7d2b4cfeb2c32c446150b59140057ddac63`.
This pre-existing failure is documented in the matched-delivery predecessor:
commit d03f2a6 added live metadata without changing biological populations.
Neither the old artifact nor its expected hash was revised.

The scientific live command is documented in the preregistration for an explicitly
planned independent replication. Do not rerun the unchanged experiment to seek
recovery. One seed/pulse/window and engineering bands cannot prove biological
balance, gait, or passive-versus-active motor causation. Unity Editor itself was
not run by the agent.
