# LF proximal reference binding review v1

Prospective contract, 2026-10-25. Data/reference inspection only; zero CNS or
physics transitions, no admission, no force application and no decoder changes.
Baseline: origin/newBrain e5964d0 (merged PR #265). Commit this specification and
implementation before generating the new derived report. Existing results and
original raw-freeze expectations remain authoritative and unchanged.

## Question and fixed evidence

Can the five exact LF populations be bound to the seven existing tendon hypotheses
with justified activation semantics, and does that suffice for a position decoder?
Reuse the complete v1.1 admission reviewer, including body-ID/dense-index/alias
verification, old nulls and local covector checks. Use every candidate inventory
entry and every tendon hypothesis; never select by activity, axis dominance or
movement. Require exact agreement with all seven registered tendons and bases.

Inspect the original local FlyMimic XML as bytes. Its SHA256 must equal the frozen
registration's source-model hash a72d4a3167a6f6382d31936d32f2481db5895441a0cc2d02cdbd0452a6209a81.
The CLI requires its explicit path; absence or mismatch stops this review. Parse
the XML without compiling/loading physics. Preserve each selected actuator's
attributes and its muscle default, exact tendon sites and raw hash. Check unique
actuator/tendon bindings, muscle dynamics/gain/bias inheritance, positive specified
peak force, nonnegative control range and unit transmission gear. This is a static
source contract, not a measured activation/force response. Do not copy parameters
into the validated FlyGym model or install FlyMimic's different physics version.

## Reference semantics to test

The frozen convention is R = -dL/dq. For tensile magnitude T >= 0, virtual work
gives tau = -T*dL/dq = T*R. MuJoCo's negative muscle scalar force and transmission
gradient are consistent with this identity. R_G = J_GM^(-T) R_M remains the existing
local reference transform. Report each three-component R_G and its component
signs **conditional on positive tensile force**, never as a neuron-to-angle sign.
Zero tension gives zero active tensile contribution; passive tension, force-length
and velocity effects and activation dynamics require separate treatment.

References checked 2026-10-25:

- [MuJoCo 3.2.7 muscle actuators](https://mujoco.readthedocs.io/en/3.2.7/modeling.html#muscle-actuators):
  activation produces pulling force, with active and passive terms.
- [MuJoCo 3.2.7 actuation](https://mujoco.readthedocs.io/en/3.2.7/computation/index.html#actuation-model):
  the transmission maps scalar actuator force into generalized forces.
- [FlyMimic authors' repository](https://github.com/gizemozd/FlyMimic): converted
  OpenSim musculoskeletal models used for imitation learning. This review uses the
  exact locally frozen XML hash, not a claim that current upstream equals it.
- [Azevedo et al. supplementary anatomical methods](https://faculty.washington.edu/tuthill/docs/azevedo24_appendix.pdf),
  Table A1 and Figure A4: promotor classes have anterior actions; the remotor/
  abductor has posterior/lateral actions. Figure A4 distinguishes tendon-linked
  remotor/abductor insertions from direct posterior-rotator cuticle insertions.
  These qualitative class observations do not identify the repository's individual
  MaleCNS body IDs or split its broad promotor pool into model tendons. Access here
  was through indexed text excerpts; the full large PDF could not be fetched by
  the web reader. No claim of full figure or specimen-to-specimen matching.

## Decisions fixed before report generation

Keep all exact identities and aliases. One existing tendon hypothesis for a class
is a single hypothesis, not independently confirmed biological binding. The broad
promotor retains three alternatives; each of its four body IDs has an unassigned
tendon. All other per-neuron tendon assignments also remain unassigned absent an
independent crosswalk. Never average alternatives or infer membership from order.

For every population, neuron-to-tendon crosswalk, spike-to-activation law,
activation-to-force transfer and force-to-position-target transfer remain explicit
unresolved gates. Existing MotorDecoder.activation is a modeled rate conversion,
not independent proximal muscle calibration. Its 17-Hz scale and all other neural
and motor parameters remain unchanged. An anatomical action, coordinate torque,
instantaneous acceleration and position target are distinct quantities; coupled
inertia, constraints, coactivation and pose prevent substituting one for another.

Report outcome is REFERENCE_SEMANTICS_ONLY_ADMISSION_BLOCKED when static contracts
hold. No candidate is admission-ready. Old raw-freeze failures remain reported as
failures even if canonical Git content agrees. A failed new static contract is an
integrity error, not an invitation to refresh the expected hash or pick a new model.

## Follow-on gate

Next acquire an independently traceable per-neuron/per-muscle crosswalk (or retain
the unresolved class explicitly), and specify whether the intended interface is a
muscle-force model or an explicitly engineered position-target approximation.
Neither path may silently reuse geometric magnitudes as gains. Declare supported
pose/range, force units, temporal activation/passive terms and transfer validation
before a bounded application experiment. No bounded CNS/physics admission protocol
is executable yet because those numerical/application prerequisites are absent.
The original raw scientific prerequisites must also pass independently first.

## Manual Git Bash check after merge

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain
git pull --no-rebase --no-edit
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe"
MODEL="$HOME/Documents/FlyMimic/flymimic/assets/models/best_combined_cvt3.xml"
"$PY" -m malecns_backend.embodiment.lf_proximal_binding_review --model "$MODEL" --report docs/evidence/lf-proximal-binding-review-v1/review.json
code docs/LF_PROXIMAL_BINDING_RESULTS.md
```

Expected: reference review verified; seven tendon hypotheses; five populations;
20/42 unchanged, newly admitted 0, CNS/physics transitions 0; admission BLOCKED.
This does not launch Unity or rerun prior scientific trials.
