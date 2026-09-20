# M7C-B initial support / pose calibration

## Scope and evidence boundary

M7 is immutable scientific evidence. M7C-A was a read-only, zero-transition diagnosis of that evidence and its reset geometry. M7C-B is a new physics-only engineering calibration: it constructs no MaleCNS brain and may execute no neural transition. This repository change only implements and freezes the experiment; the local environment has neither FlyGym nor MuJoCo, so no physics candidate was executed and no result was invented.

## Installed-runtime provenance preflight

The project runtime used in the validated Windows evidence identifies the initial pose as `FlyGym default pose (no pose override)` and constructs `Fly(enable_adhesion=False, control="position")`, `SingleFlySimulation`, and `FlatTerrain` at 0.1 ms. The local environment cannot import `flygym` or `mujoco`, so Phase 1 inspection of the *installed Windows distribution's* package version, sources, examples, tests, pose resources, reset behavior, and defaults remains an explicit preflight requirement. The runner must record module paths, package versions, constructor signatures, and the exact installed files/functions establishing any supported pose. It must fail closed rather than infer those facts from internet documentation. No walking controller or reference trajectory is admitted.

## M7C-A geometry carried forward

The zero-step audit records root qpos position `[0, 0, 0.5]`, identity orientation, ground surface z=0, and six Tarsus5 centers with world z values from about 1.486 to 1.894. Conservative lower bounds (center z minus the largest recorded geom size) remain about 1.426 to 1.838, all above ground. Thus root z is a generalized coordinate, not foot height; z=0.5 does **not** put these feet near the physical ground. The state is conservatively classified **D: incompatible pose for the current joint configuration**, rather than a normal supported stance.

The inherited calibration box is centered beneath LMTarsus5 at z=1.4171913588 with half-height 0.002. It is therefore separate from the ground support plane and intentionally remains present and fixed in the primary experiment. The initial contact list contains two duplicate MuJoCo contact records for `0/LHCoxa` versus `0/RHCoxa`, each at distance -0.0245360594. There is no initial foot-ground contact. Dynamic persistence, resolution, and force are unknown until Windows execution.

## Frozen candidates and validity gate

Before execution, `m7c_b_preregistration.json` freezes exactly two candidates:

1. **canonical_control** — exact M7 root, orientation, default joints, measured post-reset 42-position baseline targets, disabled adhesion, and inherited surface.
2. **distal_tarsus_support_translation** — the same state with one geometry-derived vertical root translation, computed once as `ground_z - minimum(conservative Tarsus5 lower z)`. It is not a sweep and cannot be changed based on survival.

No locally defensible installed FlyGym standing-pose preset could be preregistered without access to the actual Windows installation. The Windows preflight must first document such a preset. If it exists, stop without physics and amend the preregistration in a new commit rather than silently changing this frozen candidate set.

Before any step, each candidate records root pose, qpos/qvel, 42 joints, targets and mismatch, every contact and distance/force, all foot positions, ground/body relationship, self-contact, and calibration-surface interaction. Nonfinite state, body penetration, severe foot penetration, unsupported feet, or mixed support surfaces fails closed. A gate failure is not rescued by later survival.

## Execution and interpretation

A passing candidate holds its measured reset joints with the baseline position controller for exactly 1,000 transitions at 0.0001 s (100 ms). Adhesion stays disabled and zero; the surface stays fixed. Samples include initial, 13 ms (transition 130), and 100 ms states; compact extrema/event summaries replace large telemetry. Fall remains `body height < 0.25`; rollover remains `body-up Z <= 0`. Contacts track exact geom pairs, penetration, force, persistence, and resolution. Mechanical viability is not locomotion.

Because local imports fail, the tracked result is explicitly `NOT_RUN_ENVIRONMENT_UNAVAILABLE`, with zero physics and neural transitions. No supported/unsupported execution classification is emitted before the validated run. Calibration-surface or static-adhesion follow-ups may be justified only from the corresponding single-variable evidence, never bundled here.

## Windows commands

From the repository root in the validated Windows environment:

```powershell
python -c "import inspect, importlib.metadata as m, flygym, mujoco; print(m.version('flygym')); print(flygym.__file__); print(mujoco.__version__); print(inspect.signature(flygym.Fly))"
python -m pytest tests/test_m7c_initial_support.py tests/test_m7c_initial_stability_audit.py -q
python -m malecns_backend.embodiment.m7c_initial_support --write-preregistration
```

Stop after these commands and document the installed-source standing-pose findings. Physics execution is intentionally not exposed until that preflight confirms or rejects an installed supported-pose candidate.

M7 CANONICAL RESULT MODIFIED: NO  
M7 SCIENTIFIC RERUN: NO  
M6C RERUN: NO  
MALECNS BRAIN CONSTRUCTED: NO  
NEURAL TRANSITIONS EXECUTED: 0  
NEURAL PARAMETERS CHANGED: NO  
MOTOR DECODER CHANGED: NO  
SENSORY MODEL CHANGED: NO  
GAIT CONTROLLER ADDED: NO  
BALANCE CONTROLLER ADDED: NO  
ADHESION CONFIGURATION CHANGED: NO  
CANONICAL RAW MODIFIED: NO  
M7C-B TYPE: PHYSICS-ONLY ENGINEERING CALIBRATION  
NEXT ACTION: `python -c "import inspect, importlib.metadata as m, flygym, mujoco; print(m.version('flygym')); print(flygym.__file__); print(mujoco.__version__); print(inspect.signature(flygym.Fly))" && python -m pytest tests/test_m7c_initial_support.py tests/test_m7c_initial_stability_audit.py -q && python -m malecns_backend.embodiment.m7c_initial_support --write-preregistration`
