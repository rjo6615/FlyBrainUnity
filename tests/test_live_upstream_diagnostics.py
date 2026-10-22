"""Readout checks and deterministic A/B proof on the real LIF runtime."""
import copy
import json
from types import SimpleNamespace
import unittest
from contextlib import ExitStack
from unittest.mock import patch

import numpy as np

from malecns_backend.neural import MaleCNSBrain, ModelConfig
from malecns_backend.embodiment.motor import MotorActivityObserver
from malecns_backend.embodiment._windows_m8_live_condition import _readonly_telemetry
from malecns_backend.live.upstream_diagnostics import CandidateUpstreamProbe, report_json, status_text
from malecns_backend.live import headless


NAME = "joint_RFFemur"
DEFINITIONS = {NAME: {"positive_populations": {"P": (103,)},
                      "negative_populations": {"N": (104,)}}}


def fixture():
    data = SimpleNamespace(
        neuron_count=4, row_ptr=np.array([0, 2, 3, 3, 3]),
        target_indices=np.array([2, 3, 2]), synapse_counts=np.array([6, 4, 6]),
        neuron_sizes=np.ones(4), nt_signs=np.array([1., -1., 1., 1.]),
        neurotransmitter_ids=np.array([1, 2, 1, 1]),
        superclass_ids=np.zeros(4, dtype=int), superclasses=["central"],
        class_ids=np.zeros(4, dtype=int), classes=["other"], types=["x"] * 4,
        body_ids=np.array([101, 102, 103, 104]), body_id_to_index={101: 0, 102: 1, 103: 2, 104: 3},
    )
    config = ModelConfig(min_synapses=6, psp_scale=1., inhibitory_gain=1.,
                         size_alpha=0., neuromodulation=False)
    brain = MaleCNSBrain(data, config)
    observer = MotorActivityObserver({"P": (2,), "N": (3,)})
    observer.reset(brain.spike_counts)
    channels = {NAME: {"populations": {"P": (2,), "N": (3,)}, "observer": observer}}
    return brain, channels


class UpstreamDiagnosticsTests(unittest.TestCase):
    def test_exact_identity_and_effective_edge_orientation(self):
        brain, channels = fixture()
        probe = CandidateUpstreamProbe(brain, channels, DEFINITIONS)
        p, n = probe.rows[NAME]
        self.assertEqual((p["body_id"], p["dense_index"]), (103, 2))
        self.assertEqual((p["incoming_edges"], p["effective_exc_edges"], p["effective_inh_edges"]), (2, 1, 1))
        self.assertEqual((n["incoming_edges"], n["effective_exc_edges"], n["effective_inh_edges"]), (1, 0, 0))

    def test_mapping_mismatches_fail_closed(self):
        for kind in ("body", "population", "observer"):
            with self.subTest(kind=kind):
                brain, channels = fixture()
                if kind == "body":
                    brain.data.body_ids[2] = 999
                elif kind == "population":
                    channels[NAME]["populations"]["P"] = (1,)
                else:
                    channels[NAME]["observer"].used = np.array([2])
                with self.assertRaisesRegex(RuntimeError, "mismatch"):
                    CandidateUpstreamProbe(brain, channels, DEFINITIONS)

    def test_raw_counts_are_checked_against_observer(self):
        brain, channels = fixture()
        probe = CandidateUpstreamProbe(brain, channels, DEFINITIONS)
        brain.spike_counts[2] = 1
        with self.assertRaisesRegex(RuntimeError, "readout mismatch"):
            probe.sample(brain)

    def test_real_runtime_dynamics_and_rng_identical_with_probe(self):
        plain, plain_channels = fixture()
        watched, channels = fixture()
        probe = CandidateUpstreamProbe(watched, channels, DEFINITIONS)
        for brain in (plain, watched):
            brain.set_external_drive([0, 1], 2000.)
        first = None
        for _ in range(30):
            np.testing.assert_array_equal(plain.step(), watched.step())
            plain_channels[NAME]["observer"].update(plain.spike_counts, plain.config.dt)
            channels[NAME]["observer"].update(watched.spike_counts, watched.config.dt)
            state = probe.sample(watched)
            if first is None:
                first = copy.deepcopy(state)
            for field in ("v", "g_exc", "g_inh", "refractory", "adaptation", "spike_counts",
                          "external_drive", "weights", "pre_sign", "depression_resource"):
                np.testing.assert_array_equal(getattr(plain, field), getattr(watched, field))
            self.assertEqual(plain.rng.bit_generator.state, watched.rng.bit_generator.state)
        row = state["channels"][NAME][0]
        self.assertGreater(row["peak_abs_g_exc"], 0.)
        self.assertGreater(row["peak_abs_g_inh"], 0.)
        self.assertGreater(row["exc_steps"], 0)
        self.assertEqual(first["samples"], 1)
        self.assertEqual(probe.samples, 30)
        self.assertEqual(len(probe.rows[NAME]), 2)
        self.assertEqual(state["channels"][NAME][1]["min_post_step_threshold_gap"], 7.)
        frozen = _readonly_telemetry(state)
        self.assertEqual(json.loads(report_json(frozen))["samples"], 30)
        self.assertIn("identity=verified readout=verified", status_text(frozen))

    def test_headless_periodic_and_shutdown_reports(self):
        brain, channels = fixture()
        state = CandidateUpstreamProbe(brain, channels, DEFINITIONS).sample(brain)
        telemetry = headless.LatestLiveTelemetry()
        telemetry({"neural_transition_index": 1, "candidate_upstream_state": _readonly_telemetry(state)})
        self.assertIn("upstream_samples=1", telemetry.status_text())
        from io import StringIO
        output = StringIO()
        session = SimpleNamespace(initialize=lambda: SimpleNamespace(time_ms=0.), close=lambda: None)
        headless.run(session_factory=lambda: session, max_transitions=0,
                     clock=lambda: 0., output=output, live_telemetry=telemetry)
        self.assertIn('LIVE final upstream={', output.getvalue())
        self.assertIn('"body_id": 103', output.getvalue())

    def test_v3_factory_probe_is_opt_in_and_requires_observer(self):
        base = "malecns_backend.embodiment."
        with ExitStack() as stack:
            stack.enter_context(patch(base + "_windows_m7d_corrected_spontaneous_adapter._protocol",
                                      return_value=({}, [], [])))
            stack.enter_context(patch(base + "live_v2_motor_interface.derive_v2", return_value=({}, [], [])))
            stack.enter_context(patch(base + "live_v3_motor_interface.derive_v3", return_value=({}, [], [])))
            create = stack.enter_context(patch(base + "_windows_m8_live_condition.create_scientific_session"))
            headless.create_live_v3_session()
            self.assertNotIn("motor_state_probe_factory", create.call_args.kwargs)
            headless.create_live_v3_session(telemetry_observer=lambda _: None, upstream_diagnostics=True)
            self.assertIs(create.call_args.kwargs["motor_state_probe_factory"], CandidateUpstreamProbe)
            with self.assertRaisesRegex(ValueError, "telemetry observer"):
                headless.create_live_v3_session(upstream_diagnostics=True)


if __name__ == "__main__":
    unittest.main()
