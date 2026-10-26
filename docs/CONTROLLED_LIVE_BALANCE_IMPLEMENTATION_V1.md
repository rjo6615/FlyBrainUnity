# Controlled live balance implementation V1 (prospective execution contract)

This file is part of the execution source lock. Actual tests, prerequisites and
results belong in CONTROLLED_LIVE_BALANCE_IMPLEMENTATION_RESULTS.md, not edits
to this specification after execution. The original design/specification and
V1/V1.1 scientific sources remain unchanged. Schema:controlled-live-balance-execution-v1.

controlled_live_balance.py owns explicit child lifecycle and a bounded driver
over the existing ScientificSession.step API; it does not implement physics or
CNS stepping. Existing Trial/create_session, initialization accounting, recorder,
auditors, compact proof/comparison and behavior analysis are called unchanged.
No module-global factory mutation. Fixed NC/WC/NP/WP;seed1;20,000physics/4,000neural
updates and20,001states per arm; original42actuator assistance and20motor authority.
Original tick1001pre-safety withdrawal, force5000..5199,392-slot RNG, all prefixes,
terminal proposal and full analysis windows stay fixed. No retry/resume/tuning.

balance_live_observer.py projects the actual recorded state using validated native
scalar addresses. It reuses replay_snapshot and PoseServer/wire v1 without a new
coordinate conversion. The checked server subclass only surfaces thread/listener
errors. Local wire offers, exact queued packets, indices, wall times, sent/replaced
counts and faults are separate compressed display artifacts. Native raw samples
and neural traces are never downsampled for display. No client controls scientific
state; no display-pacing sleeps are added to the scientific worker.

Bind before native initialization. Bind failure stops with error receipt and no
scientific steps. Later observation errors disable that arm's publication but
leave the fixed scientific run intact. Display offers are provisional, never
accepted balance evidence before offline audit. Every arm has a fresh process and
display session. Full recorder lifecycle/initialization/stop handling mirrors the
original ordering; terminal update4000 is retained and not physically applied.
Ctrl+C asks the controller to publish STOP.json and wait for worker preservation;
hard OS termination may leave only logs/claims. Missing receipts remain errors.

Reports have a NEW schema and bind all original sources plus this spec, new code
and the unchanged live design. The original evaluator is not tricked into
accepting new source identities: this evaluator delegates original audit_arm,
proof, compare_proofs and behavior explicitly under its own report schema.
All four original integrity groups/guards remain mandatory. Display failure and
reference-file availability are reported separately; neither can waive scientific
failure. Exact cross-record comparison retains complete initial/context/physical/
neural/initialization records; OS/PID and display metadata are outside those fields.
Missing or changed reference data gives an explicit diagnostic, never a rerun.

Projection verification does not prove client receipt or complete visual coverage.
Display status remains UNCONFIRMED when projection passes, with projection_status
VERIFIED and actual local counts; faults/corruption yield FAILED. Only human review
can confirm what appeared. Scientific acceptance, visual status and behavior are
printed separately. The old saved replay gate stays unchanged and does not accept
this new report schema; any future replay of new records needs an explicit adapter.

Default --output runs original construction-free preflight only and writes an
exclusive folder. --live additionally requires original prerequisites, committed
complete source identity and --review-note documenting the user's actual prior
full-body replay review. No placeholder review should be supplied. It permits
ONE fixed campaign into a fresh folder; output cannot be overwritten or resumed.
The user must close other localhost8765 live/replay servers first. Use the existing
LiveFly scene, Play and Frame Current Fly; initialize/arm switches may take time.
No guaranteed real-time speed, independent balance or gait. Motor coverage20/42.
