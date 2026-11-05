# Antennal gravity sense, Step D (JO zone-crossing tilt): results

Run 2026-11-05. The run used the preregistered protocol
`docs/evidence/jo-zone-crossing-v1/protocol.json` (sha b002e1c8…), committed and pushed in
7564a78 before any arm ran. All 37 arms ran once, in fresh processes, and were evaluated
once.
- Two 50-step plumbing smokes checked the wiring and were discarded unread, apart from the
  wiring checks.
- Report: `docs/evidence/jo-zone-crossing-v1/run/report.json` (sha e64811f7…), with
  `console.txt` alongside. The 37 raw arms stay local and untracked; their hashes are in the
  report.
- Design: `JO_ZONE_CROSSING_V1.md`.

## Verdict

| Check | Result |
|---|---|
| I1 to I7 integrity | all pass |
| O1 operating point (OFF window d) | pass. LEVEL −0.173 to −0.183; DOWN20 +0.169 to +0.185 (both sides, all 6 seeds) |
| Physical precondition (OFF arms < 45°) | pass. OFF peak tilt 4.8–5.5° LEVEL, 18.0–18.7° DOWN20 |

**`INTEGRITY_ACCEPTED`**

| Assignment | ρ | p | Label |
|---|---:|---:|---|
| G1 (E active at LEVEL, goes off at DOWN20) | 0.167 | 0.156 | **`JO_TILT_PATTERN_WEAK`** |
| FLIP (C active at LEVEL, E comes on at DOWN20) | 0.995 | 1/32 | **`JO_TILT_PATTERN_CONSISTENT`** |

r_GF = **−0.035**.

## Predictions (recorded before the run)

| | Prediction | Outcome | Basis |
|---|---|---|---|
| P1 | G1 CONSISTENT | **NOT_HELD** | WEAK (ρ 0.17, p 0.16) |
| P2 | FLIP CONSISTENT | **HELD** | ρ 0.995, p 1/32 |
| P3 | r_GF < 0 | **HELD**, by the rule only | −0.035, essentially zero. Not a meaningful anti-correlation. |
| P4 | DNp73 and DNbe001 opposite signs, G1 vs FLIP, all 6 seeds | **NOT_HELD** | see the DN table |

The prediction behind P1, P3 and P4 was that switching the E drive off (G1) would mirror
switching it on (FLIP). That was wrong. The FLIP onset response is large and reproducible.
The G1 offset response is small and inconsistent.

## Measured contrasts (reported, not labelled)

| Arm type | Mean \|Δ\| per seed (Hz) | ‖S‖ per seed (Hz) | Tonic leg-MN rate, 0–500 ms (Hz) |
|---|---|---|---|
| OFF | 0.33–0.79 | — | 5.50–6.79 |
| G1 | 0.66–1.93 | 10.7–30.2 | 14.6–18.8 |
| FLIP | 13.2–15.4 | 139–163 | 5.50–6.63, equal to OFF in seeds 20–24 |

Statements about the C route rest only on these measurements:
- **The C route (about 21 Hz in FLIP at LEVEL) leaves leg MNs at the OFF rate.**
  - The 0–500 ms tonic rate under FLIP equals OFF exactly in 5 of 6 seeds.
  - FLIP_LEVEL and OFF_LEVEL have identical window body statistics in seeds 20, 21 and 23.
- **The E route is strong both tonically and at onset.**
  - G1 tonic E drive raises the MN rate about 2.5–3 times.
  - E onset in FLIP gives a mean |Δ| about 20–40 times the OFF value.

**Direct JO-target DNs, DOWN20 − LEVEL (Hz), seeds 19–24:**

| DN | G1 | FLIP |
|---|---|---|
| DNp73 | +1.4, −9.5, −6.8, −12.5, −12.5, −7.4 | +10.5, +9.5, +11.5, +10.1, +9.8, +11.5 |
| DNbe001 | +19.3, 0.0, +1.0, 0.0, −0.3, +2.0 | +1.7, +1.4, +1.4, +3.4, +2.0, +2.7 |
| DNg29 | +2.0, −7.1, −2.7, −6.4, −9.5, −4.1 | +7.4, +6.4, +7.4, +7.4, +8.8, +6.8 |
| DNp18 | +13.2, −0.3, +0.3, −0.3, −0.7, +2.0 | +1.0, +1.7, +0.3, +2.4, +1.4, +2.0 |
| pIP1 | +7.8, −1.0, 0.0, 0.0, −0.3, +1.0 | +0.7, +1.7, +0.3, +1.0, +1.4, +1.0 |

Reading the DN table:
- DNp73 and DNg29 have opposite signs between G1 and FLIP in 5 of 6 seeds. Seed 19 is the
  exception, and its G1_DOWN20 arm rolled over.
- DNbe001 shows no G1 sign reversal: it is 0 in seeds 20 and 22 and positive in 19, 21 and 24.
- OFF contrasts are 0.0 for all five DNs in all seeds.

## Rollover in ON arms (a physical outcome, not gated)

**Five of the 12 ON DOWN20 arms passed 45° and turned over** (peak tilt 150–156°):
- G1_DOWN20 in seeds 19, 21 and 24;
- FLIP_DOWN20 in seeds 23 and 24.

No OFF arm and no LEVEL arm did. The protocol gates only OFF arms, so the labels stand. Under
AGENTS.md, physical divergence after a neural intervention is an outcome, and it is recorded
here as one.

Consequences:
- The window d of the rolled arms did not stay at the planned operating point. G1_DOWN20_19
  was −0.21 / −0.23; G1_DOWN20_21 and FLIP_DOWN20_23 were about 0; G1_DOWN20_24 was +0.05.
  Their S therefore contains the sensory consequences of the fall.
- G1 has three rolled seeds out of six. Its low ρ mixes upright and rolled seeds.
- FLIP stayed CONSISTENT with two rolled seeds, because the E-onset response dominates the
  window.

**Not distinguished:**
- whether G1's weakness is E offset being intrinsically small, adaptation after 500 ms of
  tonic E drive, or rollover;
- why ON arms roll while OFF arms do not.

A further observation: tonic E drive under G1 gives a body roll of about 4–5° at LEVEL
(OFF about 0.3°). Under FLIP, the upright DOWN20 arms roll 3.4–4.8° against OFF's −0.6 to −1.2°. The sign is
read with the left/right reconstruction asymmetry in mind; no roll-sensing claim is made.

## Declared interpretation that applies

"One assignment CONSISTENT, or r_GF ≥ 0": switching the active zone is not a simple sign
flip. Here the asymmetry is concrete:
- E onset gives a reproducible leg-MN pattern;
- E offset after a tonic history does not;
- the C route at about 21 Hz is silent at the leg-MN level.

**In this reconstruction, the E/C pair does not act as a signed tilt-direction channel.** The
leg-MN readout behaves like a one-sided E-onset detector.

**Not claimed:**
- the true zone sign;
- balance or a corrective response;
- any cause of the rollovers;
- any motor coordinate status change (20/42 admitted, +4 conditional).

## Limits

- All of Step C's limits apply:
  - the transduction is modelled, at a 120 Hz engineering scale, with an arbitrary G1 label;
  - the tilt is an idealised gravity step;
  - the OFF subtraction works only to first order;
  - coxa MNs are read out only;
  - the right-side JO reconstruction is sparser.
- LEVEL against DOWN20 is no tilt against tilt.
- Rollover in 5 ON arms contaminates their contrasts. There was no post-hoc exclusion,
  reselection or rerun.

## Reproduce the evaluation (Git Bash; writes a separate file)

```bash
P="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
PYTHONPATH="$PWD" "$P" -m malecns_backend.live.jo_zone_crossing --evaluate docs/evidence/jo-zone-crossing-v1/run --repro-ref "$HOME/Documents/FlyBrainUnity/docs/evidence/coxa-push-replication-v1/run/N0_7.json.gz" --cache "$HOME/Documents/FlyBrainUnity/.cache/malecns-v1" --output docs/evidence/jo-zone-crossing-v1/run/report.recheck.json
```

This needs the 37 local raw arms. Expected outcome: the same status, labels and predictions
as `report.json`.
