import unittest
from unittest.mock import Mock

import torch

from brain_body_bridge import BrainEngine


class BrainEngineAdvanceTests(unittest.TestCase):
    def test_advance_delivers_every_neural_sample_to_decoder(self):
        brain = BrainEngine.__new__(BrainEngine)
        brain.populations = {"vision": [0]}
        brain.num_neurons = 1
        brain.dt = 0.1
        brain.step = Mock(side_effect=[
            torch.tensor([[0.0]]),
            torch.tensor([[1.0]]),
            torch.tensor([[0.0]]),
        ])
        brain.get_dn_spikes = Mock(side_effect=[{"P9_left": value}
                                                for value in (0, 1, 0)])
        brain.get_population_spikes = Mock(return_value={"vision": 0.25})
        decoder = Mock()
        callback = Mock()

        result = brain.advance(decoder, steps=3, on_step=callback)

        self.assertEqual(brain.step.call_count, 3)
        self.assertEqual(decoder.update.call_count, 3)
        self.assertEqual(callback.call_count, 3)
        self.assertEqual(result.item(), 0.0)
        self.assertEqual(brain.last_activity, 1.0)

    def test_advance_rejects_empty_batches(self):
        brain = BrainEngine.__new__(BrainEngine)
        with self.assertRaisesRegex(ValueError, "at least one"):
            brain.advance(Mock(), steps=0)

    def test_steps_for_elapsed_preserves_neural_clock(self):
        brain = BrainEngine.__new__(BrainEngine)
        brain.dt = 0.1
        self.assertEqual(brain.steps_for_elapsed(0.01), 100)
        brain.dt = 1.0
        self.assertEqual(brain.steps_for_elapsed(0.01), 10)


if __name__ == "__main__":
    unittest.main()
