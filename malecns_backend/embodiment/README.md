# Milestone 3B — one-leg MaleCNS ↔ NeuroMechFly interface

This package is the first deliberately narrow embodiment layer for
`MaleCNSBrain`. It **does not make the fly walk**. It has no gait, oscillator,
behavior state, root translation, posture recovery, or Unity dependency.

## Selected pathway

The selected physical degree of freedom is the **left middle-leg (T2/LM)
tibia joint**. This is the strongest compact choice in the audited map because
all three ends have an explicit, identical `tibia_T2_left` target:

* `chordotonal T2 left`: 80 annotated sensory neurons;
* `Ti extensor MN T2 left`: two annotated motor neurons, direction `+1`;
* `Ti flexor MN T2 left`: five annotated motor neurons, direction `-1`.

The exact records are resolved—not rediscovered—from
`../interface_map.json`. The FlyGym correspondence is LM action element 12,
`joint_LMTibia` (the tibia element in the second of six seven-DOF leg blocks).
That coordinate correspondence is an explicit engineering mapping, not a
connectome fact.

## Separation of responsibilities

* `mappings.py`: exact, validated 3A audit records and anatomical provenance.
* `sensory.py`: unit-preserving physical frame and modeled population code.
* `motor.py`: cumulative-count observation, 40-ms filter, modeled antagonist
  decoder, and safety clamps.
* `body.py`: optional headless FlyGym adapter. It never imports a FlyGym CPG or
  preprogrammed step controller.
* `loop.py`: explicit causal multi-rate scheduler.
* `telemetry.py`: selected-signal JSONL, never whole-CNS state dumps.
* `experiment.py`: opt-in bounded real experiment.
* `audit.py`: engineering validation and dependency/status report.

`MaleCNSBrain` remains body-independent. Its existing generic
`set_external_drive(indices, rates)` API already has the required semantics:
the supplied values are rates in Hz, and `step()` samples stochastic external
events at `rate * neural_dt / 1000`. Consequently no neural-runtime API change
was needed and sensory encoding never writes voltage, weights, or motor cells.

## Equations and units

The raw `LegSensoryFrame.tibia_angle_rad` is **PHYSICS_MEASURED** in radians.
The **MODELED_TRANSDUCTION** is the reference application's ordered Gaussian
population code:

```text
x = (q - (-1.35 rad)) / (1.30 rad - (-1.35 rad))
preferred_k = (k + 0.5) / N
rate_k = 120 Hz * exp(-(x - preferred_k)^2 / (2 * 0.25^2))
rate_k = 0 when rate_k <= 5 Hz
```

There is no separately added proprioceptive baseline. Zero radians is a real
joint position and therefore normally produces nonzero population activity.
The left population is never reflected or copied to the right. Distribution
is one ordered preferred angle per audited dense index. Transduction is
deterministic; stochasticity occurs only in the ordinary MaleCNS external-rate
input process. The source is `fly-brain-main/src/sim/senses.js::popCode`.

For every selected motor neuron and observation interval `Δt`:

```text
instantaneous_i = (count_i(t) - count_i(t-Δt)) * 1000 / Δt_ms
filtered_i(t) = filtered_i(t-Δt) + (Δt_ms / 40 ms)
                * (instantaneous_i - filtered_i(t-Δt))
population_rate = arithmetic mean(filtered_i)
activation(r) = 1 - exp(-r * ln(2) / 17 Hz)
offset = 0.25 rad * (activation(extensor) - activation(flexor))
```

Count increments and the 40-ms filter reproduce
`fly-brain-main/src/sim/motor.js::Motor.readBrain`. Antagonist signs are
**ANNOTATION_DERIVED**. Activation, differential magnitude, and conversion to
a FlyGym position target are **MODELED_MOTOR_DECODING**, not connectome-derived.

## Timing and causal order

| Quantity | Interval |
|---|---:|
| MaleCNS neural step | 0.5 ms |
| MuJoCo physics step | 0.1 ms |
| control interval | 1.0 ms |
| sensory sample | 1.0 ms |
| motor decode | 1.0 ms |

Each control interval observes the current body, encodes and applies rates,
advances two neural steps, observes motor counts, computes one command, and
then advances ten physics steps. Thus the new command cannot affect the sensor
sample that produced it.

## Safety constraints

Engineering-only clamps restrict the selected joint to `[-1.35, 1.30]` rad,
the modeled per-sample offset to `±0.25` rad, and target slew to `4 rad/s`.
They do not coordinate limbs, create a gait, select behavior, or restore pose.
Nonselected FlyGym joints are held at their latest observed positions because
the FlyGym position-control action is a complete 42-element vector.

## Commands

```bash
python -m malecns_backend.embodiment.audit
python -m malecns_backend.embodiment.audit --run-real
python -m unittest discover -s tests -p "test_embodiment.py" -v
```

The first command validates components and reports whether the real experiment
ran. `--run-real` refuses to substitute a fake body if FlyGym is unavailable.
Test fixtures exercise only isolated interfaces and never count as a
NeuroMechFly result.

See [EXPERIMENT_REPORT.md](EXPERIMENT_REPORT.md) for the experiment status and
all unresolved assumptions.
