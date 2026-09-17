# Milestone 3B experiment report

**Report date:** 2026-09-17
**Status:** implementation/component validation complete; real NeuroMechFly
experiment blocked in the validation container because neither `flygym` nor
`mujoco` is installed and network installation is unavailable. No fake body
result is reported as a closed-loop experiment.

1. **Selected leg/joint.** Left T2 (FlyGym LM) tibia/femur-tibia joint.
2. **Why selected.** The 3A map provides an 80-cell angle population and
   explicit flexor/extensor motor antagonists with the same side and actuator,
   making it stronger than pathways lacking an antagonist or physical match.
3. **Sensory population.** `chordotonal T2 left`, 80 neurons, audited
   `tibia_T2_left` target (**ANNOTATION_DERIVED**).
4. **Motor populations.** `Ti extensor MN T2 left` (`dir=+1`, two cells) and
   `Ti flexor MN T2 left` (`dir=-1`, five cells), both
   **ANNOTATION_DERIVED**.
5. **Exact MaleCNS body IDs.** Sensor:
   `112864, 114917, 149788, 341116, 807595, 807785, 807860, 807931, 807970,
   808077, 808491, 808512, 808757, 808822, 808826, 809102, 809230, 809250,
   809398, 809476, 809976, 810085, 811112, 811348, 811608, 811889, 812705,
   812744, 812951, 813009, 813126, 813349, 813500, 813850, 814251, 814335,
   814612, 814775, 814905, 814949, 815325, 817150, 817792, 817992, 817993,
   819193, 819619, 819822, 821654, 822336, 824332, 824431, 828811, 902316,
   904740, 905218, 905219, 905239, 905242, 905243, 906269, 908146, 908214,
   908702, 909477, 909478, 910015, 910446, 910836, 911075, 911942, 912309,
   912703, 912704, 912926, 936028, 936168, 1052290937, 1053563856,
   1061501467`. Extensor: `800911, 801234`. Flexor:
   `802295, 818295, 823739, 824041, 927808`.
6. **NeuroMechFly sensor.** LM tibia position in radians from the `joints`
   observation (**PHYSICS_MEASURED**). No contact/load channel is encoded in
   this first pathway.
7. **NeuroMechFly actuator.** Position action element 12,
   `joint_LMTibia`; this cross-system correspondence is modeled/engineered.
8. **Sensory transduction.** Ordered Gaussian population code, `[-1.35,1.30]`
   rad normalization, width `0.25`, `120 Hz` peak, values `<=5 Hz` set to zero,
   no extra baseline. Rates enter the normal stochastic MaleCNS external path
   (**MODELED_TRANSDUCTION**).
9. **Motor decoding.** Cumulative count increments → Hz → per-cell Euler
   low-pass (`tau=40 ms`) → population means → half-17-Hz saturation →
   extensor-minus-flexor position offset (**MODELED_MOTOR_DECODING**).
10. **Timing.** Neural `0.5 ms`; physics `0.1 ms`; control, sensory, and motor
    `1.0 ms`; causal order is observe, encode, two neural steps, decode,
    command, ten subsequent physics steps.
11. **Safety.** Joint range `[-1.35,1.30] rad`, offset `±0.25 rad`, slew
    `4 rad/s`; engineering constraints only.
12. **Baseline result.** **NOT RUN** on NeuroMechFly due to the dependency
    incompatibility above; no locomotion inference is made.
13. **Sensory-only result.** Component checks show finite bounded rates and
    stimulation of only the 80 audited indices. The real MaleCNS + body test is
    **NOT RUN** here.
14. **Motor-isolation result.** An explicitly labeled **ENGINEERED DEBUG
    INPUT** count increment changes filtered extensor Hz and only emits the LM
    tibia command. The real FlyGym actuator response is **NOT RUN** here.
15. **Closed-loop result.** **NOT RUN**; no fake body result is substituted.
16. **Causal control.** Not applicable because Test 4 produced no real result.
17. **Scientific outcome A/B/C.** **Unclassified / NOT RUN.** A/B/C applies
    only after a real NeuroMechFly Test 4; absence of the dependency is not C.
18. **CNS numerical health.** Component values are finite. Full-CNS health for
    this experiment is not measured in this container.
19. **Body numerical health.** Not measured because NeuroMechFly did not run.
20. **Performance.** Component wall time and RSS are printed by `audit`.
    Neural steps/s, physics steps/s, simulated time, real-time factor, and real
    run RAM remain unmeasured until the real experiment runs.
21. **Modeled assumptions.** FlyGym LM corresponds to anatomical T2-left;
    action element 12 is LM tibia; reference angle coordinates can be used
    without an offset/sign calibration; motor force-frequency saturation can
    parameterize a position offset; the two selected annotated pools suffice;
    arithmetic population means are appropriate; clamps are safe.
22. **Unresolved biology/mapping.** Coordinate-frame calibration, moment arms,
    force constants, muscle recruitment, passive joint mechanics, whether the
    small selected pools cover all tibia muscles, and FlyGym position-control
    equivalence to biological muscle actuation are unresolved.
23. **Behavior controller/state machine participated?** **NO.** Neither old
    brain, old behavior bridge, CPG, gait, Unity, nor root translation is
    imported or invoked.

## Reproduction/blocker

`python -m malecns_backend.embodiment.audit --run-real` exits with a precise
blocker if FlyGym is absent. In this container, `python` is 3.14.4,
`import flygym` and `import mujoco` fail, and the configured package index is
unreachable (HTTP tunnel 403). The implementation does not rewrite FlyGym or
silently use the unit-test `FakeBody`.
