# Milestone 4B-1 — Six-tibia interface validation

This milestone loads the audited 4A anatomy without rediscovery and validates one tibia at a time. It does **not** provide simultaneous neural control, walking, gait/CPG coordination, descending drive, or a behavior controller.

## Authoritative inventory

### LF — T1 left

- **Sensor (EXACT):** `chordotonal T1 left` — 23 neurons — body IDs `135305, 142571, 248280, 815569, 815843, 817298, 817680, 817839, 902324, 902359, 903843, 905037, 905335, 905339, 905340, 906290, 906558, 906823, 911316, 912317, 914116, 935383, 935541`.
- **Actuator:** `joint_LFTibia`, action index 5, range [-1.35, 1.3] rad (`PHYSICS_MEASURED`).
- **Motor confidence:** **SUPPORTED**. Active antagonist decoding is supported by explicit audited +1/-1 directions.
  - `Acc. ti flexor MN T1 left`: flexor / negative actuator direction; body IDs `806599, 815246, 816215, 816404, 817283, 819869, 825516, 867630, 903298, 1050115387` (`ANNOTATION_DERIVED`).
  - `Ti extensor MN T1 left`: extensor / positive actuator direction; body IDs `800636, 815344` (`ANNOTATION_DERIVED`).
  - `Ti flexor MN T1 left`: flexor / negative actuator direction; body IDs `807165, 809912, 818057, 819384, 909831` (`ANNOTATION_DERIVED`).

### LM — T2 left

- **Sensor (EXACT):** `chordotonal T2 left` — 80 neurons — body IDs `112864, 114917, 149788, 341116, 807595, 807785, 807860, 807931, 807970, 808077, 808491, 808512, 808757, 808822, 808826, 809102, 809230, 809250, 809398, 809476, 809976, 810085, 811112, 811348, 811608, 811889, 812705, 812744, 812951, 813009, 813126, 813349, 813500, 813850, 814251, 814335, 814612, 814775, 814905, 814949, 815325, 817150, 817792, 817992, 817993, 819193, 819619, 819822, 821654, 822336, 824332, 824431, 828811, 902316, 904740, 905218, 905219, 905239, 905242, 905243, 906269, 908146, 908214, 908702, 909477, 909478, 910015, 910446, 910836, 911075, 911942, 912309, 912703, 912704, 912926, 936028, 936168, 1052290937, 1053563856, 1061501467`.
- **Actuator:** `joint_LMTibia`, action index 12, range [-1.35, 1.3] rad (`PHYSICS_MEASURED`).
- **Motor confidence:** **EXACT**. Active antagonist decoding is supported by explicit audited +1/-1 directions.
  - `Ti extensor MN T2 left`: extensor / positive actuator direction; body IDs `800911, 801234` (`ANNOTATION_DERIVED`).
  - `Ti flexor MN T2 left`: flexor / negative actuator direction; body IDs `802295, 818295, 823739, 824041, 927808` (`ANNOTATION_DERIVED`).

### LH — T3 left

- **Sensor (EXACT):** `chordotonal T3 left` — 93 neurons — body IDs `129014, 242782, 258676, 266941, 802350, 804010, 806934, 808015, 808417, 808818, 809932, 809969, 810173, 810526, 811124, 811540, 811959, 812422, 812454, 812610, 812934, 812984, 813450, 813644, 813693, 813911, 814484, 814628, 815423, 815697, 815926, 815974, 816388, 816498, 816580, 816764, 817112, 817819, 817913, 818186, 818466, 818712, 818714, 818772, 818896, 818960, 819005, 819219, 819410, 819500, 819633, 819645, 820328, 820681, 821947, 824254, 825749, 826324, 827773, 828667, 828868, 829386, 830558, 846679, 903209, 903377, 903986, 908529, 908533, 908534, 908535, 908723, 908804, 908806, 908816, 909035, 909036, 909240, 910401, 910406, 910408, 910413, 910819, 912852, 932861, 933250, 936408, 936785, 937492, 939462, 942680, 1058841949, 1066481166`.
- **Actuator:** `joint_LHTibia`, action index 19, range [-1.35, 1.3] rad (`PHYSICS_MEASURED`).
- **Motor confidence:** **SUPPORTED**. Active antagonist decoding is supported by explicit audited +1/-1 directions.
  - `Acc. ti flexor MN T3 left`: flexor / negative actuator direction; body IDs `817374, 829873, 843389, 934519, 1050003192, 1050123559, 1050233038, 1050263576` (`ANNOTATION_DERIVED`).
  - `Ti extensor MN T3 left`: extensor / positive actuator direction; body IDs `800621, 812953` (`ANNOTATION_DERIVED`).
  - `Ti flexor MN T3 left`: flexor / negative actuator direction; body IDs `803147, 804919, 819112, 822945, 908762, 929376, 1050088257, 1050100010, 1050166426` (`ANNOTATION_DERIVED`).

### RF — T1 right

- **Sensor (EXACT):** `chordotonal T1 right` — 13 neurons — body IDs `107573, 262161, 556667, 816782, 817154, 817245, 817825, 826042, 833439, 905668, 912365, 913052, 933556`.
- **Actuator:** `joint_RFTibia`, action index 26, range [-1.35, 1.3] rad (`PHYSICS_MEASURED`).
- **Motor confidence:** **SUPPORTED**. Active antagonist decoding is supported by explicit audited +1/-1 directions.
  - `Acc. ti flexor MN T1 right`: flexor / negative actuator direction; body IDs `817509, 833140, 837745, 909713, 1050005026, 1050091581, 1050126678, 1050156705, 1050268065` (`ANNOTATION_DERIVED`).
  - `Ti extensor MN T1 right`: extensor / positive actuator direction; body IDs `804257, 815678` (`ANNOTATION_DERIVED`).
  - `Ti flexor MN T1 right`: flexor / negative actuator direction; body IDs `810098, 821635, 827188, 1050031705, 1050189039` (`ANNOTATION_DERIVED`).

### RM — T2 right

- **Sensor (EXACT):** `chordotonal T2 right` — 83 neurons — body IDs `104602, 111523, 113192, 119972, 804542, 805328, 807064, 807900, 807915, 808016, 808082, 808136, 808463, 808529, 808576, 808697, 809027, 809353, 809904, 810041, 810445, 811313, 811456, 811532, 811919, 812275, 813417, 813516, 814108, 814221, 814297, 814342, 814466, 814699, 814742, 815766, 815798, 816304, 816362, 816665, 819655, 820887, 821240, 822285, 822321, 823267, 823935, 824367, 824940, 825449, 826386, 830907, 832162, 832415, 875542, 902550, 903831, 905052, 905796, 906018, 908166, 908603, 908773, 908774, 909548, 909549, 910306, 910391, 910632, 910829, 910830, 911307, 911780, 912510, 913881, 913882, 913886, 913890, 913891, 919643, 933121, 936031, 1065618685`.
- **Actuator:** `joint_RMTibia`, action index 33, range [-1.35, 1.3] rad (`PHYSICS_MEASURED`).
- **Motor confidence:** **SUPPORTED**. Active antagonist decoding is supported by explicit audited +1/-1 directions.
  - `Acc. ti flexor MN T2 right`: flexor / negative actuator direction; body IDs `805568, 812531, 905235, 907848, 909255, 1052521030` (`ANNOTATION_DERIVED`).
  - `Ti extensor MN T2 right`: extensor / positive actuator direction; body IDs `830514, 928579` (`ANNOTATION_DERIVED`).
  - `Ti flexor MN T2 right`: flexor / negative actuator direction; body IDs `804405, 805010, 816222, 822013, 903363` (`ANNOTATION_DERIVED`).

### RH — T3 right

- **Sensor (EXACT):** `chordotonal T3 right` — 100 neurons — body IDs `86060, 105298, 113457, 218015, 804744, 805712, 806491, 806526, 806695, 806859, 807459, 807805, 808592, 808807, 808991, 809120, 809278, 809375, 809595, 810187, 810234, 810643, 810683, 810800, 810876, 810980, 811189, 811266, 811516, 811643, 811808, 811841, 811918, 811967, 812049, 812117, 812228, 812527, 812659, 812848, 812869, 812871, 812928, 813011, 813147, 813172, 813185, 813286, 814486, 814658, 814806, 814843, 814881, 815497, 815864, 815949, 816536, 817331, 817356, 817657, 818182, 818362, 818478, 818930, 818992, 819134, 819524, 819559, 819951, 820818, 820903, 821363, 821461, 822523, 822975, 823347, 824107, 828434, 847034, 855317, 903471, 903726, 905526, 905633, 907742, 907744, 908277, 908278, 908862, 909318, 909379, 909726, 909836, 910042, 912413, 912444, 914543, 915047, 932315, 936153`.
- **Actuator:** `joint_RHTibia`, action index 40, range [-1.35, 1.3] rad (`PHYSICS_MEASURED`).
- **Motor confidence:** **SUPPORTED**. Active antagonist decoding is supported by explicit audited +1/-1 directions.
  - `Acc. ti flexor MN T3 right`: flexor / negative actuator direction; body IDs `801637, 813629, 910296, 1050032839, 1050160514, 1050202461, 1050460102, 1059707690` (`ANNOTATION_DERIVED`).
  - `Ti extensor MN T3 right`: extensor / positive actuator direction; body IDs `800158, 809935` (`ANNOTATION_DERIVED`).
  - `Ti flexor MN T3 right`: flexor / negative actuator direction; body IDs `803072, 808685, 823665, 827968, 840740, 910178, 1050013311, 1050303231` (`ANNOTATION_DERIVED`).

## Component validation

- The existing `SensoryEncoder` is reused unchanged: ordered Gaussian population code, normalized width 0.25, maximum 120 Hz, and 5 Hz cutoff. Population length is read from each audited sensor record.
- The existing `MotorActivityObserver` and `MotorDecoder` equations are reused unchanged: cumulative-count increments, Hz, 40 ms low-pass, population mean, 17 Hz half-activation, signed antagonism, and 0.25 rad offset.
- Supported tibiae pool only populations carrying the same explicit audited direction. The `SUPPORTED` confidence is retained; it is never promoted to `EXACT`.
- Each `IsolatedTibiaDecoder` owns its observer, filter, cumulative-count baseline, and previous actuator target. `SixTibiaIsolation.select()` constructs exactly one such decoder. There is no multi-interface actuation API.
- Decoder-only sign tests use prominently identified `ENGINEERED_DEBUG_INPUT`; these counts are not biological observations.

## M3D reference and actuator safety

LM retains `chordotonal T2 left` (80), `Ti extensor MN T2 left` (800911, 801234), `Ti flexor MN T2 left` (802295, 818295, 823739, 824041, 927808), `joint_LMTibia`, and action index 12. Tests compare its indices and sensory rates, spike increments and filtered rates, antagonist activation/offset, and final actuator command against the independent M3D classes with exact deterministic equality.

The common decoder retains measured-position synchronization, the [-1.35, 1.30] rad tibia range, 4 rad/s slew, 1 ms control interval, and position actuation. No scientific/model constant, neural weight, threshold, stochastic drive, or neural state is changed.

## Running the non-intervening audit

```bash
python -m malecns_backend.embodiment.six_tibia_audit --check
```

The audit prints six inventory rows, component results, LM/M3D equivalence, cross-leg isolation, and explicit negative-scope confirmations. The optional real-body experiment was not implemented because it depends on a configured FlyGym environment; therefore there are no biological silence/subthreshold or physical-displacement claims in this component milestone.
