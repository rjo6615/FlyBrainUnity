# Fore-aft push response with the four conditional coxa channels — results (V1)

2026-11-03. One run of the preregistered protocol after commit b31435a (protocol sha
ec3f0de1…). Twenty-seven fresh-process arms ran from 16:17 to 18:25 local time,
4–5 min each, followed by one evaluation.

- **Report:** `evidence/coxa-push-response-v1/run/report.json` (sha 4c03a59e…).
- **Console logs:** committed.
- **Raw arms:** kept local in the main checkout's `docs/evidence/coxa-push-response-v1/run/`.
  Their SHA-256 values are in the report.

These are physics and CNS runs, not mocks. Nothing was retried, re-windowed or tuned.

## Integrity: INTEGRITY_ACCEPTED; pulse precondition met

- **I1–I7:** all pass.
- **I3:** `N0_1..3` equal coxa-admission `C0_1..3` over the whole run. That covers every
  sample's qpos and every tick's spikes, uniforms and hair deliveries.
- **I4:** every pushed arm applied exactly the planned ±x Thorax wrench on transitions
  5,000–5,199, with zero torque and nothing else. The `_0` arms applied none.
- **I6:** the first coxa command came at sample 216 (seed 1), 141 (seed 2) and 146
  (seed 3), the same in all six C and X arms of each seed.
- **Pulse:** `NF_s` and `NB_s` were resolved perturbations in all six seed-direction
  cases. The peak orientation error was 2.07–2.60°, against a floor of 0.25°.

## Labels

| Push | Q_LOOP | Q_SIGN |
|---|---|---|
| F (forward, +x) | **LOOP_AMPLIFIES** | SIGN_INDEPENDENT |
| B (backward, −x) | **LOOP_AMPLIFIES** | SIGN_SPECIFIC |

D is the integral of root deviation from the arm's own unpushed control over 520.1–2,000
ms, in model mm·s. R = D(C)/D(N) and R′ = D(X)/D(N). The bar is R ≥ 1.10 in all seeds.

| Push | Seed | D(N) | D(C) | D(X) | R | R′ |
|---|---|---:|---:|---:|---:|---:|
| F | 1 | 0.0335 | 0.0416 | 0.0469 | 1.24 | 1.40 |
| F | 2 | 0.0270 | 0.0552 | 0.0423 | 2.04 | 1.57 |
| F | 3 | 0.0419 | 0.0558 | 0.0366 | 1.33 | 0.87 |
| B | 1 | 0.0322 | 0.0418 | 0.0390 | 1.30 | 1.21 |
| B | 2 | 0.0439 | 0.0600 | 0.0452 | 1.37 | 1.03 |
| B | 3 | 0.0424 | 0.0526 | 0.0360 | 1.24 | 0.85 |

**With the four conditional channels, the body was displaced more by both pushes, in
every seed.** The narrowest pass is R = 1.24. The prediction for F was possible
attenuation, and for B no consistent effect. Both were wrong.

**Q_SIGN splits by direction.**
- **F:** R′ also passes the amplification bar in seeds 1 and 2, so the flipped wiring
  reproduces the effect: SIGN_INDEPENDENT.
- **B:** R′ fails the bar in seeds 2 and 3 (1.03, 0.85): SIGN_SPECIFIC by the declared
  rule.
- Read the B label together with the next section. It is the declared outcome, but the
  measured channel activity does not show a push-driven reflex.

## What the channels did during the push (reported measures, not labelled)

**The loops did not respond to the push.** In each pushed arm, the window-mean hair-plate
rates and coxa offsets are close to those of its own unpushed control.

| Measure (window mean) | `_0` controls | Pushed (F, B) |
|---|---|---|
| LF hair-plate rate | 119.6–120 Hz | 119.9–120 Hz |
| LH hair-plate rate, C arms | 103.9–108.4 Hz | 101.1–109.7 Hz |
| LH hair-plate rate, N and X arms | 120 Hz | 120 Hz |
| LM, RM hair-plate rate | 0 Hz | 0 Hz |
| LF / LH offset, C | +0.17…+0.19 / +0.21 rad | +0.17…+0.19 / +0.20…+0.22 rad |
| LF / LH offset, X | −0.17…−0.19 / −0.22 rad | −0.18…−0.19 / −0.21…−0.23 rad |
| LM, RM offset, C and X | \|≤ 0.015\| rad | \|≤ 0.013\| rad |

- **Front and hind loops.** They act as near-constant posture offsets, saturated or
  close to it, from about 15–22 ms onward. They are effectively unchanged by a 20 ms push.
- **Middle loops.** They stay silent. In this unperturbed assisted posture the middle
  hair plates are below threshold (0 Hz). The 1.024 × 20 ms pulse never recruits them.
  - In C2 and C3 they reached 99–120 Hz only under an imposed servo-equilibrium
    displacement.
- **Coxa motor neurons.** Pushed-minus-control differences were at most about 6 Hz
  (T3 left, N arms). Their sign was not consistent across seeds or sets.

**The channels change the posture the push acts on.** Mean tilt over the run is:

| Set | Mean tilt over the run |
|---|---|
| N | 3.8–4.3° |
| C | 9.1–10.2° (peak about 11.4–12.9°) |
| X | 0.86–1.05° |

So the most likely mechanism of the amplification is the static posture change, through
the fixed LF/LH setpoint offsets. It is not a push-evoked reflex. That is the declared
SIGN_INDEPENDENT reading ("added servo stiffness or a posture shift"). It applies to B as
well, even though B's label is SIGN_SPECIFIC.

**This is an interpretation from reported measures, not a tested claim.** One way to read
the B split: the C and X postures tilt in opposite directions, so a backward push can
interact with them asymmetrically. That reading is untested.

## Other descriptives

- **No arm recovered** into the inherited relative band within the window
  (NOT_RECOVERED_IN_WINDOW), including every N arm. The band is not met even without the
  loops.
- **Peak orientation error:** N 2.07–2.60°, C 2.36–3.93°, X 2.54–3.38°.
- **Peak root deviation:** N 0.041–0.077 mm, C 0.069–0.091 mm, X 0.068–0.101 mm.
- **Support:** minimum contacts were 4 in all arms except CF_1 and XB_2 (3). There was no
  rollover and no low-height sample.
- **The signed fore-aft deviation has no consistent sign** across seeds or sets.
  - The cleared-window means are −0.025…+0.022 mm.
  - The deviation oscillates rather than holding a displaced position.

## Consequence (declared in advance)

**LOOP_AMPLIFIES is recorded as is.**
- The four conditional channels, as wired (H1), do not make the assisted body resist a
  fore-aft thorax push. They make the displacement 24–104 % larger.
- The reported measures indicate that this works through the posture the channels set,
  not through a reflex evoked by the push.

In every case:
- no channel, weight, threshold, gain, magnitude or seed changes;
- no coordinate status changes;
- coverage stays 20/42 admitted, +4 conditional.

**What this does and does not say about the conditional tier.** CONDITIONAL status
records that each channel resists displacement of its own joint (C1–C4). This test adds
two things:
- At the body level, in this posture, the loops are tonic offsets that destabilise. They
  do not stabilise.
- The middle loops are inactive without a displacement large enough to cross their
  threshold.

## Limits

- **Position-assisted posture.** All 42 servos stay on, and the loops only modulate
  setpoints. This is not independent balance.
- **One engineering pulse.** Magnitude 1.024 for 20 ms, from M9B, in a declared fore-aft
  direction. It is too brief and small to recruit the middle hair plates, and a larger or
  longer push could behave differently. That would need its own preregistered protocol.
- **Three seeds,** which vary only stochastic sensory timing. There is no noise estimate
  for R. The 10 % bar is an engineering resolution, and R ranged 1.24–2.04.
- **The mechanism reading is post hoc.** The posture explanation is drawn from
  preregistered reported measures, but it was not itself tested.
- **Root deviation is relative to a moving control,** so it is not absolute stability.

## Reproduce (Windows Git Bash, from the repository root)

```bash
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
for a in N0 NF NB C0 CF CB X0 XF XB; do for s in 1 2 3; do
  PYTHONPATH="$PWD" "$PY" -m malecns_backend.live.coxa_push_response --arm ${a}_$s \
    --output docs/evidence/coxa-push-response-v1/run/${a}_$s.json.gz; done; done
PYTHONPATH="$PWD" "$PY" -m malecns_backend.live.coxa_push_response \
  --evaluate docs/evidence/coxa-push-response-v1/run \
  --c0-dir docs/evidence/coxa-admission-v1/run \
  --output docs/evidence/coxa-push-response-v1/run/report.json
```

The arms take about 2.3 h in total. The expected result is INTEGRITY_ACCEPTED, with both
directions LOOP_AMPLIFIES (F SIGN_INDEPENDENT, B SIGN_SPECIFIC) and the arm hashes as in
the report.
