# Hair-plate Step C — results

2026-11-01. One run of the preregistered protocol after commit 4ff134b: four fresh-process
arms, 19:19-19:38 UTC (~5 min each), then evaluation. Report:
`evidence/hair-plate-posture-v1/run/report.json`; console log committed. The four raw arms
(37-40 MB each) are kept local; their SHA-256 values are in the report.

## Integrity: INTEGRITY_ACCEPTED

All four arms complete (20,001 states, 4,000 ticks); identical external schedule and per-tick
uniforms in all arms; A and R first differ at state 5006 in both OFF and ON pairs; the
declared row-zeroing applied in R arms only; hair-plate events delivered only in ON arms
(A_ON 3,215, R_ON 3,605; OFF 0).

## Q1: POSTURE_SENSITIVE

Mean coxa-MN rate, cleared window 520-2000 ms:

| | Posture held (A) | Posture released (R) | Difference |
|---|---:|---:|---:|
| Hair plates OFF | 1.89 Hz | 1.89 Hz | 0.00 Hz |
| Hair plates ON | 10.41 Hz | 9.32 Hz | 1.09 Hz |

Without hair plates, coxa motor activity is blind to posture (identical spike totals).
With them it differs, and per leg strongly: front-left 22.7 vs 9.8 Hz, hind-right 3.7 vs
13.6 Hz (held vs released).

## Q2: REFLEX_DIRECTION_CONSISTENT

In held arms, hair-plate input raises posterior-moving coxa MNs from 2.67 to 16.67 Hz
(+14.0) while anterior-moving ones stay flat (1.05 to 0.98 Hz): the published CxHP8
"push the leg back" direction, emerging from connectome wiring with no tuning.

## Descriptive

- Not uniform across legs: front-left and hind-left coxa MNs rise to 22.7 and 32.3 Hz,
  front-right barely changes (0.55 Hz; 5 hair plates and 194 synapses vs 7 and 826 on the
  left), and middle-left coxa MNs fall from 9.2 to 0.4 Hz although middle-leg hair plates
  are silent: an indirect, cross-leg effect.
- Hair-plate input changed the held body from 28.6 ms (A_OFF vs A_ON first physical
  difference) but not its posture (tilt 3.9 deg in both).
- No rescue: released arms still roll over (mean tilt 150.2 deg OFF, 151.0 deg ON; rollover
  samples 13,917 vs 14,213). Expected: the coxa MNs are still not wired to any coxa joint.
- R_OFF reproduces the V1.2 R_NC posture (mean 150.18 deg, peak 160.63 deg).

## Interpretation

The brain now senses coxa position and responds in the anatomically predicted direction,
and the response depends on posture. That closes the loop on the sensory side. It does
not produce balance: the responding coxa MNs still drive nothing, because the 18 coxa
joints remain unmapped (20/42). Limits: one seed; modeled encoder saturated at rest in
four legs; Q1 passes on a 1.09 Hz pooled difference against an exact-zero OFF difference,
with large opposite-signed per-leg differences.

## Files and checks

New: `malecns_backend/live/hair_plate_posture.py`, `tests/test_hair_plate_posture.py`
(11 synthetic tests passed in 2.90 s), `docs/HAIR_PLATE_POSTURE_V1.md`, this file,
`docs/evidence/hair-plate-posture-v1/{protocol.json,run/report.json,run/console.txt}`;
`.gitattributes`, handoff, roadmap. A 50-step implementation smoke test ran before commit.

```bash
cd "$HOME/Documents/FlyBrainUnity" && PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" && D=.cache/hair-plate-posture-repro && mkdir -p $D && for a in A_OFF A_ON R_OFF R_ON; do "$PY" -m malecns_backend.live.hair_plate_posture --arm $a --output $D; done && "$PY" -m malecns_backend.live.hair_plate_posture --evaluate $D --output $D/report.json
```

Expected (~20 min): INTEGRITY_ACCEPTED, POSTURE_SENSITIVE, REFLEX_DIRECTION_CONSISTENT and
the numbers above.
