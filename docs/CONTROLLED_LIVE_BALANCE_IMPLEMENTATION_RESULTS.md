# Controlled live balance implementation and execution checkpoint

2026-10-26. New schema controlled-live-balance-execution-v1 implements the fixed
prospective live design without editing frozen V1/V1.1 science/specification or
historical results. Dedicated controller/worker plus instance-local LiveObserver;
existing Trial/create_session/ScientificSession/kernel/recorders/auditors and
PoseServer/wire/conversion reused. All42position actuators retain assistance;
20admitted neural motor coordinates,392proprio input, tactile OFF.

## Engineering validation before native execution

Broader original/new suite:114passed in181.06s. Initial new suite33passed/1failed
in39.36s: Windows resets a connection closed with unread rejected client bytes;
test now accepts EOF or ConnectionResetError, retaining the input rejection and
unchanged-science assertions. Server behavior unchanged. Two final stop/cleanup
regressions added; targeted suite37passed in37.72s before final source-lock audit.
Final source-lock validation is recorded in engineering-checks.json.

These use synthetic sessions/miniature neural fixtures and actual OS child,
ancestry/registry and socket checks. They are not native fly/full-connectome
experiments. Coverage includes exact/permuted native projection and existing
saved-replay equivalence, incomplete/invalid/source rejection, fixed20,000-step
and4,000-update terminal semantics, full old-auditor/behavior equivalence on a
synthetic null, no-client/slow-client/input rejection, listener/transport faults,
no global factory mutation, stop-before-initialize, partial/error preservation,
same-interpreter fresh OS workers and no retry. A failed display remains separate
from original scientific integrity and never changes the physics schedule.

Original construction-free prerequisite checks now pass: expected package versions,
static authorities, original calibration/data identities. Missing M6C/context LFS
payloads and excluded graph/reference NPZs were hydrated by their original IDs in
the isolated worktree. No locks, data, environment packages or parameters changed.
Earlier missing-pointer/data refusals remain in tool output. engineering-preflight-01
and02 retain NOT_RUN development-source snapshots with valid original prerequisites;
they are not scientific runs or current-source accepted assay reports.

User confirmed the whole fly/all feet were visible in the accepted replay with no
unexpected visual issue, then confirmed Unity in Play and the previous replay
stopped. These are user observations, not a new agent Unity visual measurement.
The implementation must be committed before ONE native run-desktop-01 attempt.

## Native execution

Pending at this implementation commit. The results/handoff will be updated after
the one fixed attempt. Preserve any failure/partial data without retry or tuning.
No favorable behavioral outcome is required; stability alone cannot establish
independent neural balance. Live poses are provisional until full offline audit.

## Changed files

- malecns_backend/live/controlled_live_balance.py: fresh process/controller,
  fixed lifecycle, exclusive evidence, original scientific audit and reference
  comparison under an explicit new report schema; default preflight only.
- malecns_backend/live/balance_live_observer.py: checked existing server,
  native-address projection, exact wire journal and separate display audit.
- tests/test_controlled_live_balance.py: synthetic/OS/socket regressions.
- CONTROLLED_LIVE_BALANCE_IMPLEMENTATION_V1.md: frozen prospective execution contract.
- This document, handoff and roadmap: actual progress and commands.
- .gitattributes and new engineering/preflight evidence: exact bytes and receipts.

## Windows Git Bash engineering checks after merge

```bash
cd "$HOME/Documents/FlyBrainUnity" &&
git switch newBrain &&
git pull --no-rebase --no-edit &&
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" &&
"$PY" -m pytest -q -p no:cacheprovider tests/test_controlled_live_balance.py
```

Expected:37engineering tests pass, no native fly experiment. Default --output
also runs construction-free preflight only, into an exclusive directory. Native
execution is separately gated by --live, a truthful --review-note, all original
prerequisites and committed sources. Do not rerun the bounded campaign after
the delivered record exists. Instructions for saved evaluation will follow the
actual execution checkpoint. Old balance_contribution_replay deliberately rejects
the new execution schema; its gate was not weakened. Existing accepted V1.1
replay stays available through the previous documented command.

Roadmap:recorded assay and full-body review done; live adapter/engineering done;
one bounded live attempt next. Coverage20/42,0new admissions; independent balance
and walking unproven. The current test retains position assistance. Its removal
or reduction needs a separate prospective scientific experiment, not a tuned rerun.
