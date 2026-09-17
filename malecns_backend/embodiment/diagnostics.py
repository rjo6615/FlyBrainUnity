"""Measured classification rules for the closed-loop diagnostic milestone."""
from dataclasses import dataclass


@dataclass(frozen=True)
class OutcomeCriteria:
    meaningful_body_response_rad: float = 1e-8

    def classify(self, motor_spikes, nonsensory_spikes, final_joint_change_rad):
        if motor_spikes > 0 and final_joint_change_rad > self.meaningful_body_response_rad:
            return "A. SENSORIMOTOR PROPAGATION OBSERVED"
        if nonsensory_spikes > 0:
            return "B. NEURAL PROPAGATION WITHOUT MEANINGFUL BODY RESPONSE"
        return "C. NO RELEVANT PROPAGATION"


OUTCOME_CRITERIA = OutcomeCriteria()


def classify_weak_link(metrics, response_epsilon_rad=1e-12):
    """Locate the earliest absent/measurably weak stage; never infer activity."""
    if metrics["sensory_spikes"] == 0:
        return "S0", "none of the targeted sensory neurons generated a spike"
    if metrics["nonsensory_spikes"] == 0:
        return "S1", "sensory neurons spiked but no non-sensory neuron spiked"
    if metrics["motor_spikes"] == 0:
        return "S2", "non-sensory network spikes occurred but no annotated motor neuron spiked"
    if metrics["peak_antagonist_signal"] <= 0.0:
        return "S3", "annotated motor neurons spiked but the measured antagonist signal was zero"
    if metrics["peak_raw_motor_command_rad"] <= response_epsilon_rad:
        return "S4", "motor activity reached the decoder but its measured raw output was negligible"
    if (metrics["peak_final_motor_command_rad"] > response_epsilon_rad and
            metrics["max_displacement_rad"] <= response_epsilon_rad):
        return "S5", "a nonzero final command reached the body but no measurable joint response followed"
    if metrics["max_displacement_rad"] <= OUTCOME_CRITERIA.meaningful_body_response_rad:
        return "S6", "a physical response was measured but stayed below the outcome threshold"
    return "UNRESOLVED", "every measured stage was nonzero; finer causal measurements are required"
