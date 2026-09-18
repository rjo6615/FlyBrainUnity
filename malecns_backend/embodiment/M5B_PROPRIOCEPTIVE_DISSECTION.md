# M5B-1 — ambiguous proprioceptive sensor dissection

## Scope and scientific constraint

This is a read-only audit of the 15 `Coxa`, `Coxa_roll`, and `Coxa_yaw`
interfaces on LF, LM, LH, RM, and RH. RF is excluded because M5A classifies
its corresponding sensory mappings as `MISSING`, not `AMBIGUOUS`. The audit
does not alter M4A/M5A, activation eligibility, simulation behavior, or neural
parameters. Connectivity is descriptive evidence only and is never used to
assign sensory identity.

## Why every interface was ambiguous

M4A selects the same side/segment hair-plate population for each of the three
coxa-related FlyGym DOFs. The source bodymap metadata says `kind:
joint_angle`, and its `joint` is only `coxa_T{1,2,3}_{left,right}`. It contains
no axis, direction, roll, yaw, twist, abduction/adduction,
protraction/retraction, or flexion/extension discriminator. Thus each case has
both ambiguity **B** (one population spans multiple physical DOFs) and **C**
(the annotation identifies only the broader joint/segment).

The five populations are `hair plate T1 left` (1 body), `hair plate T2 left`
(18), `hair plate T3 left` (12), `hair plate T2 right` (15), and `hair plate
T3 right` (14). Within each included leg, all three interfaces receive exactly
the same population and body-ID set; consequently all IDs are shared and none
is unique to an axis. Candidate records are preserved separately on every
physical interface rather than being collapsed.

## Result

All 15 interfaces are `BROAD_PROPRIOCEPTIVE`: their population is defensibly
associated with the correct coxa region, segment, and side, but the local
annotation cannot separate the three model axes. There are zero
`RESOLVABLE_EXACT`, zero `RESOLVABLE_SUPPORTED`, zero `CONFLICTING`, and zero
`INSUFFICIENT` results, hence zero newly potentially resolvable interfaces.
This is an audit classification and is **not** activation eligibility or a
recommendation to promote a mapping.

The committed JSON includes the complete population body IDs, exact local
annotation vocabulary and provenance, per-leg 3-axis overlap, and a real
MaleCNS outgoing-connectivity summary. Direct downstream overlap is expected
to be identical among sibling axes because those axes start from the exact
same body IDs; that topology supplies no axis identity.

## Authoritative run

From the repository root on Windows:

```bat
python -m malecns_backend.embodiment.m5b_proprioceptive_audit --json malecns_backend/embodiment/interface_output/m5b_proprioceptive_dissection.json
```

For annotation-only development when graph artifacts are unavailable, add
`--annotations-only`; the output explicitly marks connectivity as not
computed and does not fabricate results.
