# Antennal gravity Step D5: results

Run 2026-11-08, once, from the preregistered commit 09ae896 (protocol
`docs/evidence/jo-frozen-response-v1/protocol.json`, sha a1ab56a7…, no amendments). 61 arms, each
in a fresh process, 19:36:16Z–23:54:11Z (about 4.3 h). Evaluated once (`run/report.json`).
Design: `JO_FROZEN_RESPONSE_V1.md`.

**Status: INTEGRITY_ACCEPTED. Q1 `JO_FALLS_REPLICATED` (p = 0.0005). Q2 pooled `INDETERMINATE`
(b = 8, c = 4, p = 0.19).** The two JO types go in opposite directions (reported, not gated):
freezing the FLIP input prevents every FLIP fall (6 → 0), and freezing the G1 input does not
prevent G1 falls (8 → 10).

## Integrity

| Check | Result |
|---|---|
| Z1 completeness (61 arms, 20,001 states, 4,000 ticks) | pass |
| Z2 frozen = sighted exactly through state 5005 | pass (first body difference at states 5136–5296 for G1F, 5306–5591 for FLIPF) |
| Z3 freeze audit (frozen rates = partner's last pre-tilt rates; sighted = encoder) | pass |
| Z4 gravity G0 then R_y(−20°)·G0 from 5006, no applied wrench | pass |
| Z5 JO delivery (OFF withheld every tick) | pass |
| Z6 REPRO = Step D's G1_DOWN20_19 exactly (hard gate) | pass; it fell again at 583 ms, peak 154° |
| Z7 sources and seeds | pass |

## Falls

Fall = tilt ≥ 45° after state 5005. Each cell is the fall time after the tilt in ms, or – for an
arm that stayed up. Every fall went past 148°, so every fall was a full roll-over. Every arm
that stayed up peaked between 17.9° and 20.2°, which is the tilt itself.

| Seed | OFF | G1 | G1F | FLIP | FLIPF |
|---|---|---|---|---|---|
| 25 | – | 1294 | – | – | – |
| 26 | – | 1147 | 1372 | – | – |
| 27 | – | – | 956 | 987 | – |
| 28 | – | – | 1276 | – | – |
| 29 | – | 1367 | 744 | 1291 | – |
| 30 | – | 1349 | 1381 | 1447 | – |
| 31 | – | – | 1208 | 1257 | – |
| 32 | – | – | 590 | 1378 | – |
| 33 | – | 1163 | 1014 | – | – |
| 34 | – | 1073 | 1160 | – | – |
| 35 | – | 826 | 1011 | 964 | – |
| 36 | – | 1440 | – | – | – |
| **Falls** | **0/12** | **8/12** | **10/12** | **6/12** | **0/12** |

## Questions

**Q1 (gated): `JO_FALLS_REPLICATED`.** Sighted arms fell 14/24 and OFF arms 0/12 (one-sided Fisher
p = 0.0005). Step D's unplanned observation (5/12 vs 0/12) holds on fresh seeds, at a higher rate.
In this context, the modelled JO gravity sense makes the closed-loop fly less stable under a 20°
nose-down tilt, not more.

**Q2 (gated, pooled over 24 pairs): `INDETERMINATE`.** b = 8 (only the sighted arm falls), c = 4
(only the frozen arm falls), one-sided p = 0.19 for RESPONSE_NEEDED. The pooled test mixes two
types whose effects point in opposite directions.

**Reported per type, not gated:**

| Type | Sighted falls | Frozen falls | b | c | Exact p | Label by the Q2 rule |
|---|---|---|---|---|---|---|
| G1 | 8 | 10 | 2 | 4 | 0.89 (needed) | RESPONSE_NOT_NEEDED |
| FLIP | 6 | 0 | 6 | 0 | 0.016 (needed) | RESPONSE_NEEDED |

Frozen vs OFF (reported): 10/24 vs 0/12, Fisher p = 0.008.

## JO input after the tilt (mean over 12 seeds, Hz)

| Arm | C left | C right | E left | E right |
|---|---|---|---|---|
| G1 sighted | 15.0 | 18.9 | 5.0 | 6.5 |
| G1F (held at G1 pre-tilt) | 0.0 | 0.0 | 23.8 | 20.7 |
| FLIP sighted | 2.3 | 3.8 | 16.6 | 19.9 |
| FLIPF (held at FLIP pre-tilt) | 20.5 | 20.3 | 0.0 | 0.0 |

The tilt moves the JO input from one zone to the other in both sighted types. Freezing keeps each
type in its pre-tilt pattern: E driven for G1F, and C driven for FLIPF.

## Expectations

- **E1 (Q1 replicates): correct.**
- **E2 (pooled Q2 is RESPONSE_NEEDED): wrong.** The pooled result is INDETERMINATE. The FLIP falls
  need the input to follow the tilt; the G1 falls do not.
- **E3 (FLIPF falls less than FLIP; G1F falls at least as often as G1): correct** (0 < 6; 10 ≥ 8).

## Reading

- **FLIP:** every fall needed the JO input to follow the tilt. With the input held at its
  pre-tilt rate (C on, E off), no FLIP fly fell. This fits Step D's E-onset finding: in FLIP, the
  tilt switches the E route on.
- **G1:** the falls do not need a tilt response. With the input held at G1's pre-tilt rate (E on,
  C off), the fly fell as often or more. In G1, the sighted tilt response is E-offset/C-onset, so
  freezing keeps E on.
- **Post hoc pattern, not tested:** arms with E driven after the tilt (G1F, FLIP, and G1 at a lower
  E rate) fell in 6–10 of 12 seeds; arms with no E after the tilt (OFF, FLIPF) never fell. G1 sighted is the exception
  to a simple "E rate" story: it has only ~6 Hz of E but fell 8/12. Whether the E route carries the
  falls is a separate prospective question. It is not established here.
- The falls look like Step D's: late (590–1447 ms after the tilt), abrupt and complete (> 148°).

## What this does not show

- No balance, corrective reflex or biological role for JO zones. FROZEN is a probe; real JO
  neurons do not freeze.
- Q1 does not control for the pre-tilt state, which differs between OFF and each JO type.
- The per-type split is reported, not gated, and was not a preregistered question.
- One tilt and one context (Step D, assisted posture). Modelled transduction (Step B encoder).
- Motor coordinates are unchanged (20/42 admitted, +4 conditional).

## Evidence

- `docs/evidence/jo-frozen-response-v1/protocol.json` (sha a1ab56a7…).
- `docs/evidence/jo-frozen-response-v1/run/console.txt` and `report.json` (committed).
- 61 raw arms, local and untracked, in the main checkout's
  `docs/evidence/jo-frozen-response-v1/run/`. Their sha256 values are in the report.
