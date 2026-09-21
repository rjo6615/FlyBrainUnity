# M9A-2 — physics-only perturbation calibration escalation

M9A-2 is a new output namespace. M9A Attempt 1 evidence is immutable and is
verified byte-for-byte before preflight. M7D/M8 initialization remains frozen.
MaleCNS is neither constructed nor advanced, and M9B has no execution route.

## Preregistered rationale and sweep

Attempt 1 applied 0.0001, 0.0002, 0.0004, and 0.0008 native force units. Its
responses were effectively invariant: approximately 0.002774 mm maximum root
displacement, 0.055924 degrees maximum tilt, no authoritative contact-pattern
change, and no fall or rollover. Using only that physical evidence, M9A-2
freezes a coarse factor-four logarithmic sweep:

**0.002, 0.008, 0.032, and 0.128 native force units**, in that order.

The first value is 2.5 times Attempt 1's ceiling; each next value is four times
the preceding value. This deliberately searches orders of magnitude rather
than tuning incrementally or reacting to outcomes. All values and their order
are frozen in the preregistration before any candidate is executed.

## Frozen procedure and selection

Each fresh candidate uses the exact inherited physical initialization and fixed
baseline actuator semantics. A direct `data.xfrc_applied` force targets the
unique authoritative source body `Thorax`, resolved by the exact final
slash-delimited component of its compiled name (for example `0/Thorax` or
`1/Thorax`), in
world +Y with zero torque, for exactly 200 outgoing 0.1 ms transitions from
500 ms inclusive to 520 ms exclusive. Observation lasts 1500 ms. Authoritative
six-leg ground contacts and distal-tarsus positions are recorded.

The original criteria are unchanged. A qualifying candidate must be finite,
cause no fall or rollover by 600 ms, remain at or below 1.5 mm maximum root
displacement and 60 degrees maximum tilt, cause an authoritative contact
pattern change, produce at least 0.05 mm displacement or 5 degrees tilt, and
reduce displacement or tilt deviation by at least 25% in the 1250–1500 ms late
window. The lowest qualifying preregistered magnitude is selected. If none
qualifies, selection fails closed.

No gait, balance, stabilization, adhesion scheduling, AI, RL, reward, reference
trajectory, scripted neural stimulation, outcome-dependent control, or hidden
assistance is permitted. M9A-2 establishes only external physical perturbation
calibration; it cannot establish neural or biological recovery.

## Authorization boundary

Codex must run only zero-transition/unit tests. After review, the separately
authorized pinned Windows commands are:

```powershell
python -m malecns_backend.embodiment.m9a_2_perturbation_calibration --windows-preflight
python -m malecns_backend.embodiment.m9a_2_perturbation_calibration --run-windows
```

The live command writes exclusively under
`interface_output/m9a_2_perturbation_calibration` and refuses overwrite. Do not
run it before authorization. M9B remains prohibited regardless of outcome.
