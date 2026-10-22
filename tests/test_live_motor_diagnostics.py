"""Passive candidate telemetry regressions; no neural/physics runtime."""
import copy
from io import StringIO
import importlib.util
from pathlib import Path
import sys
from types import MappingProxyType, ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


PATH = Path(__file__).resolve().parents[1] / "malecns_backend/live/motor_diagnostics.py"
spec = importlib.util.spec_from_file_location("candidate_diagnostics_test_module", PATH)
diagnostics = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = diagnostics
spec.loader.exec_module(diagnostics)
NAME = diagnostics.CANDIDATES[0]


def record(positive=0., negative=0., raw=0., final=0., spikes=(0, 0)):
    return {
        "neural_transition_index": 1,
        "pooled_positive_rate_hz": {NAME: positive},
        "pooled_negative_rate_hz": {NAME: negative},
        "raw_signed_contribution_rad": {NAME: raw},
        "final_contribution_rad": {NAME: final},
        "per_neuron_spike_increments": {NAME: spikes},
        "population_mean_filtered_rate_hz": {NAME: {"positive pool": positive, "negative pool": negative}},
    }


class CandidateDiagnosticsTests(unittest.TestCase):
    def test_silent_complete_records_are_distinct_from_missing_channels(self):
        observer = diagnostics.CandidateMotorDiagnostics()
        self.assertEqual(observer.status_text(), "")
        observer.observe(record())
        summary = observer.channels[NAME]
        self.assertEqual((summary.samples, summary.spikes, summary.final_steps), (1, 0, 0))
        self.assertIn("RFFemur(pos_hz=0", observer.status_text())
        self.assertNotIn("LFTarsus1", observer.status_text())
        observer.observe({"final_contribution_rad": {NAME: 0.}})
        self.assertIn("unavailable samples=1", observer.status_text())
        observer.observe({"final_contribution_rad": {"joint_LMTibia": .1}})
        self.assertEqual(observer.status_text(), "")

    def test_brief_activity_survives_later_silent_terminal_sample(self):
        observer = diagnostics.CandidateMotorDiagnostics()
        observer.observe(record(positive=10., raw=-.05, final=-.02, spikes=(1, 2)))
        observer.observe(record())
        summary = observer.channels[NAME]
        self.assertEqual((summary.samples, summary.spikes, summary.positive_steps,
                          summary.negative_steps, summary.raw_steps, summary.final_steps),
                         (2, 3, 1, 0, 1, 1))
        self.assertEqual(summary.peak_final_rad, .02)
        self.assertIn("final_rad=+0", observer.status_text())
        self.assertIn("final_steps=1 peak_final_rad=0.02", observer.status_text())

    def test_cancelling_pools_and_suppressed_output_remain_distinguishable(self):
        observer = diagnostics.CandidateMotorDiagnostics()
        observer.observe(record(positive=10., negative=10., spikes=(1, 1)))
        observer.observe(record(positive=12., raw=-.1, final=0., spikes=(1, 0)))
        summary = observer.channels[NAME]
        self.assertEqual((summary.spikes, summary.positive_steps, summary.negative_steps,
                          summary.raw_steps, summary.final_steps), (3, 2, 1, 1, 0))
        self.assertIn("positive pool=12", observer.status_text())

    def test_observation_is_read_only_and_storage_stays_bounded(self):
        source = record(positive=5., raw=.01, final=.01, spikes=(1, 0))
        before = copy.deepcopy(source)
        def freeze(value):
            if isinstance(value, dict):
                return MappingProxyType({key: freeze(item) for key, item in value.items()})
            return value
        frozen = freeze(source)
        observer = diagnostics.CandidateMotorDiagnostics()
        for _ in range(1000):
            observer.observe(frozen)
        self.assertEqual(source, before)
        self.assertEqual(len(observer.channels), 3)
        self.assertIs(observer.latest, frozen)
        self.assertEqual(observer.channels[NAME].samples, 1000)
        self.assertEqual(observer.channels[NAME].spikes, 1000)

    def test_headless_wiring_counts_neural_only_and_reports_at_shutdown(self):
        # Load the actual runner; stub only its ScientificSession type import.
        modules = {name: ModuleType(name) for name in (
            "malecns_backend", "malecns_backend.live", "malecns_backend.embodiment",
            "malecns_backend.embodiment.scientific_session")}
        modules["malecns_backend.embodiment.scientific_session"].ScientificSession = object
        modules["malecns_backend.live.motor_diagnostics"] = diagnostics
        name = "malecns_backend.live.headless"
        spec = importlib.util.spec_from_file_location(name, PATH.with_name("headless.py"))
        headless = importlib.util.module_from_spec(spec)
        modules[name] = headless
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(headless)
        telemetry = headless.LatestLiveTelemetry()
        telemetry({"physics_transition_index": 1})
        self.assertEqual(telemetry.candidate_diagnostics.channels[NAME].samples, 0)
        telemetry(record(positive=2., raw=.01, final=.01, spikes=(1, 0)))
        telemetry(record())
        self.assertEqual(telemetry.neural_records, 2)
        self.assertIn("final_steps=1", telemetry.status_text())
        session = SimpleNamespace(
            initialize=lambda: SimpleNamespace(time_ms=0.),
            step=lambda **kwargs: SimpleNamespace(time_ms=.1, physics_transitions=1,
                neural_transitions=2, root_position_xyz=(0., 0., 0.), finite=True),
            close=lambda: None,
        )
        output = StringIO()
        headless.run(session_factory=lambda: session, max_transitions=1,
                     clock=lambda: 0., output=output, live_telemetry=telemetry)
        self.assertIn("LIVE final candidates=[", output.getvalue())
        self.assertIn("samples=2 spikes=1", output.getvalue())


if __name__ == "__main__":
    unittest.main()
