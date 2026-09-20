"""Immutable M7 values shared by execution and post-run analysis.

This module must remain data-only so evidence inspection does not acquire a
transitive dependency on the scientific runner.
"""
from types import MappingProxyType

CONDITIONS = ("SPONTANEOUS_NEURAL_EMBODIMENT", "ALL_NEURAL_MOTOR_DISABLED")

THRESHOLDS = MappingProxyType({
    "joint_divergence_rad": 1e-6,
    "com_displacement_m": 1e-6,
    "orientation_divergence_rad": 1e-6,
    "height_divergence_m": 1e-6,
    "oscillation_prominence_rad": 1e-4,
    "oscillation_min_extrema": 3,
    "rollover_body_up_z_max": 0.0,
    "fall_height_fraction": 0.5,
})
