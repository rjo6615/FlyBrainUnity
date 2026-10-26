# Balance V1.1 completed native result and Unity checkpoint

2026-10-26: the single prospective V1.1 run at committed source d05a2dd
completed NC/WC/NP/WP: **80,000 physics transitions, 16,000 neural updates,
80,004 saved states**. Each arm has 20,001 states and 4,000 neural updates.
All nine original integrity groups pass; status COMPLETE / INTEGRITY_ACCEPTED,
unity_replay_eligible=true. This supersedes the pre-run checkpoint below.

[Raw record and report](evidence/balance-contribution-process-v1_1/run-desktop-01/report.json),
[concise measured result](evidence/balance-contribution-process-v1_1/run-desktop-01/accepted-result-summary.json)
and [packet verification](evidence/balance-contribution-process-v1_1/run-desktop-01/replay-verification.json)
are preserved. Every arm used a fresh process with an empty original registry,
measured Windows venv ancestry and unchanged original source/protocol guards.
The original failed V1 attempt remains separate and unchanged. No retry occurred.

Behavior: **MIXED_OR_UNRESOLVED**. In the fixed cleared window, NP mean absolute
tilt was 3.8505 degrees versus WP 4.3072; peak 4.2674 versus 4.3491 degrees.
The peak difference is below the declared 0.25 degree resolution. Relative to
its own matched control, NP had larger disturbance and later sustained-band
return (entry 613.5 ms, confirmation 713.5 ms) than WP (520.1 / 620.1 ms).
All arms had zero rollover, low-height or fewer-than-three-support samples.
These are one-seed, two-second, position-assisted observations. They do not
establish independent balance, walking or general neural benefit. Coverage
remains 20/42; zero new motor admissions.

The native command exited 1 only at its final console print: NumPy int64 could
not be serialized, AFTER the complete accepted report had been saved. This
presentation error is preserved in the summary. The executed source remains
unchanged; a separate balance_contribution_console.py wrapper fixes reporting
and has three synthetic tests passing in 0.42 s. No scientific rerun was used.

The separate replay adapter/existing transport suite passed **24 tests in
1.66 s**. Offline reconstruction matched the saved evaluation and validated
all **80,004 actual pose packets**, with native imports and CNS construction
forbidden. These are engineering/display checks, separate from the real native
experiment. All 42 recorded coordinate addresses are resolved from the native
inventory; the tested neural contribution still covers only 20 coordinates.

Unity 6000.3.10f1 opened the existing LiveFly scene and entered Play. TCP
connected, rig binding reported 64/64, counters advanced, and recorded poses
were visibly applied. Play was stopped after observation. The default camera
crops the upper body, so full-body visual balance review is still pending camera
framing. Cold import reported missing Blender imports; they did not block this
scene's Play/connection. No Unity source or scene changes are included.
[Sanitized visual record](evidence/balance-contribution-process-v1_1/run-desktop-01/unity-visual-check.json).
Raw local editor logs are ignored because they include machine/licensing details.

**Unity distance:** accepted recorded balance data and a working scene connection
are available now. Next: frame the complete fly for human review. Independent
neural balance and a live Unity/CNS balance experiment remain later milestones.
[Replay commands and expected behavior](BALANCE_CONTRIBUTION_UNITY_REPLAY_V1.md).

Changed files in this delivery: balance_contribution_replay.py and
balance_contribution_console.py; their two test files; replay engineering and
native raw/receipt/report/verification evidence; this result document, replay
guide, handoff, roadmap and .gitignore for the private local editor log.
The 72-test frozen implementation check below remains the pre-native record.

## Historical implementation checkpoint (before the native run)


2026-10-26. Engineering validation: **72 passed in 106.78 s**. Native execution
status at this implementation commit: **NOT_RUN**. Results will be added to this
checkpoint after the prospective run; the frozen specification stays unchanged.

The new `malecns_backend/live/balance_contribution_process.py` isolates every
fixed arm in a fresh process and delegates the complete native/CNS session and
per-arm audits to unchanged V1 code. It measures OS ancestry, including Windows'
venv redirector, checks an empty original FlyGym registry without modifying it,
preserves logs/claims/raw partial evidence, and stops without retry on failure.
Offline comparison loads one raw arm at a time, keeping every original strict
prefix/RNG/identity check and the same behavioral analysis. No gains, weights,
thresholds, signs, maps, force, seed, clocks, range/slew or assistance changes.

[Prospective V1.1 specification](BALANCE_CONTRIBUTION_PROCESS_V1_1.md) and
[machine-readable protocol](evidence/balance-contribution-process-v1_1/protocol.json)
justify a fresh four-arm attempt after V1's name-registry implementation failure.
The failed V1 record remains intact and supplies no reused control.

The final focused suite includes process-boundary tests, full synthetic null
equivalence with the original auditor/analysis, fresh OS child launches with
fake registry/data (zero native/CNS models), graceful-stop and incomplete/error
rejection, actual calibrated JS/Python parity, original neural runtime tests and
six real checkout-byte regressions. These tests do not establish native success
or balance. [Engineering record](evidence/balance-contribution-process-v1_1/engineering-checks.json)
also preserves 22 initial passes, 8 smoke-subset passes and a 66-pass/2-failure
run invalidated when the protocol document was edited during source-hash checks.
The source guard was retained; source/protocol were frozen for the final72pass.

Unity gates: environment/reference checks passed; process implementation tests
passed; complete four-arm native integrity pending; verified saved-pose adapter
using existing Unity transport pending. Valid null/negative/unrecovered behavior
can be displayed after integrity. This is an assisted20-coordinate contribution
test, not independent balance or walking. Motor coverage20/42;0new admissions.

Changed files: new process driver and `tests/test_balance_contribution_process.py`;
prospective specification/protocol; this result document; engineering check
record; `.gitattributes` for exact new evidence/LFS arms; handoff and roadmap.
Original V1 code, prospective design, historical evidence and locks are unchanged.

After user merge, Windows Git Bash engineering checks:

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain && git pull --no-rebase --no-edit
PY="$HOME/Documents/FlyBrainUnity/.cache/malecns-balance-python312-v1/Scripts/python.exe"
"$PY" -m pytest -q -p no:cacheprovider \
  tests/test_balance_contribution_process.py tests/test_balance_contribution.py \
  tests/test_neural_runtime.py tests/test_calibrated_neural_parity.py \
  tests/test_balance_checkout_locks.py
```

Expected:72passes in the pinned environment, with original hydrated sources and
Node available. No native scientific execution is authorized by this test block.
Any scientific run uses a new exclusive namespace after committed sources and
original prerequisites. Preserve all outputs; no automatic retries/resume.
