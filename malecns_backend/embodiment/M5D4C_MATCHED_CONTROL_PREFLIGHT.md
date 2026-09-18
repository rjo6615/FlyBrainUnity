# M5D-4C — matched-control correction and intervention preflight

## Status and scope

The checked-in artifact is **`NOT_RUN`**. This environment has not executed the
validated Windows FlyGym/MuJoCo stack, so no timestamps or physical result are
fabricated. M5D-4C is a 25-ms intervention-boundary preflight, not a rerun or
reinterpretation of canonical M5D-4 and not evidence of neural motor causality.

## Corrected control path

Both conditions construct the complete tactile → MaleCNS → six motor-observer →
decoder path. The observer and raw decoder calculation do not receive the
condition flag. Both use one `MatchedControlPipeline`; the flag is read exactly
once to define the admitted contribution:

```
raw = existing decoded antagonist offset
enabled_admitted  = raw
disabled_admitted = 0.0
candidate = baseline + admitted
command = final_range_clamp(slew(previous_physical_target,
                                 range_clamp(candidate)))
```

Thus baseline calculation, joint-range clamps, the unchanged 4 rad/s slew
limiter, command persistence, and command-array writing follow the same code.
The disabled decoder and observer continue evolving normally.

## Baseline and state

The baseline retains the M5D-4 convention: the current measured position is
sampled at each 0.5-ms neural update. The resulting actuator command persists
between neural updates. It is computed without the condition flag. Each fresh
condition owns a physical command pipeline. Its `previous_physical_target` is
initialized from that update's measured baseline, then updated only to the
common pipeline's final command. Consequently the histories must be exactly
equal while admitted contributions are zero, but may diverge as the intended
physical consequence of a nonzero enabled admission.

## Exact preflight rule

The intervention boundary is the first neural update at which the enabled
admitted contribution is nonzero. At that update, enabled and disabled raw
contributions must still match exactly and disabled admission must be exactly
zero. Before it, comparisons are exact (no tolerance) for all 42 commands, six
tibiae, adhesion, MuJoCo `ctrl`, `qacc`, `qvel`, `qpos`, numerical contact
forces, M5D-4A semantic contact sets, measured/baseline/previous targets,
observer/filter/raw decoder states, sensory encoding, and RNG state.

Classification is evidence driven and fail-fast. `PREFLIGHT_PASS` requires an
observed nonzero admission, exact pre-intervention equivalence, and no command
or physical divergence before admission. No intervention in 25 ms is
`NO_NEURAL_INTERVENTION`; feedback closure is optional. Even a pass means only
that the corrected design maintained exact physical equivalence before the
intended intervention and physical divergence did not precede it.

## Provenance

The live entry point verifies established M5D-2C/M5D-3 locks and semantic
manifests for canonical M5D-4, M5D-4A, and authoritative M5D-4B. These locks
select small scientific/status fields and fail closed; they do not hash giant
trajectories or depend on line endings. The canonical M5D-4 runner cannot be
called through this module: duration and seed are fixed at 25.0 ms and 1.

## Windows live command

From the repository root in the validated Windows environment:

```powershell
python -m malecns_backend.embodiment.tactile_motor_matched_control_audit --live --duration-ms 25.0 --seed 1 --json malecns_backend\embodiment\interface_output\tactile_motor_matched_control_preflight.json
```

This command writes only the M5D-4C artifact. It does not run or overwrite the
canonical 100-ms M5D-4 artifact.
