# Antennal gravity sense, Step D4 (direction of the post-tilt commands): results

Run 2026-11-06. The run used the preregistered protocol
`docs/evidence/jo-command-direction-v1/protocol.json` (sha a7e804f2…), committed and pushed
in 6d10635 before any arm ran. All 27 arms ran once (fresh process each, about 1.9 h) and
were evaluated once.
- One plumbing smoke (50 steps, POST_NEG__G1_DOWN20_19) was discarded; only its exit status
  and yoke audit were read. It ended before the tilt, so it did not exercise the transforms.
- Output: `docs/evidence/jo-command-direction-v1/run/report.json` (sha 8dc55e70…), with
  `console.txt` alongside. The 27 raw arms stay local and untracked; their sha256 values are
  in the report.
- Design: `JO_COMMAND_DIRECTION_V1.md`.

This is an **open-loop physics experiment** on the D3 yoke path: the CNS ran but its output
did not reach the body.

## Headline: a protocol defect confounds POST_NEG, POST_HALF and POST_SCRAMBLE

**The preregistered clip range was wrong for these coordinates.** The protocol clipped every
transformed value to [−1.35, 1.30] rad, taken from the default `MotorSafety` dataclass. The
live decoders do not use that default: each pathway has its own joint range
(`MotorSafety(**m['safety'])`, `joint_range_rad`). Five admitted coordinates sit outside the
default range in **both** archives at all times:

| Coordinate | Leg joint | OFF / ON range after the tilt (G1_DOWN20_19) |
|---|---|---|
| 10 | LM femur | −1.79 to −1.63 |
| 12 | LM tibia | +1.70 to +1.99 |
| 17 | LH femur | −1.56 (constant) |
| 31 | RM femur | −1.84 to −1.65 |
| 33 | RM tibia | +1.69 to +1.96 |

Coordinates 19 (LH tibia) and 40 (RH tibia) also exceed +1.30 for part of the window in the ON
archive.

**Consequence.** In POST_NEG, POST_HALF and POST_SCRAMBLE, these coordinates were pinned to the
clip bound for the whole post-tilt window instead of following the declared transform:
- about 75,000 values were clipped per POST_HALF arm, although a half-way value can never leave
  a valid range;
- every transformed arm had a 0.45–0.49 rad step in a commanded position at the tilt (POST_ONLY:
  0.24 rad in G1, 0.002 rad in FLIP);
- the middle legs (and the left hind femur) were moved to a different posture in every
  transformed arm.

POST_SCRAMBLE takes coordinates 10, 12 and 33 from ON directly (sign +1), but 17 and 31 have
sign −1 and were clipped.

So each transformed condition differs from POST_ONLY in two ways at once: the declared
transform, and a large clipping-induced posture change of both middle legs. **The direction,
pattern and half-dose labels below cannot be attributed to the direction, pattern or size of
the JO-driven change.** This was found after the single evaluation, from the reported clip
counts (a declared diagnostic). The preregistered labels are recorded as computed; nothing was
re-run or re-labelled.

POST_ONLY and the upright controls use ON values directly, with no arithmetic and no clip. They
are **not** affected.

## Verdict

| Check | Result |
|---|---|
| Z1: 27 arms COMPLETE, 20,001 samples, 4,000 ticks | pass |
| Z2: each fallen POST_ONLY arm equals the D3 POST_ONLY arm's qpos exactly | pass |
| Z3: applied commands equal the declared (clipped) schedule exactly; adhesion all zero | pass |
| Z4: gravity G0 to state 5005, R_y(−20°)·G0 from 5006; no applied force | pass |
| Z5: Step D and D3 reports, 18 archives, 5 D3 arms match their sha256 | pass |

**`INTEGRITY_ACCEPTED`** under the preregistered checks. The integrity checks verify that the
declared schedule was applied; they do not catch a wrongly declared clip range.

## Outcomes

Fall: tilt ≥ 45° after state 5005. "Falls" gives ms after the tilt; "up" gives the peak tilt.

| Source | POST_ONLY | POST_NEG* | POST_HALF* | POST_SCRAMBLE* |
|---|---|---|---|---|
| G1_DOWN20_19 | falls 611 | up 32° | up 25° | falls 293 |
| G1_DOWN20_21 | falls 878 | up 32° | up 25° | falls 218 |
| G1_DOWN20_24 | falls 1178 | up 31° | up 25° | falls 304 |
| FLIP_DOWN20_23 | falls 981 | up 31° | up 26° | falls 1057 |
| FLIP_DOWN20_24 | falls 1415 | up 32° | up 27° | falls 479 |

\* Confounded by clipping (see above).

| Preregistered label | G1 (3) | FLIP (2) |
|---|---|---|
| direction | `DIRECTION_SPECIFIC`, CONSISTENT* | `DIRECTION_SPECIFIC`, CONSISTENT* |
| pattern | `PATTERN_NONSPECIFIC`, CONSISTENT* | `PATTERN_NONSPECIFIC`, CONSISTENT* |
| half dose | `HALF_DOSE_STAYS_UP`, CONSISTENT* | `HALF_DOSE_STAYS_UP`, CONSISTENT* |

**Upright controls (POST_ONLY, not affected by the defect):**

| Source | Degenerate? | Outcome |
|---|---|---|
| G1_DOWN20_20 | no | **falls 1430** |
| G1_DOWN20_22 | no | **falls 1245** |
| G1_DOWN20_23 | no | **falls 1305** |
| FLIP_DOWN20_19 | no | up 19° |
| FLIP_DOWN20_20 | yes (ON = OFF body until the tilt) | up 19° |
| FLIP_DOWN20_21 | yes | up 19° |
| FLIP_DOWN20_22 | yes | up 19° |

| Expectation | Result |
|---|---|
| E1: POST_NEG stays up in ≥ 4 of 5 | **HELD by the rule, confounded** (5/5 stay up, with clipped middle legs) |
| E2: POST_HALF stays up in all 5 | **HELD by the rule, confounded** (5/5, with clipped middle legs) |
| E3: no non-degenerate upright control falls | **NOT_HELD** (all 3 G1 upright controls fall) |

## What this shows (unconfounded parts only)

1. **D3's POST_ONLY result reproduces exactly** in a new code path (Z2), so the post-tilt ON
   commands topple an OFF-posture body in all 5 fallen sources.
2. **In G1, the post-tilt commands of the arms that stayed up topple the body too.** All 3 G1
   upright sources fall under POST_ONLY (1245–1430 ms after the tilt). In closed loop, with
   their own ON posture before the tilt, the same commands kept them up. So in G1, the
   post-tilt commands are not what separates the fallen arms from the upright ones. By the
   declared interpretation: something else, here the pre-tilt ON posture (or how the commands
   developed with the body), kept those arms up. This qualifies D3: for the G1 fallen arms the
   pre-tilt posture was not needed for the fall, but for the G1 upright arms it appears to
   prevent one.
3. **FLIP:** the one non-degenerate upright control stays up; the other three are degenerate.
   FLIP gives no contrast here.
4. **Size alone does not separate them (descriptive).** Mean |ON − OFF| over the post-tilt
   window is 0.100–0.114 rad in the fallen sources and 0.092–0.114 rad in the upright ones.

## What this does not show

- **Nothing about the direction, pattern or dose of the JO-driven change.** That was the main
  question, and this run cannot answer it because of the clip defect.
- Open loop; five fallen and seven upright sources, labels per source, no statistics.
- Step D's limits apply. No balance, corrective, zone-sign or cause claim. No motor coordinate
  status change (20/42 admitted, +4 conditional).

## Next step (not run)

A versioned protocol (D4 v2) that clips each transformed coordinate to its own live decoder
joint range, read from the pathway metadata the live session uses, or does not clip at all
where the value stays inside that range. It would re-ask the same direction, pattern and
dose question with a new preregistration. This version's evidence stays as recorded.

## Reproduce

```bash
P="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
PYTHONPATH="$PWD" "$P" -m malecns_backend.live.jo_command_direction --archives "$HOME/Documents/FlyBrainUnity/docs/evidence/jo-zone-crossing-v1/run" --d3 "$HOME/Documents/FlyBrainUnity/docs/evidence/jo-command-yoke-v1/run" --evaluate docs/evidence/jo-command-direction-v1/run --output docs/evidence/jo-command-direction-v1/run/report.json
```

This needs the 27 local raw arms, the 18 Step D archives and the 5 D3 POST_ONLY arms. The
output path must not exist (it is opened exclusively).
