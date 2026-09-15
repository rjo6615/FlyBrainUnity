import unittest

import numpy as np

from brain_body_bridge import BrainBodyBridge


class DecoderStub:
    def __init__(self, normalized=None):
        self.normalized = normalized or {}

    def get_normalized(self, name):
        return self.normalized.get(name, 0.0)

    def get_pop_rate(self, name):
        return 0.0


class BrainBodyBridgeDriveTests(unittest.TestCase):
    def test_sparse_p9_activity_is_scaled_to_an_effective_walking_drive(self):
        decoder = DecoderStub({
            "P9_left": 0.15,
            "P9_right": 0.15,
            "P9_oDN1_left": 0.15,
            "P9_oDN1_right": 0.15,
        })
        bridge = BrainBodyBridge(decoder)

        drive = bridge.compute_drive()

        np.testing.assert_allclose(drive, [0.6, 0.6])
        self.assertEqual(bridge.mode, "walking")

    def test_locomotor_gain_keeps_output_in_turning_controller_range(self):
        decoder = DecoderStub({
            "P9_left": 1.0,
            "P9_right": 1.0,
            "P9_oDN1_left": 1.0,
            "P9_oDN1_right": 1.0,
            "DNa01_left": 1.0,
        })
        bridge = BrainBodyBridge(decoder)

        drive = bridge.compute_drive()

        self.assertTrue(np.all(drive >= -0.5))
        self.assertTrue(np.all(drive <= 1.5))


if __name__ == "__main__":
    unittest.main()
