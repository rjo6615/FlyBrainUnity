# Where we are: Unity, neural balance and the LF force-interface milestone

Current2026-11-04: desk audit of the remaining coxa coordinates. The forward-limit encoder cannot see roll/yaw; RH Coxa has no H1 channel; RF blocked. No remaining coordinate is testable with current validated components.

```text
Remaining coxa audit          [none of 14 testable: roll/yaw invisible to encoder (12), RH Coxa unbound, RF blocked]
Coxa push replication         [run: AMPLIFICATION_DIRECTIONAL F / B (R>1 6/6); yoke DO_NOT_REPRODUCE; FREE_COMMANDS_INCREASE_D F / B]
Coxa conditional tier         [LF/LH/LM/RM CONDITIONAL (fore-aft Coxa); RF/RH blocked by input]
Motor coverage                [##########-----------] 20/42 admitted (+4 conditional); ceiling with current components
Independent balance / gait    [not established]
```

Current2026-11-04: push response + offset yoke replicated on six new seeds (55 arms). Amplification direction replicates (R > 1 in 6/6, magnitude 1.05-1.97, below the 10 % bar in one seed per direction); fixed offsets do not reproduce it; free post-push coxa commands raise D in 6/6 per direction. Seed scatter about 0.17-0.24 SD in log ratio.

```text
Coxa push replication         [run: AMPLIFICATION_DIRECTIONAL F / B (R>1 6/6); yoke DO_NOT_REPRODUCE; FREE_COMMANDS_INCREASE_D F / B]
Coxa offset yoke              [run: OFFSETS_DO_NOT_REPRODUCE F / B; replicated on seeds 7-12]
Coxa push response            [run: LOOP_AMPLIFIES F (SIGN_INDEPENDENT) / B (SIGN_SPECIFIC); direction replicated, magnitude scatters]
Coxa conditional tier         [LF/LH/LM/RM CONDITIONAL (fore-aft Coxa); RF/RH blocked by input]
Motor coverage                [##########-----------] 20/42 admitted (+4 conditional, counted separately)
Independent balance / gait    [not established]
```

Current2026-11-04: replication of the push response and offset yoke on six new seeds designed (55 arms). Not run.

```text
Coxa push replication         [designed: N / C / Y x no-push/F/B x seeds 7-12 + REPRO; next: build]
Coxa offset yoke              [run: OFFSETS_DO_NOT_REPRODUCE F / B; amplification needs free post-push coxa commands in 2/3 seeds]
Coxa push response            [run: LOOP_AMPLIFIES F (SIGN_INDEPENDENT) / B (SIGN_SPECIFIC); mechanism: not posture alone]
Coxa conditional tier         [LF/LH/LM/RM CONDITIONAL (fore-aft Coxa); RF/RH blocked by input]
Motor coverage                [##########-----------] 20/42 admitted (+4 conditional, counted separately)
Independent balance / gait    [not established]
```

Current2026-11-03: open-loop coxa offset yoke run. Replaying the unpushed C coxa commands does not reproduce the push amplification (OFFSETS_DO_NOT_REPRODUCE, both directions); the posture-only reading is not supported.

```text
Coxa offset yoke              [run: OFFSETS_DO_NOT_REPRODUCE F / B; amplification needs free post-push coxa commands in 2/3 seeds]
Coxa push response            [run: LOOP_AMPLIFIES F (SIGN_INDEPENDENT) / B (SIGN_SPECIFIC); mechanism: not posture alone]
Coxa conditional tier         [LF/LH/LM/RM CONDITIONAL (fore-aft Coxa); RF/RH blocked by input]
Motor coverage                [##########-----------] 20/42 admitted (+4 conditional, counted separately)
Independent balance / gait    [not established]
```

Current2026-11-03: open-loop coxa offset yoke designed (9 arms): does replaying the unpushed C coxa commands reproduce the push amplification? Not run.

```text
Coxa offset yoke              [designed: Y0/YF/YB (coxa 0/7/14/28 yoked to C0_s) x 3 seeds; next: build]
Coxa push response            [run: LOOP_AMPLIFIES F (SIGN_INDEPENDENT) / B (SIGN_SPECIFIC); loops not push-recruited]
Coxa conditional tier         [LF/LH/LM/RM CONDITIONAL (fore-aft Coxa); RF/RH blocked by input]
Motor coverage                [##########-----------] 20/42 admitted (+4 conditional, counted separately)
Independent balance / gait    [not established]
```

Current2026-11-03: fore-aft push response run. With the four conditional coxa channels the body is
displaced more (LOOP_AMPLIFIES, both directions); the loops act as tonic posture offsets, not push reflexes.

```text
Coxa push response            [run: LOOP_AMPLIFIES F (SIGN_INDEPENDENT) / B (SIGN_SPECIFIC); loops not push-recruited]
Coxa conditional tier         [LF/LH/LM/RM CONDITIONAL (fore-aft Coxa); RF/RH blocked by input]
Motor coverage                [##########-----------] 20/42 admitted (+4 conditional, counted separately)
Independent balance / gait    [not established]
```

Current2026-11-03: fore-aft push response with the four conditional coxa channels designed (27 arms). Not run.

```text
Coxa push response            [designed: N / C (4 H1) / X (4 FLIP) x no-push/F/B x 3 seeds; next: build]
Coxa conditional tier         [LF/LH/LM/RM CONDITIONAL (fore-aft Coxa); RF/RH blocked by input]
Motor coverage                [##########-----------] 20/42 admitted (+4 conditional, counted separately)
Independent balance / gait    [not established]
```

Current2026-11-03: middle-leg coxa C3 run. joint_LMCoxa and joint_RMCoxa CONFIRMED 3/3 new seeds
-> CONDITIONAL. First bilateral conditional pair; +4 conditional in total.

```text
Middle-leg coxa (LM/RM)       [CONFIRMED 3/3 new seeds -> CONDITIONAL (C1-C4 met)]
Coxa conditional tier         [LF/LH/LM/RM CONDITIONAL (fore-aft Coxa); RF/RH blocked by input]
Motor coverage                [##########-----------] 20/42 admitted (+4 conditional, counted separately)
Independent balance / gait    [not established]
```

Current2026-11-03: middle-leg coxa C3 confirmation designed (seeds 4-6 + REPRO). Not run.

```text
Middle-leg coxa (LM/RM)       [C2_PASSED 3/3; C3 designed: seeds 4-6, CONFIRMED -> CONDITIONAL; next: build]
Coxa conditional tier         [LF/LH CONDITIONAL; LM/RM C2 passed; RF/RH blocked by input]
Motor coverage                [##########-----------] 20/42 admitted (+2 conditional, counted separately)
Independent balance / gait    [not established]
```

Current2026-11-03: middle-leg coxa displacement test run. joint_LMCoxa and joint_RMCoxa C2_PASSED
3/3 (first bilateral pair); graded hair-plate feedback seen. Awaiting C3.

```text
Middle-leg coxa (LM/RM)       [C2_PASSED 3/3 both (imposed displacement); next: C3 on seeds 4-6]
Coxa conditional tier         [LF/LH CONDITIONAL; LM/RM C2 passed; RF/RH blocked by input]
Motor coverage                [##########-----------] 20/42 admitted (+2 conditional, counted separately)
Independent balance / gait    [not established]
```

Current2026-11-03: middle-leg coxa resistance-reflex test designed (imposed displacement, 9 arms). Not run.

```text
Middle-leg coxa (LM/RM)       [designed: imposed forward displacement, H1 vs FLIP x 3 seeds (C2 step); next: build]
RF input deficit              [V1 + V2 INCONCLUSIVE; no local neuron-level identity; RF stays BLOCKED_BY_INPUT]
Motor coverage                [##########-----------] 20/42 admitted (+2 conditional, counted separately)
Independent balance / gait    [not established]
```

Current2026-11-03: RF hair-plate BANC check V2 run: INCONCLUSIVE_INTEGRITY (coverage LF 5/7,
RF 3/5; BANC matches are group-level or non-sensory). Thread recommended closed.

```text
RF input deficit              [V1 + V2 INCONCLUSIVE; no local neuron-level identity; RF stays BLOCKED_BY_INPUT]
Motor coverage                [##########-----------] 20/42 admitted (+2 conditional, counted separately)
Independent balance / gait    [not established]
```

Current2026-11-03: RF hair-plate BANC check V2 designed (neuron-level matches). Not run.

```text
RF input deficit              [V1 INCONCLUSIVE; V2 designed: follow the model's own RF/LF neurons into BANC by match]
Motor coverage                [##########-----------] 20/42 admitted (+2 conditional, counted separately)
Independent balance / gait    [not established]
```

Current2026-11-03: RF hair-plate BANC check run: INCONCLUSIVE_INTEGRITY (21.7 % excluded;
BANC SNpp45 type broader than MaleCNS). No labels; anatomy vs reconstruction still open.

```text
RF input deficit              [BANC check INCONCLUSIVE (type names not equivalent); V2 needs neuron-level matches]
Released-posture coxa test    [NO_RESCUE; no consistent assist or loop effect on T_roll (3 seeds)]
Motor coverage                [##########-----------] 20/42 admitted (+2 conditional, counted separately)
Independent balance / gait    [not established]
```

Current2026-11-03: RF hair-plate cross-connectome check designed (BANC, data only). Not run.

```text
RF input deficit              [designed: BANC v888 count/size check vs MaleCNS; next: build]
Released-posture coxa test    [NO_RESCUE; no consistent assist or loop effect on T_roll (3 seeds)]
Motor coverage                [##########-----------] 20/42 admitted (+2 conditional, counted separately)
Independent balance / gait    [not established]
```

Current2026-11-02: released-posture coxa test run. All labels null as predicted; every arm
rolls over 67-91 ms after release. CONDITIONAL status unchanged.

```text
Released-posture coxa test    [NO_RESCUE; no consistent assist or loop effect on T_roll (3 seeds)]
Coxa admission                [LF/LH Coxa CONFIRMED 3/3 -> CONDITIONAL; RF/RH blocked by input; rest untested]
Motor coverage                [##########-----------] 20/42 admitted (+2 conditional, counted separately)
Independent balance / gait    [not established]
```

Current2026-11-02: released-posture test with the conditional coxa channels designed (12 arms). Not run.

```text
Released-posture coxa test    [designed: R22 / K (keep 2 servos) / KC / KF x 3 seeds; next: build]
Coxa admission                [LF/LH Coxa CONFIRMED 3/3 -> CONDITIONAL; RF/RH blocked by input; rest untested]
Motor coverage                [##########-----------] 20/42 admitted (+2 conditional, counted separately)
Independent balance / gait    [not established]
```

Current2026-11-02: coxa confirmation run. joint_LFCoxa and joint_LHCoxa CONFIRMED 3/3 seeds
(isolated) -> CONDITIONAL tier (counted separately; not admission).

```text
Coxa admission                [LF/LH Coxa CONFIRMED 3/3 -> CONDITIONAL; RF/RH blocked by input; rest untested]
Motor coverage                [##########-----------] 20/42 admitted (+2 conditional, counted separately)
Independent balance / gait    [not established]
```

Current2026-11-02: coxa admission question designed (policy tier + 9-arm confirmation). Not run.

```text
Coxa admission                [designed: CONDITIONAL tier proposal; LF/LH Coxa confirmation x3 seeds; next: build]
Relay causal test             [NOT_NECESSARY (LF hair drive suprathreshold); NONSPECIFIC (sham flaw: reached relay)]
Motor coverage                [##########-----------] 20/42 (proven; at most +2 conditional possible, counted separately)
Independent balance / gait    [not established]
```

Current2026-11-02: relay intervention run. Q_NEC NOT_NECESSARY (0.823), Q_SUF NONSPECIFIC
(sham recruited the relay); injection raised RF pool 1.5 -> 24.2 Hz.

```text
Relay causal test             [NOT_NECESSARY (LF hair drive suprathreshold); NONSPECIFIC (sham flaw: reached relay)]
RF other excitation           [right relay can drive RF when active (exploratory); silent because of weak RF hair input]
Motor coverage                [##########-----------] 20/42 (proven; coxa = hypothesis only)
Independent balance / gait    [not established]
```

Current2026-11-02: hair-plate relay intervention designed (5 arms). Not run.

```text
RF other excitation           [ACTIVITY_GAP; relay IN03A066/075/080 silent on right; Q3 rule degenerate]
Relay causal test             [designed: silence left / inject right, with shams; next: build]
Motor coverage                [##########-----------] 20/42 (proven; coxa = hypothesis only)
Independent balance / gait    [not established]
```

Current2026-11-01: RF other excitation is an activity gap: wiring present, relay
interneurons silent; left-side excitation is hair-evoked.

```text
Right-side coxa drive         [explained in-model: synapses/source + no other excitation; engine 9%]
RF other excitation           [ACTIVITY_GAP; relay IN03A066/075/080 silent on right; Q3 rule degenerate]
Motor coverage                [##########-----------] 20/42 (proven; coxa = hypothesis only)
Independent balance / gait    [not established]
```

Current2026-11-01: RF coxa MN excitation question designed (data only). Not run.

```text
Right-side coxa drive         [explained in-model: synapses/source + no other excitation; engine 9%]
RF other excitation           [designed: wiring vs activity, hair-evoked vs baseline; next: build]
Motor coverage                [##########-----------] 20/42 (proven; coxa = hypothesis only)
Independent balance / gait    [not established]
```

Current2026-11-01: right-front coxa drive explained within the model: small RF hair-plate
neurons + no other excitation onto RF coxa MNs; engine choices 9 %.

```text
Coxa D3: closed-loop test     [NOT_CONSISTENT 2/4; LF+LH resist and reverse; H1_FAVOURED]
Right-side coxa drive         [explained in-model: synapses/source + no other excitation; engine 9%]
Motor coverage                [##########-----------] 20/42 (proven; coxa = hypothesis only)
Independent balance / gait    [not established]
```

Current2026-11-01: right-front coxa drive asymmetry designed (data only). Not run.

```text
Coxa D3: closed-loop test     [NOT_CONSISTENT 2/4; LF+LH resist and reverse; H1_FAVOURED]
Right-side coxa drive         [designed: data-only pathway + replay comparison; next: build]
Motor coverage                [##########-----------] 20/42 (proven; coxa = hypothesis only)
Independent balance / gait    [not established]
```

Current2026-11-01: coxa D3 run: NOT_CONSISTENT by the 3-leg rule; a working
resistance loop in LF and LH only; right front blocked by weak hair-plate -> MN drive.

```text
Coxa D1/D2                    [D1_D2_READY]
Coxa D3: closed-loop test     [NOT_CONSISTENT 2/4; LF+LH resist and reverse; H1_FAVOURED]
Right-side coxa drive         [weak: RF MNs 0.55 Hz under 120 Hz hair plates]
Motor coverage                [##########-----------] 20/42 (proven; coxa = hypothesis only)
Independent balance / gait    [not established]
```

Current2026-11-01: coxa D3 closed-loop test designed (C0/H1/H1_FLIP/H2). Not run.

```text
Coxa D1/D2                    [D1_D2_READY]
Coxa D3: closed-loop test     [designed; next: build + preregister]
Motor coverage                [##########-----------] 20/42 (proven; coxa = hypothesis only)
Independent balance / gait    [not established]
```

Current2026-11-01: coxa D1/D2 D1_D2_READY: action table and two rule-built hypothesis
bindings (H1 13 channels, H2 8). Nothing admitted.

```text
Coxa D1: action table         [D1_D2_READY; front roll/yaw near-degenerate at rest]
Coxa D2: H1/H2 bindings       [H1 13 ch, H2 8 ch; H2 drops all rotators]
Coxa D3: closed-loop test     [next: preregister]
Motor coverage                [##########-----------] 20/42 (proven; coxa = hypothesis only)
Independent balance / gait    [not established]
```

Current2026-11-01: coxa motor hypothesis track V1 designed (labelled bindings H1/H2,
closed-loop resistance-reflex test). Not run; no admission.

```text
Hair plate C: on/off test     [POSTURE_SENSITIVE, REFLEX_DIRECTION_CONSISTENT]
Coxa D1: action table         [designed]
Coxa D2: H1/H2 bindings       [designed]
Coxa D3: closed-loop test     [designed]
Motor coverage                [##########-----------] 20/42 (proven; coxa = hypothesis only)
Independent balance / gait    [not established]
```

Current2026-11-01: hair-plate Step C: coxa MNs now sense posture and respond in the
published reflex direction; no balance yet (coxa joints unmapped).

```text
Hair plate A: identity        [MATCH_ALL]
Hair plate B: encoder         [ENCODER_READY]
Hair plate C: on/off test     [POSTURE_SENSITIVE, REFLEX_DIRECTION_CONSISTENT]
Coxa sensory loop             [closed on the sensory side]
Coxa motor side               [unmapped: 18 coordinates]
Motor coverage                [##########-----------] 20/42 (proven)
Independent balance / gait    [not established]
```

Current2026-11-01: hair-plate Step B ENCODER_READY; standing pose already at the
encoder's forward limit in four legs.

```text
Hair plate A: identity        [MATCH_ALL, 6/6 legs]
Hair plate B: encoder         [ENCODER_READY; rest-pose saturation caveat]
Hair plate C: on/off test     [pending decision]
Motor coverage                [##########-----------] 20/42 (proven)
Independent balance / gait    [not established]
```

Current2026-11-01: hair-plate Step A MATCH_ALL: our SNpp45 hair plates show the
published CxHP8 coxa limit-reflex wiring in all six legs.

```text
Posture-sense inventory       [done]
Hair plate A: identity        [MATCH_ALL, 6/6 legs]
Hair plate B: encoder         [next]
Hair plate C: on/off test     [pending]
Motor coverage                [##########-----------] 20/42 (proven)
Independent balance / gait    [not established]
```

Current2026-11-01: pivot to posture senses. Inventory V1: hair plates are the best
next sense (direct path to coxa MNs, not yet encoded).

```text
Stage 1 DNg100 rhythm         [NOT_REPRODUCED]
Posture-sense inventory       [done; hair plates best candidate]
Hair-plate encoder            [next: preregister design]
Motor coverage                [##########-----------] 20/42 (proven)
Independent balance / gait    [not established]
```

Current2026-11-01: Stage 1 of the discovery program (DNg100 rhythm in our engine)
NOT_REPRODUCED: specific but tonic front-leg recruitment, no rhythm.

```text
Stage 1 DNg100 rhythm         [NOT_REPRODUCED; pathway present, tonic output]
Stage 2 coxa hypotheses       [not started]
Stage 3 emergent stepping     [blocked: no rhythm in engine as-is]
Motor coverage                [##########-----------] 20/42 (proven)
Independent balance / gait    [not established]
```

Current2026-11-01: blind serial motor-fingerprint test FAILED its preregistered
bar (real signal, 0.62 vs needed 0.70). See SERIAL_MOTOR_FINGERPRINT_RESULTS.

```text
Connectivity identity method  [V1 FAIL; signal above chance, below bar]
Motor coverage                [##########-----------] 20/42 (blocked)
Independent balance / gait    [not established]
```

Current2026-11-01: local-only project by user decision; anatomy data requests
withdrawn, no outside contact.

```text
Anatomy data requests         [withdrawn by user; local-only project]
Motor coverage                [##########-----------] 20/42 (blocked; no qualifying local/public anatomy)
Independent balance / gait    [not established]
```

Current2026-11-01: anatomy data requests drafted for the 22 blocked coordinates
(ANATOMY_DATA_REQUESTS_V1, not sent).

```text
V1.2 Unity replay             [implemented; watched by user]
Anatomy data requests         [drafted; not sent]
Motor coverage                [##########-----------] 20/42 (blocked on anatomy data)
Independent balance / gait    [not established]
```

Current2026-11-01: saved V1.2 campaign poses can now be replayed in the existing
LiveFly scene behind a full re-verification gate (see ASSISTANCE_CAMPAIGN_V1_2_REPLAY).

```text
Eight-arm assistance run      [COMPLETE, INTEGRITY_ACCEPTED]
V1.2 Unity replay             [implemented; real evidence verified; Editor review pending]
Motor coverage                [##########-----------] 20/42 (blocked on anatomy data)
Independent balance / gait    [not established]
```

Current2026-10-31: V1.2 eight-arm assistance campaign COMPLETE and
INTEGRITY_ACCEPTED (~4.8 h). Neutralizing the 22 baseline-only servos rolls the
fly over in every R arm; the 20 neural channels make no resolved difference.
See ASSISTANCE_CAMPAIGN_V1_2_RUN_RESULTS.

```text
Eight-arm assistance run      [COMPLETE, INTEGRITY_ACCEPTED]
Finding                       [22 baseline servos hold posture; neural 20 do not replace them]
Next milestone                [expand neural motor coverage before reducing assistance]
Motor coverage                [##########-----------] 20/42
Independent balance / gait    [not established]
```

Current2026-10-31: V1.1 attempt completed A_NC with native qualification passed,
then stopped at a saved-JSON read-back defect (preserved). V1.2 read-back and
journal-clock corrections and a faster exact model-phase check (est. ~1.3-1.6 h
for eight arms, was ~8-9 h) implemented; offline audit of retained A_NC passes.

```text
V1 live attempt               [failed at binding; preserved]
V1.1 live attempt             [A_NC complete; stopped at transfer read; preserved]
Native qualification          [passed on actual model (V1.1 A_NC)]
V1.2 read-back correction     [implemented; retained A_NC audit passes]
Eight-arm assistance run      [not run]
Motor coverage                [##########-----------] 20/42
Independent balance           [not established]
```

Current2026-10-31: the ONE V1 campaign attempt stopped at A_NC binding on a
false live-data guard alarm (0 physics/neural; preserved). Versioned V1.1 guard
correction implemented; no new native run. See ASSISTANCE_CAMPAIGN_V1_1_RESULTS.

```text
Campaign/full evaluator       [merged]
V1 live attempt               [failed at binding; preserved]
V1.1 guard correction         [implemented; toy-MuJoCo + synthetic tests]
Native qualification          [not reached]
Eight-arm assistance run      [not run]
Motor coverage                [##########-----------] 20/42
Independent balance           [not established]
```

Current2026-10-31: eight-arm campaign controller/workers and complete piecewise
evaluator implemented; 46 synthetic/real-process engineering tests pass. Native
qualification and the eight-arm run have NOT run. See ASSISTANCE_CAMPAIGN_RESULTS.

```text
Accepted recorded assay       [done; behavior mixed]
Saved Unity review            [confirmed]
Eight-arm assistance design   [specified]
Mechanical adapter/tests      [checked with synthetic fixtures]
Campaign/full evaluator       [implemented; synthetic tests]
Native qualification          [next; not run]
Eight-arm assistance run      [not run]
Motor coverage                [##########-----------] 20/42
Independent balance           [not established]
```

Current2026-10-26: assistance mechanical adapter and synthetic checks complete.
Actual native binding/force qualification and eight-arm campaign have NOT run.
75engineering checks pass; source/design --check verified in Windows Git Bash.
Next integrate complete eight-arm scientific evaluator and fresh OS controller/
workers with full original guards; commit before the one bounded native attempt.
See ASSISTANCE_NATIVE_ADAPTER_RESULTS.md. Prior prospective docs remain frozen.

```text
Accepted recorded assay       [done; behavior mixed]
Saved Unity review            [confirmed]
Eight-arm assistance design   [specified]
Mechanical adapter/tests      [checked with synthetic fixtures]
Campaign/full evaluator       [next]
Native qualification          [not run]
Eight-arm assistance run      [not run]
Motor coverage                [##########-----------] 20/42
Independent balance           [not established]
```

The milestone is measuring22baseline-servo support versus contribution from
existing20neural inputs. No new Unity behavior in this engineering update; no
new motor admissions, tuning or physical/biological claim. Retained20position
actuators still assist posture. Bars describe coverage/milestones, not total
project completion. Older dated entries below retain their historical status.

Current2026-10-26: PR292 merged; user reviewed new saved V1.1 movement and reported
normal motion/no unexpected issues. Acquisition live delivery remains unconfirmed
(0sent). The eight-arm partial assistance-contribution protocol is now specified
and statically checked, NOT implemented/run. It compares original versus
neutralized22baseline-only servos while retaining20neural position actuators,
crossed with neural input continuation/withdrawal and fixed push/no-push.
No changes to neural parameters, old acceptance, source locks or historical data.
26static tests pass; no new physics/CNS. See ASSISTANCE_CONTRIBUTION_DESIGN_RESULTS.

```text
Accepted recorded assay    [done; behavior mixed]
New saved Unity review     [confirmed by user]
Assistance test design     [specified; 8 arms]
Native adapter and tests   [next]
Force-law qualification    [not run]
Assistance campaign        [not run]
Motor coverage             [##########-----------] 20/42
Independent balance        [not established]
```

Next implement/test/commit the versioned adapter and model-phase audit before
ONE bounded qualification/campaign. The first question is whether22baseline-only
servos conceal a contribution from existing neural inputs. Retained20actuators
still assist posture, so this comparison cannot establish fully independent
balance by itself. These are milestone states, not percentages of total completion.
Earlier dated entries below describe historical checkpoints.

Latest2026-10-26:V1.1 fixed four-arm native campaign COMPLETE/INTEGRITY_ACCEPTED,
80,000scientific physics/16,000neural/80,004states. All4science traces exactly
match prior accepted reference under unchanged assistance/settings. Behavior
MIXED_OR_UNRESOLVED;20/42motors,0new admissions. No independent balance/gait.
Complete source prerequisite correction is verified; prior failures preserved.

Live pose projection verified15,256offers, but0sent to clients:live Unity viewing
is unconfirmed. New integrity-gated recorded adapter allows review of these exact
poses without rerunning science. Next:human review with the NEW command, then
prospective assistance-contribution study. See CONTROLLED_LIVE_BALANCE_V1_1_RESULTS.

```text
Native four-arm acquisition [####] 4/4
Scientific integrity       [accepted]
New recorded review        [next]
Live client delivery       [unconfirmed]
Motor coverage             [##########-----------] 20/42
Independent balance        [not established]
```

2026-10-26 V1.1:complete original-source checks now mandatory in controller,
each worker before initialization and after acquisition. New schema, frozen V1
driver/observer/scientific kernel reused unchanged.67engineering checks pass;
real construction-free source/data/environment gates verify. Commit first,
then ONE fresh four-arm attempt is next. Prior V1 initialization refusal remains
retained. No new live pose or behavioral claim at this implementation checkpoint.
Motor20/42,0new admissions; position assistance unchanged. See V1_1_RESULTS.

Actual live V1 result2026-10-26: initial NC stopped in original loader validation
before poses because the isolated checkout lacked original graph_w3.bin.0states/
scientific transitions/neural updates; WC/NP/WP unstarted. Raw failure retained,
no retry. Read-only source guard now verifies restored original file plus all old
prerequisites. Next:separately versioned V1.1 must require/bind that complete guard
before a fresh campaign. Frozen executed V1 source/specification stay unchanged.
Final live engineering37pass; source-guard/failure replay11pass; prior broader114pass.
Recorded assay/full-body review done; live poses not yet obtained.20/42 motors,
0new admissions; independent balance/gait unproven. See implementation RESULTS.

2026-10-26 live adapter checkpoint: existing20motor/42assisted-actuator experiment
now has an isolated controller/observer under its own schema, with original
scientific audits unchanged. Broader114tests and targeted37stop/cleanup tests pass;
original construction-free prerequisites verify. User confirmed full-body replay
review, Unity ready and old replay stopped. Commit implementation, then ONE bounded
live NC/WC/NP/WP campaign is next. Live poses remain provisional until offline
audit; local publication cannot establish human visual review or independent
balance. See CONTROLLED_LIVE_BALANCE_IMPLEMENTATION_RESULTS.md for actual status.
No new admissions:20/42. Older design-only statuses below are historical.

Current continuation2026-10-26: camera PR289 merged. Controlled live observation
is now separately [specified](CONTROLLED_LIVE_BALANCE_V1.md), not implemented or
run. It will display the existing assisted20motor four-arm experiment during
computation with provisional labels, full raw recording and strict original
integrity; real-time speed is not guaranteed. Next implement/test its isolated
worker/lifecycle/observer and commit before one bounded campaign. Full-body human
review of the accepted recording remains unconfirmed. Independent balance needs
a separately justified assistance comparison; no servo/neural tuning here.

```text
Recorded assay          [done]
Unity replay connection [done]
Full-body human review  [pending confirmation]
Controlled-live design  [specified]
Live adapter and checks [next]
Bounded live experiment [not run]
Independent balance    [not established]
Motor coverage         [##########-----------] 20/42
```

Current desktop continuation2026-10-26: PR288 is merged; accepted recorded data
and Unity transport are available. [Frame Current Fly](LIVE_FLY_CAMERA_FRAMING_V1.md)
adds an explicit presentation-only fit of the actual received pose, holding a
fixed world view. Full-body human review is next; no scientific rerun is needed.
Then predeclare a controlled live experiment with explicit assistance and matched
controls. A continuous20motor live viewer already exists but does not establish
causal or independent balance. No neural/force/assistance/acceptance changes here.
Coverage20/42; recorded outcome MIXED_OR_UNRESOLVED. Older dated checkpoints below
retain their original implementation/review status rather than defining current
readiness. Desktop interpreter:fly-brain-interactive/.venv/Scripts/python.exe.

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

V1.1 continuation2026-10-26: [process-boundary results](BALANCE_CONTRIBUTION_PROCESS_RESULTS.md).
72engineering/reference checks pass. Each planned arm now gets genuinely fresh
process-global state; all original identity/prefix/RNG/safety/force auditors stay
strict. No native V1.1 run at this implementation checkpoint. Unity distance:
environment passed; process engineering passed; full four-arm native integrity
pending; verified saved-pose replay adapter pending. User wants this gate/status
update after every run. Current20/42 motors,0new admissions; independent neural
balance and walking remain unestablished. Older failures remain preserved below.

Desktop result2026-10-26: [environment and bounded attempt](BALANCE_DESKTOP_ENVIRONMENT_V1.md).
Pinned Python3.12 environment is installed separately; pip/import checks,
37focused tests and6checkout regressions pass. Static original authorities pass.
The first ACTUAL native/CNS attempt completed NC20000physics/4000neural; WC stopped
at initialization because the historical0/... names differ from fresh instance
1/... names. NP/WP did not start. Full NC/partial WC and error are preserved;
INCOMPLETE/INCONCLUSIVE_INTEGRITY, no accepted Unity replay or balance comparison.
Next gate is a separately versioned instance/process-lifecycle correction with
strict actual-model identity checks, tests and commit before a justified new run.
No retry or new motor admission; coverage20/42, LF target correspondences0/8,
independent balance/walking unestablished. The earlier environment blocker below
is historical and has now been resolved.

Latest continuation2026-10-26: [balance implementation V1](BALANCE_CONTRIBUTION_IMPLEMENTATION_V1.md)
adds the isolated adapter/recorder/evaluator;23synthetic engineering checks and
13existing neural reference checks pass. No actual four-arm experiment or Unity
replay ran. Legacy desktop Python launcher is broken; required physics packages
andpyarrow are absent from the bundled test runtime. Original static prerequisites
remain incomplete. Next restore/access the validated environment, pass those
gates, then perform the single committed fixed NC/WC/NP/WP execution. Motor
coverage20/42; newadmissions0; LF target correspondences0/8. Independent neural
balance/walking remain unestablished. A synthetic null acceptance tests the
evaluator only; it is not observed fly behavior or native runtime readiness.

The dated sections below retain earlier milestone context.

Checkpoint2026-10-25. This is a roadmap, not a new experimental acceptance
protocol or a claim that the milestones below are already complete.

## At a glance

Motor coverage: **20/42 admitted coordinates — 47.6%**.

```text
Motor coverage   [##########-----------] 20/42
```

This is motor coverage only, not overall project completion or biological
validation. Tibia, femur and femur roll each contribute 6/6; front Tarsus1
contributes 2/6; coxa/roll/yaw contribute 0/18. Remaining: 22 coordinates.

| Roadmap gate | Current position |
|---|---|
| Existing 20-coordinate runtime and controlled sensory observations | Available within recorded conditions; ordinary live tactile disabled |
| LF source mechanics / numerical interface | Scoped reference and synthetic checks verified; historical failures retained |
| Three historical motor/sign/registration raw locks | Checkout-byte defect fixed; guarded repair verifies original hashes3/3 in isolated checkout; historical failures retained |
| Middle/hind distal target references | New generation-pinned BANC leads43rows; conflicts/missing/duplicate references retained; no new population admission |
| LF target attachment anatomy — active gate | Reference required; 0/8 supported endpoint correspondences in the reviewed corpus |
| Physical scaling, neural binding and activation | Unresolved; cannot infer these from a geometry check |
| Bounded moving-body muscle experiment, then Unity review | Pending prerequisites; no new Unity behavior from current document/reference checks |
| Independent neural balance, then walking | Not established |

Latest continuation: [reference acquisition V1](LF_REFERENCE_ACQUISITION_V1.md)
followed publication/data/code leads and found an upstream rig-compatibility
discussion. No qualifying target annotation artifact was acquired. Some data
shares could not be inspected with the browsing tool; that is an access limit,
not evidence of absence. Next input is an accessible, revisioned anatomical
attachment/landmark bundle tied to the exact assets in the existing request.
Another pose sweep or saved-report replay cannot supply it. This research gate
has no defensible completion percentage or fixed number of remaining PRs.

Independent engineering maintenance now addresses a reproducible Windows newline
defect; see [motor-freeze checkout repair](MOTOR_FREEZE_CHECKOUT_V1.md). The three
original hashes are satisfied by restoring their exact committed bytes, without
changing any expected hash or interpreting canonical equivalence as a raw pass.
This removes a checkout integrity obstacle while the anatomical reference gate
remains blocked. It adds no motor channels and no new Unity behavior.

An independent distal workstream now has new primary-source annotation leads;
see [distal tarsus reference findings](DISTAL_TARSUS_REFERENCE_RESULTS.md). These
narrow the exact neurons and disagreements needing anatomical review, including
right-middle801477 and right-hind869369/800358. The four missing distal populations
remain unqualified. Next establish homologous function, dataset-version identity
and full antagonist membership, preserving every conflicting candidate. V1.3 is
strictly static; earlier serialization and construction-boundary failures remain
documented. Motor count20/42 and the LF attachment gate are unchanged.

## The milestone we are working toward

The user selected an independent near-term milestone: a controlled test of the
existing20motors' neural contribution to posture under declared position-control
assistance. [Protocol V1](BALANCE_CONTRIBUTION_V1.md) is now specified, not
implemented/run. Next build/test its adapter/evaluator, execute its fixed four
arms once after prerequisite checks, then review valid saved poses in Unity.
This can proceed while new motor anatomy is blocked; no42-channel completion
or independent-balance claim is required for an honest controlled contribution
test. The LF muscle interface remains a separate longer-term milestone below.

A trustworthy **left-front proximal muscle-force interface**: supported neural
populations feed an explicit activation model, source mechanics map force into
the intended body coordinates, and existing position actuation is replaced only
where declared. Activation/body state advance once; force buffers and other
controls remain intact. Biological assumptions and synthetic engineering checks
must stay distinguishable.

This could support the three LF coxa coordinates that remain unadmitted, but a
working numerical interface alone does not admit them. Anatomical binding,
physical transfer and neural conversion still need evidence. Broader expansion
toward42 coordinates, richer sensory input, causal balance and eventually walking
remain the larger goals. No gait script or sensory-to-actuator shortcut substitutes
for neural emergence.

## Current position

| Item | Evidence at this checkpoint |
|---|---|
| Neural motor coverage | **20/42 motor action coordinates admitted**; this is not overall project completion |
| Existing body/sensory work | Prior matched tactile, disturbance and yoke observations are preserved within their recorded conditions |
| Source force/activation checks | Declared source/fixture checks pass; source Euler transient failures remain preserved |
| Native actuator replacement isolation | Selective suppression/preservation passed at the declared fixed inputs, without advancing the fly |
| Endpoint API | Explicit initial/terminal/interior sampling contract independently verified; no tolerance fitted to old residues |
| Synthetic coupled validation | V2 passes the declared same-model numerical/ownership checks using explicit endpoint roles; V1 remains **INTEGRITY_FAILURE**, unchanged |
| Transfer prerequisite inventory | V1 complete; explicit source parameters identified; unsupported conversions remain null |
| Unit/conversion-lineage audit | V1 complete with unresolved result: OpenSim sources and conversion PDF found, exact conversion chain and physical scale unproven; no force multiplier chosen |
| Native LF orientation registration | V1 measured kinematics agree with the modeled map at all15declared poses;196samples in range, no integration/CNS; attachment/length/velocity transfer still unvalidated |
| Source routes / target attachments | Four source paths/eight sites inventoried; native target has no tendons or matching source muscle-site definitions; attachment correspondence remains unresolved; active LF mesh is mirrored RFCoxa |
| Paired endpoint/body-frame observer | V1.1 verifies source endpoint reconstruction, all105source lengths and derivatives;106target frames recorded, no target sites/forces; original V1namespace setup failure preserved |
| Target attachment decision | Current reviewed evidence supports0/8target endpoint correspondences; registration not authorized. Exact reference request prepared; next acquire/qualify independent anatomical or landmark data |
| Moving-fly muscle transfer | Physical units/geometry/velocity/length, raw prerequisites and anatomical/neural conversion remain unresolved gates |
| Independent neural balance/walking | Not established |

## How far until another meaningful Unity test?

The existing20-coordinate runtime is still the existing runtime. Replaying it
would inspect the same interface; these engineering updates do not introduce new
Unity behavior. For a Unity test of the NEW muscle interface, the remaining
sequence is:

1. The transfer inventory and unit-lineage audit are complete; physical scaling
   remains unresolved pending authoritative conversion records. Native target
   orientation now agrees at the declared probes. Source route/attachment audit
   identifies the target endpoint gap. Paired source endpoint and target body-frame
   observations have now validated a geometric observer in V1.1 without
   assigning target muscle sites or choosing physical scale. The registration
   decision now identifies a reference-data requirement: acquire/qualify independent
   anatomical/landmark correspondence tied to the exact source/target assets.
   Further pose sweeps cannot supply that missing authority. Preserve null target
   correspondence while it is missing.
   Resolve source-to-body prerequisites:
   physical units and registered
   geometry/length/velocity dependence, original raw-source requirements, exact
   anatomical population-to-muscle interpretation and neural-to-activation law.
   Reference fidelity does not by itself calibrate biological force or gain.
2. Run a bounded headless native experiment under a predeclared replacement/support
   context, using the existing transition kernel. Record integrity and all outcomes
   before deciding what can be replayed or tested in Unity.
3. Inspect that supported experiment in Unity with a concrete observation goal
   and the relevant matched comparison, rather than expecting a visual change
   from code/reference tests alone.

This is several distinct engineering/research gates. A reliable date or number of
PRs cannot be inferred; unresolved anatomy or physical calibration may require
more evidence and can legitimately remain inconclusive. No promise of a passing
Unity run, a new admission or improved balance follows from an API check.

## Are we moving toward balancing on its own?

Yes, the work supports that goal by making the neural-to-body interface more
defensible. It has not yet demonstrated independent neural balance. The current
body uses engineered position actuators; unadmitted coordinates receive baseline
position-control commands. This assistance can contribute to a stable appearance.
Prior neural intervention results can establish a bounded contribution under their
conditions without establishing independent balance or gait.

A future balance milestone needs predeclared disturbance/recovery measurements,
matched neural enabled/withheld or appropriate yoke controls, verified input/output
boundaries and an explicit mechanical-assistance policy. Merely staying upright,
moving more, or looking as though it is balancing is insufficient. Any change to
support/actuation context must be separately specified and shared where matching
requires it; do not tune neural gains, thresholds or drive until a test passes.

After every run, report: what ran, what its result establishes and cannot establish,
current motor count, active milestone/gate and next concrete step.
