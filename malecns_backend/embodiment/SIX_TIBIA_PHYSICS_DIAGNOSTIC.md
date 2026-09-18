# M4C-2A passive `-RH` physics diagnostic

This diagnostic answers an engineering question about the reproducible MuJoCo
`mjWARN_BADQACC` outcome. It does **not** alter or repair the model. In
particular, it changes no physics setting, timestep, solver, contact, limit,
gain, decoder, encoder, neural parameter, connectome, initial state, seed, or
intervention. It neither clamps invalid values nor retries a condition.

## Exact Windows command

From the repository root:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.six_tibia_physics_diagnostic --json malecns_backend/embodiment/perturbation_output/six_tibia_minus_rh_physics_diagnostic.json
```

The command uses the existing M4C-2 condition runner to create fresh seed-1
`ALL SIX` and `-RH` conditions. It does not run the other five interventions.

## What is recorded

Immediately before each MuJoCo call, a bounded approximately 20 ms ring stores
the control and simulation times, the DOF-39 joint position, qvel and prior
qacc, associated actuator control and force, limit proximity, all six tibia
positions/velocities/targets/decoded offsets, body pose, finite checks, and the
largest absolute qvel/qacc with their indices. Sparse 475, 480, 485, 490 and
495 ms samples support the matched comparison without a long dense tensor.

The JSON distinguishes `last_successful_state` from
`input_to_failed_physics_step`. No post-exception MuJoCo state is read.

## DOF identity and interpretation

The command resolves DOF 39 against the instantiated `mjModel`: it finds the
unique `jnt_dofadr` interval containing 39, then independently obtains the
joint's `jnt_qposadr` interval, body, type, limits and joint-transmission
actuators. Names come from the model name table. Missing or ambiguous metadata
is emitted as unresolved rather than inferred from source/action ordering.

If the real run confirms extreme divergence, it should be described only as
**a reproducible physical/numerical divergence under the modeled `-RH`
sensory-withholding counterfactual**. A MuJoCo invalid-state warning is an
engineering/model outcome, not evidence of biological, gait, balance, or
coordination failure.
