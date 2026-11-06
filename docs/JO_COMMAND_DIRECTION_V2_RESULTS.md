# Antennal gravity sense, Step D4 v2 (direction of the post-tilt commands, live joint ranges): results

Run 2026-11-06 under the preregistered protocol
`docs/evidence/jo-command-direction-v2/protocol.json` (sha 5b77fd9e…). The protocol was
committed and pushed in 658c6a4 before any arm ran.
- **Runs:** all 15 arms ran once, each in a fresh process (about 70 min), and were evaluated
  once.
- **Preflight:** one 50-step plumbing smoke (POST_NEG__G1_DOWN20_19) was discarded. Only its
  exit status, yoke audit and the Z6 range records were read. It ended before the tilt.
  - 20 live channels, exactly the admitted set, every one with range (−1e6, 1e6).
  - All 42 actuators had `jnt_limited` false, `ctrllimited` true and `ctrlrange` ±1e6.
- **Output:** `docs/evidence/jo-command-direction-v2/run/report.json` (sha 262950cd…), with
  `console.txt` alongside. The 15 raw arms stay local and untracked; their sha256 values are
  in the report.
- **Design:** `JO_COMMAND_DIRECTION_V2.md`. It supersedes D4 v1 for the transformed arms only.
  v1's evidence (`JO_COMMAND_DIRECTION_RESULTS.md`) stays as recorded.

This is an **open-loop physics experiment** on the D3 yoke path: the CNS ran, but its output
did not reach the body.

## Verdict

| Check | Result |
|---|---|
| Status | **INTEGRITY_ACCEPTED** |
| Z1 complete (15 arms, 20,001 samples, 4,000 ticks) | pass |
| Z2 pre-tilt anchor (qpos = v1 POST_ONLY, states 0–5005) | pass |
| Z3 yoke audit (all 42 commands = schedule; adhesion 0) | pass |
| Z4 gravity (G0, then R_y(−20°)·G0 from 5006; no wrench) | pass |
| Z5 sources (3 reports, 9 archives, 5 v1 POST_ONLY arms; source/seed) | pass |
| Z6 live range (one channel per admitted coordinate, range = declared; values inside) | pass |
| Z7 no clipping | pass (0 clipped values in every arm) |

| Source | Direction | Pattern | Half dose |
|---|---|---|---|
| G1_DOWN20_19 | DIRECTION_SPECIFIC | PATTERN_SPECIFIC | HALF_DOSE_STAYS_UP |
| G1_DOWN20_21 | DIRECTION_SPECIFIC | PATTERN_SPECIFIC | HALF_DOSE_STAYS_UP |
| G1_DOWN20_24 | DIRECTION_SPECIFIC | PATTERN_SPECIFIC | HALF_DOSE_STAYS_UP |
| FLIP_DOWN20_23 | DIRECTION_SPECIFIC | PATTERN_SPECIFIC | HALF_DOSE_STAYS_UP |
| FLIP_DOWN20_24 | DIRECTION_SPECIFIC | PATTERN_SPECIFIC | HALF_DOSE_STAYS_UP |

**Consistency:** G1 (3 sources) and FLIP (2 sources) are each CONSISTENT on all three labels.
There is no pooling.

**Expectations:** these are not blind; they were carried over verbatim from v1.
- E1 (POST_NEG stays up in ≥4/5): **HELD**, 5/5.
- E2 (POST_HALF stays up in 5/5): **HELD**.

## Outcomes

All 15 transformed arms stayed up. The POST_ONLY reference is reused from v1: it fell in all
5 sources.

| Source | POST_ONLY (v1) | POST_NEG | POST_HALF | POST_SCRAMBLE |
|---|---|---|---|---|
| G1_DOWN20_19 | falls 610.7 ms | up, peak 22.6° | up, 16.9° | up, 25.9° |
| G1_DOWN20_21 | falls 878.3 ms | up, 23.5° | up, 17.3° | up, 25.0° |
| G1_DOWN20_24 | falls 1177.9 ms | up, 24.5° | up, 16.7° | up, 24.9° |
| FLIP_DOWN20_23 | falls 980.9 ms | up, 24.0° | up, 17.7° | up, 23.5° |
| FLIP_DOWN20_24 | falls 1415.0 ms | up, 25.8° | up, 17.0° | up, 23.8° |

The peak tilt is measured after state 5005. The fall threshold is 45°.

### Diagnostics (declared, not gates)

| Condition | Largest step at the tilt | Largest command | Largest excursion beyond ON/OFF span | Transitions with a change > 0.002 rad |
|---|---|---|---|---|
| POST_NEG | G1 0.243–0.245 rad; FLIP 0.001 rad | 2.02–2.03 rad | 0.247–0.258 rad | 2,900–2,993 |
| POST_HALF | G1 0.121–0.123; FLIP 0.001 | 1.86–1.89 | 0 | 696–832 |
| POST_SCRAMBLE | as POST_NEG | as POST_NEG | 0.231–0.234 | 2,899–2,990 |

- The steps at the tilt match the design's archive-derived figures. They equal POST_ONLY's
  step, or half of it for HALF.
- The last column counts post-tilt physics transitions, out of 15,000, whose largest commanded
  change exceeds the live slew limit per neural update (4 rad/s × 0.5 ms). There is one neural
  update per 5 physics steps, so NEG and SCRAMBLE come close to exceeding the limit at every
  one of the roughly 3,000 post-tilt updates. That assumes commands change only at updates,
  which is not checked here.
- The same count was **not** computed for POST_ONLY, because it was not part of this protocol.
  So it is not known whether the falling condition also exceeds the slew limit this often.

### v1 ↔ v2 (descriptive: what pinning the middle legs did)

| Condition | v1 (clipped to [−1.35, 1.30]) | v2 (live ranges, no clip) |
|---|---|---|
| POST_NEG | 5/5 up, peak 31.2–32.1° | 5/5 up, peak 22.6–25.8° |
| POST_HALF | 5/5 up, peak 24.6–26.7° | 5/5 up, peak 16.7–17.7° |
| POST_SCRAMBLE | **5/5 fall** (218–1057 ms, peak 161–164°) | **5/5 up**, peak 23.5–25.9° |

- v1's labels were **DIRECTION_SPECIFIC, PATTERN_NONSPECIFIC, HALF_DOSE_STAYS_UP**. v2 changes
  only the pattern label, to **PATTERN_SPECIFIC**.
- Every SCRAMBLE fall in v1 went with the middle-leg pinning. Removing the clip removed every
  one of them. In every condition, pinning also raised the peak tilt by about 7–9°.
- This describes the v1 defect. It says nothing about the JO route.

## What this shows

Within this open-loop yoke setting, on these 5 fallen sources:
- **Direction matters.** Applying the same post-tilt command change with the opposite sign
  (POST_NEG) does not topple the OFF-posture body, while the original change (POST_ONLY) does
  in 5/5. The step at the tilt is the same size in both, and NEG's values are exactly as far from OFF
  as POST_ONLY's. This is the declared reading of `DIRECTION_SPECIFIC` and `PATTERN_SPECIFIC`: the
  fallen arms' JO-driven post-tilt change has a specific destabilising direction in this open
  loop.
- **Another direction of the same size does not topple it either** (POST_SCRAMBLE, one sign
  vector). So the original direction is specifically destabilising; it is not that the reversed
  direction is uniquely protective. This rests on a single scramble vector.
- **Half the change does not topple it** (POST_HALF 5/5 up, with the lowest peak tilts). The
  falls depend on dose as well as direction. Halving lowered the peak by 6–9° relative to NEG
  and SCRAMBLE, but this protocol did not measure the peak tilt for POST_ONLY before it fell.
- **FLIP:** the step at the tilt is only 0.001 rad, so in FLIP the destabilising effect comes
  from how the commands evolve after the tilt, not from a step.
- **Combined with v1's G1 upright controls**, which also fell under POST_ONLY (declared reading):
  in G1 the destabilising direction is shared by the fallen and upright arms. The closed-loop
  pre-tilt posture is what kept the upright ones up. This combines the v1 controls with v2; it
  was not tested as one experiment.

## What this does not show

- It does not show that the JO response "causes" falls in the closed loop. The mixed streams
  never occurred in a closed loop, and the body here is in the OFF posture, not the ON posture.
- It does not show which coordinates or which time course carry the destabilising direction.
- **No balance or corrective-response claim.** Staying up under NEG is not a correction. The
  command stream is fixed in advance.
- **NEG and SCRAMBLE are probes, not physiology.**
  - Their values go up to 0.26 rad beyond anything the live session produced at that
    transition.
  - They change faster than the live slew limit at nearly every update.
  - Either property could matter physically, and neither was controlled for in POST_ONLY.
- **One scramble vector:** "another direction" is a single sample.
- **Five sources.** Labels are per source, with no statistics.
- **Inherited limits.** Step D's limits apply: an idealised gravity step and modelled JO
  transduction.
- **No motor coordinate status change** (20/42 admitted, +4 conditional).

## Next step (not run)

Rhythm (the roadmap's next item). One possible later refinement:
- A POST_ONLY slew/excursion-matched control.
- The same diagnostics computed for the reused POST_ONLY schedules, as separately versioned
  evidence.

These would tell whether the slew-limit difference matters. That would need its own design.

## Reproduce

```bash
P="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
PYTHONPATH="$PWD" "$P" -m malecns_backend.live.jo_command_direction_v2 --archives "$HOME/Documents/FlyBrainUnity/docs/evidence/jo-zone-crossing-v1/run" --v1 docs/evidence/jo-command-direction-v1/run --evaluate docs/evidence/jo-command-direction-v2/run --output docs/evidence/jo-command-direction-v2/run/report.json
```

This needs:
- the 15 local v2 raw arms;
- the 9 Step D archives;
- the v1 raw arms, which include the 5 POST_ONLY arms.

This run read the v1 arms from the `jo-dir` worktree. The output path must not exist, because
it is opened exclusively.
