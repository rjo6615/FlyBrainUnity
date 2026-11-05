# FlyBrainUnity — local Codex handoff

## Antennal gravity Step D (JO zone-crossing tilt): design — 2026-11-05

Designed only (no protocol, code or run). Why: Step C kept d <= 0, so it compared the E route
with the C route instead of opposite zones for opposite tilts. Step D places the tilt so d
crosses zero: LEVEL (no gravity change, expected window d ~ -0.18 from C2) vs DOWN20 (gravity
R_y(-20 deg) at state 5005, expected ~ +0.17 from Step B geometry + C2 posture terms). Arms
{OFF, G1, FLIP} x {LEVEL, DOWN20} x new seeds 19-24 + REPRO_N0_7 = 37 (~3 h); Step C context,
measures, statistics, labels and I1-I7 unchanged except the tilt set. New O1 operating-point
condition on OFF arms (window d > +0.05 DOWN20, < -0.05 LEVEL, else
INCONCLUSIVE_OPERATING_POINT). Predictions recorded: P1 G1 CONSISTENT, P2 FLIP CONSISTENT,
P3 r_GF < 0 (E drive goes off under G1, on under FLIP), P4 DNp73/DNbe001 opposite signs in
G1 vs FLIP in all seeds. No zone-sign, balance or corrective claim. See JO_ZONE_CROSSING_V1.md.

IMMEDIATE NEXT (on approval): lock protocol, build module/tests, smoke, commit, run 37 arms.

## Antennal gravity Step C2 (JO operating-point attribution): ROOT / GRAVITY — 2026-11-05

Preregistered (d3d76db, protocol 1527f2fc), run once (geometry replay of the 36 Step C arms,
1.18M mj_forward, ~8 min), evaluated once (result 981ee47c). INTEGRITY_ACCEPTED: replay of
recorded jo_d bit-exact (max diff 0.0 over 144k ticks), state-0 d = Step B rest, Shapley
additivity 2e-16. Q1 (pre-tilt drift, -0.030 L / -0.025 R): DOMINANT_ROOT both sides -- body
pitches 3.4-6.2 deg nose-up relative to gravity (ROOT -0.06), passive neck sags ~2.0 deg
nose-down (NECK +0.033, opposes), antenna joints negligible (A2+A3+ARISTA < 0.001; a2-a3
deflection ~0.01-0.03 deg). Q2 (window): DOMINANT_GRAVITY for UP and DOWN; beside the tilt,
ROOT lowers d in both directions (-0.096 UP, -0.057 DOWN), which is why Step C's nose-down d
sat at ~0. Tilt contrast DOWN-UP 0.34-0.38 = gravity 0.335 + ROOT 0.04 (OFF/FLIP; only
0.008-0.030 in G1). Encoder and Step C labels unchanged. Observation (not tested): the
model's a2-a3 joint barely deflects, so a joint-angle JO encoder would carry almost no
signal without a mechanics change. See JO_OPERATING_POINT_RESULTS.md.

IMMEDIATE NEXT: user's choice. Candidates (each its own versioned design): a JO live step
whose tilts are placed around the measured live operating point (pre-tilt d ~ -0.18,
posture response included) so both zones engage, with expected d verified as integrity;
or neck stabilisation (connectome-driven neck motor output) as its own track.

## Antennal gravity Step C2 (JO operating-point attribution): design — 2026-11-05

Designed only (no protocol, code or run). Why: in Step C the live JO drive drifted from
Step B's rest value (-0.144 at t=0) to about -0.17 before the tilt and about -0.38 after the
nose-up tilt, so the nose-down tilt only reached d ~ 0 and each assignment modulated one zone.
Method: replay recorded qpos of the 36 Step C seed arms through mj_forward in the Step B
runtime; exact 6-factor Shapley attribution of d(target) - d(state 0) over ROOT orientation,
NECK (Head joints, passive k=10), A2 (Pedicel), A3 (Funiculus, the a2-a3 JO joint), ARISTA
(all passive k=1.0, FlyGym defaults) and GRAVITY. Targets: state 5005 (Q1, pre-tilt) and
the window mean (Q2, UP/DOWN separately). Integrity J1-J4 (hashes, replay equals recorded
jo_d to 1e-9, state-0 d = Step B rest, additivity). Labels DOMINANT_<factor> (median share
>= 0.5 and sign in >= 90% arms) / MIXED / NO_MATERIAL_DRIFT. No CNS, no physics stepping, no
encoder or Step C label change. See JO_OPERATING_POINT_V1.md.

Superseded by the run above.

## Antennal gravity Step C (live JO tilt routing): G1 CONSISTENT, FLIP WEAK — 2026-11-05

Preregistered (0ef9dbe, protocol 05655b40), two plumbing smokes deleted unread, 37 arms run
once (fresh processes), evaluated once. INTEGRITY_ACCEPTED: I1-I7 pass (REPRO_N0_7 = N0_7
exactly); OFF peak tilt 17.5 deg (< 45). G1 (C=+d, E=-d): JO_TILT_PATTERN_CONSISTENT, rho 0.70,
p 1/32 (floor), all 15 seed-pair correlations > 0. FLIP: JO_TILT_PATTERN_WEAK, rho 0.06,
p 0.22. r_GF +0.39 (not additive). Key finding: the live body starts slightly nose-up, so the
first post-tilt d was ~-0.34 (UP) and ~0 (DOWN), d <= 0 in both; the tilt modulated only
the E set under G1 (~40 -> ~1 Hz) and only the C set under FLIP. So G1 vs FLIP compares the
E route vs the C route, not mirrored zone use (design expected DOWN d ~ +0.03). E route:
DNp73/DNbe001/DNg29/DNp18/pIP1 DOWN-UP -4 to -21 Hz, same sign 6/6 seeds (silent in OFF);
C route reaches only DNg29 weakly. Tonic E triples leg-MN rate (6 -> 16-20 Hz) and adds
4-5 deg roll before the tilt; tonic C leaves MNs unchanged. Largest S_G1: T3 right
femur_twist/coxa_abduct/coxa +7-9 Hz (pools that drive no admitted joint). Not balance, not
corrective, no zone-sign claim, no coordinate change. See ANTENNAL_GRAVITY_LIVE_RESULTS.md.

IMMEDIATE NEXT: user's choice. Candidates (each needs its own versioned design): a JO
operating-point/frame check (why the live rest d sits below Step B's level-head value), a
design that engages both zones (tilts spanning d = 0), or a test of whether the E-route
pattern acts on admitted joints.

## Antennal gravity Step C (live JO tilt routing): design — 2026-11-05

Designed only (no protocol, code or run). Question: does a sustained 10 deg pitch tilt,
encoded by the Step B JO encoder, change leg-MN activity in a seed-consistent pattern beyond
the other senses? Context: push-response N (A_ON assisted posture, hair plates, 20 v3
channels, no coxa channel, no push). Tilt = model.opt.gravity rotated -10 (DOWN) / +10 (UP)
deg about world y at state 5005, held. Arms OFF/G1/FLIP x UP/DOWN on new seeds 13-18 + REPRO_N0_7
= 37 arms (~3 h); schedule proprio+hair+JO common to all arms (CRN), JO withheld in OFF.
Measure: window 520-2000 ms, leg MN pools; Delta = DOWN-UP; S = Delta_ON - Delta_OFF;
rho = mean pairwise seed correlation of S; exact sign-flip p (min 1/32). Labels per
assignment: JO_TILT_PATTERN_CONSISTENT (rho>0, p<=1/32) / WEAK (p<=0.25) / NO_CONSISTENT.
r_GF (G1 vs FLIP) reported as a linearity check; it cannot identify zone sign. Integrity
I1-I7 + OFF no-rollover precondition. No balance claim, no admission. See
ANTENNAL_GRAVITY_LIVE_V1.md.

Superseded by the run above.

## Antennal gravity Step B (kinematic JO C/E encoder): ENCODER_READY — 2026-11-05

Preregistered (2e2def7, protocol 0e97fe33), one discarded-unread smoke, run once (geometry
only, B4 runtime, imposed whole-body rotations, mj_forward; result 35ff3da4). B0-B4 pass:
t.x_head 0.966, sets = Step A, |d| <= 1 (-0.61..0.36), mirror max diff 3.5e-9, monotonic in
pitch. Rest (level head) d = -0.144 both sides -> G1: E 17.2 Hz, C 0 (FLIP: C 17.2 Hz).
Pitch slope 0.965/rad (nose-down raises d; zero crossing +5..+10 deg nose-down); roll slope
+-0.215/rad opposite per side (small roll channel, descriptive only under the L/R rule).
All three recorded predictions held (same geometry, so an implementation check, not fly
evidence). Step C must separate the tonic rest drive (~17 Hz in one zone per side) from the
tilt-dependent part, e.g. tilt-direction contrasts within an arm. See
ANTENNAL_GRAVITY_ENCODER_RESULTS.md.

IMMEDIATE NEXT: Step C design (live JO_OFF / G1 / G1_FLIP in the assisted-posture context;
preregistered pitch-driven, within-side contrast; no balance claim, no admission).

## Antennal gravity Step B (kinematic JO C/E encoder): design — 2026-11-05

Designed only (no protocol locked, no code, no run). Signal: d = gravity . t, where t is the
arista's motion tangent for a3 rotation about its geometric long axis (funiculus anchor ->
funiculus inertial centre), signed so +d = arista pulled anteriorly (mirror-consistent).
Replaces the outline's joint_<side>Funiculus (y) axis, which is a generic Euler axis, not
the a3 axis. Tonic one-sided 120 Hz x max(+-d, 0); G1: C = +d, E = -d (arbitrary label);
G1_FLIP swaps. L/R rule declared before any output: Step A sets as reconstructed, identical
per-neuron rule both sides, no per-side gain; primary quantities pitch-driven / within-side
/ bilateral sums; no L-R difference read as roll sensing. Static checks B0 frame, B1
identity = Step A, B2 |d|<=1, B3 mirror |dL-dR|<=0.05 at zero roll, B4 monotonic in pitch
(-30..30 deg imposed whole-body rotations, mj_forward only). Corrections recorded: runtime
antenna joints have stiffness 1.0 (FlyGym default), not 0; head is not fixed (neck spring
10, no stabilisation). Predictions (hand arithmetic, zero pose): rest d ~ -0.1..-0.2,
pitch slope ~1/rad, roll slope ~0.2/rad opposite per side. See ANTENNAL_GRAVITY_ENCODER_V1.md.

IMMEDIATE NEXT (on approval): lock protocol, build module/tests, smokes, commit, run once.

## Antennal gravity Step A (JO C/E identity): IDENTITY_READY — 2026-11-04

Preregistered (a0a1777, protocol dcbe4e5c), run once (data only, result 5b735be5). A1-A4
pass: C 31 L / 22 R, E 157 L / 110 R exact; C-vs-E weighted direct-target overlap 0.071 L /
0.039 R (segregated zones); all four sets synapse directly onto DNs (DNp73, DNp18, DNg29,
DNp33/DNg99 for C; pIP1, DNbe001 for E). A4 weak (2 hops reach 437-795 DNs). Leg MN 2-hop
reach mostly ipsilateral, E >> C. Key limit: left/right output-synapse ratio C 5.31, E 2.54
(counts 1.41/1.43) -> right reconstruction far less connected; a symmetric encoder would
inject a built-in roll-like bias. Design note corrected: JO-mz counted as "other" (untyped
4 L / 92 R). See ANTENNAL_GRAVITY_IDENTITY_RESULTS.md.

IMMEDIATE NEXT: Step B design (kinematic encoder, G1 vs G1_FLIP) must declare the left/right
handling rule before any output is inspected (e.g. as-reconstructed with label, a non-L/R
quantity such as pitch, or per-side arms).

## Antennal gravity sense (JO zones C/E) track: design — 2026-11-04

User chose "richer senses" (coxa coverage at ceiling; desk audit in PR #321). Designed (no
code/run). Johnston's organ wind/gravity neurons: 475 exact identities, unencoded, 178 reach
leg MNs in 2 hops; the body has no gravity-referenced sense today. Typed C/E: C 31 L / 22 R,
E 157 L / 110 R; 92/98 JO-unclear are right-side (annotation asymmetry; all statusLabel "RT
Hard to trace"). Step A (data only, specified): A1 identity, A2 bilateral >= 10 per set,
A3 C vs E weighted direct-target overlap < 0.5 per side, A4 C and E reach a descending neuron
within 2 hops per side -> IDENTITY_READY / PARTIAL / NOT_READY. Steps B (kinematic encoder:
gravity projected on funiculus rotation tangent; G1 vs G1_FLIP zone sign) and C (live
JO_OFF/G1/FLIP) outlined only. Not an admission or balance test. See ANTENNAL_GRAVITY_SENSE_V1.md.

IMMEDIATE NEXT (on approval): build Step A protocol/module/tests, commit, run once, evaluate.

## Remaining coxa coordinates desk audit: none testable with the existing method (no status change) — 2026-11-04

PR #320 merged. User chose to return to motor coverage. Desk audit of committed results only
(no run, no protocol). The forward-limit hair-plate encoder is blind to coxa roll and yaw in
all six legs (|df| <= 0.0005 per 0.1 rad vs ~0.1 for Coxa; hair-plate-encoder-v1
axis_direction_per_0p1rad), so no roll/yaw coordinate can change the C2 measure. RH Coxa is
visible but has no H1 channel (near-tie 0.76/0.74 fixed in advance); RF Coxa blocked by input.
Result: none of the 14 non-CONDITIONAL coxa coordinates is testable by the existing
encoder/binding/C2 measure; with Tarsus1 source-blocked, all 22 unadmitted coordinates are
untestable with current validated components (ceiling 20/42 +4 conditional). A tip-based
measure would be circular; a multi-axis encoder is not defensible from local metadata
(M5B-2). Noted: COXA_COORDINATE_STATUS.md "Other middle-leg coxa (7)" is inconsistent (4).
See COXA_REMAINING_COORDINATES_AUDIT.md.

IMMEDIATE NEXT (user choice): coverage needs new evidence, not a new test. Candidate
directions: richer senses (e.g. unused campaniform/load, labelled PROXY_ONLY in M5D-1),
using the 24 channels toward balance, or reconciling the coxa status file.

## Push response + offset yoke replication on seeds 7-12: DIRECTIONAL / DO_NOT_REPRODUCE / FREE_COMMANDS_INCREASE_D (no status change) — 2026-11-04

Preregistered (80ad349, protocol 01a6ea1c), 55 arms run once, evaluated once (report
cdb953a1); I1-I7 and pulse pass (REPRO_N0_1 equals push-response N0_1 in content). Per
direction on seeds 7-12: R = D(C)/D(N) F 1.25/1.05/1.55/1.97/1.44/1.25, B
1.19/1.36/1.09/1.42/1.92/1.63 -> AMPLIFICATION_DIRECTIONAL both (R > 1 6/6, sign p = 1/64;
one seed under 1.10 each). E = D(Y)/D(C) F 0.64-0.93, B 0.74-0.99 -> FREE_COMMANDS_INCREASE_D
both (prediction NO_CONSISTENT_SIGN wrong); yoke rule OFFSETS_DO_NOT_REPRODUCE both
(replicates). R_Y F median 0.99 (fixed offsets ~ N), B 0.98-1.55. Pooled 9 seeds: SD of log
ratio 0.17-0.24; D(N) CV ~20-23 %; E < 1 in 8/9 per direction (seed 1 the exception). Reflex
vs generic closed-loop divergence not separable. Coverage unchanged: 20/42 admitted, +4
conditional. See COXA_PUSH_REPLICATION_RESULTS.md.

IMMEDIATE NEXT (user choice): the earlier 10 % bars are narrower than the measured seed
scatter; any further body-level coxa test should set bars from this spread. Options: a
preregistered test separating a structured coxa response from generic divergence (e.g.
response to the push timing/sign versus a matched neural-only perturbation), or returning to
coverage work.

## Push response + offset yoke replication on seeds 7-12 (noise estimate): design — 2026-11-04

PR #319 merged. Designed (no code/run). The push-response LOOP_AMPLIFIES and the yoke
OFFSETS_DO_NOT_REPRODUCE rest on seeds 1-3 with wide spread (R 1.24-2.04, E 0.51-1.11) and
no noise estimate. Arms {N, C (H1), Y (coxa 0/7/14/28 yoked to own C0_s)} x {0, F, B} x
never-used CNS seeds 7-12 = 54, plus REPRO_N0_1 (must equal push-response N0_1) = 55 (~4.5 h).
Per direction on new seeds: Q1 R >= 1.10 all 6 REPLICATES / R > 1 all 6 DIRECTIONAL (sign
p = 1/64) / NOT_REPLICATED; Q2a the yoke rule unchanged; Q2b E < 1 all 6
FREE_COMMANDS_INCREASE_D / E > 1 all 6 DECREASE_D / NO_CONSISTENT_SIGN; Q3 pooled 9-seed
spread reported only. Not an admission test; earlier labels untouched. See
COXA_PUSH_REPLICATION_V1.md.

IMMEDIATE NEXT (on approval): build protocol/adapter/evaluator/tests, smokes, commit, run
55 arms once, evaluate once.

## Open-loop coxa offset yoke: OFFSETS_DO_NOT_REPRODUCE both directions (no status change) — 2026-11-03

Preregistered (532b949, protocol 309cade6), 9 arms run once, evaluated once (report
5afb991f); I1-I7 pass (Y0_s equals push-response C0_s exactly; 18 reference hashes match).
R_Y = D(Y)/D(N): F 1.37/1.33/0.94, B 1.43/0.70/0.91; E = D(Y)/D(C): F 1.11/0.65/0.71, B
1.10/0.51/0.74 -> OFFSETS_DO_NOT_REPRODUCE both. Prediction (REPRODUCE) wrong. Fixed
setpoints alone amplify only in seed 1; seeds 2-3 need free post-push coxa commands. Correction
to the push-response reading (addendum there): C-arm coxa commands differ from control in
12,265-14,605 transitions by 0.009-0.033 rad mean (window means hid it); reflex vs chaotic
divergence not separable. Y arms tilt like C (8.7-10.4 deg) yet do not amplify in seeds
2-3, weakening the tilt explanation. Coverage unchanged: 20/42 admitted, +4 conditional. See
COXA_OFFSET_YOKE_RESULTS.md.

IMMEDIATE NEXT (user choice): the seed variability (E 0.51-1.11) is now the main limit on
body-level coxa questions; options are a preregistered variance estimate (more seeds of the
existing N/C push arms) before any further mechanism test, or returning to coverage work.

## Open-loop coxa offset yoke (reflex or posture?): design — 2026-11-03

PR #318 merged. Designed (no code/run): tests the push-response post hoc reading. Reuses the
tibia dissection's selected-index yoke on coxa actions 0/7/14/28 (H1), source = push-response
C0_s (unpushed, local; hashes in report 4c03a59e), sample n+1 convention, N configuration.
Arms Y0/YF/YB x seeds 1-3 = 9 (~45 min); references N/C push-response arms, not rerun.
I3: Y0_s must equal C0_s exactly. R_Y = D(Y)/D(N), E = D(Y)/D(C) per direction:
OFFSETS_REPRODUCE (R_Y >= 1.10 and 0.90 <= E <= 1.10 all seeds) / PARTLY / DO_NOT.
Not an admission test. See COXA_OFFSET_YOKE_V1.md.

IMMEDIATE NEXT (on approval): build protocol/adapter/evaluator/tests, smoke (Y0_2 prefix
vs C0_2; YF_2 past the pulse), commit, run 9 arms once, evaluate once.

## Fore-aft push response: LOOP_AMPLIFIES both directions (no status change) — 2026-11-03

Preregistered (b31435a, protocol ec3f0de1), 27 arms run once, evaluated once (report
4c03a59e); I1-I7 pass (N0_s equal coxa-admission C0_s exactly), pulse resolved in all six
seed-direction cases. R = D(C)/D(N): F 1.24/2.04/1.33, B 1.30/1.37/1.24 -> LOOP_AMPLIFIES
both. Flip R': F 1.40/1.57/0.87 -> SIGN_INDEPENDENT; B 1.21/1.03/0.85 -> SIGN_SPECIFIC by
rule. Reported measures: the loops did not respond to the push (pushed hair rates and coxa
offsets equal own control; LF/LH tonic ~+-0.17-0.22 rad; LM/RM hair 0 Hz, offsets ~0,
never recruited by the 20 ms pulse). C mean tilt 9.1-10.2 deg vs N 3.8-4.3, X 0.86-1.05:
amplification most likely via the static posture the LF/LH offsets set, not a reflex
(post hoc reading, untested). No arm, including N, recovered into the inherited band.
Coverage unchanged: 20/42 admitted, +4 conditional. See COXA_PUSH_RESPONSE_RESULTS.md.

IMMEDIATE NEXT (user choice): either test the posture explanation directly (a
preregistered tonic-offset control that replays the C arms' fixed setpoint offsets without
the neural loop), or a disturbance that actually recruits the middle hair plates, each as
its own versioned protocol.

## Fore-aft push response with the four conditional coxa channels: design — 2026-11-03

PR #317 merged. Remaining coxa coordinates are locally blocked (RF input, RH H1 on
Coxa_roll invisible to the fore-aft encoder, distal Tarsus1 sources), so the next question
integrates the four CONDITIONAL channels (LF/LH/LM/RM Coxa). Designed (no code/run): Step C
A_ON, reused M9B/tactile thorax pulse (1.024 x 200 transitions, impulse 0.02048) with a
declared fore-aft direction (F +x, B -x). Arms {N none, C H1 x4, X H1_FLIP x4} x {no push, F,
B} x CNS seeds 1-3 = 27. Primary D = integral of root-position deviation vs own unpushed
control (520.1-2000 ms). Q_LOOP per direction: R = D(C)/D(N) <= 0.90 all seeds attenuates,
>= 1.10 amplifies; Q_SIGN via X. Not an admission test. See COXA_PUSH_RESPONSE_V1.md.

IMMEDIATE NEXT (on approval): build protocol/adapter/evaluator/tests, smoke past the pulse,
commit, run 27 arms once (~2.3 h), evaluate once.

## Middle-leg coxa C3: LM/RM Coxa CONFIRMED -> CONDITIONAL (+4 conditional) — 2026-11-03

Preregistered (3c677c2, protocol dd268b80), ten arms (REPRO_1 + P0/PC/PF x CNS seeds 4-6)
run once, evaluated once; I1-I7 pass (REPRO_1 equals C2 P0_1 exactly), context met.
joint_LMCoxa and joint_RMCoxa CONFIRMED 3/3 new seeds, no flags (LM PC -0.031..-0.041 / PF
+0.089..+0.096; RM -0.032..-0.046 / +0.174..+0.193) -> CONDITIONAL (COXA_CONDITIONAL_H1).
Totals 20/42 admitted, +4 conditional (LF/LH/LM/RM); first bilateral conditional pair.
Pre-displacement offsets ~0 (|<=0.013|); pre-stimulus position df mostly <= 0.026 but LM
seed 4 PC +0.046 (opposite sign; recorded as a bar-noise limit). Graded feedback and MN
tracking as in C2. See MIDDLE_COXA_C3_CONFIRMATION_RESULTS.md.

IMMEDIATE NEXT (user choice): with four conditional fore-aft coxa channels (two bilateral
in the middle legs), a preregistered question that uses them together (e.g. a matched
released/perturbed posture comparison) or extending the displacement method to the hind
legs' remaining untested channels.

## Middle-leg coxa C3 confirmation: design — 2026-11-03

PR #316 merged. Designed (no code/run). C3 for joint_LMCoxa / joint_RMCoxa under Part A:
identical C2 context (A_ON, SHIFT_SERVO_EQUILIBRIUM at 5005, same Delta, H1/H1_FLIP by
hash), never-run CNS seeds 4-6: P0/PC/PF x 3 + REPRO_1 (must equal C2 P0_1 exactly) = 10
arms. Same rule (PC df <= -0.02 and PF df >= +0.02). CONFIRMED 3/3 -> CONDITIONAL;
PARTIAL -> stays C2 passed; NOT_CONFIRMED -> NOT_SUPPORTED. Reports pre-displacement
offsets and df (400-500 ms) for the C2 timing caveat. See MIDDLE_COXA_C3_CONFIRMATION_V1.md.

IMMEDIATE NEXT (on approval): build protocol/adapter/evaluator/tests, smoke, commit, run 10
arms once (~50 min), evaluate once.

## Middle-leg coxa displacement test: LM/RM Coxa C2_PASSED 3/3 — 2026-11-03

Preregistered (f91fd74, protocol 9854e0af), nine arms (P0/PC/PF x CNS seeds 1-3) run once,
evaluated once; I1-I7 pass (P0 reproduces coxa-admission C0 through 5005), context met
(P0 middle hair LM ~120, RM 94-113 Hz). joint_LMCoxa and joint_RMCoxa both C2_PASSED, no
flags: LM PC df -0.030..-0.058 / PF +0.067..+0.087; RM -0.032..-0.038 / +0.186..+0.189.
Descriptive: graded negative feedback (PC drives hair 120 -> 7-59 Hz; PF keeps ~120),
PF offsets 2-4x PC (positive vs negative feedback), middle coxa MNs fall in PC; no cross-leg
or tilt effect. Caveat: channels issue commands from 46-158 ms, before the displacement.
Status: "C2 passed, awaiting C3" (counted nowhere). See MIDDLE_COXA_DISPLACEMENT_RESULTS.md.

IMMEDIATE NEXT (on approval): the C3 confirmation for LM/RM Coxa on CNS seeds 4-6
(separately preregistered); would make the first bilateral CONDITIONAL pair.

## Middle-leg coxa resistance reflex (imposed displacement): design — 2026-11-03

PR #315 merged (RF thread closed). Middle-leg Tarsus1 remains source-blocked
(DISTAL_ANATOMICAL_QUALIFICATION_RESULTS.md), so the next coordinates are the middle coxae.
Designed (no code/run): at state 5005 shift the LM/RM Coxa servo equilibrium (biasprm[0]
+= kp*Delta, corrected from the design's -=; Delta LM -0.2450, RM -0.2199 rad, by rule from Step B to one encoder band past
the walking forward limit). Arms P0/PC/PF x CNS seeds 1-3 (9). PC/PF = H1/H1_FLIP
joint_LMCoxa + joint_RMCoxa only. Precondition: P0 middle hair >= 30 Hz. Seed pass: PC df <=
-0.02 and PF df >= +0.02; C2_PASSED 3/3. This is the C2 step only; CONDITIONAL needs a later
C3 on seeds 4-6. See MIDDLE_COXA_DISPLACEMENT_V1.md.

IMMEDIATE NEXT (on approval): build protocol/adapter/evaluator/tests, smoke, commit, run 9
arms once (~45 min), evaluate once.

## RF hair-plate cross-connectome check V2: INCONCLUSIVE_INTEGRITY — 2026-11-03

Preregistered (8ea584a, protocol 9b1ec930), run once (data only). I1, I2 (100 %), I4
(100 %), I5 pass; I3 fails: anchors with a BANC counterpart LF 5/7, RF 3/5 (bar 75 %). No
labels. Post hoc: B1 (malecns_match) is group-level (9 BANC LF SNpp45 -> one MaleCNS body);
B2 (mancBodyid -> manc_match) reaches interneurons and a motor neuron (design had no
sensory check: flaw recorded). B1-only numbers repeat V1 (ratio ~0.74), not independent.
Conclusion: local metadata cannot give neuron-level identity; resolving this needs BANC
synapse tables (not local; would require a download, excluded by the local-only rule).
Recommendation: close the RF anatomy-vs-reconstruction thread; joint_RFCoxa stays
BLOCKED_BY_INPUT. See RF_HAIR_PLATE_CROSS_CONNECTOME_V2_RESULTS.md.

IMMEDIATE NEXT (user choice): move to other unmapped coordinates (e.g. the four
middle/hind Tarsus1 target mappings or the LF/LH coxa roll/yaw components).

## RF hair-plate cross-connectome check V2 (neuron match): design — 2026-11-03

Designed (no code/run; no anchor looked up). Anchors: the model's own MaleCNS T1 SNpp45
neurons (7 L, 5 R; 821165 reported). Bridges: BANC malecns_match == anchor body ID (B1);
BANC manc_match contains the anchor's mancBodyid (B2); union, distinct root_id. Integrity:
sources + Step A counts, >= 90 % BANC malecns_match IDs exist in v1.0 annotations, >= 75 %
anchors matched per side, >= 80 % side-consistent counterparts, cable present. Labels and
bars copied unchanged from V1 (Q_COUNT, Q_SIZE, Q_RF); Q_SIZE is the informative one
(count is matching-bounded). V1 diagnostics seen beforehand are disclosed.
See RF_HAIR_PLATE_CROSS_CONNECTOME_V2.md.

IMMEDIATE NEXT (on approval): build protocol/code/tests, commit, run once (seconds).

## RF hair-plate cross-connectome check: INCONCLUSIVE_INTEGRITY — 2026-11-03

Preregistered (f1a147e, protocol 856fe70b), run once (data only, seconds). I1, I2, I4, I5
pass (MaleCNS reproduces Step A 7/5/12/11/8/9); I3 fails: 36/166 BANC SNpp45 rows (21.7 %)
outside the nerve rule (32 on the prothoracic leg nerve, 22 right / 10 left). No labels.
Diagnosis (post hoc): BANC `SNpp45` is a broader type than MaleCNS (T2 48/37 vs 12/11) and
its T1 nerve split decides the sign of any count difference (primary 8 L/4 R; all
prothoracic 22 L/26 R). Type-name counting across connectomes is invalid here; a V2 would
need neuron-level identity (BANC malecns_match/manc_match or connectivity). joint_RFCoxa
stays BLOCKED_BY_INPUT; anatomy vs reconstruction still open.
See RF_HAIR_PLATE_CROSS_CONNECTOME_RESULTS.md.

IMMEDIATE NEXT (user choice): (a) design a V2 using neuron-level matches; (b) leave RF and
move to other unmapped coordinates.

## RF hair-plate cross-connectome check: design — 2026-11-03

PR #314 merged. Designed (no code/run; no BANC per-leg tally inspected). joint_RFCoxa is
BLOCKED_BY_INPUT because MaleCNS RF SNpp45 neurons are fewer (5 vs 7) and much smaller;
anatomy vs reconstruction was left open twice. The committed BANC v888 metadata (86ccf5df,
distal-tarsus provenance) types SNpp45 with nerve, side and cable length: local only, no
download. Same nerve rule as Step A. Labels Q_COUNT (d = n_RF - n_LF; <= -2 replicated,
|d| <= 1 symmetric), Q_SIZE (median cable ratio; <= 0.67 replicated, 0.85-1.18 symmetric),
Q_RF overall. No weights change from any outcome. See RF_HAIR_PLATE_CROSS_CONNECTOME_V1.md.

IMMEDIATE NEXT (on approval): build protocol/code/tests, commit, run once (seconds).

## Released-posture coxa test: all nulls, NO_RESCUE — 2026-11-02

Preregistered (bc38189, protocol 16659830), 12 arms (R22/K/KC/KF x CNS seeds 1-3) run once,
evaluated once; integrity I1-I7 all pass (R22_1 reproduces Step C R_ON). T_roll 567-592 ms
(67-91 ms after release) in every arm; all differences < 20 ms with mixed signs:
NO_CONSISTENT_ASSIST_EFFECT, NO_CONSISTENT_LOOP_EFFECT, Q_SIGN NOT_EVALUATED, NO_RESCUE
(all as predicted). Descriptive only: loop active and sign-opposed through the fall (LH
near bound 2-9 %), rollover direction differs by arm type (body-z y component R22 0.06-0.12,
KC 0.17-0.20, K/KF 0.30-0.38), KF cross-leg LM hair/MN rise. CONDITIONAL status unchanged.
Process: a chained test command let a failing lock test pass silently; cause was missing
-text rules (fixed 117d1ac). See COXA_RELEASE_POSTURE_RESULTS.md.

IMMEDIATE NEXT (user choice): the coxa coordinates cannot affect whole-body rollover with
20 other servos released. Options: (a) a preregistered question on the descriptive
rollover-direction difference; (b) widen the conditional set (RF/RH input gap); (c) return
to admission coverage of other unmapped coordinates.

## Released-posture coxa test: design — 2026-11-02

PR #313 merged. Designed (no code/run). Constraint found: the Step C release zeroes all 22
baseline-only actuators, including joint_LFCoxa and joint_LHCoxa, so the conditional
channels would act on zero-gain servos. Arms per CNS seed 1-3: R22 (Step C release), K
(release 20, keep the two coxa servos, no neural channel: assistance control), KC (K + H1
conditional channels), KF (K + H1_FLIP); 12 arms. Integrity I1-I7 (R22_1 reproduces Step C
R_ON; release records exact). Primary measure T_roll (first tilt > 90 deg after release).
Labels Q_ASSIST (K vs R22), Q_NEURAL (KC vs K), Q_SIGN (KF), Q_RESCUE; 20 ms bar, all 3
seeds. Predictions: NO_RESCUE, likely no consistent effects (exploratory).
See COXA_RELEASE_POSTURE_V1.md.

IMMEDIATE NEXT (on approval): build protocol/adapter/evaluator/tests, smoke past the
release, commit, run 12 arms once, evaluate once.

## Coxa admission confirmation: LF/LH Coxa CONFIRMED -> CONDITIONAL — 2026-11-02

Part A tier approved by the user. Preregistered (0c94284, protocol 3b97fbb8), nine arms
(C0/CAND/FLIP x CNS seeds 1-3) run once, evaluated once; integrity I1-I6 all pass (C0_1
reproduces Step C A_ON). joint_LFCoxa and joint_LHCoxa CONFIRMED 3/3 seeds with only those
two channels enabled (LF CAND -0.162..-0.168, FLIP +0.145..+0.161; LH -0.185..-0.189,
+0.211..+0.215); no BOUND_LIMITED, no ROLLOVER. Isolated effects match D3 all-channel ones.
Limits: LF hair input saturated (direction test, not graded feedback; only LH shows the
sensor falling, 120 -> 101-109 Hz); seeds vary only sensory event timing; offset-on-servo.
Status table: COXA_COORDINATE_STATUS.md (20/42 admitted, +2 conditional). See
COXA_ADMISSION_RESULTS.md.

IMMEDIATE NEXT (user choice): the track design's next question, the released-servo (R)
posture test using the conditional channels (labelled), vs V1.2 R_NC and Step C R_ON.

## Coxa admission question: design — 2026-11-02

PR #312 merged. Designed (no code/run). Part A: the existing v3 standard is unchanged and
cannot admit coxa (anatomical reference gate blocked; local-only). Proposed, for user
decision, a separately counted CONDITIONAL tier (C1 rule-fixed binding, C2 falsification
with sign reversal, C3 prospective isolated confirmation across new seeds, C4 integrity),
never merged into 20/42; plus BLOCKED_BY_INPUT (RFCoxa, RHCoxa_roll), UNTESTED, NOT_SUPPORTED.
Part B: confirm joint_LFCoxa and joint_LHCoxa (H1, D2 definitions by hash) isolated, seeds
1-3, arms C0/CAND/FLIP per seed (9). Per seed pass: firing leg, CAND df <= -0.02, FLIP df >=
+0.02; CONFIRMED = 3/3, PARTIAL 1-2, NOT_CONFIRMED 0. Flags BOUND_LIMITED, ROLLOVER.
Seeds 2/3 via adapter replacing brain.rng at attach (no kernel change; else
PROTOCOL_NOT_BUILDABLE). See COXA_ADMISSION_QUESTION_V1.md.

IMMEDIATE NEXT (on approval of Part A and Part B): build protocol/adapter/evaluator/tests,
smoke, commit, run nine arms once, evaluate once.

## Hair-plate relay intervention: NOT_NECESSARY, NONSPECIFIC — 2026-11-02

Preregistered (80433ba, protocol 29b756b7), five arms run once, evaluated once; integrity
I1-I5 all pass (C0 reproduces Step C A_ON exactly). Sets: LEFT_RELAY 4, RIGHT_RELAY 8,
matched IN03A shams. Q_NEC NOT_NECESSARY: silencing the left relay removed ~82 % of the LF
best MN's other excitation but LF pool fell only 18 % (ratio 0.823; hair drive 19.6 >> g*).
Q_SUF NONSPECIFIC: R_INJ raised RF pool 1.5 -> 24.2 Hz (best MN 4 -> 47), but R_SHAM raised it
5.9 Hz. Flaws recorded, labels not reinterpreted: (1) sham rule did not exclude edges onto
the relay; sham injection recruited the right relay (1.94 Hz, 2.09 of 2.57 g_other);
(2) hair-rate confound check saturated at the 120 Hz cap; (3) R_INJ landed exactly on the
RESCUED threshold (coincidence). Both predictions failed. See RF_RELAY_INTERVENTION_RESULTS.md.

IMMEDIATE NEXT (user choice): a V2 with a sham that has no path into the relay (new
versioned protocol), or return to the coxa track. No coordinate admitted; 20/42.

## Hair-plate relay intervention: design — 2026-11-02

PR #311 merged. Designed (no code/run) the first causal test of the post-hoc relay
hypothesis: five fresh-process arms in the Step C A_ON context (C0 must reproduce A_ON;
L_SIL/L_SHAM withhold transmission of left relay IN03A066/075/080 or a rate-matched IN03A
sham; R_INJ/R_SHAM inject left-matched Poisson trains from an independent seeded generator
into the right relay or a sham, OR-ed into the forced mask so CNS RNG is untouched).
Integrity I1-I5, labels Q_NEC (NECESSARY/CONTRIBUTES/NOT_NECESSARY/NONSPECIFIC) and Q_SUF
(RESCUED/PARTIAL/NO_EFFECT/NONSPECIFIC), sensory-confound flag, predictions recorded.
Engineering interventions in the model only. See RF_RELAY_INTERVENTION_V1.md.

IMMEDIATE NEXT (on approval): resolve and freeze sets/trains into the protocol, build
adapter/evaluator/tests, smoke, commit, run five arms once, evaluate once.

## Right-front coxa MN excitation: ACTIVITY_GAP, HAIR_EVOKED — 2026-11-01

Preregistered (a259a83), run once, data only (Step C A_OFF + A_ON replay, both REPLAY_EXACT).
Q1 HAIR_EVOKED (LF 99.5 %, LH 68 % of other excitation is hair-evoked). Q2/Q2b ACTIVITY_GAP:
RF has nearly LF's available excitatory weight (397 vs 420) but partners deliver ~46x less.
LF's extra excitation is mostly a hair-plate relay via left IN03A066/075/080; their right
copies are wired to RF (IN03A066 60.9 vs 43.9) but silent. Q3 PRE_EXISTING_ASYMMETRY by the
rule, degenerate (A_OFF RF 0.000 vs LF 0.043; no minimum-baseline clause), recorded not
reinterpreted. Post-hoc exploratory: RF hair plates give the right relay copies ~1/4 the
synapses (26/10/12 vs 98/46/37). See RF_COXA_EXCITATION_RESULTS.md.

IMMEDIATE NEXT (user choice): any causal test (driving the right relay or silencing the left)
is an intervention needing its own versioned protocol; or return to the coxa track.

## Right-front coxa MN excitation: design — 2026-11-01

PR #310 (drive asymmetry) merged. Designed a data-only follow-up (no code/run): why RF
coxa MNs get almost no non-hair-plate excitation (0.2 vs LF 8.6, LH 22.1). Replays Step C
A_OFF and A_ON with per-partner attribution; splits the RF gap into WIRING (available
excitatory weight) vs ACTIVITY (delivery rate), and asks whether LF/LH extra excitation is
hair-evoked (A_ON - A_OFF), which would make RF's gap a consequence of its weak hair plates.
Labels Q1-Q3 and predictions recorded. See RF_COXA_EXCITATION_V1.md.

IMMEDIATE NEXT (on approval): build module/tests, hash-lock protocol, commit, run once.

## Right-front coxa drive asymmetry: INTEGRITY_ACCEPTED, REPLAY_EXACT — 2026-11-01

Preregistered (2c1ca42), run once, data only. Replay of Step C A_ON reproduces all 62 coxa
MNs' window spikes exactly. Q1 RF_DIRECT_SUFFICIENT by the mean-field rule (8.98 vs g* 8.09),
but that rule assumed 120 Hz delivered; measured delivered hair-plate g on the best RF MN is
6.0 (< g*). Q2 (RF vs LF) SYNAPSES_PER_SOURCE (RF SNpp45 neurons are small overall: 320-378
total outputs vs LF mostly 680-1,320); Q2b (vs LH) SOURCE_COUNT; Q3 INHIBITION_NOT_DECISIVE.
Engine share (floor + size scaling) 0.09. RF coxa MNs also get almost no other excitation
(0.2 vs LF 8.6, LH 22.1). Anatomy vs reconstruction undecided. See COXA_DRIVE_ASYMMETRY_RESULTS.md.

IMMEDIATE NEXT (user choice): no fix is implied. Options are a versioned question about the
missing non-hair-plate excitation onto RF coxa MNs, or returning to the coxa track with RF
recorded as a known limit.

## Right-front coxa drive asymmetry: design — 2026-11-01

PR #309 (D3) merged. Designed a data-only comparison (no code/run) of why RF hair plates
at 120 Hz leave RF coxa MNs at 0.55 Hz. Part S (cache): SNpp45 inventory, engine-exact
effective direct weights, hair-plate-only mean-field drive vs threshold, and an exact
four-factor decomposition (source count, synapses/source, 6-synapse floor, size scaling)
for RF vs LF and RF vs LH. Part M: exact replay of input conductances onto every coxa MN
from the recorded Step C A_ON spikes, verified by single-neuron LIF reproduction. Labels
Q1-Q3 and predictions recorded. Cannot separate anatomy from reconstruction artifact;
not a fix. See COXA_DRIVE_ASYMMETRY_V1.md.

IMMEDIATE NEXT (on approval): build module/tests, hash-lock protocol, commit, run once.

## Coxa hypothesis D3: NOT_CONSISTENT (2/4 legs), H1_FAVOURED — 2026-11-01

Preregistered (f4c06a8), preflight passed, four arms run once (C0/H1/H1_FLIP/H2), CNS +
physics. INTEGRITY_ACCEPTED (C0 reproduces Step C A_ON exactly). Q3 NOT_CONSISTENT: H1
moved the coxa back in LF (-0.173) and LH (-0.191), with the flip reversing it (+0.145/+0.206),
but not in RF (hair plates 120 Hz, coxa MNs 0.55 Hz, channel never moved) or RH (barely
above threshold, 0.16 Hz). Q4 H1_FAVOURED (2 vs 0; H2 has no fore-aft reflex). H1 tilts the
assisted body more (10.6 deg vs 3.8). Raw arms local. See COXA_HYPOTHESIS_D3_RESULTS.md.

IMMEDIATE NEXT (user choice): the right-front hair-plate -> coxa MN weakness is the
identified blocker (anatomy, reconstruction or engine?); a data-only left/right pathway
comparison is the cheapest next question. Any rerun is a new versioned protocol.

## Coxa hypothesis D3: design — 2026-11-01

PR #308 (D1/D2) merged. D3 designed (no code/run): arms C0 (Step C path, must reproduce
saved A_ON exactly), H1, H1_FLIP, H2 using D2 channel definitions loaded by hash; a
hypothesis-labelled derived v3 table/gate/assertion (v3 untouched); preflight P1-P5,
integrity I1-I5; Q3/Q4 labels and the 0.02 bar unchanged from the track design.
Predictions recorded (front-leg failure possible; H2 hind adductors posterior-inward).
See COXA_HYPOTHESIS_D3_V1.md.

IMMEDIATE NEXT (on approval): build adapter/evaluator/tests and hash-lock the protocol,
commit, then run the four arms once.

## Coxa hypothesis D1/D2: D1_D2_READY — 2026-11-01

Preregistered (e4f2791), run once, geometry/data only. All checks pass (anterior, 18 nonzero
action vectors, +Coxa posterior in all legs, audit identities, kernel resolver accepts
H1/H2/H1_FLIP). +Coxa is the fore-aft DoF in every leg; front-leg roll and yaw are near
degenerate at rest. H1: 13 channels, posterior rotators -> Coxa+ (RH: Coxa_roll), front
remotor/abductor -> yaw (near-tie). H2: 8 channels, all rotators unassigned (cos 0 on yaw).
D1c walking cross-check 3/6. Near-ties recorded, not acted on. See COXA_HYPOTHESIS_D1_D2_RESULTS.md.

IMMEDIATE NEXT: user decision on D3 (closed-loop C0/H1/H1_FLIP/H2), which needs its own
hash-locked protocol and a hypothesis-labelled session path (v3 refuses coxa admission).

## Coxa motor hypothesis track V1: design — 2026-11-01

User chose the labelled coxa hypothesis track after Step C. Design only (no code/run):
D1 geometry action table for the 18 coxa DoFs plus a recorded-walking-range cross-check;
D2 two rule-generated bindings (H1 name-geometry, H2 bodymap-label) resolving the shared
remotor/abductor IDs by max |cos|; D3 closed-loop test on Step C A_ON (C0, H1, H1_FLIP,
H2) with preregistered integrity and Q3 resistance-reflex / Q4 H1-vs-H2 labels.
Hypothesis channels are not admissions; coverage stays 20/42. See COXA_HYPOTHESIS_TRACK_V1.md.

IMMEDIATE NEXT (on approval): build and hash-lock D1/D2, run once, commit tables
before any D3 code runs.

## Hair-plate Step C: posture-sensitive, reflex-consistent — 2026-11-01

Four-arm run (preregistered 4ff134b, once): A/R posture x hair plates ON/OFF.
INTEGRITY_ACCEPTED. Q1 POSTURE_SENSITIVE: coxa-MN rate held vs released 1.89/1.89 Hz OFF,
10.41/9.32 Hz ON (per leg up to 22.7 vs 9.8 Hz). Q2 REFLEX_DIRECTION_CONSISTENT:
posterior coxa MNs 2.67 -> 16.67 Hz, anterior flat. Released arms still roll over (coxa
joints unmapped). Raw arms local; report committed. See HAIR_PLATE_POSTURE_RESULTS.md.

IMMEDIATE NEXT (user choice): the sensory side of the coxa loop now exists; the motor
side (18 coxa coordinates) is the gap. Options: a labelled coxa hypothesis track now
that +joint_<leg>Coxa = posterior is known, or more seeds / a retuned encoder.

## Hair-plate Step B: encoder ENCODER_READY, rest-pose caveat — 2026-11-01

SNpp45 coxa forward-limit encoder (preregistered 0ddff0f, static run once): forward
component of the coxa axis in the Thorax frame; tonic one-sided tuning at the 90th
percentile..max of the recorded FlyGym untethered walking step replayed on our body;
120 Hz max. All checks pass. Caveat: the B4 standing pose has front/hind coxae beyond
the recorded walking forward limit, so the encoder fires ~max at rest in LF/RF/LH
(RH 68.5 Hz) and not in middle legs. Geometry: +joint_<leg>Coxa = posterior in all
legs. See HAIR_PLATE_ENCODER_RESULTS.md.

IMMEDIATE NEXT: user decision on Step C (A/R x ON/OFF) with this encoder as-is, or a
separately justified tuning version first. No delivery into the CNS yet.

## Hair-plate Step A: SNpp45 matches published CxHP8 wiring — 2026-11-01

SNpp45 hair plates = CxHP8 (front legs, VProN) and serial copies (middle/hind):
a tonic coxa forward-limit detector (Nature Communications 2026 preprint PMC12139860).
Preregistered connectivity check (d5e84d0), run once: MATCH_ALL. In all six legs
SNpp45 directly excites posterior-moving coxa MNs (194-1,056 synapses; front legs
remotor/abductor, middle/hind sternal posterior rotator), essentially never anterior,
and the two-hop network inhibits the anterior set. Two-hop drive to the posterior set
is also negative (not gated). See HAIR_PLATE_IDENTITY_RESULTS.md.

IMMEDIATE NEXT: Step B, a preregistered SNpp45 encoder for all six legs: coxa
forward component in the thorax frame, tonic one-sided limit tuning with a fixed
geometric threshold rule, no physics run. Then Step C (A/R x ON/OFF).

## Posture-sense pivot: inventory V1 — 2026-11-01

Stage 2 (coxa posture) was redesigned: neural joints add offsets to posture-holding
servos, and V1.2 spikes show coxa MNs fire the same upright vs upside down (only
tibia angle is sensed). User chose to pivot to posture senses. Data-only inventory
(preregistered 0bbc0d9): all annotated hair plates, campaniform sensilla,
chordotonal, JO wind/gravity, haltere and neck neurons exist in our connectome.
Middle/hind hair plates directly contact coxa-rotator MNs (224-1,024 synapses per
leg) and are not encoded; front-leg hair plates were missed by the nerve rule;
leg load (CS) is barely annotated. See POSTURE_SENSE_INVENTORY_RESULTS.md.

IMMEDIATE NEXT: a separately preregistered hair-plate coxa-angle encoder design
(which joint each plate reports, fixed tuning, front-leg nerve question), then a
matched on/off test of whether coxa MN activity starts reflecting posture.

## Stage 1 DNg100 rhythm V1: NOT_REPRODUCED — 2026-11-01

Discovery program (user-approved): Stage 1 asks whether our untuned whole-CNS LIF
engine reproduces the Pugliese et al. 2025 preprint's DNg100 -> front-leg motor
rhythm. Preregistered (2bf3541), run once: best rhythmicity 0.196 (needed 0.5),
2.8 Hz. DNg100 does specifically recruit 12/68 front-left MNs (coxa promotor,
tibia flexor/extensor, rotator, femur reductor) but tonically, with flexor and
extensor co-active. E1/E2 silencing vacuous. See DNG100_RHYTHM_RESULTS.md.

IMMEDIATE NEXT: user choice. Stage 3 (emergent stepping) not expected with the
engine as-is; Stage 2 (coxa posture hypotheses) does not need a rhythm. Any
engine-parameter follow-up is a new versioned question, never tuning to oscillate.

## Serial motor fingerprint V1: FAIL — 2026-11-01

Local-only attempt to infer motor-neuron identity from connectivity. Preregistered
blind test (committed 59d7724, run once): presynaptic cell-type fingerprints
assign annotated leg MNs in another leg at 0.62 type accuracy (null 0.06,
p=0.001) but miss the bar (needed 0.70; femur_twist joint 0.10; T1-reference
0.59). Adjacent segments transfer better than T1<->T3. Method not validated for
Tarsus1 candidates; 22 coordinates stay blocked; nothing admitted. See
SERIAL_MOTOR_FINGERPRINT_RESULTS.md.

IMMEDIATE NEXT: user choice. Any refinement (e.g. adjacent-segment chaining) is
a new versioned protocol, not a V1 retune. 20/42; balance/gait unproven.

## Local-only project; data requests withdrawn — 2026-11-01

The user does not want anyone else involved: no author/team contact, no data
requests, no sending project information. ANATOMY_DATA_REQUESTS_V1 is withdrawn
(kept as a blocker record). Do not propose outreach. Use only local or already
public, downloadable data. The 22 unadmitted coordinates therefore stay blocked
unless qualifying evidence turns up in such sources. 20/42.

IMMEDIATE NEXT: pick local-only work with its own protocol, e.g. more V1.2
seeds or sensory work; independent balance/gait unproven.

## Anatomy data requests drafted (not sent) — 2026-11-01

User watched the V1.2 replay (fly falls). Motor coverage is the bottleneck, and
all 22 unadmitted coordinates need anatomy absent from reviewed public sources.
`ANATOMY_DATA_REQUESTS_V1.md` drafts Request A (FlyMimic: coxa attachment/
landmark correspondences, rotator lines of action) and Request B (MANC/BANC/
MaleCNS: per-neuron coxa muscle targets for 26 exact pools, T2/T3 tarsal
homologs). Status NOT SENT; the user sends them. Replies get a separate versioned
qualification review; nothing is admitted from a reply alone. 20/42.

IMMEDIATE NEXT: user decides whether to send. While waiting, work that needs no
new anatomy (e.g. additional seeds of V1.2, sensory work) needs its own protocol.

## V1.2 saved-pose Unity replay entry point — 2026-11-01

`assistance_campaign_v1_2_replay` re-runs the unchanged V1.2 evaluator once and
projects poses from the arms it reads. It displays them only if the rebuilt
evaluation equals the saved report and integrity is accepted. Verified on the
real local evidence (905.6 s, all 8 arms x 20,001 states); 42 synthetic replay
tests pass. Unity Editor visual review not yet done. Raw archives are local
only. See ASSISTANCE_CAMPAIGN_V1_2_REPLAY.md.

IMMEDIATE NEXT: user Unity review of A_NP vs R_NP. Motor coverage stays blocked
on external anatomy (coxa binding/axes, coxa-yaw sign, middle/hind Tarsus1). 20/42.

## V1.2 eight-arm assistance campaign COMPLETE — 2026-10-31

User-approved ONE V1.2 attempt at 61cafca, 18:20-23:07 UTC: COMPLETE /
INTEGRITY_ACCEPTED (all 8 arms, qualification transferred, piecewise/frozen/
mechanical audits, prefixes and RNG pass). A arms upright (3.9-4.3 deg); all R
arms roll over (~150 deg mean) with or without push or neural input. N vs W
MIXED_OR_UNRESOLVED at both levels; A pushed arms recover (613.5/520.1 ms), R
pushed arms confounded by control posture loss. One seed; display UNCONFIRMED;
reference EXACT_MISMATCH 'initial' (diagnostic, uninvestigated). Reports and
receipts committed; 4.67 GB raw kept local, hashes in raw-not-committed.json.
See ASSISTANCE_CAMPAIGN_V1_2_RUN_RESULTS.md.

IMMEDIATE NEXT: the 20 neural channels cannot replace the 22 baseline-only
servos, so expand neural motor coverage (coxa / roll / yaw) under a new
preregistered protocol before reducing assistance further. 20/42; balance/gait unproven.

## V1.1 attempt: A_NC complete, transfer read-back failed; V1.2 — 2026-10-31

User-approved ONE V1.1 attempt at 92652b5: ERROR/INCONCLUSIVE_INTEGRITY. A_NC
COMPLETE (20,001 states/4,000 neural/20,001 mechanical; qualification passed in
memory; ~62 min; 560 MB raw + 175 MB qualification), then the controller's
re-read of the saved qualification failed: json_safe +/-inf markers (adhesion
force ranges) not decoded. 7 arms unstarted; no retry; evidence committed.
V1.2 (assistance_campaign_v1_2) decodes markers exactly and compares the trace
journal clock at the runtime 1e-12 bound (second defect, found by an offline
audit of the retained A_NC), and checks per-state model phase by exact byte
snapshots instead of re-hashing 109 MB twice per state (~123 -> est. ~28 ms/step).
Offline audits 02/03: A_NC identity/scientific/
mechanical/qualification all pass (diagnostic only, not acceptance, no reuse).
See ASSISTANCE_CAMPAIGN_V1_2*.md; amendment locks both failures.

IMMEDIATE NEXT: review/merge; move untracked V1.1 evidence aside before pull
(commands in V1_2_RESULTS); V1.2 --check and preflight; then a fresh eight-arm
attempt (est. ~1.3-1.6 h, ~4.5 GB) only with explicit approval. 20/42; balance/gait unproven.

## V1 campaign attempt failed at binding; V1.1 guard correction — 2026-10-31

User-approved ONE V1 attempt at 953b607: INCOMPLETE/INCONCLUSIVE_INTEGRITY.
A_NC stopped in adapter binding (`mechanical capture mutated native data`):
1 state, 0 physics/neural, qualification not started, 7 arms unstarted. All
evidence committed under evidence/assistance-campaign-v1/run-desktop-01; no retry.
Cause: V1 guard hashed every exposed MjData buffer, including arena scratch that
changes between reads with no call (toy MuJoCo 3.2.7 diagnosis; fly fields not
recorded by V1). Separately versioned assistance_native/trial/campaign_v1_1 guard
mjSTATE_INTEGRATION fields (equal to mj_getState on real toy MjData), name changed
fields; science/acceptance unchanged; executed V1 sources and failed report locked
by evidence/assistance-campaign-v1_1/protocol.json. See ASSISTANCE_CAMPAIGN_V1_1*.md.

IMMEDIATE NEXT: review/merge; move untracked evidence copies aside before pull
(commands in V1_1_RESULTS); V1.1 --check and construction-free preflight; a new
live attempt to evidence/assistance-campaign-v1_1/run-desktop-01 only with explicit
user approval. Other fly-specific failures are possible; they will be named.
20/42, 0 new admissions; independent balance/gait unproven.

## Eight-arm campaign/evaluator implemented — 2026-10-31

Branch codex/assistance-campaign-v1 from merged PR294 (0b42311), sparse worktree;
primary LiveFly.unity edit untouched. New assistance_campaign.py: fixed A_NC..R_WP
fresh OS workers; complete V1.1 original prerequisites before/after controller AND
each worker; every campaign/adapter/design/frozen source committed at HEAD;
exclusive fsynced artifacts; first-A_NC qualification published separately
(failed/partial retained) and re-evaluated/transferred by hash to later arms.
Evaluator: A arms must pass the frozen constant auditor AND equal the piecewise
audit; R arms piecewise M0 0..5005 / derived MR 5006..20000; mechanical trace,
declared prefixes/RNG, 8 pair comparisons, posture-loss qualifier, contrasts.

46 new engineering tests pass (synthetic models; two real child processes with
a synthetic adapter). NO native model/CNS/qualification/physics run. Sparse
worktree lacks graph_w3.bin, so the campaign must run from a full checkout.
See ASSISTANCE_CAMPAIGN_RESULTS.md / ASSISTANCE_CAMPAIGN_V1.md.

IMMEDIATE NEXT: user review/merge, then in the full primary checkout run the
construction-free --output preflight, then ONE --live campaign (no retry/tuning).
Per-state full-model hashing cost is unmeasured; record actual runtime/storage.
Saved-replay entry point for the new schema is not implemented. 20/42, 0 new
admissions; independent balance/gait unproven.

## Assistance mechanical component checked — 2026-10-26

PR293 merged fdf60fbf4d53c65834bc773cb306113e3f0dcef6. Fresh isolated branch
from latest origin/newBrain; primary local LiveFly.unity edit unchanged.
New assistance_native.py implements exact actual-model20/22native binding,
lossless complete typed model records, bounded shadow qualification/restoration,
M0/MRevent and mechanical-only full-trace audit. New assistance_trial.py subclasses
the frozen original Trial and uses unchanged driver's explicit factory injection.
Original gating/encoder/safety/kernel/pulse still own all scientific steps.
Mechanical/qualification partials are retained under a new schema; full scientific
audit flag is FALSE. No frozen source/spec/protocol/result changed.

75engineering tests pass14.89s (new70including unchanged design checks, plus5
original driver/source/stop/partial regressions). All scientific models/sessions
synthetic; existing no-client observer regression uses a real socket. No native
body/CNS construction/qualification/scientific campaign. Git Bash --check passes;
this is source/design identity only, NOT full future runtime prerequisites.
Source manifest:evidence/assistance-native-adapter-v1/implementation.json.
Details/files/commands/limits:ASSISTANCE_NATIVE_ADAPTER_RESULTS.md.

IMMEDIATE NEXT: implement separately versioned COMPLETE eight-arm scientific
evaluator and fresh-process controller/workers. Reuse original force/command/RNG/
contact/recovery math with explicit piecewise context; NEVER fabricate A reports
or waive old constant-model checks. Require all original raw/data/environment/
graph guards before/after controller AND each worker, committed own sources,
fixed arm order, exclusive durable raw/partial artifacts, qualification transfer,
exact science/neural prefixes and all declared contrasts/posture-loss qualifier.
Test failed initialization/qualification, stop, cleanup and artifact persistence.
Do not launch the internal assistance_trial.run_arm as a standalone experiment:
it intentionally lacks campaign gates and full scientific acceptance.

After complete implementation/tests, COMMIT before ONE bounded first-A_NC-model
shadow qualification and eight fresh arms. Actual22-coordinate native binding,
force-law qualification, native model hashing performance and moving force audit
are still UNVERIFIED. No extra native initialization, retry, prior-control reuse,
fall truncation or outcome tuning.20/42,0new admissions; all20retained servos still
assist. No new Unity run this update; independent balance/gait unproven.

## Assistance-contribution prospective design — 2026-10-26

PR292 merged at3baaaa7afea3e24c716723ca633dfda0d45ee626; this update starts
from that latest origin/newBrain in an isolated worktree. User reviewed NEW V1.1
saved movement: normal, nothing weird, similar to prior runs. This confirms
recorded human review, not live delivery: acquisition sent_frames0 remains true.
Primary checkout's local LiveFly.unity edit and all historical results untouched.

ASSISTANCE_CONTRIBUTION_V1.md and evidence/assistance-contribution-v1/protocol.json
predeclare eight fresh arms: original versus neutralized22baseline-only servos,
neural20continued versus withdrawn, push versus no-push. Retain all20neural
position actuators and safety;22coordinates remain unadmitted. This is partial
assistance contribution, not removal of all support. No parameter/acceptance tuning.
One future budget160,000physics/32,000neural/160,008states, no prior-control reuse,
retry/resume/early fall truncation. Known reference behavior remains MIXED.

Static planner/checker only:26tests pass0.88s; exact Windows Git Bash verification
passes. No new native model/CNS construction, qualification or experiment. Native
bindings deliberately null. Original locks checked read-only, complete future
runtime prerequisites NOT verified by this static design. See
ASSISTANCE_CONTRIBUTION_DESIGN_RESULTS.md for files, commands and limits.

IMMEDIATE NEXT: implement separately versioned instance-local Trial/observer/
piecewise model evaluator around existing injectable run_arm factories/kernel.
Reuse native inventory/force projection and unchanged complete original source
guard, never modify frozen executed V1/V1.1 sources or weaken their auditors.
Prove exact22/20selection, boundary after sample5005, phase5006onward, force-law
suppression and full traces with engineering tests. Commit implementation first.
Then ONE bounded native qualification on first arm's model/shadow data (12explicit
shadow resets/forwards,0live forward/reset/integration/CNS), followed only if valid
by eight fresh arms. Any qualification failure stops/preserves data, no retry.
Moving force audit still mandatory. No extra native initialization for preflight.
20/42coverage,0new admissions; independent balance/gait unproven. No new Unity run
in this design delivery. Older checkpoints below retain their dated status.

## V1.1 native campaign completed — 2026-10-26

ONE campaign at4ad0c04 COMPLETE/INTEGRITY_ACCEPTED:NC/WC/NP/WP each20kphysics/
4kneural/20001states,total80,000/16,000/80,004. Mandatory complete original
loader-source checks passed controller and each worker before/after acquisition.
Frozen executed V1.1 code/protocol/doc and V1 sources remain unchanged. Original
failed live V1 and older accepted reference intact. No retry/tuning/dependency change.
All4full science-trace reference comparisons EXACT_MATCH(initial/context/samples/
neural/init operations), environment/original scientific-source differencesfalse.

Behavior MIXED_OR_UNRESOLVED:NPmean/peak world tilt3.8505/4.2674deg vsWP4.3072/
4.3491;peak difference below0.25deg resolution. Own-control band return NP613.5/
713.5ms vsWP520.1/620.1ms. No rollover/low-height/<3support in declared cleared
window; raw startup samples retained. One-seed2s assisted test,20/42,0new admissions;
no independent neural balance/gait. See CONTROLLED_LIVE_BALANCE_V1_1_RESULTS.md.

All15,256offered/queued live packets projection-verified;sent_frames0forALLarms.
Do not claim actual live Unity viewing. New controlled_live_balance_replay.py
explicitly verifies the new schema before using existing projection/playback/
transport; no scientific rerun.32new-adapter/existing replay/socket tests pass.
Full actual saved-packet verification passed:80,004packets, saved evaluation
exactly reconstructed in197.23s with native imports and CNS/session constructors
forbidden. No server/human visual review in that check. Native raw/
receipts/summary:evidence/controlled-live-balance-v1_1/run-desktop-01/.

IMMEDIATE NEXT:merge/review this PR, then human Unity review via NEW saved-replay
entry point/commands in RESULTS. Old replay adapters intentionally reject new
schemas. No more native attempts under this protocol. After visual review, design
a separately declared assistance-contribution experiment; current servos support
posture and mixed output does not justify gain/drive/threshold/seed changes.

## Controlled live V1.1 engineering — 2026-10-26

New controlled_live_balance_v1_1.py and CONTROLLED_LIVE_BALANCE_V1_1.md/protocol
require the complete original source guard in parent and EVERY worker before
initialization and after acquisition. Own schema/source identity; unchanged
V1 run_arm/observer and original scientific auditors/proof/behavior. Prior V1
failed report/executed source manifest locked; preserve all prior source/results.
67engineering checks pass81.59s (synthetic/miniature neural fixtures plus actual
OS/sockets, no new native fly/full-CNS experiment). Real construction-free
prerequisites verify; both original source/compressed graphs included up front.
An early policy-versus-package schema comparison refused real preflight before
execution; corrected with real-receipt test, not parameter/acceptance relaxation.
Development01/02preflights retained. See CONTROLLED_LIVE_BALANCE_V1_1_RESULTS.md.

Commit tested code/spec/tests BEFORE ONE new fixed NC/WC/NP/WP attempt. No prior
control reuse, retries or tuned behavior. User previously confirmed full-body
old replay visible/no issues, Unity in Play and old replay stopped. Live output
remains provisional until full offline audit; no new visual result claimed here.
20/42,0new admissions, assistance unchanged; independent balance/gait unproven.

## Live V1 actual attempt retained — 2026-10-26

ONE attempt at committed2055e06: INCOMPLETE/INCONCLUSIVE_INTEGRITY. NC failed
inside original loader validation: graph_w3.bin unavailable for graph orientation
source comparison. Isolated sparse checkout omitted it.0states/physics/neural,
0display poses; WC/NP/WP unstarted. Original loader call1observed; initialization
did not complete. Full partial raw/display/OS receipts and exact saved refusal
retained in evidence/controlled-live-balance-v1/run-desktop-01/. No retry.
Old accepted V1.1 recording remains unchanged. Behavior of live V1 is unmeasured.

Historical base.preflight checks7core artifacts but misses this additional source.
New SEPARATE balance_source_prerequisites.py verifies original graph_w3 Git bytes
from frozen baseline2bcd103 without decoding/constructing a CNS; combines all old
checks. Before-hydration failure retained; restored exact63,726,728byte source
SHAc34efca42d074786e8fb4fe4b6723d5b15aa4d69be17b0cf457321cb2ac6e030;
combined check now passes. No expected hash/source/result change. Executed runner,
observer and implementation contract at2055e06 remain immutable after this attempt.

Final new live tests37pass36.07s; earlier broader114pass181.06s; source guard plus
actual retained failure reconstruction11pass0.48s. Git Bash/source checks in
CONTROLLED_LIVE_BALANCE_IMPLEMENTATION_RESULTS.md; no new fly run in those commands.
User confirmed full-body replay visible/no issues and Unity ready. New attempt
emitted no poses, so no new Unity visual result is claimed.

IMMEDIATE NEXT: prospective/versioned V1.1 complete-loader-source prerequisite
correction, requiring the new guard and binding it into each worker's explicit
source identity. Test/commit before ONE fresh bounded four-arm attempt, no old
control reuse, registry tricks, source/hash relaxation or behavior tuning. Do not
rerun frozen V1 merely because the file is now present.20/42,0new admissions;
independent balance/gait remain unproven under current position assistance.

## Controlled live adapter — 2026-10-26

New controlled_live_balance.py and balance_live_observer.py implement the fixed
prospective design with explicit source/schema identity, instance-local output
observation and fresh per-arm processes. All original scientific APIs/auditors
and42actuator assistance remain unchanged. See
CONTROLLED_LIVE_BALANCE_IMPLEMENTATION_RESULTS.md for engineering checks, exact
prerequisites, pending native status and commands. Broader suite114pass; targeted
final stop/cleanup suite37pass before source-lock audit. User confirmed full-body
recorded review with no unexpected issues, Unity in Play, prior replay stopped.
Commit tested implementation BEFORE one new bounded NC/WC/NP/WP attempt, into
evidence/controlled-live-balance-v1/run-desktop-01. No retry/tuning. Live poses are
provisional; science/display status separate. Do not modify frozen old science or
the new execution contract after the attempt. Default --output is preflight only.
Original prerequisites verify after targeted LFS hydration. No new motor admission;
20/42; independent balance/gait unproven. Native results will supersede this
pre-execution checkpoint in the next top entry without erasing failures.

## Controlled live balance design — 2026-10-26

PR289 merged at03098a0. CONTROLLED_LIVE_BALANCE_V1.md and separate machine-readable
evidence/controlled-live-balance-v1/protocol.json specify prospective live
observation of ONE new bounded NC/WC/NP/WP campaign. DESIGN_ONLY: no new runtime,
native initialization, experiment or Unity review in this update. Known prior
result remains MIXED_OR_UNRESOLVED; no improved behavior promised by a viewer.
Scientific settings,20/42motor authority,42actuator assistance,392proprio RNG,
force/withdrawal/timing/bands/budget and all original integrity criteria unchanged.
All streamed output must be provisional until complete offline audit, distinct
from accepted saved replay. Journal emitted/attempted display observations
separately; client presence, input, disconnects and FPS must not control science.
New worker/controller identity must be explicit, not masquerade as frozen V1.1.
No old source/spec/expected hash/result edits. Static design checks only.

IMMEDIATE NEXT: implement/test the dedicated instance-local live observation and
fresh-process lifecycle/report adapter using existing Trial/create_session,
ScientificSession, PoseServer and original auditors; commit before any native
attempt. Prior full-body human review remains unconfirmed; complete it before
the bounded live execution. Reduced assistance/independent balance is a separate
future scientific question. Desktop commands and actual checks in
CONTROLLED_LIVE_BALANCE_DESIGN_RESULTS.md. No new live-run command exists yet.

## Desktop camera continuation — 2026-10-26

PR288 is now merged at7e14bc0; its open-review status below is historical.
New presentation-only `Frame Current Fly` menu fits current active renderer bounds
and freezes the world camera without changing scientific rig poses or saving the
scene. Use after receiving a pose in Play; full-body human review remains pending.
See LIVE_FLY_CAMERA_FRAMING_V1.md for desktop commands, checks and limitations.
The desktop environment actually available is fly-brain-interactive/.venv with
Python3.12.10/NumPy2.0.2; the laptop's ignored .cache venv is absent here.
Existing replay/transport/console checks27pass; Unity camera/scene EditMode6pass.
No new scientific experiment or manual full-body review occurred in this update.
Keep executed process source/spec/protocol and accepted/failed evidence unchanged.
Next after visual review: separately predeclare the controlled live experiment
and assistance policy, reusing existing20motor kernel/transport. Existing
continuous live viewing is not itself a matched balance assay. Motor20/42;
independent balance and gait remain unproven. Preserve primary local files.

Latest 2026-10-26 completed checkpoint: V1.1 NC/WC/NP/WP all complete,
80,000 real physics transitions / 16,000 neural updates / 80,004 states; all
integrity checks accepted. Behavioral label MIXED_OR_UNRESOLVED under position
assistance, one seed, 20/42 motors, zero new admissions. Original failed V1
retained. Offline all-packet verification passed; Unity LiveFly Play connected
and applied advancing poses (64/64 rig bindings). Default camera crops the fly:
full-body visual review remains pending framing; Blender import errors did not
block this smoke test. No independent balance or gait claim. See
[BALANCE_CONTRIBUTION_PROCESS_RESULTS.md](BALANCE_CONTRIBUTION_PROCESS_RESULTS.md)
and [replay guide](BALANCE_CONTRIBUTION_UNITY_REPLAY_V1.md). PR288 remains the
single active review; user merges. Frozen executed process source/spec/protocol
must stay unchanged to preserve evidence identity. Separate console wrapper
fixes final-print int64 error without rerunning the assay.

Earlier dated checkpoints below preserve their historical status.

## V1.1 process-boundary continuation — 2026-10-26

User requests a Unity-distance update after EVERY run. Report actual tests/
native counts, integrity versus behavior, remaining replay gates and20/42 motor
coverage without an arbitrary completion percentage or independent-balance claim.

New `live/balance_contribution_process.py` uses a fresh process per fixed arm;
old V1 driver/auditors remain unchanged. Prospective protocol/specification are
BALANCE_CONTRIBUTION_PROCESS_V1_1.md and evidence/balance-contribution-process-v1_1/
protocol.json. See BALANCE_CONTRIBUTION_PROCESS_RESULTS.md for latest results.
72engineering/reference checks passed106.78s; includes actual OS child smoke
tests with fake registries/data, original auditor/analysis equivalence, stop and
incomplete guards, calibrated JS/Python parity and checkout locks. Earlier
66pass/2source-hash failures from editing the protocol doc during tests retained.
No native V1.1 execution at this implementation checkpoint. Commit first, then
one fresh bounded NC/WC/NP/WP attempt under unchanged original scientific rules.
No registry reset/name stripping, old controls, lowered guards, tuning or retries.

Unity distance: environment ready; process engineering validated; full four-arm
native integrity and verified saved-pose replay still pending. Replay may show
valid null/negative outcomes. Independent balance/walking and42-coordinate coverage
are not prerequisites or results of this assisted20-coordinate contribution test.

Current draftPR288 is the active review; continue related corrections there as
agreed with the user rather than making additional superseding drafts.

## Desktop continuation — 2026-10-26, after the first bounded attempt

Read `BALANCE_DESKTOP_ENVIRONMENT_V1.md` first. Environment blocker is resolved:
new ignored `.cache/malecns-balance-python312-v1/Scripts/python.exe` under the
PRIMARY Documents/FlyBrainUnity checkout is Python3.12.14, FlyGym1.2.1,
MuJoCo3.2.7, dm_control1.0.27, NumPy2.0.2, SciPy1.15.3, pyarrow25.0.1.
pip check/imports and37focused tests pass. Old Python3.10 venv is unchanged.
Hashed136-wheel lock, desktop inventory and receipt are preserved in new evidence.

Original static authorities pass after cached LFS hydration and guarded original
Git-byte restoration of two CRLF-converted JSONs in the isolated worktree only.
Original backups/locks retained; new -text attributes plus6real checkout tests.
Do not refresh expected hashes or repair the user's primary edits incidentally.

ONE ACTUAL ATTEMPT: `docs/evidence/balance-contribution-execution-v1/run-desktop-01/`
at committed implementation266285f. NC completed20000physics/4000neural,20001states.
WC failed during initialization:1initial state,0scientific transitions/updates.
NP/WP unstarted. Status INCOMPLETE/INCONCLUSIVE_INTEGRITY; behavior null (not a
measured biological null); Unity ineligible. Saved evaluation/hash replay passes
with native imports/CNS construction forbidden. No automatic retry occurred.

WC discrepancy is84absolute-name fields only: current FlyGym instance1/... versus
historical M5A0/...; all numeric joint/actuator IDs and address comparisons match.
Installed1.2.1 source preserves an existing-name registry across fresh instances.
The adapter's historical absolute instance-name assumption is defective. Actual
native inventory validation passed before the extra comparison rejected WC.
Raw initial/context/prefix comparisons also contain names; deleting only the
first guard is not an end-to-end fix. No identity, physiology or mapping waived.

Next concrete gate: prospective/versioned instance/process-lifecycle correction,
prefer fresh process per arm while keeping actual-model resolution and strict
original checks; tests and commit before any justified new four-arm attempt.
No registry reset, guessed IDs, mere name stripping, resume-from-WC or repeat
until favorable output. That correction/new attempt is NOT implemented/run here.
20/42 motors,0new admissions, LF target0/8; no balance/gait claim. Roadmap+GitBash.

Older checkpoints below retain their dated facts; their environment-blocked and
native-not-run statements describe the earlier implementation delivery.

## Continuation checkpoint — 2026-10-26

Balance-contribution V1 adapter/recorder/evaluator is implemented separately in
`malecns_backend/live/balance_contribution.py`. See
`BALANCE_CONTRIBUTION_IMPLEMENTATION_V1.md` for actual checks, failures and Git
Bash commands. Original design/JSON remain immutable historical specifications.
New engineering checks23passed; existing neural runtime checks13passed after a
Node sandbox-permission rerun. Full synthetic four-arm null acceptance is an
evaluator test only. No actual native body/full connectome experiment or Unity
replay was run. Coverage20/42, newadmissions0, LF target correspondence0/8.

EXECUTION BLOCKED: legacy desktop venv points at missing Python3.10; bundled
Python3.12/NumPy2.3.5 lacks FlyGym/MuJoCo/dm_control/pyarrow. Do not install or
upgrade dependencies incidentally. Original cached LFS prerequisites were
hydrated only in the isolated worktree; initial M6C pointer failure is explained,
not waived. Static authority now reaches missingpyarrow; later locks unverified.
Seven original neural/calibration identities verify (binary/data raw; calibration
text canonicalLF with actual raw hash retained). Preserve all refusal reports.

Next: restore/access validated Python3.12, NumPy2.0.2, FlyGym1.2.1, MuJoCo3.2.7,
dm_control1.0.27 environment and its existing reference dependencies; complete
construction-free prerequisite checks. Commit tested implementation before the
single bounded NC/WC/NP/WP execution. Real native recorder/factory/initialization
instrumentation remains unverified; synthetic tests are not runtime readiness.
No retries/tuning or new motor admissions. Preserve the primary checkout's local
live_v1_motor_output_experiment_result.json change. Continue roadmap+GitBash.

The checkpoint below records the preceding design delivery and earlier history.

Checkpoint: 2026-10-25. Repository: `rjo6615/FlyBrainUnity`.
Verified baseline for balance-contribution protocol design: `origin/newBrain` at
`2bcd103` (merged PR #285).
Fetch and inspect current state before starting work.

USER-SELECTED NEXT WORKSTREAM: controlled balance-contribution test using the
existing20motors. Design completed in BALANCE_CONTRIBUTION_V1.md plus machine-
readable evidence/balance-contribution-v1/protocol.json. Status explicitly
SPECIFIED_NOT_IMPLEMENTED_NOT_RUN: no new runner or native/CNS initialization.
Next implement/test the isolated session adapter, recorder and evaluator using
existing kernels/encoders/safety/observers; commit implementation before a single
bounded four-arm experiment. Do not resume repeated anatomical audits as the
default main task; missing independent anatomy remains a separate blocker.

Protocol: fresh NC,WC,NP,WP in that order, seed1,2s,20kphysics/4kneural per arm,
current20motor authority; all42position actuators keep identical assisted policy.
Only392tibia proprioceptive input, tactile off; existing assay-only392-slot common
CNS RNG and existing per-leg samplers, no parameter changes. At neural1001/state
5005/time500.5ms W zeros decoder inputs BEFORE unchanged safety/range/slew;
do not use final_contribution_gate to hard-zero final targets or reset history.
Residual target offset returns naturally; record it separately from pre-slew
admitted input. Pulse[0,1.024,0] at Thorax COM outgoing5000..5199. All-arm prefix
through state5000, same-push-class physical prefix through5005; first possible
withdrawal physical effect5006. Terminal update4000 at2000ms is retained but
unapplied (no outgoing transition20000). Fixed cleared window5201..20000 and
inherited bands/resolution; no fall truncation/retries/tuning. Baseline assistance
can support posture; no independent balance/gait claim. Null/negative results
with valid complete integrity may be replayed in Unity; do not require success.
Capture initialization operations separately; no hidden extra inventory model.

Distal qualification used exact original eLife96084 supp3/6 CSVs. For20T2/T3 BANC
rows, all21distinct MANC body refs found;16limb-only targets,5other named muscles,
no named tarsal serial rows. Primary Figure7D explicitly leaves those T2/T3 targets
unresolved. IDs/groups/serial/type namespaces and blank match fields kept distinct.
Reviewed BANC metadata transfer/derivation does not establish independent anatomy.
No new motor admissions, old sources/hashes changed or author messages. See
DISTAL_ANATOMICAL_QUALIFICATION_RESULTS.md and new qualification.json.
Static source/manifest/timing checks and pure safety reference checks are the
only validation in this update; no new physics/CNS experiment or mocked fly run.

Latest independent reference work: `DISTAL_TARSUS_REFERENCE_RESULTS.md`. Two
generation-pinned BANC/MaleCNSv0.9 mirror snapshots acquired separately; current
BANC mirror differs from paper file, and publication archive returned403. Raw
sources, metadata/generations/checksums and code/schema revisions preserved.
43broad-query rows retained (30BANC tarsus types+13external-label controls), complete
original source fields, exact runtime indices, aliases and missing/many-to-one/
action/MANC/NBLAST disagreements. Match ID values are unvalidated reference leads,
not confidence or proven homology. All proposed populations/actuators/signs/gains
null; admission remains20/42. New source does not fill LF target attachments.

Right-middle levator801477(MNml81) has duplicate BANC and conflicting MANC/NBLAST
references. Right-hind869369(MNhl65)/800358(MNhl64) have concordant recorded MANC
references but incomplete population/function qualification. Other references
conflict with current long-tendon/proximal labels. Do not reassign them or mirror
missing left levator references. Next qualify exact cross-dataset anatomy/morphology,
v0.9/v1.0 correspondence and complete antagonist membership for all four distal
coordinates, then mechanical/action sign and a separate admission protocol.

V1NaN partial JSON, V1.1datetime error, V1.2complete but boundary-limited report
preserved. Strict test exposed old admission.verify -> live inventory/model
construction; V1-V1.2not construction-free and constructor operations unmeasured.
V1.3 reuses existing lf_force_static_reference.load; actual43-row reconstruction
passes with FlyGym/MuJoCo/neural imports, legacy enumeration, audit.build and
transition kernel forbidden. Do not relax that boundary. Accepted namespace:
evidence/distal-tarsus-reference-v1_3/run/. 39tests passed18.80s (24new+15existing);
the broader legacy audit regression itself constructs a model. No CNS/moving-fly
assay. Original three raw locks true here; historical failures and primary edits
preserved. Continue Git Bash and roadmap status after each run.

Latest independent engineering fix: `MOTOR_FREEZE_CHECKOUT_V1.md`. Three old
motor/sign/registration result Git blobs exactly match their unchanged original
freeze/manifest hashes, but Windows CRLF conversion breaks working-copy raw checks.
Exact -text attributes now preserve future checkouts. New `motor_freeze_checkout`
CLI is read-only by default; explicit --repair requires an exclusive backup
directory, exact original Git/hash/index agreement and CRLF-only working changes.
It refuses scientific/staged edits, backs up all three originals, rechecks and
atomically restores original Git bytes. No new hashes, criteria or source results.

Actual isolated-worktree repair verified original three locks3/3; existing saved
22-row audit still reports recorded rawFalse/currentTrue,20/42,0new admissions,
0scientific transitions and unchanged12/6/4 blocker counts. Historical failed
reports remain intact. This fixes checkout provenance only, not biological
function, target correspondence, physical scaling or neural activation. The
primary checkout/local edits were not repaired or overwritten by the agent.
Users with existing CRLF files need the documented guarded command after pull;
an attributes-only pull need not rematerialize unchanged files.

Active research blocker remains the same LF target attachment/landmark reference
bundle. No observer campaign or guessed mapping substitutes for it. Independent
maintenance was selected after user continuation; new anatomy/data is still needed
before advancing the new moving-body muscle interface or admitting channels.

Latest continuation: `LF_REFERENCE_ACQUISITION_V1.md` records a bounded official
publication/data/code acquisition review. No qualifying target annotation bundle
was acquired; no new physics/CNS or observer campaign. Original development repo
returned GitHub API404; raw-imaging shares were JS-only, empty in extraction or
inaccessible to the browsing tool. These are access limits, not absence proofs.
FlyGym issue276 provides a distinct-rig compatibility warning; retrieved body and
metadata preserved in `evidence/lf-reference-acquisition-v1/flygym-276-snapshot.json`.
Its mesh/body claims were not reproduced against our locked assets and do not
authorize target attachments, dependency changes or body substitution.
After the user's repository pointer, full public FlyMimic main tree at9ea1131
was inspected (119blobs,not truncated), along with local ZIP contents and OpenSim
PathPoint inventory. Both OpenSim models contain37source path points; these exist
but do not establish exact target correspondence. Mesh ZIP has only STL payloads;
demo ZIP has policy files. Public tree metadata preserved separately in
`evidence/lf-reference-acquisition-v1/flymimic-tree.json`; no local source edits.

Immediate next action: request an accessible model-development/anatomical
annotation artifact or authoritative revision/download meeting the existing
reference-request.json. That remains the active research blocker. No author
outreach without user authorization; no observer-only PR or guessed fit as a
substitute. Motor coverage20/42 (47.6% coverage, not project completion), new
admissions0, target correspondence0/8, target points null, muscle coupling disabled.
Roadmap now includes a compact progress display and separates numerical checks
from anatomy/physical/neural gates and independent balance/walking.

## What the user wants

A scientifically controlled connectome-based fly whose movement emerges from
neural activity coupled to body physics and environmental senses. The intended
sequence is expanding the anatomically supported motor inventory toward all 42
coordinates, adding senses, then testing balance and locomotion. Stable gait
has not been established. Do not make neurons fire merely to make a joint move.
The user explicitly reaffirmed this constraint during the recent work.

Each update uses a new branch from latest `newBrain` and a PR back to `newBrain`.
The user reviews/merges. Include files changed, tests actually run, manual Git
Bash instructions and expected outcomes. Keep negative results and experimental
limitations visible. Read root `AGENTS.md` for enduring workflow requirements.
The user explicitly wants a copy-paste Git Bash run block in every final update;
provide post-merge/pull replay commands directly, not just a documentation link.
The user also requests a roadmap update after EVERY run: what ran, what its result
establishes and its limits, current motor count, active gate and next concrete gate.

## Current runtime and code map

- `malecns_backend/neural.py`: calibrated NumPy LIF runtime; graph CSR rows are
  presynaptic. Default dt=0.5 ms, rest/reset=-52 mV, threshold=-45 mV,
  tau_mem=20 ms, tau_syn=5 ms, PSP scale=0.55, minimum synapses=6,
  refractory=3.76 ms, inhibitory gain=0.606. Conductance mode is active.
- `fly-brain-main/src/lif.js`, `src/brainmodel.js`, `src/ratenet.js`, and
  `public/data/brain_params.json`: checked-in fast-neural reference and calibration.
- `malecns_backend/live/__main__.py` and `live/headless.py`: live launcher/session
  factories. Default interface v1=11 motors; v2=17; v3=20. All currently use six
  tibia proprioceptive populations (392 neurons), with tactile delivery disabled.
- `malecns_backend/embodiment/_windows_m8_live_condition.py`: shared scientific
  transition kernel, observers and optional passive probes. Reuse it rather than
  invent a second embodiment loop. Its optional old tactile path selects LM only.
- `embodiment/sensory.py`: existing modeled tibia angle encoder. Preferred angles
  depend on frozen list order, not measured individual sensory tuning.
- `live/upstream_diagnostics.py` and `live/presynaptic_trace.py`: body-ID/readout
  checks, post-step states, selected shortest positive paths and input activity.
- `live/sensory_coverage.py`: offline midpoint/up/down prescribed-angle experiment,
  optional pathway diagnostics, no physical body or motor commands.
- `live/contact_readiness.py`: bounded passive live-v3 exact Tarsus5/force survey.
- `live/contact_context.py`: fixed two-second passive live-v3 solver-force
  attribution audit with exact body/sensor ownership, complete raw evidence and
  strict observational context checks. It never enables tactile delivery.
- `embodiment/tactile_contact.py`: existing contact-only onset encoder. Engineering
  threshold 1e-12 model force units, maximum modeled rate 120 Hz, 20-ms linear
  onset pulse, no sustained-contact retrigger. These are not biological measurements.
- `embodiment/tactile_targeted_contact_calibration.py`: legacy environment-only
  targeted calibration; already accepts all six leg arguments. Source is locked
  by later milestone provenance and should remain intact.
- `embodiment/six_foot_contact_calibration.py`: new fixed batch and strict evaluator.

The authoritative maps are checked-in artifacts; inspect consumers and tests
before editing. Do not infer roles from similar names. Historical COMPLETE data
can coexist with older narrative docs saying NOT_RUN; inspect actual artifacts.

## Established recent findings

### Candidate motors and prescribed sensory stimulation

The three investigated v3 channels are `joint_RFFemur`, `joint_LFTarsus1`, and
`joint_RFTarsus1`. All were silent in the original resting live run. Identity and
observer checks passed; input reached some cells but remained subthreshold.

A seed-1, 10-second-per-condition offline experiment recruited all 392 sensors:

| Candidate channel | Midpoint spikes | Upward sweep | Downward sweep |
|---|---:|---:|---:|
| Right front femur | 3 | 1 | 3 |
| Left front tarsus | 2 | 1 | 1 |
| Right front tarsus | 0 | 0 | 0 |

The traced repeat reproduced those totals. On selected path
815569 -> 800022 -> 903285 -> 820110, counts were 363/144/0/0 at midpoint,
404/148/2/0 upward, and 392/40/0/0 downward. Motor 820110 received excitation but
remained at least 6.2316 mV below threshold in upward-condition post-step samples.
Other selected intermediates 902679 and 46348 never spiked in these conditions.
Paths are structural examples, not exhaustive causal routes. Voltage is sampled
after spike reset and synaptic decay; maxima are not pre-spike peaks. Separate
excitation/inhibition peaks cannot be subtracted as simultaneous net drive.
These sparse results establish neither useful movement nor biological function.

### Neural scaling and neuromodulation

PR #252 corrected a demonstrated regional median convention mismatch: JS uses
upper middle size for even populations; Python had averaged the middle pair.
The canonical VNC input-scale effect is about +0.001515%, too small to claim as
an explanation/remedy for the silent tarsus. Actual calibrated JS constructor
and 160-step mixed-input parity checks pass. User independently ran the 14-test
neural/parity check successfully. See `embodiment/NEURAL_SCALING_AUDIT.md`.

Python removes OA fast signs but omits the reference's separate slow modulation
system. This documented scope difference is not automatically a bug. PR #253's
static reference audit found 37 OA cells, 16 IPCs and 10004 direct OA targets.
None of the 21 watched cells (including seven right-tarsus motors and selected
intermediates) has direct OA input at minSyn=6. No direct target is in a vnc_*
superclass; descending/ascending targets leave indirect effects possible.
No physiology was enabled. See `embodiment/NEUROMODULATION_SCOPE_AUDIT.md/.json`.

### Contact readiness: positive observational result

User ran PR #254's two-second current-v3 passive survey:
`v3-contact-readiness.json`, completed=true, 20001 samples, no tactile delivery.
All feet had positive and negative exact Tarsus5-ground contact samples.
Force-above-1e-12 matched exact contact presence with zero mismatches in every
sample for every foot. This is posture-specific correspondence evidence, not a
matched threshold calibration or proof of biological sensing/balance.

### Latest calibration: controls contaminated, no feet admitted

User ran PR #255's fixed six-foot calibration and uploaded
`six-foot-contact-calibration.json`. All twelve physics conditions completed.
Each condition contains 501 samples over 0.05 seconds at dt=0.0001 seconds.
All six feet failed exactly `control_never_touches_target_surface`; accepted_legs
is empty and all_six_accepted=false. Other strict checks passed.

| Foot | Control contact samples | Contact-condition contact samples | First control contact (ms) |
|---|---:|---:|---:|
| LF | 44 | 46 | 2.9 |
| LM | 92 | 92 | 3.1 |
| LH | 80 | 82 | 3.4 |
| RF | 45 | 46 | 2.9 |
| RM | 91 | 89 | 3.1 |
| RH | 79 | 83 | 3.4 |

The nominal negative surface starts with a 0.01 model-unit gap but is contacted
during the trajectory. Exact contact/force presence agrees in **all 6012 samples**
(6 feet x 2 conditions x 501). Thus the strict failure is the negative-control
design, not a demonstrated sensor failure. The older threshold evaluator filters
out contacted control samples before computing false positives; its
THRESHOLD_ACCEPTED output must not override the newer full-condition rejection.
Do not drop those samples, shorten the window after seeing contact times, or
weaken acceptance merely to admit the feet.

A derived machine-readable summary with source-file hashes is in
`docs/evidence/contact-calibration-checkpoint.json`. It is a summary of user-run
measurements, not the complete raw record or automatic experimental approval.
The raw uploads may not be committed; look in the user's repository/root outputs
before requesting files. If unavailable, retain the checkpoint and distinguish
what cannot be independently rechecked. Do not rerun an unchanged failed protocol.

## Latest update — separately versioned isolated control implemented

`embodiment/six_foot_contact_calibration_v2.py` implements the predeclared
collision-isolation protocol in `docs/SIX_FOOT_NEGATIVE_CONTROL_V2.md`. Both arms
exclude ground, self and other-foot collisions. The negative surface is remote
and collision-disabled; the positive permits only the exact selected pair.
This changes physical support/collision context and does not validate ordinary
live-v3 contact. Original v1 sources/evidence/acceptance remain intact.

Actual local physics completed both twelve-arm runs. Initial v2 rejected all feet
for implementation integrity defects (auto-generated namespaces and float32 norm
precision). The separately documented v2.1 correction fixes those contracts,
without weakening checks or changing physical/neural parameters. It was committed
before its justified verification repeat. All six pass v2.1 in the isolated assay.
Full rejected and accepted evidence, hashes, environment and checks are preserved
under `docs/evidence/six-foot-v2*.json.gz` and
`docs/evidence/six-foot-contact-v2-checkpoint.json`. See
`docs/SIX_FOOT_NEGATIVE_CONTROL_RESULTS.md` for counts and limits.

The context-transfer prerequisite was investigated by the following separate
observational protocol. Isolated acceptance by itself did not establish transfer.

## Latest update — normal supported live-v3 context observed

The protocol in `docs/LIVE_CONTACT_CONTEXT_V1.md` was committed at 80aba8d before
its single two-second live-v3 CNS/physics experiment. The existing kernel and
normal corrected support/collision context ran unchanged, with no tactile input.
All 20000 physics transitions / 4000 neural updates completed; 20001 raw states
and 333454 complete contact records are preserved through Git LFS in
`docs/evidence/live-contact-context-v1.json.gz`. Hashes and complete evaluation
are in `docs/evidence/live-contact-context-checkpoint.json`.

All six feet passed exact sensor/body/geom ownership, force reconstruction,
telemetry conversion, immutable-context and full-window correspondence checks.
Positive/negative state counts LF/LM/LH/RF/RM/RH were 19970/31, 19946/55,
19946/55, 19902/99, 19943/58, 19938/63. No ambiguous direct sources or force,
reconstruction or telemetry disagreements occurred. All distal positive sources
were ordinary ground; the calibration surface had no positive coverage. Do not
generalize this result to unobserved collisions, other seeds/poses or continuous
geometry between physics samples. This remains observational, not causal.

127 tests plus 9 subtests passed, including full archived-evidence hash/source
verification and replay of every reported check. A separate paired ten-transition
physics-only implementation smoke test showed exact observed/unobserved parity;
its held-joint context is not scientific live-v3 evidence. See
`docs/LIVE_CONTACT_CONTEXT_RESULTS.md` for details and Git Bash commands.

The next task at that checkpoint was to design and separately version matched tactile-delivery
enabled/withheld experiment in the tested supported context, reusing the encoder
and independent/common candidate sampling, with pre-intervention equivalence and
verified delivery/readout boundaries. Define treatment of unobserved contact
sources explicitly. No tactile delivery is enabled by this update. Acceptance
does not establish balance, gait or biological transduction.

## Latest update — matched tactile delivery changed the simulated body

The fixed two-second WITHHELD/ENABLED protocol and instance-local external-input
adapter were committed at 24af69f before execution. Both fresh live-v3 arms ran
20000 physics transitions / 4000 neural updates, keeping normal supported physics,
20 motor interfaces and all physiological/encoder parameters fixed. They use a
prospectively common 2269-slot CNS external RNG schedule in both arms; this is an
explicit assay context. No locked kernel/neural/encoder source or ordinary live
default was changed. Six complete tactile populations (1877 neurons) are sampled
in both arms; only the input delivery mask differs. No retries or tuning ran.

All paired integrity and calibrated-context checks passed. First eligible tactile
event / CNS divergence was 0.5 ms; non-input state divergence 2.5 ms; non-input
spike divergence 5.5 ms; motor spike/decoder/command divergence 14.5 ms; physical,
joint and contact-force divergence 14.6 ms. Excluding all 2269 input neurons
distinguishes downstream effects from directly driven sensory spikes.

WITHHELD delivered zero tactile events; ENABLED delivered 64431 over the fixed
window. Later contact/candidate totals legitimately diverge in closed loop. The
previously investigated right-front femur motor readout had 0/56 spikes
(WITHHELD/ENABLED), left-front tarsus 0/9, right-front tarsus 0/0. Full-window A/B
joint differences reached 15.10 degrees at left-middle tibia; maximum root
separation was 0.291869 model mm. These are simulated effects, not balance/gait
or biological validation. No positive calibration-surface coverage was observed.

Full raw pair is in Git LFS at `docs/evidence/matched-tactile-v1.json.gz`; hashes,
full checks, counts and descriptive magnitudes are in
`docs/evidence/matched-tactile-checkpoint.json`. See
`docs/MATCHED_TACTILE_DELIVERY_V1.md` for prospective criteria and
`docs/MATCHED_TACTILE_DELIVERY_RESULTS.md` for actual checks and Unity commands.
The older tactile-contact artifact hash test fails unchanged in origin/newBrain
because d03f2a6 added live metadata without changing biological populations;
neither the expected hash nor the artifact was refreshed in this update.

Immediate next task: review the paired recorded Unity poses and intervention
evidence, then design any ordinary live tactile mode or next motor/balance
experiment separately. `live.tactile_replay --condition BOTH --speed 0.1` streams
the saved arms through the existing output-only protocol without rerunning CNS.
The standard live-v3 launcher remains tactile-disabled. Unity Editor was not run
by the agent; an actual two-pose TCP smoke check passed. Preserve the right-front
tarsus null result and distinguish passive mechanical motion from motor spikes.

## Latest update — matched-state disturbance/recovery completed

Protocol, runner and metrics were committed at ce2dde9 before the three fresh
two-second runs OFF_C, OFF_P, ON_P. ON_C reuses the fully verified archived
matched-pair ENABLED trace. All cells share exact neural/physical history through
500 ms. OFF withdraws tactile from 500.5 ms; P adds the unchanged historical M9B
Thorax pulse [0, 1.024, 0], outgoing transitions 5000..5199. Existing kernel,
encoder, physiology, support, collision and common 2269-slot RNG schedule remain
fixed. All integrity checks passed, including full prefix matching, exact wrench
and sensor attribution. No retries, parameter tuning or weakened acceptance.

Functional outcome is adverse: continued tactile had peak/mean orientation
deviation 12.798550/5.763657 deg versus withdrawn 3.418028/1.340016, each relative
to its own undisturbed control. The prospective label is amplified orientation
response. Both baselines qualified, both pulses resolved and exited recovery
bands, but neither met the fixed 100 ms sustained return within two seconds.
Neither rolled over or crossed the low-height limit. This does not establish
beneficial balance, gait or biological validation. Keep the adverse result.

Full fresh traces and evaluation: `docs/evidence/tactile-recovery-v1/`; prospective
criteria: `docs/TACTILE_DISTURBANCE_RECOVERY_V1.md`; results/manual Git Bash checks:
`docs/TACTILE_DISTURBANCE_RECOVERY_RESULTS.md`. Ordinary live tactile remains off.
`live.tactile_recovery_replay --manifest docs/evidence/tactile-recovery-v1/manifest.json
--condition PUSHED --speed 0.1` streams measured clips with explicit reset and
intervention labels; a clip reset is not a simulated jump. Unity Editor was not
run by the agent. Preserve the known predecessor artifact-hash test failure.

Immediate next task: review recorded pushed and undisturbed conditions, then
separately design/preregister a motor-application control with exact replayed
command provenance and matched state/sampling to distinguish active motor
application from passive mechanics and withdrawal effects. Do not tune neural
parameters, increase the pulse or broaden normal live mode to obtain a pass.

## Latest update — motor-command yoke control completed

Protocol/runner committed at 220899c before two fresh fixed two-second trials Y_C
then Y_P. All tactile/CNS/decoder computation continues, but each outgoing physical
action uses the exact same-transition archived undisturbed ENABLED command.
Y_C exactly reproduced the entire original trajectory/contact/encoder and all
4000 neural records. Y_P uses the unchanged 500..520 ms Thorax pulse. All initial,
pre-push, common RNG, input/readout, contact, applied-command and force checks pass.
Y_P altered 14720 proposed outgoing actions, first at transition 5280 (528.0 ms).

The prospective YOKING_REDUCES_RESPONSE label is supported: peak/mean orientation
deviation was 1.447819/0.453098 deg yoked versus 12.798550/5.763657 closed loop,
each against its own undisturbed control. Peak absolute tilt was nevertheless
higher yoked (9.947980 vs 7.323098 deg). Neither rolled over or crossed the low-
height limit; neither met sustained recovery within two seconds. Baseline active
actuation remains, so this is not a fully passive-body test or proof of balance.
Keep both relative-response and absolute-tilt results visible. No tuning/retries.

Protocol/results: `docs/TACTILE_MOTOR_YOKE_V1.md` and
`docs/TACTILE_MOTOR_YOKE_RESULTS.md`; complete traces/manifest in
`docs/evidence/tactile-motor-yoke-v1/`. Recorded replay:
`live.tactile_motor_yoke_replay --manifest docs/evidence/tactile-motor-yoke-v1/manifest.json
--condition BOTH --speed 0.1`, comparing Y_P and original ON_P. Explicit resets
are not physical jumps. Ordinary live mode remains tactile-disabled.
Validation: 252 tests plus 9 subtests passed, including full saved analysis and
actual recorded-pose TCP checks. Fresh Windows CRLF checkout failures were resolved
by restoring original Git blob bytes and protecting five provenance-sensitive
paths with -text; no scientific content or expected hash changed. The separate
legacy metadata-related artifact failure remains 6 passed / 1 failed. Unity
Editor was not run by the agent.

Immediate next task: separately preregister admitted motor-command dissection
using the existing M11 infrastructure in this exact 20-motor tactile context,
with matched disturbed/undisturbed controls and a channel-selection rule chosen
before outcomes. Track absolute tilt and disturbance-relative response separately.
No neural parameter tuning or channel search until a favorable result appears.
Baseline active commands/passive mechanical support remain unresolved components.

## Latest update — anatomical tibia command-group dissection completed

Protocol/runner/tests committed at 9f58379 before fresh fixed two-second T_C then
T_P trials. All six tibias selected by existing M11 anatomical mapping and exact
v3 indices 5/12/19/26/33/40, not outcome ranking. Only those six applied actions
follow the undisturbed recording; other 36 coordinates (including 14 admitted
motors) exactly retain their contemporaneous native proposals. CNS/tactile/
decoder computation remains active. All integrity checks pass; T_C reproduces
the complete original control trajectory/contact/encoder and all neural records.
Same pulse/seed/window/physiology/metrics; no tuning or retries.

Peak/mean orientation deviation is 9.881202/3.725524 deg tibia-only versus
12.798550/5.763657 full closed-loop and 1.447819/0.453098 all-command-yoked,
each relative to its own undisturbed control. The predeclared primary label is
SELECTIVE_YOKING_REDUCES_RESPONSE. Absolute tilt is nevertheless worse than full
closed loop (9.667409 vs 7.323098 deg), as are peak linear/angular velocity errors.
No rollover or low-height crossing, but no sustained recovery. Not a balance proof.

T_P replaces 14720 outgoing transitions from transition 5280 (528 ms); per-channel
LF/LM/LH/RF/RM/RH exposure counts are 14385/14560/14425/0/14695/14720. Preserve RF
tibia zero command-intervention exposure: it is not proof of silent motor neurons
or an individual causal contribution. Group effects can be non-additive and other
motors can compensate. Existing M11 classification helpers and yoke/kernel reused.

Complete evidence: `docs/evidence/tibia-command-dissection-v1/`; protocol/results
and manual Git Bash review: `docs/TIBIA_COMMAND_DISSECTION_V1.md` and
`docs/TIBIA_COMMAND_DISSECTION_RESULTS.md`. Recorded Unity command:
`live.tibia_command_replay --manifest docs/evidence/tibia-command-dissection-v1/manifest.json
--condition BOTH --speed 0.1`, T_P versus original ON_P; ALL adds T_C and Y_P.
Shared pose-stream helper preserves the earlier replay CLI; clip resets are not
physical jumps. Ordinary live tactile mode remains disabled.
Validation: 275 tests plus 9 subtests passed across the focused matrix and final
new archived-evidence/TCP check. All saved new/upstream source/hash/evaluation
checks replayed; actual recorded T_P/ON_P/Y_P endpoint poses passed local TCP.
The separate legacy tactile-contact suite remains 6 passed / 1 unchanged metadata
hash failure. No Unity Editor run, neural tuning or duplicate scientific trial.

Immediate next task: separately preregister the complementary 14 admitted motor
channels, defined as the fixed inventory minus these six tibias, with matched
disturbed/undisturbed controls and tibias retaining native closed-loop commands.
Complete the group comparison before interpreting interactions or individual
channel contributions. Preserve all tradeoffs/nulls; do not tune neural parameters
or select channels from outcome rankings to obtain a favorable result.

## Latest update — complementary 14-motor command group completed

Protocol/runner/tests committed at 939459a before fresh fixed two-second C_C then
C_P trials. The group is the exact v3 inventory minus the six tibias: six femur,
six femur-roll and LF/RF Tarsus1 channels. Only those 14 commands use archived
undisturbed actions; other 28 coordinates (including all six tibias) exactly retain
native proposals. All CNS/sensory/readout/decoder computation continues. No neural
tuning, force/window/seed/acceptance changes or retries. All integrity checks pass;
C_C exactly reproduces the entire original control trajectory and neural records.

Complementary replay peak/mean orientation deviation is 6.094436/2.337358 deg
versus full closed-loop 12.798550/5.763657, tibia-only 9.881202/3.725524 and all-
command-yoked 1.447819/0.453098, each against its own undisturbed control. Primary
label SELECTIVE_YOKING_REDUCES_RESPONSE. Peak absolute tilt is nevertheless highest
in the complementary replay (14.781105 vs 7.323098 deg closed loop), and peak
linear-velocity error increases to 19.454490 vs 11.501194 model mm/s. No rollover
or low-height crossing, but no sustained recovery. Preserve the mixed tradeoffs.

All four group contexts are now measured. Full closed loop has the lowest peak
absolute tilt and largest orientation departure from its undisturbed trajectory.
This supports a modeled posture-related motor-application effect, not general
balance, gait, intent, individual-channel necessity or fully passive support.
Group comparisons are context-dependent and non-additive; do not infer fractions
explained from differences of peak norms. C_P alters 14720 outgoing actions from
transition 5280 (528 ms). RF Tarsus1 has zero command-intervention exposure; preserve
this and the earlier RF tibia null, without claiming silent neurons.

Full evidence: `docs/evidence/complement-command-dissection-v1/`; prospective
protocol/results and manual Git Bash instructions:
`docs/COMPLEMENT_COMMAND_DISSECTION_V1.md` and
`docs/COMPLEMENT_COMMAND_DISSECTION_RESULTS.md`. Replay:
`live.complement_command_replay --manifest docs/evidence/complement-command-dissection-v1/manifest.json
--condition BOTH --speed 0.1`, C_P versus original ON_P; ALL includes C_C/T_P/Y_P.
Reuse the shared output-only measured-pose loop. Ordinary live tactile stays off.
Validation: 298 tests plus 9 subtests passed across the focused matrix and final
new/upstream archived-evidence/actual-TCP check. Actual saved C_P/T_P/ON_P/Y_P poses
passed local TCP. Separate legacy tactile-contact remains 6 passed / 1 unchanged
metadata-hash failure. Real dry CLI returned NOT_RUN/1; no Unity Editor run.

Immediate next task: separately preregister a saved-evidence time-aligned posture
analysis of the four frozen contexts, distinguishing absolute tilt/world state
from disturbance-relative trajectory error. Declare any root-vector interaction
estimand and fixed windows before computation; do not add peak norms as channel
contributions. No new CNS/physics runs are needed. Use those results to decide
the next motor/sensory roadmap step without parameter tuning or winner searches.

## Latest update — frozen posture analysis and mapping status

Analysis protocol/analyzer/tests committed at e7f808f before computing new timing
and vector interactions. All original outcomes/protocols remain unchanged. Full
frozen source/raw/evaluation chains validated, then eight root traces reduced to
20001 states each. All four unpushed controls match exactly; pre-force histories
and all old response summaries reproduce. Zero new CNS/physics transitions.

Absolute tilt and distance from a moving control explain the mixed results. Full
closed loop has absolute peak tilt 7.323098 deg at 1998.7 ms and relative orientation
peak 12.798550 at 2000 ms, while relative body-up peaks 7.788052 at 774.2 ms. At the
complementary replay's absolute peak 14.781105 deg (777.6 ms), its control is already
tilted 10.512604 deg and full relative error is only 4.288840 deg. Full orientation
includes heading; do not subtract angle metrics to calculate yaw. Last-state
relative maximum leaves behavior beyond the fixed window unknown.

Predeclared signed root-vector interaction (all replay - tibia - complement +
closed loop, each pushed minus own control) peaks 0.263570 model mm at 911.9 ms,
xyz [0.003593,-0.262681,0.021328], exceeding inherited .005 model-mm resolution.
Dimensionless body-up-vector interaction peaks .173875 at 940.8 ms. Group effects
are non-additive and context-dependent, not percentages explained or statistical
significance. No general balance/gait/intent/passive-support proof or recovery.

Evidence/report/plots: `docs/evidence/group-posture-analysis-v1/`; prospective
specification/results: `docs/GROUP_POSTURE_ANALYSIS_V1.md` and
`docs/GROUP_POSTURE_ANALYSIS_RESULTS.md`. `docs/LEG_MAPPING_STATUS.md` answers the
user's mapping question: 20/42 model coordinates admitted (6 tibia, 6 femur, 6
femur roll, 2 front Tarsus1), remaining 18 coxa + 4 middle/hind Tarsus1. Structural
coordinate names are known; motor admission is not percentage biological mapping.
Six tibia proprioceptive/experimental tactile populations remain as before;
ordinary live tactile remains off. No additional interface admitted in this work.

75 focused tests passed; 2 previous archived simulation/TCP tests explicitly
excluded, while full upstream evaluations were recomputed during actual analysis.
New saved numeric-artifact math and all original compressed/raw hashes verified.
Separate legacy tactile-contact remains 6 passed / 1 unchanged metadata hash failure.
Charts visually inspected; no new Unity Editor run, physics, neural tuning or raw
evidence change. User can run `live.group_posture_review --report
docs/evidence/group-posture-analysis-v1/analysis.json` and open posture/interaction
PNGs in VS Code; no further Unity run is needed for this update.

Immediate next task: return to the 42-coordinate motor-admission roadmap. Audit
the existing ordered admission/candidate/reference reports for each remaining 22
coordinates: body-ID/population mapping, completeness/antagonism, mechanical sign
provenance, existing validation and exact missing prerequisites. Identify the next
defensible separate admission protocol from reference evidence, not activity or
effect ranking. Preserve calibrated physiology, all locks/nulls/tradeoffs and the
distinction between structural mapping, validated admission and emergent behavior.

## Latest update — remaining 22 admission coordinates audited

Data-only current-v3 projection confirms 20/42 admitted motors. All remaining
22 rows have exact action/annotation/neuron identity and blocker records in
`docs/evidence/remaining-leg-admission-audit-v1_1/`. Results:
12 Coxa/Coxa_roll shared-axis ambiguities; 6 Coxa_yaw anatomical sign bridges
unresolved; 4 middle/hind Tarsus1 exact target mappings absent. Tarsus2 annotations
are different targets and are not promoted/mirrored. Newly admitted channels = 0.

Initial audit v1 (source commit 0128b86) failed on an incorrect global population-
name uniqueness assumption; its error output is preserved under v1. The separately
documented v1.1 correction committed at 2996dcc before generation validates every
selected alias against identical complete body-ID/dense-index identities and
exhaustive metadata, retaining multi-target ambiguity. No last-wins selection or
pool union. The exact immutable neurons.flyn index was decoded; no brain/physics
runtime or scientific transition was constructed/executed by the auditor.

All six old yaw anterior projections remain zero, classifications unresolved and
coordinate signs null. Existing LF-only local registration has seven covectors
whose transforms reproduce within 1e-12; it explicitly does not establish MaleCNS
coordinate signs/decoder weights or admission. Five LF candidate identities are
checked. Existing three-seed recruitment null decisions remain older 11-motor
context records, not inevitable silence in current tactile/v3 context.

Three old raw freeze checks fail in CRLF representation; canonical LF bytes match
both unchanged expected hashes and original Git blobs. Audit records raw failure
separately (all_original_raw_freezes_satisfied=false), not as a passed prerequisite.
No artifact/hash/verifier is altered; future scientific execution must satisfy
the original raw prerequisites independently. Admission remains blocked regardless.

Relevant matrix: 55 passed / 5 historical failures, all five reproduced on primary
checkout without new code. One assumes NOT_RUN despite frozen COMPLETE, three
call preflight against occupied frozen output, one double-converts CRLF. No old
test/code/artifact changed to hide these failures. All 15 new audit tests pass;
actual v1.1 generation and user review command pass. Zero new admissions/steps.

Read `docs/REMAINING_LEG_ADMISSION_RESULTS.md` and
`docs/LF_PROXIMAL_ADMISSION_PREREQUISITES_V1.md`. Review:
`embodiment.remaining_leg_admission_review --report
docs/evidence/remaining-leg-admission-audit-v1_1/audit.json`; open matrix.md and plan
in VS Code. No Unity run. Include exact Git Bash commands in every final update.

Immediate next task: LF proximal reference-backed population-to-muscle activation/
sign binding and multi-axis mapping prerequisites, using the five exact populations
and seven LF-only local tendon records. Resolve broad promotor multi-tendon hypotheses
without averaging/ranking by outcome. Do not infer a coordinate sign from names,
neurotransmitter alone or geometric dominance. Only after independent reference and
numeric/application gates are specified, create a separate bounded validation
protocol in the current context. Never tune neural parameters to obtain activity,
reinterpret frozen yaw nulls, mirror front tarsi or flip current admission flags.

## Latest update — LF proximal muscle-reference semantics reviewed

Protocol/code/tests committed at aeb4824 before generating
`docs/evidence/lf-proximal-binding-review-v1/review.json`. Static XML inspection
verifies the original local FlyMimic source-model raw hash against the frozen
registration (a72d4a31...). All seven LF tendon actuators have the recorded muscle
activation/gain/bias semantics and unit gear. No XML compilation, mesh loading,
physics/CNS transitions, force application, dependencies or current decoder change.

Reference R=-dL/dq gives tau=T*R for positive tensile magnitude T; the scalar
pulling-force sign must not flip R a second time. Virtual-work/reference algebra
tests pass. This is conditional local generalized torque, not neuron-to-angle
sign, acceleration, decoder gain or biological validation. Current shared kernel
uses position commands; force-to-target transfer remains absent.

Complete existing admission reviewer rechecks five populations/13 neurons and
every alias, seven local covectors and original raw failures/nulls. All three
broad-promotor alternatives remain separate (even roll signs differ). All
per-neuron tendon assignments, spike-to-activation, activation-to-force,
force-to-position transfers, decoder vectors and gains remain unassigned. Four
single-class hypotheses are not independently established specimen crosswalks.
Current admission remains 20/42; no new channel or ordinary tactile mode enabled.

31 focused tests pass (16 new plus 15 existing audit tests). Initial sandbox run
had 26 pass/5 temp-directory setup errors; writable fresh --basetemp resolves the
execution issue without changing code/scientific criteria. Actual generation and
saved-report verification pass; original raw-freeze flags remain false. No new
Unity run. See `LF_PROXIMAL_BINDING_REVIEW_V1.md` for primary sources/access limits
and `LF_PROXIMAL_BINDING_RESULTS.md` for all changed files, tests and Git Bash code.
Review CLI: `embodiment.lf_proximal_binding_review --model
"$HOME/Documents/FlyMimic/flymimic/assets/models/best_combined_cvt3.xml" --report
docs/evidence/lf-proximal-binding-review-v1/review.json`.

Immediate next evidence requirement: independently traceable neuron-to-muscle/
tendon crosswalk, especially the four broad-promotor neurons versus three model
tendons, and an explicit force-interface versus engineered position-target design.
Do not repeat the same audit or infer bindings from labels/order/activity. Without
new independent evidence, report the unresolved blocker rather than enabling
channels. Specify activation/passive dynamics, units, supported pose/range and
transfer validation before a separate numerical/application experiment. Original
raw scientific prerequisites must pass independently; canonical agreement does
not waive them. No numerical bounded admission experiment is ready yet.

## Latest update — independent LF anatomical source crosswalk

New primary reference acquisition, not another replay of the same saved audit.
Official MaleCNS v1.0 raw annotations are separately archived in Git LFS at
`docs/evidence/lf-anatomical-crosswalk-v1/annotations.feather`, raw SHA
2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2,
14483314 bytes / 211577 source rows. Dataset CC-BY attribution recorded. The
existing runtime remains unchanged; this broader source table does not add cells.

Exact source pools reproduce five LF classes / all 13 existing body IDs, types,
side fallback, motor superclass, front-leg subclass, T1 and exit nerves. Full
selected source rows are in crosswalk.json. Twelve recorded mancBodyid matches
are retained as published annotations, not independently revalidated morphology.
Body 1050335829 has null mancBodyid; its mancGroup 21241 is not a substitute ID.
No individual FANC MN number, tendon, sign or gain is assigned to any body ID.

Full author-hosted 46-page Azevedo anatomical appendix was downloaded and relevant
figures/captions visually inspected (PDF pages 15-19), resolving the previous
web-reader size limit. Figure A2 explicitly says each of its four promotor MN
targets is uncertain even within the original two-muscle grouping. FANC is a
different specimen; atlas numbering, names/counts/nerve agreement do not establish
a MaleCNS-to-FANC individual match or a split into FlyMimic's three tendons.
Four other classes have single-class anatomical support, still modeled hypotheses
when transferred to the simulation. No complete individual tendon crosswalk found.

Source research was inspected before the written report; no claim of prospective
physiological experimentation. 45 focused tests pass (14 new / 16 LF reference /
15 audit), including actual full official-byte and upstream identity verification.
Actual generation and saved-review CLI pass. No new CNS/physics/Unity trial,
dependencies, neural tuning or admission; current 20/42 and old raw failures remain.
See `LF_ANATOMICAL_CROSSWALK_V1.md` and `LF_ANATOMICAL_CROSSWALK_RESULTS.md`.
Git Bash: LFS pull new annotations.feather, then run
`embodiment.lf_anatomical_crosswalk --report
docs/evidence/lf-anatomical-crosswalk-v1/crosswalk.json`. Include full copy-paste
commands in every delivery. Local PDF/rendered pages remain untracked in this
update's tmp/pdfs; source URL, hash and locators recorded in tracked reports.

Immediate next engineering scope: separately specify an LF muscle-force reference
adapter and isolated force-projection/isolation validation using four explicit
class-to-muscle hypotheses, keeping broad promotors unassigned and production
20-motor behavior intact. Do not repeat the same audit to force a promotor split.
Reuse existing observer/registration, distinguish torque from position targets,
and prevent double actuation. Specify force units, activation/passive dynamics,
supported reference pose/range and numerical/application gates before scientific
coupling. Synthetic known-tension fixtures establish software/reference mechanics,
not biological gain or neural recruitment. No production admission or bounded CNS
experiment until original raw and remaining scientific prerequisites independently
pass. Preserve all historical nulls and never tune to get activity.

## Latest update — isolated LF force-reference adapter validated

Initial protocol/fixture/adapter/tests committed at 8228e84 before archived v1.
Four explicit single-class tendon hypotheses project known nonnegative tensions
through frozen R_G; no broad promotor, per-neuron tendon assignment, neural gain or
activation law. Synthetic fixture has free root + sentinel hinge + three LF-named
reference hinges; DOFs 7/8/9, qpos 8/9/10, not logical action indices 2/0/1.
Require exact reference pose/time, zero actuators/passive/contact forces, and exact
force ownership. Apply/clear reject pose/velocity/foreign force/double application.
No production runner or position actuator behavior changed; current 20/42.

V1 array checks passed but strict review-boundary test exposed inherited side
effect: audit.build -> corrected _protocol -> old._inventory ->
enumerate_live_actuators constructs FlyGym and calls mj_forward during model init.
Its calls were outside the fixture counter. V1 operation/construction-free-review
provenance is rejected and raw evidence preserved, with context-audit-v1_1.json.
No CNS/integration transitions identified. Older audit/crosswalk implementations
remain untouched; their inventory calls can construct a native model despite
earlier data-only phrasing. Do not infer zero construction from zero transitions.

V1.1 correction committed at 276c4f1 before justified fixed repeat. New local
static loader reuses original snapshot/frozen_record/codec/inspect_lf/row_record/
crosswalk validators plus locked build_live_protocol and pure v2/v3 metadata
derivations; no live enumeration or fabricated physical records. All exact LF
records/aliases/nulls/covectors and 22 remaining rows reproduce. This is static
admission verification, not newly compiled current-fly physical validation.

Six native fixture conditions all pass. Across preflight/execution, Python API
instrumentation observes exactly 18 mj_forward and 0 mj_step calls; compiler-
internal calculations are not counted as API calls. No integration or CNS.
Complete matrices/accelerations/poses/forces preserved in
`docs/evidence/lf-force-reference-v1_1/validation.json`. Max projection error
8.674e-18, dynamics residual 7.807e-17, virtual-work error 4.337e-19 under declared
1e-12/1e-10 implementation tolerances. Old raw prerequisites remain false.

74 focused tests pass (29 new, 45 previous). Discovery matrix was 71 pass/1 strict
boundary failure; corrected path keeps that test and also forbids enumeration and
integration. Exact saved-review command passed in Windows Git Bash. No dependency
changes, Unity Editor or neural/fly behavioral experiment. Saved review is now
verified without dynamics. See LF_FORCE_REFERENCE_V1.md, V1_1.md and RESULTS.md.
Git Bash after pull/LFS: `embodiment.lf_force_reference_validation --report
docs/evidence/lf-force-reference-v1_1/validation.json`. Include full copy-paste
commands every delivery. V1 remains preserved and is rejected by v1.1 review.

Immediate next scope: separately specify pose-dependent mechanical transfer and
activation/passive tension/units, plus selective actuator replacement preventing
double actuation in a moving fly. Current adapter deliberately supports only the
exact synthetic reference pose and nu=0, not production attachment. No arbitrary
finite-angle reuse, peak-force/gain transfer or new admission from fixture success.
Original raw and remaining biological/application prerequisites must independently
pass before bounded neural coupling. Preserve broad-promotor uncertainty and
historical nulls. Do not tune neural parameters or gains to produce activity.

## Latest update — pose-dependent rotation/source-force reference

Protocol/code/XML+71-asset locks committed at 51a22f3 before v1. Original source
XML hash unchanged, assets 13961614 bytes. Validated MuJoCo3.2.7 reused without
environment/source changes. Four class hypotheses only; broad promotors unassigned.
New declared map Q_G=Q_M(q)*Q_M(qref)^T, target intrinsic XYZ. J=inverse(B_G)*B_M,
R_G=inverse(J)^T*R_M. This is a modeled rotational correspondence, NOT anatomical
finite-angle registration to actual FlyGym, attachment/mass or translation matching.

Fixed 15 source poses: center, +/- .05 on each axis, 8 corners. Activation0/.5/1,
six +/-1e-6 derivative probes per pose, two central activation derivatives. Exactly
137 explicit mj_forward calls; observed mj_step0, no integrated observation/CNS.
Compiler-internal model validation is not counted as explicit API calls. Preserve
all nonselected/passive source forces. No production actuator replacement or gain.

V1 completed but failed moment/total-force checks: raw actuator_moment is sparse,
despite a misleading dense-sized allocation. Rotation and muscle-function checks
passed; archived length differences independently matched frozen R_M2.765e-11.
Preserve failed v1 raw in LFS. Sparse-decoding correction committed at 7b9bbad
before justified v1.1 repeat. Native mju_sparse2dense plus archived raw CSR metadata;
saved review independently reconstructs with SciPy CSR. Same poses/epsilon/criteria.

V1.1 all checks pass: maximum tendon FD error1.889e-10, axes8.922e-11,
JacobianFD2.221e-10, native force reconstruction1.777e-15, work5.552e-17.
Central frozen J/R reproduce1e-10. J changes up to .02433096925 over sampled poses;
four R_G column component changes max .006291/.002568/.003326/.003562, descriptive
only, not a continuous-pose envelope or new gains. Total99 tests pass (25 new+74
prior); saved Git Bash review5.10s, strict no model construction/dynamics. Old
raw prerequisites false; current20/42, new admissions0. No Unity/neural experiment.

Central zero-activation source anterior-rotator tension11.60235359 native units
is passive; full activation total18.45632371. Others central passive0. Native
selected control floor.0001 means rawctrl0 at activation0 has derivative+2/s.
At activation.5 ctrl0/1 gives -1562.1875/+4000/s. Source tau_act/deact .0001/.0004s
before state factors are model choices, not measured MaleCNS physiology. No
activation transient/integration stability or biological force units established.

Evidence: `docs/evidence/lf-pose-force-v1/input-manifest.json`, failed
`lf-pose-force-v1/run/validation.json`, accepted `lf-pose-force-v1_1/run/validation.json`.
Both native records in LFS. Specs LF_POSE_FORCE_V1.md/V1_1.md; full outcomes and
manual commands LF_POSE_FORCE_RESULTS.md. Review `embodiment.lf_pose_force --report
docs/evidence/lf-pose-force-v1_1/run/validation.json`, without dynamics or external
meshes. LFS pull both pose records + existing annotations.feather. Always include
copy-paste Git Bash block in delivery; no Unity run for saved review.

Immediate next scope: separately specify bounded source activation-transient/
integration validation and zero-input/passive-preload baseline semantics. Establish
force/mass/length units and physical registration before current-body application.
Do not blindly copy source peak forces/time constants or existing 17Hz rate scale
as physiology. Future matched arms must retain identical passive/preload context.
Selective removal of exact3coxa position actuators must precede torques while
other39controls stay intact; do not globally disable20motors or double actuate.
No moving-fly neural coupling/admission until independent raw and numeric/application
gates pass; preserve broad-promotor ambiguity/nulls and never tune for movement.

## Latest update — source activation transients reveal numerical limits

Protocol/source binding/generated zero-DOF native fixture committed at9b95220
before one nine-condition campaign. Native muscle defaults/params/control limits
copied unchanged from exact source XML; fixed lengths equal prior central source
records, all activation0/.5/1 force values reproduce. Fixture nq=nv0,nu=na4;
no joint/body movement or CNS. Source-law surrogate only, not force-unit transfer.

Predeclared100/50/25us Euler grids,10ms duration, three conditions per grid:
RELAX_ZERO a0=0/rawctrl0; FLOOR_BASELINE a0=.0001/rawctrl0; PULSE same floor state
with rawctrl1 outgoing[2ms,5ms), zero otherwise. Control floor/passive bias retained.
Independent DOP853 reference uses native mju_muscleDynamics, tight declared
tolerances/maxstep2.5us, split at exact control boundaries; one fine reference per
condition reused for native grids. No new physiology or neural conversion law.

All implementation integrity checks pass:2100 explicit mj_step calls advance
activation/time only;2112 explicit mj_forward refreshes, zero CNS/body-joint
transitions. Compiler-internal validation excluded from API counts. During-step
force belongs to preintegration activation; refreshed force to updated activation.
Native Euler update, source forces, fixed contexts, source hashes and exact matched
baseline/pulse prefix through2ms all pass. Stationary baseline activation=.0001.

NUMERICAL_LIMITS_OBSERVED: all three PULSE cases FAIL predeclared full-window
activation error<=.01/bounds criterion. Maximum errors100/50/25us are
1.380663692/.559500792/.209847371.100us maxactivation1.999300240 (no configured
activation clamps);50/25us bounded but still inaccurate. Endpoint errors only
.000232091/.000125484/.0000653802 do not rescue full-window failures. Six zero-
input/baseline cases pass numerically. No grid chosen, no retry, no clamp/time-
constant/gain/threshold/window change. Both numerical failures and integrity
success are explicit; evidence review success is NOT timestep numerical acceptance.

Complete LFS record: docs/evidence/lf-activation-transient-v1/run/validation.json,
3799210bytes,SHA539c26fb35d15824d970b482d36af579186e2ed4fe1bf707c03c4e592a90e5fc.
115tests pass (16new+99prior), including actual native timing and strict no-native/
reference-integration review. Exact Windows Git Bash saved review5.60s. Full-window
plots generated by tools/plot_lf_activation_transient.py and visually inspected;
no overshoot clipped. No dependencies, Unity/neural experiment or production change.
Current20/42, newlyadmitted0, old raw prerequisites remain false.

Read LF_ACTIVATION_TRANSIENT_V1.md and RESULTS.md. Git Bash review module
embodiment.lf_activation_transient --report docs/evidence/lf-activation-transient-v1/run/validation.json
prints TRANSIENT EVIDENCE VERIFIED, NUMERICAL_LIMITS_OBSERVED and3PULSE FAIL lines
as expected findings. Pull new record and previous pose records/annotations via
LFS. Review performs no native or reference integration. Include full copy-paste
commands after each update and explain expected FAIL findings; no Unity run yet.

Immediate next scope: separately specify/validate a reference-faithful activation
state integrator with explicit ownership and force timing, keeping the same native
law/time constants/control floor/passive preload and all failed Euler baselines.
Do not add clamps or tune source/neural parameters/timesteps for a pass. Integration
fidelity is not biological calibration or movement evidence. Force units/physical
registration, exact selective actuator replacement, original raw prerequisites,
individual binding and neural conversion remain gates before moving-fly coupling.

## Latest update — source-law activation integrator validated at fixed lengths

Prospective protocol/solver/assay/tests committed at e1dadc7 before one nine-case
campaign, fresh baseline a5b8cdd. Same 100/50/25us external intervals and 10ms full
window, controls/initial states/passive preload/fixture/source parameters as the
old transient campaign. Radau rtol1e-9/atol1e-12, max_step=external interval; native
mju_muscleDynamics unchanged. No clamp, tuned time constants, grid search or retry.

All nine cases pass integrity and numerical acceptance: ALL_NUMERICALLY_ACCEPTED.
Full-window pulse errors 1.76429649e-10/1.24318000e-10/1.82032167e-12; all floor
baselines stationary, matched pulse prefix through2ms exact. Every case compared
at all401 archived25us reference timestamps plus macro states, with bounds also
checked on internal accepted Radau nodes. Criteria unchanged error<=.01 and bounds
[-1e-12,1+1e-12]. Not a continuous-time error theorem or biological calibration.

Reused exact prior DOP853 archive/hash, verified all coarse reference slices and
old numerical decisions. Old Euler PULSE failures stay FAIL; no historical record
modified. Pure interval solver returns copied state; zero-DOF adapter commits state
and time once, with native forward before/after for correctly aligned force and
derivative. 2100 interval solves/commits,4212 explicit mj_forward,0mj_step,CNS or
body/joint transitions. Strict zero-DOF/exact identity/address checks prevent use
as an unspecified moving-body split integrator; no production hook.

New LFS evidence docs/evidence/lf-activation-integrator-v1/run/validation.json,
7841130bytes,SHA256 cd545ca6863b2d2468da067b258d9aac0ecb7f3ab8a953f15c0d6574f62eb49b.
All accepted internal nodes, dense samples and solver costs retained. Existing
plotting tool optionally overlays new Radau results and all prior Euler failures;
comparison.png visually inspected. Read LF_ACTIVATION_INTEGRATOR_V1.md and
LF_ACTIVATION_INTEGRATOR_RESULTS.md for exact conditions and limitations.

139 implementation/reference tests passed in55.65s (24new+115prior). Includes
actual native single-interval ownership/timing checks, analytic mocked linear
solver plumbing separately, corruption/output protection and strictly model/native/
solver-free static review. Development scratch-parent setup error fixed before
campaign; full result passed. Exact Git Bash saved review5.61s, no new integration.
No dependencies, neuron/gain/production changes, Unity run or new motor admission.
Current20/42; original raw scientific prerequisites remain false.

Immediate next update: DESIGN AND STATIC AUDIT of selective LF actuator replacement
and activation/body state ownership, using exact coordinate/actuator/activation IDs,
identifying existing position controls to replace and controls to preserve. Prevent
double actuation and double integration. Keep disconnected from production. Specify
required physical-unit/geometry registration, old raw prerequisites, individual
tendon-binding and neural-conversion gates before moving-fly coupling; do not claim
those gates passed from this source-law numerical result. No Unity run yet.

Every run/final update must include a roadmap checkpoint. Admission20/42 is a
coordinate inventory, not overall project completion. Previous causal tactile/
disturbance/yoke observations remain bounded evidence, not established gait or
independent balance. Continue toward richer supported motor/sensory interfaces,
then causal balance/locomotion tests without scripted behavior substitution.

Git Bash review module: malecns_backend.embodiment.lf_activation_integrator_validation
--report docs/evidence/lf-activation-integrator-v1/run/validation.json. Pull the new
record and prior transient/pose records plus original annotations through LFS.
Expected INTEGRATOR EVIDENCE VERIFIED: ALL_NUMERICALLY_ACCEPTED and9PASS lines;
production20/42,0newadmissions, oldrawFalse. No repeat or Unity run needed.

## Latest update — selective LF actuation/state-ownership design audited

Protocol/audit/tests committed a96a469 before generating a separate static record,
fresh baseline5a3c8c4. STATIC_CONTRACT_VERIFIED_COUPLING_BLOCKED, NOT coupling or
new admission. No native model construction, forward/integration, numerical solver,
CNS or model/state mutation in the audit. Old evidence/source locks unchanged.

Exact historical M5A target basis yaw/pitch/roll uses action2/0/1, actuator2/0/1,
joint1/2/3, qpos7/8/9 and DOFs6/7/8; NOT synthetic fixture DOFs7/8/9. All39 other
joint controls preserved in the design:20admitted+19baseline position controls.
Unadmitted coordinates still have physical position-control springs. A separate
later signature has48actuator names including six adhesion controls at recorded
name IDs42..47, na0. Its full array values are unavailable; M5A body IDs/activation
addresses also missing. Nulls stay null, snapshots not asserted equivalent or
current. Four source fixture activation addresses0..3 are separately scoped, never
FlyGym data.act addresses or individual neuron-tendon assignments.

Design proposes neutralizing only selected full gain/bias rows AFTER a current
native identity and fixed-gain/affine-bias check; preserve other45actuator rows,
ordering, sensors, passive mechanics and controls. No actual gain change here.
ctrl0 alone cannot remove spring bias; no global group disable or removal/reindex.
Future matched arms must share the explicit replacement context. External source
activation vector owns its own integration; native body path owns qpos/qvel/time
exclusively. Proposed left-endpoint total tension held per body interval is a
first-order coupling DESIGN, not validated by fixed-length Radau results. Commit
external state once after successful body advancement, clear only owned force,
preserve foreign forces outside targets, reject duplicate owners/competing target
forces. Stop/retain state on failure without rollback or retry claims.

New record docs/evidence/lf-actuation-contract-v1/audit.json:77299 canonical LF
bytes, canonical SHA256385c57724f1ec3a937ad35bd86cfe76d4cb004b92d7aa52335d010c83bd81fc4.
Ordinary Git text, not LFS or a raw-lock waiver. Includes all42rows, target/retained
partition, source states, separate snapshot scopes, proposed plan, six explicit
blockers and source hashes before/after. Read LF_ACTUATION_CONTRACT_V1.md and
LF_ACTUATION_CONTRACT_RESULTS.md.

165tests passed in81.58s (26new+139prior); predecessor native fixture implementation
tests included, no new moving-fly/CNS experiment.24development checks passed with
2saved-review tests deselected. New audit/review tests forbid model/forward/step,
live enumeration, native muscle derivative, numerical solvers and CNS initialization.
Exact Windows Git Bash saved review passed; no physics or integration. No dependency,
Unity/production/neural changes. Current20/42,0newadmissions; oldrawflagFalse.

Immediate next bounded update: separately specify CURRENT native inventory capture
and selective-neutralization/preservation audit with NO integration. Declare exact
initializer/reset/forward accounting and fixed q/qvel/control probes before outcomes.
Record complete native names/IDs/body/qpos/DOF/activation/transmission/force support,
gain/bias/control/sensor/state identities. Test the isolated proposed three-row
neutralization against original baseline, verify zero selected actuation across
all declared probes and exact preservation elsewhere. Do not use historical IDs
without native re-resolution, suppress all controls or apply muscle forces yet.
Preserve partial/failing records, no retries or automatic hash refresh.

Passing that engineering isolation audit would still not waive coupled numerical
accuracy, physical units/geometry/velocity transfer, original raw prerequisites,
individual tendon binding or neural conversion. Remain disconnected from production
pending those gates. No Unity run needed yet. Continue roadmap updates after EVERY
run, including what the result cannot establish,20/42 and the next concrete task.

Git Bash review module malecns_backend.embodiment.lf_actuation_contract --report
docs/evidence/lf-actuation-contract-v1/audit.json. Pull prior annotations, pose,
transient and integrator LFS records. Expect STATIC CONTRACT VERIFIED; coupling
BLOCKED plus target table/partition and roadmap. BLOCKED is the intended readiness
result, not a broken review command. No new native run required for this review.

## Latest update — native LF position-actuator isolation verified

Fresh baselinea50ef0b. V1 prospective protocol/manifest/runner/tests committed
b4efd68 before first native campaign. Reused exact _make_live(flygym,{}) from
tactile_motor_loop_audit: position fly, disabled adhesion, existing contact arena,
reset/surface placement. No new initializer/controller or simulation step.

V1 reached27observations/restored model identity but strict JSON writing failed on
unbounded native limit -inf. Original partial export preserved unchanged in LFS:
docs/evidence/lf-native-isolation-v1/run/validation.json,2353546bytes,
SHA d6219a063538b270517ce0f9a9b86ea0bb7a3a135cc37ce93755323f9f9f0e54.
Its counters/evaluation were not serialized, so V1 is scientifically inconclusive/
SERIALIZATION_FAILED. No repaired history or inferred missing counts. Separately
specified V1.1 correction committed14d3f04 BEFORE second bounded campaign: lossless
native_nonfinite tags for inf/nan metadata, decoded before numeric/hash checks.
No probes/physics/acceptance/tolerance/neural change; nonfinite physical outputs
still fail. No third campaign. Read LF_NATIVE_ISOLATION_V1.md and V1_1.md.

V1.1 NATIVE_ISOLATION_VERIFIED_COUPLING_BLOCKED.9fixed inputs*3arms BASELINE,
CTRL_ZERO_ONLY,NEUTRALIZED. Center,+/-.05rad yaw/pitch/roll, two declared velocity
patterns; all42 position controls follow declared probe qpos+/-.01rad offsets;
adhesion0.34explicit mj_forward (7initializer+27probes),3mj_resetData;0native
step/step1/step2/Euler/RK/implicit/CNS transitions. Compiler internal native work
outside Python counters. Fresh MjData per probe, state/time unchanged by forward.

Current native capture nq94/nv93/nu48/na0/nbody72/nsensor175. Exact body13=0/LFCoxa.
Basis yaw/pitch/roll: action/actuator2/0/1,joint1/2/3,qpos7/8/9,DOF6/7/8;
actadr-1/actnum0. Full48actuator/joint/body/activation/control/sensor tables and
force support captured, matched against reused full model/option/name identities.
Uses existing DOF/name observer and validated CSR moment conversion/saved checker.
Package manifest pins196scientific source/asset/native files,62482705bytes, prior
to outcomes. MuJoCo3.2.7/FlyGym1.2.1/dm_control1.0.27/NumPy2.0.2/SciPy1.18.1;
no environment/dependency change.

Only three selected full gain/bias rows zeroed in isolated native model; all45other
rows/model fields unchanged, exact model identity restored. Every probe: selected
force and target total qfrc_actuator exactly0;45retained forces exactbaseline,
outside-target generalized difference0, passive force and complete momentmatrix
exactbaseline. Selected baseline forces approx+.45/+.45/-.45 (yaw/pitch/roll),
so suppression nonvacuous. ctrl0-only pitch atcenter=-14.92256510nativeunits;
control0 is not spring removal. This is mechanical engineering evidence, not
biological force calibration or independent balance; qacc/constraint/sensor
outputs may differ while body state/time is not advanced.

Complete V1.1 LFS record docs/evidence/lf-native-isolation-v1_1/run/validation.json,
2455324bytes,SHA ee3ddfe2e9d298d3b3f269ab04c114d7f3a332ebc68ea20c184deb7b1df2a628.
188tests passed103.57s (23new+165prior).12development checks passed/10deselected;
after V1failure, one encoding test passed/22deselected beforeV1.1. New saved-review/
preflight tests forbid model/data/reset/forward/integration/FlyGym/CNS/solver work.
Exact Windows Git Bash saved review passed. No Unity run, muscle-force application,
neural/gain tuning for activity, source physiology or production changes.20/42,
0newadmissions; raw scientific prerequisites remain false. See RESULTS.md.

Immediate next gate: separately specify a SYNTHETIC coupled-state/force-buffer
ownership and numerical convergence experiment for the proposed left-endpoint
split scheme. Reuse existing source ODE/Radau/projection conventions, but do not
reuse the zero-DOF adapter on a moving body. Declare synthetic units and mechanics,
independent reference, entire window/grid/criteria and operation counts before
outcomes. Test single external activation/body time ownership, owned force clearing
and foreign-force preservation, no double actuation/integration. Keep failed grids
and distinguish solver error from model mismatch. No production/FlyGym muscle
coupling or force-unit assumptions yet. Physical/geometry/velocity transfer,
original raw prerequisites, individual binding and neural conversion remain gates.

Continue roadmap update after EVERY run: current20/42 is motor-coordinate coverage,
not project-completion percentage. Native isolation is complete only at declared
instantaneous probes. Coupled numerics and physical/neural validity precede moving-
fly muscle experiments; causal balance/walking tests remain later. No Unity run yet.

Git Bash review: malecns_backend.embodiment.lf_native_isolation --report
docs/evidence/lf-native-isolation-v1_1/run/validation.json. Pull both native-isolation
V1/V1.1 records via docs/evidence/lf-native-isolation-v1*/run/validation.json plus
prior annotations/pose/transient/integrator LFS dependencies. Expect NATIVE ISOLATION
EVIDENCE VERIFIED, COUPLING_BLOCKED,34forwards/3resets/0integration,20/42,oldrawFalse.
Original V1 malformed JSON stays preserved as failure, never use it for review.

## Latest update — synthetic coupling numerical checks pass; integrity failure retained

Prospective protocol/fixture/runner/tests committed a0a5013 before ONE nine-case
campaign, fresh baselinec665480. Four independent zero-actuator/activation/contact
rotors with inertias[1,2,3,4], synthetic dimensionless units. Existing source native
activation law/Radau solver and R_G projection reused; frozen source gain/bias and
coefficients explicitly reinterpreted in synthetic units, not a moving muscle or
source/FlyGym physical registration. Independent DOP853 integrates SAME analytic
rotor/activation equations. Full10ms,100/50/25us,RELAX_ZERO/FLOOR_BASELINE/PULSE.

Actual3models,2100synthetic body mj_step,2112explicit forward,0reset or explicit
step1/step2/Euler/RK/implicit outside native mj_step internals,0CNS/FlyGym run.
Exact foreign sentinel generalized force.125/body z-torque.25 preserved after
owned target-force clearing. Native q/v/time solely advanced by mj_step; external
activation committed once from stored solver terminal state. All ownership,
native semi-implicit algebra/time/source/mass checks pass; matched prefix exact
through2ms. Failure tests before/after native step retain uncertain state, latch
failed, prohibit retry and do not claim rollback/external activation commit.

Original campaign verdict **INTEGRITY_FAILURE** remains unchanged. All9 numerical
budgets pass (q<=1e-5,v<=1e-3,a<=.01/bounds); both predeclared pulse refinement
ratios pass. PULSE qerrors100/50/25us=1.875e-7/9.48254e-8/5.30977e-8;
verrors=1.32577981e-4/6.12092629e-5/2.89579314e-5. E=.132577981/.061209263/
.028957931. No production timestep selected or physical-transfer claim.

Failure is V1's extra bitwise dense-endpoint versus solver terminal-state guard:
1/2/11nonidentical PULSE endpoints, max differences4.33680869e-19/1.38777878e-17/
1.11022302e-16. All committed activations are EXACT solver terminal/internal
endpoint values. Source inspection of installed SciPy1.18.1 Radau shows separate
y_new=y+Z[-1] and Q=Z.T@P dense polynomial computation; API describes cubic dense
output. The bitwise assumption was in our new audit. No epsilon/threshold/guard
change after outcomes, no experiment retry or reclassification. Read-only diagnosis
does not rescue scientific integrity. The original runner/evaluator stays unchanged.

Original LFS docs/evidence/lf-synthetic-coupling-v1/run/validation.json,
25551077bytes,SHA12805789411e5b7b2aa9dbaea0f4e18e5075671a9945501970d9e952f99d822e.
Separate lf_synthetic_coupling_review module checks exact raw hash, source locks,
reproduces original evaluation and reports diagnostics without models/solvers/CNS.
failure-review.json is descriptive postmortem, acceptance_changedFalse and
campaign_repeatedFalse. Installed radau.py SHA232f08010ccaa736e16ca34afc888c69365352df58fffbf7aecba6f863a456c6.
Original runner --report rejects integrity failure; use the separate failure review
to verify this negative record, not --execute or a rerun. Exact Git Bash review
passed, printing original INTEGRITY_FAILURE and three PULSE solver guard FAILs.

Development14tests passed/11deselected28.20s before campaign. Postmortem adds
negative-result review/diagnostic tests.9focused corruption checks passed/18
deselected3.28s after strengthening them to require a NEW evaluation difference
for each corruption, rather than inherit the existing failed verdict. Full matrix
result:215passed154.89s (27new+188prior); this does not reclassify scientific failure.
No production/neural/source-physiology or
dependency change, Unity run or new admission.20/42,raw prerequisitesFalse.

Immediate next task: independently SPECIFY/TEST SOLVER ENDPOINT OWNERSHIP/API
SEMANTICS before any new acceptance protocol. Use SciPy/source evidence and
analytic/constructed unit tests, not a tolerance fitted to these14 residues.
Distinguish authoritative terminal state from separately evaluated interpolation;
retain exact commit identity and all original failed data. A correction must be
separately versioned before new outcomes. Do not silently remove the failed guard,
label this campaign accepted, repeat until pass or advance to physical force
transfer. No moving FlyGym/production muscle coupling. Biological units/geometry/
velocity/length, original raw prerequisites, individual binding and neural
conversion remain later gates; balance/walking still require causal evidence.

Git Bash: malecns_backend.embodiment.lf_synthetic_coupling_review --report
docs/evidence/lf-synthetic-coupling-v1/run/validation.json. Pull new record plus
native-isolation V1/V1.1 and prior pose/transient/integrator/annotation LFS inputs.
Expect SYNTHETIC RECORD VERIFIED: INTEGRITY_FAILURE (experiment NOT accepted),
all9 numericalPASS,3PULSE solver-guardFAIL,20/42/0new and next endpoint-contract
task. Successful static review is not scientific acceptance. No Unity run yet.

## Latest update — endpoint state/interpolation contract independently verified

User asked how far to next Unity test, whether moving toward independent balance,
and the current milestone. See new UNITY_AND_BALANCE_ROADMAP.md. Milestone is a
trustworthy LF proximal muscle-force interface, not established neural balance.
Current20/42; stable appearance includes engineered position-control assistance.
A new meaningful Unity muscle-interface run requires corrected coupled validation,
supported physical/anatomical/neural transfer and raw prerequisites, then bounded
headless evidence. Several engineering/research gates; no reliable calendar/PR
count. Keep providing roadmap updates after every run and copy-paste Git Bash.

Fresh baseline5d92fc5. Contract/wrapper/manifest/tests committed93e7eb8 BEFORE one
fixed implementation/reference check. New lf_activation_endpoint wrapper delegates
once to the UNCHANGED existing integrator/native derivative/solver settings. It
returns exact supplied initial at offset==0, exact authoritative stored solver
terminal at offset==duration, untouched dense values for all interiors including
nextafter(duration,0). Every original dense value retained in interpolated_samples,
with explicit sample_kinds. Deep copied, no state commit/body time write, no epsilon/
np.isclose/snap/clamp/gain/ODE/tolerance change. Historical callers not connected.

Independent constructed return-object counterexample has deliberately large
boundary differences/distinct interiors; NOT an ODE or physics simulation and not
derived from the old14 residues. Two actual Radau solves use analytic LINEAR MOCK
law with fixed taus/initial/controls/durations .0001/.001s and allsample error<=1e-8.
Observed maxerrors1.97091510e-11/6.87648827e-11; terminalerrors1.07691633e-14/
1.40554235e-13. Allpolicy/reference checks pass. SciPy1.18.1/NumPy2.0.2 plus
radau.py/ivp.py raw identities pinned before check. No native muscle/model/step,
CNS, FlyGym force application, Unity or dependency change in the check.

Classification ENDPOINT_CONTRACT_VERIFIED_COUPLING_NOT_REVALIDATED. Historical
synthetic V1 rawhash and original integrator/protocol/evaluator verified unchanged;
V1 stays INTEGRITY_FAILURE. No coupled experiment repeat or acceptance change.
Do not treat endpoint API verification as physical/neural/biological validation.

New ordinary-Git docs/evidence/lf-endpoint-contract-v1/run/contract.json,
24186canonical LF bytes,SHA1f79cb1435fbc149c3691d800f6106bc985fbb53de5e6a672f349306ce72908d.
Development14passes/1malformed-test failure/7deselected: constructed terminal lists
aliased, so a test mutation changed both after/internalterminal consistently. Fixed
independent test buffers before reference check, no policy/solver change; then
15passed/7deselected. Final focused regression73passed55.63s (22new+24integrator+
27synthetic). Exact Git Bash static review.89s. Existing native fixture tests are
separate from the new two linear-mock checks; no new native/CNS campaign. Tests
reject invalid authority/nonfinite/status/time/shape, verify copy/no-snap/single
delegation, analytic solution, exclusive failure output and static saved review.

Immediate next task: separately SPECIFY a corrected synthetic coupling implementation/
protocol using explicit endpoint roles, exact authoritative terminal commit and
retained dense diagnostics. Reuse existing model/reference/projection/ownership
mechanics where possible, preserve all physical numerical budgets/window/grids
and historical failedV1. Commit before any NEW outcomes, no old guard removal or
retroactive passing classification. The endpoint wrapper is not wired into the
old synthetic runner or production. Physical force units/geometry/velocity/length,
original raw prerequisites, individual binding and neural conversion remain later
gates before moving-FlyGym muscle coupling. Balance/walking still need causal tests
with explicitly declared mechanical assistance; neural contribution != independent
balance.20/42 coordinate coverage is not project-completion percentage.

Git Bash review malecns_backend.embodiment.lf_activation_endpoint --report
docs/evidence/lf-endpoint-contract-v1/run/contract.json. Only LFS dependency is old
synthetic-coupling-v1/run/validation.json for exact historical failure provenance;
other new records are ordinary Git text. Expected ENDPOINT CONTRACT VERIFIED,
coupling NOT revalidated, historical INTEGRITY_FAILURE,20/42/0new, and next task.
No solver/native/CNS execution in saved review. Read RESULTS and new UNITY roadmap.

## Latest update — synthetic coupling V2 accepted; physical transfer remains blocked

Fresh7c8d358 baseline. V2protocol/adapter/runner/tests committedc15e80c before ONE
new nine-case campaign. Inherits V1constructor/guard/metadata/apply/clear/failure
latch and uses independently verified endpoint API. No module-global integrator
replacement. Exact endpoint sample/after/internal terminal/committed state agree;
EVERY raw dense sample retained separately with content hash. Original V1source,
protocol/evaluator and raw record untouched; V1 stays INTEGRITY_FAILURE.

Same synthetic rotors/inertias/source law/Radau/projection/foreign forces/grids/
whole10ms/threeconditions/DOP853 as V1. V2 requires its own schema and reuses ALL
V1non-schema physical/source/state/force/solver/numerical/refinement check results,
plus exact endpoint role/source/raw-data checks. No old guard removal or epsilon/
tolerance/window/force/gain/neural/seed change. V1schema check still rejects a V2
record, while V2 explicitly validates its namespace before composing acceptance.

SYNTHETIC_COUPLING_V2_VERIFIED_TRANSFER_BLOCKED:all9cases pass, bothpulse refinement
pass. Pulse qerrors100/50/25us1.875e-7/9.48254397e-8/5.30977412e-8;
verrors1.32577981e-4/6.12092629e-5/2.89579314e-5;E.132577981/.061209263/.028957931.
Budgets unchangedq1e-5/v1e-3/a.01/bounds and E_fine<=.75E_coarse+1e-12. No
production timestep selected. Still1/2/11raw dense mismatches atpulse grids with
max4.3368e-19/1.3878e-17/1.1102e-16; preserved, not committed or thresholded away.
Read-only saved comparison:ALL2100physical/activation/control/force/time/commit/
phase transitions and continuous reference records are EXACTLY identical V1/V2.
This corrects data semantics, not dynamics. Native/CNS production unchanged.

Actual3models/2100synthetic body mj_step/2112explicitforward/0reset or explicit
step1/step2/Euler/RK/implicit outside native step internals/0CNS-FlyGym run. Foreign
sentinel generalized.125/body torque.25 remain exact after clearing only owned
forces. Source/mass/nativeEuler/time/state/prefixchecks pass. New LFS
docs/evidence/lf-synthetic-coupling-v2/run/validation.json,26710381bytes,
SHA49e7443266c0b2a40129cf2600a99a468f3242764afa1a94e48ce55e72a1d891.
Endpointcontract canonical1f79cb... and failedV1raw128057... are preflight locks.

89tests passed81.68s (16V2+27V1synthetic+22endpoint+24integrator). Before campaign,
firstdev1fail/1pass/4setup errors: sparse checkout had an LFS pointer for required
historical184MB integrated_whole_leg_readiness.json, so existing M6C rawlock failed.
Hydrated original from sharedcache without hash/code waiver; then6passed/10deselected
18.75s. No native campaign had run at setup failure. Initial full worktree also
hit diskfull copying duplicated Unity assets; Git removed failed checkout. Known
clean delivered endpointworktree converted to sparse omitting duplicateUnity
workingcopies; all Git/LFS history and non-Unity science code/evidence retained,
primarycheckout/useredits untouched. New V2checkout is sparse too. Exact Git Bash
saved V2review passed with no native/solver/CNS calls; whitespace/LFS checks pass.
No dependencies, Unity behavior, production physiology/neuronal parameter changes.
Current20/42,0newadmissions; original raw scientific prerequisites remain false.

Immediate next task: SOURCE-TO-BODY TRANSFER PREREQUISITE REVIEW. Inventory existing
source/model evidence for units/scale, finite-angle registration, muscle length/
velocity dependence, exact candidate population/tendon interpretation and neural
activation conversion. Distinguish reference fidelity from biological calibration;
do not invent force scale, infer individual binding from names or tune movement.
Original raw locks stay unresolved until supported explicitly; no hash refresh.
Use read-only evidence/source review first, not another synthetic solver campaign.
Record missing/inconclusive evidence and a bounded next decision. Keep production
and moving-FlyGym muscle coupling disconnected pending physical/neural/raw gates.

UNITY_AND_BALANCE_ROADMAP.md now marks synthetic V2 software gate complete. Next
meaningful new Unity muscle-interface test requires supported transfer plus bounded
headless evidence; stable-looking current position-assisted fly is not independent
neural balance. Continue roadmap+Git Bash after every update,20/42 is not overall
project completion. No new Unity behavior to inspect yet.

Git Bash review malecns_backend.embodiment.lf_synthetic_coupling_v2 --report
docs/evidence/lf-synthetic-coupling-v2/run/validation.json. Pull prior scientific LFS
inputs, both synthetic V1/V2 records AND historical M6C integrated_whole_leg_readiness
artifact. Expected V2 VERIFIED_TRANSFER_BLOCKED,9PASS, historicalV1INTEGRITY_FAILURE,
20/42/0new and next transfer review. No solver/native/CNS execution in saved review.

## Latest update — transfer evidence inventoried; unit/parameter lineage next

Read-only LF transfer-prerequisites V1 adds a source-context snapshot and saved
review. Reuses static identity authority and V2 preflight/evaluator. Exact original
XML optionally rechecked with the existing binding inspector; no compilation in
this path. V2 nine-case acceptance remains synthetic only; failed V1 unchanged.
Selected peak forces28.7481/12.9/10.5807/157.429 are explicit source parameters,
not the default automatic acc0 scale. Source gravity-9801, mesh scale1000 and
FlyGym scaled gravity-9810 do not establish a complete physical conversion.
Observation actuator_force/1000 is not a calibrated force-transfer rule. Paper
arXiv2509.06426v2 section6 describes estimated/optimized force/velocity properties,
not directly measured physiology. See protocol for primary links and access limits.

Physical source/target force/torque conversions stay null. Target clock seconds is
supported by the pinned FlyGym source. Modeled finite-angle rotations/source
finite differences do not validate target attachment/length/velocity registration.
All5populations/7hypotheses/13exactIDs/nullindividualbindings retained; neural
activation conversion unresolved. Original raw scientific prerequisites remain
false, recorded and current, with no hash refresh. Current20/42,newadmissions0.
No moving-fly coupling, activation solve, physics transition, CNS or Unity run in
the review. Broader legacy crosswalk regression includes native model inventory,
not a new integration experiment. No production/neuronal parameters changed.

New20static/tamper tests prohibit native construction/forward/step/muscle dynamics,
solver execution and live-audit fallback during actual saved reconstruction.
Initial test11pass/9errors was sandbox temp-directory access, resolved by local
scratch. Broader first49pass/1fail was missing original B4/M7 raw NPZs excluded
by sparse checkout; restored exact original LFS files, no source/hash waiver,
and failed legacy case then passed. See RESULTS for final checks and Git Bash.
Final combined batch50passed27.74s; Git Bash saved replay passed. No new experiment.
Normal saved replay needs existing scientific LFS prerequisites, no external clone.
Optional source-model check does not certify upstream conversion lineage/assets.

Immediate next task: SOURCE-UNIT AND PARAMETER-CONVERSION LINEAGE AUDIT. Locate
original OpenSim model, MyoConverter revision/configuration and post-conversion
edits corresponding to exact locked XML. Trace dimensional conventions for both
models (length/mass/time/inertia/force/moment arm/torque) and four peak forces,
length ranges, activation constants. Preserve missing lineage; no assumed unity
conversion, fitted multiplier, changed raw lock, motor gain or behavioral tuning.
This may justify a modeled transfer without claiming measured biology. Then
separately predeclare a length/velocity and finite-angle target-registration assay;
anatomical/neural/raw gates still apply before bounded headless native coupling.
No new Unity behavior to inspect yet. Report roadmap and Git Bash every update.

## Latest update — unit/conversion lineage audited; force scale unresolved

Fresh6dcbc4f baseline. LF_UNIT_LINEAGE_V1.md fixes read-only audit rules. New
lf_unit_lineage.py reuses transfer.verify and its original authorities/evaluators;
no model construction, solve, integration, converter or CNS execution. All prior
source/physiology/failure locks remain unchanged. No parameters/dependencies changed.
Snapshot records local rjo6615/FlyMimic HEAD9ea1131626cd76f7203b74076ef8f0e9cab30bef,
tracked file inventory, raw file hashes, Git blob IDs and introduction commits.
Two included OpenSim files and locked MJCF/PDF were introduced in
`97d77223100135cea0e39a8493767255dfc2b65d`; shared provenance, not proven derivation.
External source clone and untracked registration exports preserved untouched.

Both OpenSim files have the same four selected parameter sets, declare m/N and
gravity(0,-9806.65,0). Peak forces16.07337443/9.07997319/50.19042056/98.16552432
versus MJCF28.7481/12.9/10.5807/157.429 give distinct numeric ratios
1.78855412/1.42070904/.210811144/1.60370966. These are not force-unit conversions.
Activation constants match numerically100us/400us; this is not biological evidence.
Do not equate OpenSim fiber/slack lengths to MuJoCo actuator lengthrange or infer
velocity conversion from different model parameters. Target raw geom masses are
recorded separately from compiled body masses; no mass-ratio calibration.

Found local63page best_combined_full.pdf. Text inspected1/2/47; rendered overview
48-63 and full pages1/50-53. Four named force-length plots exist. Printed aggregate
endpoint/moment-arm/force errors and cm/N labels retained only as source-report
facts, not recomputed or adopted as acceptance. No exact locked-XML hash binding,
converter revision/config or post-conversion history established. Tracked-tree
search found no conversion log, cvt1/2, Step1/2/3 inputs or converter revision/config
under recorded patterns. Scope is local tracked tree, not global absence. Author's
linked original-muscle repo inaccessible. Generic MyoConverter docs describe
independent moment-arm/kinetics optimization; no exact revision can be inferred.
Source pyproject declares MuJoCo3.3.2/dm_control1.0.30; our validated3.2.7/1.0.27
environment unchanged. Current source-law checks retain their recorded context.

Audit classification LINEAGE_AUDIT_VERIFIED_CONVERSION_AND_PHYSICAL_SCALE_UNRESOLVED.
Physical conversions, exact conversion chain and production transfer remain
null/false. Original raw prerequisites remain false;20/42,newadmissions0.
50tests passed42.88s (14new +20transfer +16binding). Actual saved reconstruction
tested with native constructor/forward/step/dynamics, solver and live-audit entry
points forbidden. Optional source-root raw/XML verification passed. See RESULTS
for Git Bash replay and final delivery checks. Saved Git Bash verification,
whitespace and LFS-pointer checks passed. No new Unity behavior.

Immediate next task: PREDECLARE AND IMPLEMENT A NON-ACTUATING NATIVE TARGET
ORIENTATION-REGISTRATION ASSAY. Reuse the existing15source poses/rotation map and
native-isolation exact LF identity/resolution authorities. Specify target body
frames, joint ordering/limits, reference offsets and whole pose set before running;
compare measured native frames and finite-angle derivatives. Zero applied muscle
forces, zero integration/CNS, no tuned pose/window/tolerance to pass. Preserve
failed/inconclusive geometry. It can progress an independent geometry gate without
claiming physical force scaling, anatomical binding or neural conversion. Do not
enable moving-fly force transfer or rewrite original raw locks. Authoritative
converter/unit lineage remains required before choosing a physical force scale.
Continue roadmap+copy-paste Git Bash every update; current runtime20/42 is not
overall completion and stable position assistance is not independent neural balance.

## Latest update — native LF orientation convention verified; force transfer blocked

Fresh9553c77 baseline. Protocol/runner/tests committedb967c8a BEFORE one native
kinematics campaign. Reuses original fifteen source poses/derivatives/map/evaluator,
native factory/identity/inventory/address/accounting authorities and existing unit
lineage verifier. Original source model not rerun, no fitted frame alignment or
changed axes/offsets/bounds/thresholds. Pure mj_kinematics in probe phase; no body
integration, activation solve, force application or CNS. Position parameters stay
unchanged; initialization can compute forces, unused zero controls are not actuator
suppression or equilibrium. New protocol LF_TARGET_ORIENTATION_V1.md.

TARGET_ORIENTATION_GEOMETRY_VERIFIED_TRANSFER_BLOCKED: all15poses/196samples pass
all integrity/numerical/range checks. Native Thorax3, LFCoxa13, ancestry13/3/2/1;
yaw/pitch/roll joint1/2/3,qpos7/8/9,DOFs6/7/8,actions2/0/1. Reference basiserror0.
Max rotation/basis/targetFD/J/chainFD errors1.110223e-15/2.220446e-16/1.471678e-11/
2.220446e-16/2.176255e-10 vs fixed1e-10/1e-10/1e-7/1e-7/1e-7. Maximum basis/J
conditions1.05912589/1.59832895<100. Full raw states/frames retained, alltime0.
Initialization7forwards/3resets; probes196kinematics/0forward/0reset; every explicit
integration/CNS count0. Full before/after model and initialized-state identities
match original accepted native context. Installed source manifest unchanged.

New LFS docs/evidence/lf-target-orientation-v1/run/validation.json,7931285bytes,
rawSHA5daa911adc01cc42e4f40576a47ff87024497ec23309e3a01645b66815db27c9.
Prior raw results, source/physiology locks and failed evidence untouched. Original
raw scientific prerequisites remain false. Production20/42,newadmissions0.
Geometry does not validate anatomical attachments, lengths/velocities, physical
force scale or neural activation; no independent balance/gait or new Unity behavior.

Before campaign37tests passed/11prospective saved-report tests skipped43.77s;
initial34pass/3setup errors from missing scratch parent resolved without scientific
changes. After campaign71passed58.58s (orientation/source-pose/native-isolation).
Then corrected5synthetic ownership fixtures to resolve native Thorax index rather
than assumebody1 and assert valid base fixture;5passed0.97s. No runner/evaluator/
protocol/campaign change. Windows Git Bash saved verification, whitespace and
LFS-pointer checks passed; commands documented in RESULTS.

Immediate next task: SOURCE ROUTE / TARGET ATTACHMENT AND LENGTH-VELOCITY
PREREQUISITE AUDIT. Inventory four selected source tendon routes and exact
site/body ownership using the locked original model and source manifest, reusing
existing reference inspectors. Inspect available target attachment/landmark
authorities; native orientation agreement alone does not supply target muscle
sites or length correspondence. Preserve missing or ambiguous correspondences;
do not invent attachments, scale source paths, convert force from ratios or
enable moving-fly force coupling. Record a bounded next decision for non-actuating
length/velocity registration only if supported. Original physical-unit/converter
lineage, anatomical binding, neural activation and raw scientific gates remain.
Continue roadmap+Git Bash per update; no new Unity behavior to inspect yet.

## Latest update — four source routes inventoried; target attachments unresolved

Fresh4702f8e baseline. LF_ROUTE_ATTACHMENT_V1 fixes static audit rules; new
lf_route_attachment.py reuses binding/model-asset inspectors, unit-lineage and
saved native orientation evaluator. No new native construction/kinematics/forces,
integration, solver or CNS; orientation campaign not rerun. Existing model/source/
raw failure/physiology locks unchanged, no dependency or neural parameter change.

Four selected two-site routes give8unique source site definitions, ordered Thorax
thenLFCoxa, explicit local positions. Source XML defines46worldbody sites total;
do not count tendon references/default templates as new site definitions. Source
Coxa compiledbody19 is inherited from locked pose record; source Thorax/site IDs
not established here remain null. Target Thorax3/Coxa13 are inventory counterparts,
NOT endpoint ownership/correspondence; all target site IDs/coordinates/transforms,
correspondence authorities and length/velocity registration remain null.

Target XML0sites/0tendons; accepted compiled native model37sites/0tendons and none
of8exact source endpoint names. Existing Femur-body-origin sign landmark is not
a muscle-insertion authority. Active target LFCoxa usesRFCoxa.stl atscale
1000/-1000/1000, not installed-unusedLFCoxa.stl. Source/active-target Thorax meshes
have5629/5629facets with unequal ordered vertex data; sourceLF/active-targetRFcoxa
have2078/3679facets. Raw/ordered-vertex inequality is NOT a homology/shape verdict;
no alignment fit, nearest-point correspondence or physical scale adopted.

Snapshot/raw mesh summaries and saved audit retain original manifests. Optional
exact original XML/full71asset manifest check passed. All earlier geometry evidence
remains accepted within its scope. Audit classification
ROUTE_AUDIT_VERIFIED_TARGET_ATTACHMENTS_UNRESOLVED. Original raw prerequisitesfalse;
production20/42,newadmissions0; independent balance/gait not established.

Initial50tests passed49.72s:20newaudit/16binding/14unit-lineage. Counterpart-ID field
then clarified before final delivery so it cannot be read as attachment ownership;
development draft retained in local scratch, fresh final review same findings.
Final50tests passed59.04s; Git Bash saved replay, whitespace and LFS-pointer checks
passed, commands recorded in RESULTS. Native/solver/live-audit
entry points forbidden during actual static reconstruction. No new Unity behavior.

Immediate next task: PREDECLARE PAIRED SOURCE ENDPOINT / NATIVE BODY-FRAME
OBSERVATIONS. Compile locked source only under original XML/assets manifest; resolve
8source site IDs and owner-body IDs exactly. On the entire existing15pose schedule
and inherited differences, record source endpoint world positions/body frames,
independently reconstruct two-point lengths/derivatives versus existing native
source tendon-length/moment-arm evidence. Record target Thorax/Coxa body/mesh
frames at mapped poses, WITHOUT target muscle sites or transplanted coordinates.
Fix complete observations/budgets before execution; no fitting poses/window/
tolerances, force application, integration or CNS. Preserve null/failed geometry.
This validates an observer and frame/translation context, not anatomical endpoint
correspondence, unit scale, neural conversion or admission. Physical-unit/converter
lineage, anatomical bindings and original raw scientific gates remain unresolved.
No moving-fly muscle coupling. Continue roadmap and Git Bash every update.

## Latest update — paired endpoint observer verified after versioned namespace fix

Fresha734b56. V1protocol/runner/tests committeddc0097b before attempt. V1stopped
during target metadata validation: full compiled mesh name was compared with raw
XML name, ignoring attachment prefix. One sourcecompile/targetinitializer7forward/
3reset, ZEROkinematics/integration/CNS. V1 remains ENDPOINT_FRAME_INTEGRITY_FAILURE;
raw631895bytes SHA4de986daefb60a8528f7fb361cc0dfe0d7120af109140ace52bf4804ca28d598.
Original V1protocol/runner/raw unchanged. Installed dm_control MJCF attachment-only
test independently demonstrates fly/mesh_Thorax versus mesh_Thorax, no compilation.

V1.1protocol/runner committed0155b10 before ONE new campaign. Uses existing
namespace helper, full raw+terminal mesh names, same full geom/mesh namespace and
numeric body/geom/mesh IDs. Reuses V1observers/algebra/evaluator non-schema guards;
no module-global monkeypatch. V1schema still rejects V1.1; own schema validated.
Full source model/state matches original V1compilation, target matches original
native baseline. No model/parameter/pose/epsilon/budget/physiology/neural change.

ENDPOINT_FRAME_V1_1_OBSERVER_VERIFIED_TRANSFER_BLOCKED:all15poses/211samples in
range, all integrity/numeric checks pass.105source/106targetkinematics; initializer
7forward/3reset;0probe forward/reset/integration/CNS. Total both attempts14initial
forwards/6resets/211kinematics; zero integration/CNS. No extra native diagnostic
campaign. Source native IDs Thorax2/Coxa19, geoms1/18; sites4/11,8/15,6/13,7/14
for remotor/adductor/anterior/posterior. Target bodies3/13,geoms2/12. Compiled site
ownership/local coordinates and exact two-SITE tendon routes verified.

Max endpoint/length/gradient/orientation/compiled-geom errors4.440892e-16/0/
1.888907e-10/0/3.108624e-15 vs1e-10/1e-10/1e-7/1e-10/1e-10. World/local endpoint
observer reproduces all old105source tendon lengths exactly. Velocitieszero;
length gradients are NOT a nonzero-velocity law/target velocity registration.
Source/target thorax-relative co xa origins and compiled mesh preprocessing frames
recorded separately, without physical equality, scale or fitted transform.
No target endpoints/sites, force application, alignment or muscle coupling.

V1.1record9131610bytes rawSHAa317d87446c5879b564f21ecd7ffa88572d7b5370e098293c032c695131eae10
at docs/evidence/lf-endpoint-frames-v1_1/run/validation.json. Original raw scientific
prerequisites remain false. Current20/42,newadmissions0; no new Unity behavior.
BeforeV1 tests29pass/12prospectiveskip57.48s. BeforeV1.1 14pass/25skip26.83s;
12completed-record tests inapplicable to incomplete V1,13V1.1prospective. Explicit
test asserts original failedV1/zero probes, rather than claiming a V1pass. Final
automated70pass/12skip89.47s; skips only completed-V1-data cases inapplicable to
setup failure. Explicit V1failure and allV1.1archive checks passed. Git Bash saved
replay, whitespace and LFS-pointer checks passed; commands in RESULTS.

Immediate next task: TARGET-ATTACHMENT REGISTRATION DECISION REVIEW. Use paired
frames, exact source/active-target asset evidence and independent anatomical
landmarks to decide whether any explicit modeled endpoint correspondence is
supported. No fitted transform selected to make lengths/forces pass, no matching-
name attachment inference, no unit/force scale chosen from ratios. Preserve null
target endpoints if authority is missing and identify the additional reference
evidence needed. Source observer acceptance is not target anatomy or physiology.
Physical-unit/converter lineage, neural-to-activation, individual binding and
original raw scientific gates remain unresolved; no moving-fly muscle coupling.
Continue roadmap + Git Bash every update,20/42 is not overall completion.

## Latest update — target attachment decision requires independent reference data

Fresh3e842c2. Read-only LF_ATTACHMENT_DECISION_V1 review reuses original accepted
endpoint V1.1 preflight/evaluator and all source/route/mesh/identity authorities.
No native construction/kinematics/forward, force application, fit, solver or CNS.
V1.1observer remains accepted; original failed V1 raw lock/criteria unchanged.

ATTACHMENT_DECISION_VERIFIED_REFERENCE_REQUIRED:0/8target correspondences supported
in reviewed corpus; NO_TARGET_ENDPOINT_REGISTRATION_AUTHORIZED_FROM_REVIEWED_EVIDENCE.
All target coordinates/transforms remain null. Source sites4/11,8/15,6/13,7/14,
source bodies2/19 and target carrier inventory3/13 retained. Carrier IDs are not
point assignments. Active target LFCoxa still mirrored RFCoxa. No mesh substituted.
Six candidate arguments rejected as insufficient current authority: rotation-only,
local-coordinate copy, body-origin/frame alignment, surface/ICP fit, LF/RF symmetry
assumption and Femur-origin sign landmark. A mathematical frame transform can be
defined without establishing anatomical point correspondence; no transform fitted.

Dated reference-review.json records reviewed paper3.1/3.2/A.2/A.3, author website/
code and inaccessible original-muscle repo link. Paper A.2 describes foreleg mesh
replacement in source model; not exact locked-target attachment attestation. Scope
is reviewed sources/local corpus, not global absence. Local untracked source export
also inspected: rawa4e9b492... differs from cited64c31c... while canonical content
matches64c31c...; source reference mechanics only, not independent target endpoints.
No historical hash refresh/raw waiver or external file modification. See RESULTS.

Saved decision.json plus reference-request.json are independently reconstructed.
Request is NOT executable mapping or admission: source/target model/mesh locks,
eight exact source IDs, missing target annotation/frame/laterality/uncertainty
fields. Completed citation strings or coordinates never auto-authorize mapping;
new reference material requires a separately versioned scientific review.
Final58tests passed67.17s (18decision+20route+20endpointV1.1); prior57passed67.01s
before source-export provenance check. Native/solver/live-audit entry points are
forbidden in real saved reconstruction. Git Bash saved replay, whitespace and
LFS-pointer checks passed; commands recorded in RESULTS.
Production20/42,newadmissions0, original raw prerequisitesfalse; no new Unity mode.

Immediate next task: REFERENCE ACQUISITION AND QUALIFICATION. Seek authoritative
anatomical annotation/model-development artifacts with independently labeled
source-target attachment/landmark correspondences tied to the exact assets in
docs/evidence/lf-attachment-decision-v1/run/reference-request.json. Inspect official
publication/data/repository links; preserve raw files, revisions/hashes, coordinate
frames/length conventions and laterality/reflection/provenance/uncertainty. Do not
repeat pose campaigns or fit transforms to obtain favorable lengths/forces. No
author/third-party messages without explicit user authorization. If bounded source
qualification cannot obtain the artifact, report the specific evidence/access
blocker and request the missing input; do not generate another observer-only PR
as a substitute. Physical units/converter lineage, neuronal binding/activation,
nonzero-velocity physiology and original raw gates remain. Keep target points null
and moving-fly muscle coupling disabled until supported. Continue roadmap+Git Bash.

## Completed predecessor task — negative-control design requirements

1. Inspect the actual legacy calibration runner, six-foot wrapper/evaluator,
   latest raw report if available, and existing tests/provenance locks.
2. Identify a defensible environment-only negative-control design that maintains
   independently verifiable separation throughout the planned window. An initial
   gap alone is insufficient. State what collision sources the control excludes
   and how total force versus exact-pair contact will be interpreted.
3. Document/version the revised protocol before inspecting its outcomes. Keep the
   engineering threshold, transduction choices and neural parameters fixed. Any
   change of support, constraint or calibration context must be explicit and
   applied consistently where matching requires it; do not disguise it as a test
   of the ordinary live body. Do not tune surface offsets until it passes.
4. Implement a focused, separately versioned runner or reusable adapter and tests;
   preserve the locked legacy source and old evidence. Require exact identities,
   intact matched poses/schedules, clean negative evidence and verified positive
   contact. Record failed and inconclusive outcomes without automatic retries.
5. Open a PR from latest `newBrain` with concrete Git Bash commands. Run relevant
   local tests and, if the validated local physics environment is available, the
   approved bounded experiment. Report exactly which checks/experiments ran.

Do **not** enable tactile input yet. After an accepted calibration, the next
separate step is a matched tactile-delivery-enabled versus withheld experiment,
reusing the existing encoder with independent/common candidate sampling and
verified input/readout boundaries. Subsequent physical divergence in closed loop
can be an outcome; require matching before the intervention. Neither calibration
nor new motor activity by itself establishes balancing or gait.

## Local environment, tests and handoff usage

User's Git Bash checkout: `~/Documents/FlyBrainUnity`. Bare `python` has worked
for their recent runs. An older validated environment may be at
`fly-brain-interactive/.venv/Scripts/python.exe`; inspect rather than assume.
Node is needed for JS reference checks. Live physics needs FlyGym/MuJoCo; do not
silently install/upgrade physics dependencies or treat mocks as physics results.
The prior remote environment lacked FlyGym; local Codex should verify what is
actually available. Full CNS loading can take minutes; use physics-only tests
for the current calibration question. Unity is not required for these CLI runs.

Useful quick checks from repository root:

```bash
python -m pytest -q tests/test_six_foot_contact_calibration.py tests/test_tactile_targeted_contact_calibration.py
python -m pytest -q tests/test_live_contact_readiness.py tests/test_live_cli.py tests/test_live_headless.py tests/test_live_motor_diagnostics.py tests/test_live_pose_transport.py
python -m pytest -q tests/test_calibrated_neural_parity.py tests/test_neural_runtime.py
node --test tests/js/neuromod_scope_audit.test.mjs
```

Latest calibration implementation validation: 57 tests + 9 subtests passed across
the batch, old targeted calibration (including artifact locks), contact survey,
CLI/headless/motor/transport. Earlier broader neural-audit testing encountered
three missing-FlyGym failures and one differing historical-artifact comparison;
these reproduced with original code. Reassess locally rather than assuming
these remain the only failures or updating artifacts to pass tests.

Before edits, fetch, protect unrelated local changes and start a new branch from
`origin/newBrain`. Follow root agent instructions. Keep this checkpoint current
when a substantive new result changes the next decision.
