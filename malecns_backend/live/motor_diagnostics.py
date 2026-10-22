"""Bounded, passive summaries of the three Live Fly v3 candidate channels."""
from dataclasses import dataclass
from typing import Any, Mapping


CANDIDATES = ("joint_RFFemur", "joint_LFTarsus1", "joint_RFTarsus1")


@dataclass
class ChannelSummary:
    samples: int = 0
    spikes: int = 0
    positive_steps: int = 0
    negative_steps: int = 0
    raw_steps: int = 0
    final_steps: int = 0
    peak_final_rad: float = 0.0


class CandidateMotorDiagnostics:
    """Count every complete neural record, never retaining a record history.

    Counts describe observed updates, not terminal samples. Missing channels or
    fields are unavailable rather than evidence of silence. Spike counts sum
    the kernel's unique-neuron increments, not population rate estimates.
    """

    def __init__(self):
        self.channels = {name: ChannelSummary() for name in CANDIDATES}
        self.latest: Mapping[str, Any] | None = None

    def observe(self, record: Mapping[str, Any]) -> None:
        self.latest = record
        fields = (
            "per_neuron_spike_increments", "pooled_positive_rate_hz",
            "pooled_negative_rate_hz", "raw_signed_contribution_rad",
            "final_contribution_rad", "population_mean_filtered_rate_hz",
        )
        for name, summary in self.channels.items():
            if not all(name in record.get(field, {}) for field in fields):
                continue
            positive = float(record["pooled_positive_rate_hz"][name])
            negative = float(record["pooled_negative_rate_hz"][name])
            raw = float(record["raw_signed_contribution_rad"][name])
            final = float(record["final_contribution_rad"][name])
            summary.samples += 1
            summary.spikes += sum(int(x) for x in record["per_neuron_spike_increments"][name])
            summary.positive_steps += positive > 0.0
            summary.negative_steps += negative > 0.0
            summary.raw_steps += raw != 0.0
            summary.final_steps += final != 0.0
            summary.peak_final_rad = max(summary.peak_final_rad, abs(final))

    def status_text(self) -> str:
        record = self.latest
        if record is None:
            return ""
        # v1/v2 do not admit these channels. Do not label them silent.
        admitted = record.get("final_contribution_rad", {})
        names = [name for name in CANDIDATES if name in admitted]
        if not names:
            return ""
        parts = []
        for name in names:
            summary = self.channels[name]
            fields = ("pooled_positive_rate_hz", "pooled_negative_rate_hz",
                      "raw_signed_contribution_rad", "population_mean_filtered_rate_hz",
                      "per_neuron_spike_increments")
            label = name.removeprefix("joint_")
            if not all(name in record.get(field, {}) for field in fields):
                parts.append(f"{label}(unavailable samples={summary.samples})")
                continue
            populations = ",".join(
                f"{population}={float(rate):.3g}"
                for population, rate in record["population_mean_filtered_rate_hz"][name].items()
            )
            parts.append(
                f"{label}(pos_hz={float(record['pooled_positive_rate_hz'][name]):.3g} "
                f"neg_hz={float(record['pooled_negative_rate_hz'][name]):.3g} "
                f"raw_rad={float(record['raw_signed_contribution_rad'][name]):+.3g} "
                f"final_rad={float(admitted[name]):+.3g} "
                f"samples={summary.samples} spikes={summary.spikes} "
                f"pos_steps={summary.positive_steps} neg_steps={summary.negative_steps} "
                f"raw_steps={summary.raw_steps} final_steps={summary.final_steps} "
                f"peak_final_rad={summary.peak_final_rad:.3g} populations=[{populations}])"
            )
        return "candidates=[" + "; ".join(parts) + "]"
