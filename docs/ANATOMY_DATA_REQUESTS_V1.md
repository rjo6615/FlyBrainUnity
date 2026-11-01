# Anatomy data requests V1 — drafts for the remaining 22 motor coordinates

**WITHDRAWN 2026-11-01 by the user: do not send.** This is a local personal
project; no one outside it is to be contacted and no project information is to
be sent. The drafts below are kept only as a record of the exact blockers.

2026-11-01. Original status: drafts, not sent; the agent contacts no one. No code, mapping, admission flag,
sign, gain or evidence changes. Coverage remains 20/42.

## Why requests are the next roadmap step

All 22 unadmitted coordinates are blocked on evidence that the reviewed public
sources do not contain (`REMAINING_LEG_ADMISSION_RESULTS.md`,
`LF_ATTACHMENT_DECISION_RESULTS.md`, `LF_REFERENCE_ACQUISITION_V1.md`,
`LF_ANATOMICAL_CROSSWALK_RESULTS.md`, `DISTAL_ANATOMICAL_QUALIFICATION_RESULTS.md`).
The V1.2 assistance campaign showed that the 20 admitted channels cannot hold
posture without the 22 baseline-only servos, so these coordinates are now the
main bottleneck. Guessing from names, mirroring other legs, or choosing the
mapping that makes joints move is forbidden by the project rules.

| Blocker | Coordinates | Request |
|---|---:|---|
| Coxa / Coxa_roll shared-axis binding | 12 | A (attachments) and B (per-neuron muscle targets) |
| Coxa_yaw anatomical action sign | 6 | A (rotator lines of action) and B |
| Middle/hind Tarsus1 target populations | 4 | B (T2/T3 tarsal serial homologs) |

## Request A — musculoskeletal model authors (FlyMimic)

Recipients: the corresponding author(s) of FlyMimic, arXiv
[2509.06426](https://arxiv.org/html/2509.06426v2), repository
[gizemozd/FlyMimic](https://github.com/gizemozd/FlyMimic). Use the contact given
in the paper; do not guess an address.

> Subject: Request: coxa muscle attachment correspondences for FlyMimic / NeuroMechFly assets
>
> Dear FlyMimic authors,
>
> I am building a connectome-driven fly body simulation (MaleCNS motor neurons
> driving a FlyGym/NeuroMechFly MuJoCo body). I would like to use your coxa
> muscle paths for the thoraco-coxal joint, but I cannot place them on the
> NeuroMechFly body without an independent correspondence, and I have read
> the rig-identity caution in FlyGym issue #276.
>
> Would you be able to share any of the following, or point me to where they live?
>
> 1. The model-development material behind FlyMimic. The link
>    `github.com/gizemozd/neuromechfly-muscles` returns 404 for me.
> 2. Labeled attachment or anatomical-landmark correspondences between your
>    source bodies (`Thorax.stl`, `LFCoxa.stl`) and the NeuroMechFly meshes
>    (`flygym/data/mesh/Thorax.stl`, `RFCoxa.stl`, which FlyGym mirrors for the
>    left front leg). Most important are the origin (p1) and insertion (p296)
>    of the pleural remotor/abductor (Miller 29), sternal anterior rotator
>    (Miller 31), sternal posterior rotator (Miller 32) and sternal adductor
>    (Miller 33).
> 3. The frame, origin, length units and left/right reflection convention for
>    those points, plus any estimate of their uncertainty.
> 4. Whether coxa muscle paths exist, or are planned, for the middle and hind legs.
>
> I would cite the source and keep your data separate from any values I infer.
> The exact asset hashes I am working with are listed below. Thank you for
> considering this.
>
> [Your name, affiliation if any, contact]

Attach or paste: the eight `required_endpoint_references` and the `mesh_locks` from
`docs/evidence/lf-attachment-decision-v1/run/reference-request.json`, which
include the model and mesh SHA-256 values.

## Request B — leg motor-neuron anatomy (MANC / BANC / MaleCNS teams)

Recipients: the corresponding author(s) of the MANC leg motor-neuron study,
eLife [96084](https://elifesciences.org/articles/96084), and/or the BANC or MaleCNS
annotation maintainers. Use published contacts or their issue trackers.

> Subject: Request: per-neuron muscle targets for coxa and T2/T3 tarsal motor neurons
>
> Dear authors,
>
> I am mapping MaleCNS leg motor neurons onto a simulated fly body and I am
> blocked on three questions that your annotations come closest to answering.
>
> 1. **Coxa motor neurons, T1-T3.** For the pools below, is there a per-neuron
>    muscle target (not only the class label)? For example, which of the four
>    T1 promotor neurons innervate the tergopleural versus the pleural promotor,
>    and do the pleural remotor/abductor neurons drive one muscle or two?
> 2. **Rotator action.** Is there a recorded or traced line of action for the
>    sternal anterior and posterior rotators, i.e. which direction each rotates
>    the coxa about its long axis?
> 3. **T2/T3 tarsus levator/depressor serial homologs.** Your Figure 7D lists
>    these as unresolved. Has anything since then identified the middle- and
>    hind-leg tarsal motor neurons? In BANC, MNml81 and MNhl64/MNhl65 are possible
>    leads, but their references conflict.
>
> The exact MaleCNS body IDs are listed below. Any partial answer, including
> "unknown", would help me avoid assigning targets by guesswork. Thank you.
>
> [Your name, affiliation if any, contact]

Attach or paste this table (MaleCNS body IDs from the repository's audited
neurons index; see `evidence/remaining-leg-admission-audit-v1_1/audit.json`):

| Population (MaleCNS annotation) | Body IDs | Model coordinates it is a candidate for |
|---|---|---|
| Tergopleural/Pleural promotor MN T1 left | 800061, 801173, 807281, 934091 | LFCoxa |
| Tergopleural/Pleural promotor MN T1 right | 801824, 802072, 805745, 810535 | RFCoxa |
| Pleural remotor/abductor MN T1 left | 802509, 803803 | LFCoxa, LFCoxa_roll |
| Pleural remotor/abductor MN T1 right | 803314, 805313 | RFCoxa, RFCoxa_roll |
| Pleural remotor/abductor MN T2 left | 800541, 902492, 905421 | LMCoxa, LMCoxa_roll |
| Pleural remotor/abductor MN T2 right | 800776, 803499, 902719 | RMCoxa, RMCoxa_roll |
| Pleural remotor/abductor MN T3 left | 800175, 902310 | LHCoxa, LHCoxa_roll |
| Pleural remotor/abductor MN T3 right | 800290, 800553 | RHCoxa, RHCoxa_roll |
| Sternal adductor MN T1 left / right | 813480 / 815854 | LF / RF Coxa_roll |
| Sternal adductor MN T2 left / right | 816018 / 909371 | LM / RM Coxa_roll |
| Sternal adductor MN T3 left / right | 904184 / 807854 | LH / RH Coxa_roll |
| Sternal anterior rotator MN T1 left / right | 806923, 919509 / 801469, 801918 | LF / RF Coxa_yaw |
| Sternal anterior rotator MN T2 left / right | 832490, 903689 / 801813, 801946 | LM / RM Coxa_yaw |
| Sternal anterior rotator MN T3 left / right | 801548, 802215 / 800316, 906235 | LH / RH Coxa_yaw |
| Sternal posterior rotator MN T1 left | 801915, 804851, 808640, 1050335829 | LFCoxa_yaw |
| Sternal posterior rotator MN T1 right | 805410, 808011 | RFCoxa_yaw |
| Sternal posterior rotator MN T2 left | 801768, 803226, 803704, 1051054875 | LMCoxa_yaw |
| Sternal posterior rotator MN T2 right | 800962, 801761, 802521, 818996 | RMCoxa_yaw |
| Sternal posterior rotator MN T3 left | 801492, 801715, 802964, 818399 | LHCoxa_yaw |
| Sternal posterior rotator MN T3 right | 903642, 903643, 907256, 1050493413 | RHCoxa_yaw |
| (none found) T2/T3 Tarsus1 | — | LM/LH/RM/RH Tarsus1 |

## How replies would be used

A reply is new reference material, not an admission. Each one gets its own
versioned qualification review against the existing requirements in
`reference-request.json` and the admission audit: provenance and revision, raw
hash, frames/units/laterality, per-neuron identity and uncertainty. Conflicting
or partial answers are preserved, not resolved by choosing the favorable one.
Only a passed review can lead to a separately preregistered, bounded admission
protocol, and any later behavioral effect remains a measured outcome. A null or
missing reply leaves the coordinates blocked, recorded as such.

Track sending in the handoff as: request, recipient, date sent, reply status.
