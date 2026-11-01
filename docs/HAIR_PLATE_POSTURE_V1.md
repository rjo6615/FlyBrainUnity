# Hair-plate Step C — posture sensitivity with SNpp45 input (V1)

Preregistered 2026-11-01 (`evidence/hair-plate-posture-v1/protocol.json`, SHA-256 locked in
`malecns_backend/live/hair_plate_posture.py`). Four fresh-process arms, one seed, 2 s each:
posture held (A) or released by zeroing the same 22 baseline-only servo rows as V1.2 after
state 5005 (R), with the Step B hair-plate encoder delivering input (ON) or withheld at the
CNS boundary with identical RNG draws (OFF). The live-v3 kernel, 20 motor channels and tibia
proprioception are unchanged; the input boundary follows `live.tactile_boundary`.

Q1 POSTURE_SENSITIVE if the ON held-vs-released difference in mean coxa-MN rate (cleared
window 520-2000 ms) is at least twice the OFF difference and at least 0.5 Hz. Q2
REFLEX_DIRECTION_CONSISTENT if, in held arms, ON raises posterior-moving coxa MN rates and
by more than anterior ones. Integrity (complete arms, common RNG, A/R prefix through state
5005, declared row write, delivery only in ON) gates any label.

An implementation smoke test (50 physics steps, intervention moved to step 20, nothing
saved) ran before commit to check wiring; it is not evidence.
Results: `HAIR_PLATE_POSTURE_RESULTS.md`.
