# Hair-plate Step B — CxHP8-like coxa forward-limit encoder (V1)

Preregistered 2026-11-01 (`evidence/hair-plate-encoder-v1/protocol.json`, SHA-256 locked in
`malecns_backend/embodiment/hair_plate_encoder.py`). Static validation only: no CNS or
physics experiment.

- Neurons: Step A's SNpp45 sets per leg (T1 VProN, T2 MesoLN, T3 MetaLN, by side).
- Signal: forward component of the coxa long axis (coxa origin to femur origin) in the
  Thorax frame; +x is checked to be anterior (towards the Head). This avoids choosing a
  FlyGym coxa coordinate or sign.
- Tuning: tonic and one-sided, as published for CxHP8. Per leg, the threshold is the 90th
  percentile and saturation the maximum of the forward component over the recorded
  real-fly untethered walking step shipped with FlyGym 1.2.1, replayed through our body's
  kinematics; rate = 120 Hz x clip((f - theta)/(f_max - theta), 0, 1) for every neuron of
  the leg. 120 Hz is the existing encoders' engineering maximum.
- Checks: identity equals Step A, threshold below saturation, 5-15% of recorded poses
  active, monotonic tuning, finite rest-pose rate. Descriptive: which coxa coordinate and
  sign moves the coxa forward. Verdict ENCODER_READY / NOT_READY / INCONCLUSIVE.

Limits: modeled transduction from one recorded step; uniform rate ignores hair-by-hair
recruitment; delivery into the CNS is Step C. Results: `HAIR_PLATE_ENCODER_RESULTS.md`.
