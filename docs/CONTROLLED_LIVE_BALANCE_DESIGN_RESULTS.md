# Controlled live balance design checkpoint

2026-10-26. Fresh baseline origin/newBrain03098a0, merged camera PR289. Controlled
live balance observation V1 is specified in CONTROLLED_LIVE_BALANCE_V1.md and
evidence/controlled-live-balance-v1/protocol.json. No new runner, native model,
physics transition, CNS update, Unity display session or motor admission here.

The next bounded experiment asks whether the existing assisted contribution assay
can be displayed during computation without changing its science. Prior behavior
is already known to be MIXED_OR_UNRESOLVED. Display is not an intervention expected
to improve it. Fixed NC/WC/NP/WP, seed1,2s each,80,000physics/16,000neural/80,004states
total; original force, withdrawal,392proprio RNG, full windows/bands and42actuator
assistance remain unchanged. Client presence/input/disconnects/FPS cannot influence
science. Live poses are provisional; full scientific integrity and display
integrity/coverage have separate statuses. No independent-balance or gait claim.

## Actual validation

47stdlib static checks passed with desktop Python3.12.10. The saved design-checks
receipt lists each check and the protocol SHA256. Checks cover original arm order,
seed/dt/duration/count inheritance, integer timing/force budget,20+22assistance
isolation, no retries, honest pending execution gates, output-only provisional
display,11reference files' raw/canonical identities, the accepted report-summary
identity, saved raw artifact references and known prior mixed outcome.

These are design checks, not pytest, a new saved scientific result reconstruction,
an environment/scientific prerequisite pass, a full native-source audit or a CNS
experiment. No synthetic fly trajectory was generated. Historical raw arm gzip
payloads were not hydrated or re-audited; recorded identities were preserved.
No package changes. Scoped Git whitespace check and Git Bash JSON parsing passed.

The first isolated checkout hit Windows' path limit on a historical tracked cache
backup. Excluding that cache and using per-command long-path handling completed
the checkout; no primary files were changed or deleted. This is unrelated to
experimental integrity. All scientific sources and historical locks are untouched.

## Changed files and purpose

- CONTROLLED_LIVE_BALANCE_V1.md: prospective scientific/observation contract.
- evidence/controlled-live-balance-v1/protocol.json: machine-readable settings,
  reference identities and explicit not-implemented/not-run gates.
- evidence/controlled-live-balance-v1/design-checks.json: actual static check receipt.
- CONTROLLED_LIVE_BALANCE_DESIGN_RESULTS.md: this delivery and commands.
- PROJECT_HANDOFF.md and UNITY_AND_BALANCE_ROADMAP.md: immediate next task/status.
- .gitattributes: preserve exact new JSON bytes across Windows checkouts.

## Windows Git Bash after merge

This command only checks/opens the design. It does not run a fly or start Unity.

```bash
cd "$HOME/Documents/FlyBrainUnity" &&
git switch newBrain &&
git pull --no-rebase --no-edit &&
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" &&
"$PY" -m json.tool docs/evidence/controlled-live-balance-v1/protocol.json >/dev/null &&
"$PY" -m json.tool docs/evidence/controlled-live-balance-v1/design-checks.json >/dev/null &&
code docs/CONTROLLED_LIVE_BALANCE_V1.md docs/CONTROLLED_LIVE_BALANCE_DESIGN_RESULTS.md
```

Expected:both JSON files parse, then the design and this checkpoint open in VS
Code. For existing accepted Unity replay, use LIVE_FLY_CAMERA_FRAMING_V1.md;
no new native execution command exists until the adapter is implemented/tested.

## Next and limits

Implement the versioned instance-local observation/controller/worker/report adapter
with existing Trial/create_session/ScientificSession/PoseServer and original
auditors. Prove engineering equivalence and output-only behavior with synthetic
sessions, actual OS workers and socket tests; these do not replace actual native
evidence. Commit implementation before one new bounded four-arm execution.
Verify original environment/data gates and confirm full-body review of the
accepted recording first. Preserve every failure and partial record, no retry.

Roadmap:recorded assay and Unity connection done; full-body human review pending
confirmation; live design specified; live adapter/checks next; live campaign not
run. Motor coverage20/42(47.6%coverage only),0new admissions. Position assistance
can maintain posture. Independent balance requires a separately justified
assistance experiment and evidence; no fixed completion date follows here.
