# Balance-contribution design delivery

The user selected a controlled balance-contribution test with the existing20
motors. The protocol and machine-readable manifest are now specified; **no runner
is implemented and no physics/CNS/model initialization or experiment ran in this
update**. Motor coverage remains20/42. This is design readiness, not runtime
readiness or an experimental pass.

Four planned fresh arms compare continued versus withdrawn20-channel decoder
input, each with/without the inherited pulse. Proprioception-only input uses the
existing explicit392-slot common RNG schedule. Position assistance is identical
in policy across arms. Withdrawal occurs before the existing safety limiter;
its bounded return to baseline is measured rather than hidden or hard-switched.
Each arm is2s/20,000physical transitions/4,000neural updates, seed1. Every null,
fall, incomplete or unrecovered outcome is retained. Full integrity and behavioral
descriptions remain separate; independent balance/walking is not claimed.

The terminal neural proposal is explicitly not counted as applied actuation.
Fixed windows, common-prefix/RNG/force/identity/command checks, observation and
recovery bands, measurement frames, safety history, exposure and initialization
operation accounting are in `BALANCE_CONTRIBUTION_V1.md`. The machine-readable
design includes all20names/indices,22baseline-only channels,20unchanged code
fingerprints, planned condition order and limits. Runtime prerequisites have
not been verified by constructing a model or brain.

Primary-source anatomical qualification is closed with an unresolved result:
21distal MANC body references are present in Supplement3, but16have limb-only
targets and5other named muscle targets. Supplement6 supplies no named tarsal
serial groups. The publication explicitly leaves T2/T3 tarsus homologs unresolved.
See `DISTAL_ANATOMICAL_QUALIFICATION_RESULTS.md`; that limitation is why this
balance design uses the existing20, without assigning new motor populations.

Actual validation uses static/data checks, not a new test suite for documents:
CSV raw hashes and namespace-safe body-ID joins; complete20-row cohort/21body
references; protocol JSON and source/document fingerprints;20/22partition;
all declared timing/force/window/terminal counts; unchanged inherited recovery
bands/resolution. The existing pure `MatchedControlPipeline` was exercised with
synthetic starting offsets[-0.25,0,+0.25]rad: zero input retains the4rad/s slew
limit and returns exactly to baseline by126updates. This is an engineering
reference check, not simulated fly behavior. Native imports were blocked.

Next: implement the isolated adapter, recorder and evaluator; add meaningful
synthetic boundary tests; then commit implementation before one bounded four-arm
execution. Inspect saved poses in Unity after integrity acceptance, even if
the behavior is null or negative. Do not skip to a success claim or repeat until
a favorable outcome. No date or guaranteed improvement is inferred.

## Windows Git Bash after merging

This update has no simulation command. Check the design data and open the spec:

```bash
cd ~/Documents/FlyBrainUnity &&
git switch newBrain &&
git pull --no-rebase --no-edit &&
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" &&
"$PY" -m json.tool docs/evidence/balance-contribution-v1/protocol.json >/dev/null &&
code docs/BALANCE_CONTRIBUTION_V1.md docs/BALANCE_CONTRIBUTION_DESIGN_RESULTS.md
```

Expected: JSON check succeeds and the design opens. Status is
SPECIFIED_NOT_IMPLEMENTED_NOT_RUN, not a measured recovery result. No additional
LFS/Unity/CNS run is required for this design review. Existing results/local edits
are preserved; source CSVs are new separate artifacts, not replacements.

Scoped whitespace checks pass outside the two original source CSVs. Those CSVs
are verified by exact raw SHA256/size and are not reformatted; Supplement3 retains
its original CRLF representation, which can produce Git whitespace warnings.
The design Git Bash JSON check passed. No repository unit/simulation suite was
run for this documentation/data-only change.
