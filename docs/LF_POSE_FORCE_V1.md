# LF pose and source-force reference v1

Prospective reference-validation protocol, 2026-10-25. Baseline origin/newBrain
0eba000 (merged #268). Commit protocol, implementation, tests and input manifest
before the archived campaign. No CNS, production attachment, admission or neural
tuning. Keep all outcomes; no threshold/pose/epsilon search or unversioned retry.

## Reference and new modeling convention

Reuse the construction-free LF reference loader, four exact single-class tendon
hypotheses and original local J/R values. Broad promotors remain unassigned.
Load the original local FlyMimic best_combined_cvt3.xml only if its raw SHA is the
original a72d4a3167a6f6382d31936d32f2481db5895441a0cc2d02cdbd0452a6209a81.
Freeze every referenced asset's relative path, size and hash before measurements
in input-manifest.json. Do not edit source XML/assets, model parameters or the
validated MuJoCo 3.2.7 environment. Historical geometry was exported with 3.3.2;
require reproduction of its local J/R within 1e-10, not assumed version parity.

Source basis: [joint_LFCoxa_yaw, joint_LFCoxa_pitch, joint_LFCoxa_roll]. Target
basis: [joint_LFCoxa_yaw, joint_LFCoxa, joint_LFCoxa_roll]. This update declares a
new **modeled rotational correspondence**, not an anatomical finite-angle result:

    Q_G(q_G) = Q_M(q_M) Q_M(q_M_ref)^T

Q_M is the native source LFCoxa body's world rotation. Q_G is intrinsic XYZ
rotation Rx(q_G0) Ry(q_G1) Rz(q_G2), with zero at the old target reference.
Use SciPy Rotation's documented intrinsic uppercase XYZ convention. This matches
orientation changes only; it does not register translations, muscle attachments,
different body inertias or an actual moving FlyGym rig. Do not silently replace
the old frozen local registration with this new finite-angle convention.

At each pose, native source hinge axes form B_M; target instantaneous axes form
B_G. J(q)=inverse(B_G)*B_M and R_G(q)=inverse(J)^T*R_M(q). Native source moment
arms use R_M=-dL/dq; derive from exact tendon-actuator transmission, not names or
dominant axes. Validate J by finite differences of the new orientation mapping.
The exported function rejects nonrotations/singular or ill-conditioned bases;
it does not assign neuron-to-tendon or coordinate signs.

## Fixed observations

Use the complete 14-value source qpos in the original registration's default-pose
record. Keep every other source coordinate fixed. Ordered 15 co​​xa offsets:
zero; negative then positive .05 rad along each of three axes; all eight
lexicographic corners of {- .05,+ .05}^3. These are prescribed reference probes,
not generated neural behavior or a validated continuous pose envelope.

For each pose: fresh native data at activation a=0,.5,1 for all four selected
actuators and raw selected ctrl=a, all other activation/control values zero.
Velocities and time zero. Preserve native control limits (including positive
lower limits); record effective clamped controls. Never assume ctrl=0 means a=0
equilibrium or that zero activation means zero total muscle tension.

Also measure fresh +/-1e-6-rad source-coordinate perturbations about each pose
at activation/control zero: six extra observations per pose. At the central pose,
add activation .5 with ctrl=0 and ctrl=1 to inspect activation derivatives. Exactly
15*(3+6)+2 = **137 explicit mj_forward calls**, no time integration/CNS. Count the
Python API across preflight and execution; forbid mj_step. Compiler-internal
calculations are not counted as explicit calls. Every observation is retained.

Record all qpos/qvel/act/ctrl/act_dot, all actuator forces and transmission moment
rows, all tendon lengths, qfrc_actuator, selected native gain/bias/dynamics outputs,
coxa rotation and instantaneous axes. Preserve nonselected passive forces rather
than masking them. Source gravity, damping, equality constraints and muscles remain
unchanged; no source trajectory or body behavior is interpreted from qacc.

## Fixed acceptance and descriptive outputs

Require exact joint/body/tendon/actuator/DOF/activation-state ownership and unit
gear. Selected actuators must have native muscle dynamics/gain/bias types. Use
native mju_muscleGain/Bias/Dynamics as the reference component implementation;
do not add a competing Hill or neural activation model.

- Complete conditions, finite arrays, unchanged source/assets and fixed qvel/time.
- Reproduce central frozen J and four R_M columns within 1e-10.
- Native -dL/dq versus symmetric finite-difference tendon lengths: <=1e-7 absolute
  source-length/rad error. Native B_M and J versus rotation/coordinate finite
  differences: <=1e-7 absolute. Rotation reconstruction <=1e-10 matrix error.
- Basis/J condition numbers <100; no gimbal/branch/singularity substitution.
- Saved full moment matrix transpose times all actuator forces reproduces native
  qfrc_actuator within 1e-8 native generalized-force units.
- Selected F = gain*a + bias within 1e-8 native force units, act_dot versus native
  muscle dynamics at effective clamped ctrl within 1e-6 /s. Selected pulling force
  <=1e-8; no imposed nonzero force/activity requirement.
- Virtual work under J/R transform within 1e-9 native work units, using fixed
  dq_M=[.013,-.027,.009] and each observed selected tensile magnitude -F.

Report passive/active components, activation/deactivation derivatives, changes in
moment arms/transformed covectors and deviation from constant J/R descriptively.
No requirement that changes exceed a threshold, no selection of favorable poses.
These are numerical reference criteria, not biological acceptance. A failed
prerequisite or check remains failed; preserve partial observations on exceptions.

## Force units, production replacement and limits

Native model force/mass units are not independently tied to FlyGym or SI. The
gravity/mesh numeric scales alone do not establish that bridge. Retain source
force/time/length parameters as reference model choices, not fitted biology. No
copy of peak forces, passive laws, activation constants or existing 17-Hz neural
decoder scale into a new production pathway is justified here.

A future production design must selectively remove position actuation on the
three exact co​​xa coordinates before adding their tendon torques, verify zero
residual direct actuator force and keep the other 39 coordinate controls intact.
Do not globally disable the 20-motor interface or layer new torque over position
holding. That replacement must be matched across future control/treatment arms.
This update implements no such production mutation. Native source total force
includes unselected/passive muscles; source decomposition is not a complete
four-muscle biological model of a leg.

Original raw scientific prerequisites remain separately reported, not waived.
Successful reference checks support this declared map at sampled poses and source
force-law fidelity only. They establish no cross-body force scale, neural muscle
law, continuous pose validity, individual tendon binding, new admission or gait.

References: [MuJoCo muscle semantics](https://mujoco.readthedocs.io/en/3.2.7/modeling.html#muscle-actuators),
[MuJoCo actuation](https://mujoco.readthedocs.io/en/3.2.7/computation/index.html#actuation-model),
[SciPy intrinsic XYZ](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.from_euler.html).
Compilation itself performs internal model validation; no claim of zero internal
compiler operations follows from an observed mj_step API count of zero.
