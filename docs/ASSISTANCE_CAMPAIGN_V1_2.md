# Assistance campaign V1.2 — exact decoding of saved non-finite floats

2026-10-31. Separately versioned engineering correction after the ONE V1.1
attempt (`docs/evidence/assistance-campaign-v1_1/run-desktop-01`, commit 92652b5).
That attempt completed A_NC (20,001 states, 4,000 neural updates, 20,001
mechanical samples; force-law qualification passed in memory under the V1.1
guard, about 62 min stepping) and then stopped: the controller's re-evaluation
of the saved qualification raised `TypeError: float() argument must be a string
or a real number, not 'dict'`. ERROR/INCONCLUSIVE_INTEGRITY, 7 arms unstarted,
no retry. Evidence committed unchanged and locked.

## Cause

The six adhesion actuators (native rows 42..47) legitimately have +/-inf force
ranges. The existing exclusive save (`json_safe`) writes non-finite floats as
`{"__arrow_nonfinite_float__": "+Infinity"}` markers; no read-back path inverted
them, so `validate_inventory` received dicts. Synthetic fixtures had no
non-finite values. Offline, with exact decoding, the saved qualification passes
all 12 cases (minimum selected baseline exposure 0.45 vs floor 1e-8).

## Change

`assistance_campaign_v1_2` decodes exactly those markers (NaN, +Infinity,
-Infinity) in every read of saved evidence: qualification transfer, worker
loading and evaluator. Everything else is reused unchanged: the V1.1 guard,
Trial, mechanical audit, V1 scientific/piecewise auditors, gates, prefixes,
comparisons and acceptance. The amendment
(`docs/evidence/assistance-campaign-v1_2/protocol.json`) locks both failed
attempts and the executed V1/V1.1 checkpoints and forbids reusing retained arms.

`--audit-retained DIR --receipt PATH` runs an offline integrity diagnostic of
COMPLETE arms in a retained V1.1 attempt from committed code (no native/CNS,
no behavior). It is NOT campaign acceptance; it only exposes further latent
defects before another hour-per-arm attempt.

A new attempt writes to `docs/evidence/assistance-campaign-v1_2/run-desktop-01`
with all eight arms fresh, needs explicit user approval, and has no retry.
Measured V1.1 cost: about 62 min stepping per arm (roughly 8-9 h for eight) and
560 MB raw per arm plus a 175 MB qualification file. Coverage 20/42;
independent balance and gait unproven.

## Second correction found by the offline audit

The first `--audit-retained` run (committed 91fe155; receipt
`retained-v1_1-a-nc-audit.json`, retained) found A_NC identity true, scientific
audit accepted by the frozen constant-model auditor and equal to the piecewise
audit, qualification passed, but mechanical audit FAILED: `mechanical boundary
journal mismatch`. Only `time_s` differed: the adapter journals MuJoCo's
accumulated clock (0.5004999999999612), the frozen `audit_trace` compared it
bit-exactly to 5005*dt, while the runtime boundary and per-sample clock checks
use 1e-12. V1.2 compares the journal clock at that same 1e-12 bound, records the
offset, then runs every other frozen journal/force/trace check unchanged. Declared
in the amendment before any V1.2 execution.
