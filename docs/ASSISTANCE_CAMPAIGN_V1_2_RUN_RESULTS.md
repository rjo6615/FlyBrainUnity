# Assistance campaign V1.2 — eight-arm run results

2026-10-31. ONE user-approved V1.2 attempt at 61cafca (`assistance_campaign_v1_2
--live`), 18:20-23:07 UTC (~4 h 47 min). No retry, no tuning, no reuse of prior
arms. Coverage 20/42, 0 new admissions; all 20 neural servos still assist.
Independent balance and gait are not established.

## Integrity

`run-desktop-01/report.json`: run_status COMPLETE, scientific status
INTEGRITY_ACCEPTED, prerequisites verified before and after, sources unchanged.

- Eight fresh worker processes in fixed order (A_NC, A_WC, A_NP, A_WP, R_NC,
  R_WC, R_NP, R_WP); 20,001 recorded states, 4,000 neural updates and 20,001
  mechanical samples per arm.
- Native qualification passed on the fly model in A_NC (12 cases, minimum
  exposure 0.45) and transferred to the other seven arms.
- A arms accepted by the frozen constant-model auditor and equal to the
  piecewise audit; R arms accepted by the piecewise M0 -> MR audit. Mechanical
  trace audit passed for every arm. Cross-arm exact prefixes and RNG passed;
  every pair first diverges physically at state 5006 as declared.

## Behavior (cleared window, 520-2000 ms)

| Arms | Mean / peak world tilt | Rollover samples | <3 supports |
|---|---|---|---|
| A_NC, A_WC, A_NP, A_WP | 3.9-4.3 deg / <=4.3 deg | 0 | 0 |
| R_NC, R_WC, R_NP, R_WP | ~150 deg / ~161 deg | ~13,900 of ~14,800 | ~14,000 |

- A vs R (22 baseline-only servos neutralized after state 5005):
  LOWER_WORLD_TILT_IN_A for all four pairs; mean difference -146.1 to -146.6
  deg, peak -156.2 to -156.5 deg. Every R arm rolls over, pushed or not, neural
  input on or off.
- N vs W (neural input): MIXED_OR_UNRESOLVED at both levels. A: peak/mean
  NP-WP -0.08/-0.46 deg, NC-WC -0.03/-0.37 deg. R: NP-WP +0.05/-0.21 deg,
  NC-WC +0.12/-0.19 deg.
- Recovery to own control: A_NP SUSTAINED_BAND_RETURN at 613.5 ms, A_WP at
  520.1 ms. R_NP and R_WP NOT_RECOVERED_IN_WINDOW, qualified
  CONTROL_POSTURE_LOSS_CONFOUNDS_RECOVERY because their unpushed controls also
  roll over.
- Recorded limits: ONE_SEED_ASSISTED_POSITION_CONTROL_NOT_INDEPENDENT_BALANCE_OR_GAIT;
  R_NC/R_WC unexpected distal contact; R_NC/R_WC/R_WP contact-force
  correspondence limits.

Interpretation (simulation observation, not a biological claim): in this
one-seed, partially assisted model the 22 baseline-only position servos carry
the posture; the 20 existing neural channels neither prevent nor measurably
slow the rollover without them. Motor coverage, not reduced assistance, is the
next bottleneck.

## Diagnostics (not integrity)

- Display delivery / visual review: UNCONFIRMED.
- Reference comparison against the earlier reader: EXACT_MISMATCH at field
  `initial` for A arms; likely the V1.2 decoding of non-finite markers versus
  the old reader. Not investigated.
- Unity replay: eligible, but no entry point exists for this schema.
- Timing: ~34 min per arm (~10 startup, ~17 stepping at ~45 ms/step, ~6 save);
  the 1.3-1.6 h estimate did not include startup and save costs.

## Evidence

Committed: `docs/evidence/assistance-campaign-v1_2/preflight-01/` and every
non-raw file in `run-desktop-01/` (report, controller, preflight, transfer,
per-arm request/claim/launch/done/receipt/log), byte-identical to the run.
Not committed (user choice, 4.67 GB): the 17 `*.json.gz` per-arm, display and
qualification archives. Their sizes and SHA-256 are in
`run-desktop-01/raw-not-committed.json`, and each hash is also locked inside
`report.json`; the files remain only on the user's desktop.
