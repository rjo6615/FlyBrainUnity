# Balance V1.1 process-boundary implementation and run checkpoint

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
