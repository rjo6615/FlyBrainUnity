# M5D-4B — motor intervention boundary / runner audit

## Status and scope

The checked-in result is **NOT_RUN**. This milestone adds diagnosis-only
instrumentation for the original M5D-4 enabled/disabled runner semantics over
15 ms (seed 1, 0.1-ms physics, 0.5-ms neural updates). It does not rerun or
modify the canonical 100-ms artifact and makes no motor-causality claim.

## Static control-flow finding

The first logical difference exists at condition construction: `apply_motor`
is true for `TACTILE_MOTOR_ENABLED` and false for
`TACTILE_MOTOR_DISABLED`. This label/flag difference is not itself physical.

At each 0.5-ms neural update, the original runner samples measured joint
positions and calls every decoder with
`apply_neural_offset=apply_motor`. The decoder computes base plus gated offset,
range-clamps, slew-limits from its persistent `previous_target`, clamps again,
and stores the new previous target. The runner then makes a second
condition-dependent choice:

* enabled writes `command.target_position_rad`;
* disabled bypasses that target and writes the current measured position.

Both branches retain their command arrays between neural updates. Thus, after
the initial decoder update, measured motion can make the enabled branch's
persistent previous-target/slew result differ from the disabled branch's fresh
measured-position hold even while decoded offset is exactly zero. This is the
first statically identified route by which condition state **can** enter the
physical command pipeline. It is a hypothesis until the Windows trace proves
the exact first value and propagation; it is not reported as the cause here.

## Telemetry meaning

`first_mapped_tibia_motor_spike` scans mapped spike increments.
`first_nonzero_decoded_tibia_output` scans decoded offsets.
`first_applied_neural_output` scans the runner's `applied_output`, defined as
decoded offset in enabled and zero in disabled. It is therefore meaning **B**:
the first nonzero specifically labelled decoded neural offset, not the first
condition-dependent action or `ctrl`. The 14.5-ms value is not, by its
implementation, proof of the physical intervention boundary.

## Mutable state

Static inspection shows fresh simulation/model/data, MaleCNS, encoder/RNG,
decoder/observer set, pending set, row list, and command array are constructed
inside each condition call. No class-level decoder state was found. Each
decoder owns `previous_target`; each observer owns copied counts and filter
arrays. The live diagnostic records object identities and fails the scientific
classification unless exact action/`ctrl` propagation is observed. No shared
mutable-state mechanism is claimed without that live evidence.

## Live trace and comparisons

For all six locked tibia indices (LF 5, LM 12, LH 19, RF 26, RM 33, RH 40),
the diagnostic records the measured base, observer and decoder state,
activations, requested and gated offset, actual clamp/slew order, final action,
and pre-step MuJoCo `ctrl`. It separately compares all 42 joint commands, six
tibiae, six adhesion commands, full `ctrl`, qacc, qvel, qpos, contact state,
and contact forces using exact equality.

Because this environment has not executed validated Windows FlyGym/MuJoCo,
logical divergence, effective physical intervention, and every physical
divergence remain null in the checked-in artifact. The classifier will not
turn the static base/hold risk into a causal result.

## Provenance and execution

The runner validates the existing M5D-2C/M5D-3 locks and semantic manifests
for canonical M5D-4 and authoritative M5D-4A before live setup. M5D-4A is
locked by its scientific fields rather than its large trajectory bytes or line
endings. A mismatch fails closed.

From the repository root on the validated Windows environment:

```powershell
python -m malecns_backend.embodiment.tactile_motor_boundary_diagnostic_audit --live --json malecns_backend\embodiment\interface_output\tactile_motor_boundary_diagnostic.json
```
