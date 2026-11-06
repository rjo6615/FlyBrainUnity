# Antennal gravity sense, Step D3 (command yoke of the falls): results

Run 2026-11-05/06. The run used the preregistered protocol
`docs/evidence/jo-command-yoke-v1/protocol.json` (sha 3fbb281d…), committed and pushed in
27e253b before any arm ran. All 45 arms ran once (fresh process each, about 3.5 h) and were
evaluated once.
- One plumbing smoke (50 steps, ONLY_FRONT__G1_DOWN20_19) was discarded; only its exit
  status and yoke audit were read.
- Output: `docs/evidence/jo-command-yoke-v1/run/report.json` (sha 5abd8a9a…), with
  `console.txt` alongside. The 45 raw arms (`*.json.gz`) stay local and untracked; their
  sha256 values are in the report.
- Design: `JO_COMMAND_YOKE_V1.md`.

This is an **open-loop physics experiment**: the CNS ran in every arm but its output did not
reach the body. All 42 commanded positions came from a declared mix of two recorded Step D
archives.

## Verdict

| Check | Result |
|---|---|
| Y1: 45 arms COMPLETE, 20,001 samples, 4,000 ticks | pass |
| Y2: each FULL_ON arm reproduces its ON archive's qpos exactly at every state | pass |
| Y3: applied commands equal the declared mix at every transition; adhesion all zero | pass |
| Y4: gravity G0 to state 5005, R_y(−20°)·G0 from 5006; no applied force | pass |
| Y5: Step D report and the 9 archives match their sha256; seeds and sources recorded | pass |

**`INTEGRITY_ACCEPTED`.** The 22 unadmitted coordinates were identical between the ON and
OFF archives in all 5 sources, as expected.

| Label | G1 (19, 21, 24) | FLIP (23, 24) |
|---|---|---|
| FRONT | `NECESSARY_NOT_SUFFICIENT`, CONSISTENT | `NECESSARY_NOT_SUFFICIENT`, CONSISTENT |
| MIDDLE | `NECESSARY_NOT_SUFFICIENT`, CONSISTENT | `NECESSARY_NOT_SUFFICIENT`, CONSISTENT |
| HIND | `NECESSARY_NOT_SUFFICIENT`, CONSISTENT | `NECESSARY_NOT_SUFFICIENT`, CONSISTENT |
| PRE_TILT_SUFFICIENT | absent in 3/3 | absent in 2/2 (degenerate, see below) |
| POST_TILT_SUFFICIENT | present in 3/3 | present in 2/2 (degenerate, see below) |

| Expectation | Result |
|---|---|
| E1, FLIP: FRONT `SUFFICIENT_AND_NECESSARY` and POST_ONLY falls | **NOT_HELD** (POST_ONLY falls; FRONT is not sufficient) |
| E2, G1: PRE_ONLY falls | **NOT_HELD** (PRE_ONLY stays up in all 3) |

## Outcomes per arm

Fall: tilt ≥ 45° after state 5005. Times are ms after the tilt; "up" gives the peak tilt.

| Condition | G1_19 | G1_21 | G1_24 | FLIP_23 | FLIP_24 |
|---|---|---|---|---|---|
| FULL_ON | falls 583 | falls 898 | falls 1162 | falls 981 | falls 1415 |
| ONLY_FRONT | up 13° | up 14° | up 14° | up 17° | up 17° |
| ONLY_MIDDLE | up 21° | up 19° | up 19° | up 20° | up 19° |
| ONLY_HIND | up 22° | up 21° | up 21° | up 22° | up 21° |
| NO_FRONT | up 21° | up 22° | up 22° | up 23° | up 22° |
| NO_MIDDLE | up 19° | up 20° | up 21° | up 19° | up 18° |
| NO_HIND | up 14° | up 15° | up 13° | up 17° | up 16° |
| PRE_ONLY | up 19° | up 19° | up 19° | up 19° | up 18° |
| POST_ONLY | falls 611 | falls 878 | falls 1178 | falls 981 | falls 1415 |

Every fall reached a peak of 150–156°. Every arm that stayed up peaked at 13–23°, close to
the 20° gravity tilt itself. No arm came near the 45° rule without falling over.

## What this shows

1. **No single leg group is sufficient, and every leg group is necessary.** Replacing any one
   group's ON commands with OFF commands prevented the fall in all 5 sources. Giving only one
   group its ON commands never produced a fall. The fall needs the JO-driven commands of the
   front, middle and hind legs together, in both G1 and FLIP. This matches the declared
   "needs a combination of groups" reading.
2. **The post-tilt commands are sufficient; the pre-tilt commands are not.**
   - **G1:** ON and OFF bodies diverge from about 45 ms after the start (states 446–466), so
     the pre-tilt JO posture really differs. Yet PRE_ONLY (ON posture up to the tilt, OFF
     after) stayed up in all 3 sources. POST_ONLY (OFF posture up to the tilt, ON after) fell
     in all 3, at times close to the original fall (611, 878, 1178 ms against 583, 898,
     1162 ms). The pre-tilt posture is neither sufficient nor needed.
   - **FLIP: the time test is degenerate.** The ON and OFF bodies were exactly identical
     until after the tilt (first qpos difference at states 5411 and 5556). PRE_ONLY was
     therefore identical to the OFF archive, and POST_ONLY to FULL_ON (same fall time and
     peak). This is consistent with Step D, where FLIP's pre-tilt drive goes to the C route,
     which leaves leg MNs at the OFF rate. FLIP's POST_TILT label adds nothing beyond "the
     FLIP command difference begins after the tilt".
3. **This contradicts the D2 hypothesis for G1.** D2 suggested that JO-driven posture puts
   the body in a less stable regime that tips at variable times. For G1, the pre-tilt posture
   is not what matters: the post-tilt commands alone reproduce the fall, from an OFF posture.
   By the declared interpretation, the falls are a delayed consequence of the tilt response,
   carried jointly by all three leg groups.

## What this does not show

- **Open loop.** The mixed streams never occurred in a closed loop. That the post-tilt ON
  commands make an OFF-posture body fall does not mean the closed-loop brain would.
- **Switching archives at the tilt** (PRE_ONLY, POST_ONLY) puts a step in the commanded
  positions at the gravity step. In G1 POST_ONLY this step is real (the postures differ); in
  FLIP it is absent.
- **Leg groups are coarse.** "All three groups needed" does not identify which channels
  within a group matter, nor whether the cause is a specific command pattern or simply the
  sum of small posture changes on all six legs.
- Five fallen sources; labels per source, no statistics.
- Step D's limits apply: idealised gravity step, modelled JO transduction.
- No balance, corrective-response, zone-sign or biological-cause claim. No motor coordinate
  status change (20/42 admitted, +4 conditional).

## Reproduce

```bash
P="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
PYTHONPATH="$PWD" "$P" -m malecns_backend.live.jo_command_yoke --archives "$HOME/Documents/FlyBrainUnity/docs/evidence/jo-zone-crossing-v1/run" --evaluate docs/evidence/jo-command-yoke-v1/run --output docs/evidence/jo-command-yoke-v1/run/report.json
```

This needs the 45 local raw arms and the 9 local Step D archives.
