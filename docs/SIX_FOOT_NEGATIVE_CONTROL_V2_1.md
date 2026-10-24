# Implementation correction v2.1, specified before the second physics run

The v2 run at implementation commit f925f34 completed all twelve arms but rejected
every foot on exact_identity_table and finite_force_measurements. Keep that full
raw record. FlyGym auto-generated a different fly namespace for each fresh model;
the observer also computed norms in float32 whereas the strict evaluator checks
the saved vector in float64 (the legacy observer already casts to float64).

Version v2.1 explicitly fixes the fly name to `calibration` in both arms and casts
the observed contact-force array to float64 before computing its norm. This
restores the intended matched identity and numerical observation contract. No
acceptance test, threshold, physical placement, masks, support, seed, schedule,
gain, neural parameter or transduction setting changes. The separately named
output is a justified implementation verification repeat, not offset tuning or a
repeat of an unchanged failed scientific protocol. It must run all twelve arms
once regardless of outcomes. The original v2 protocol document remains intact.

Use the same commands in SIX_FOOT_NEGATIVE_CONTROL_V2.md but new output paths
`six-foot-v2_1-dry.json` and `six-foot-v2_1-live.json`. The CLI module retains its
v2 family name and reports schema `six-foot-contact-calibration-v2.1`.
