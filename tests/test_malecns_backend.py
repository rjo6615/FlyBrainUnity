import math
import struct
import unittest
from unittest import mock

from malecns_backend import audit
from malecns_backend.codec import decode_neurons
from malecns_backend import loader
from malecns_backend.loader import DEFAULT_DATA_DIR, load_malecns


class MaleCNSMemoryTests(unittest.TestCase):
    def test_optional_memory_format(self):
        self.assertEqual(audit._optional_bytes(None), "unavailable")
        self.assertEqual(audit._optional_bytes(1024), "0.00 MiB (1,024 bytes)")

    def test_fallback_fills_only_unavailable_metrics(self):
        with mock.patch.object(loader, "_psutil_memory_bytes", return_value=(123, None)), \
                mock.patch.object(loader, "_unix_memory_bytes", return_value=(456, 789)), \
                mock.patch.object(loader, "_windows_memory_bytes", return_value=(None, None)), \
                mock.patch.object(loader.sys, "platform", "linux"):
            self.assertEqual(loader.process_memory_bytes(), (123, 789))


class MaleCNSArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_malecns()

    def test_binary_decoding(self):
        with (DEFAULT_DATA_DIR / "neurons.flyn").open("rb") as handle:
            self.assertEqual(struct.unpack("<II", handle.read(8)), (0x4E594C46, 1))
        count, body_ids, *_ = decode_neurons(DEFAULT_DATA_DIR / "neurons.flyn")
        self.assertEqual(count, self.data.neuron_count)
        self.assertEqual(body_ids, self.data.body_ids)

    def test_expected_counts(self):
        self.assertEqual(self.data.neuron_count, 165_122)
        self.assertEqual(self.data.edge_count, 10_511_038)
        self.assertEqual(sum(self.data.synapse_counts), 104_213_652)

    def test_effective_five_counts(self):
        selected = [weight for weight in self.data.synapse_counts if weight >= 5]
        self.assertEqual(len(selected), 6_235_682)
        self.assertEqual(sum(selected), 89_731_551)

    def test_csr_validity(self):
        d = self.data
        self.assertEqual(len(d.row_ptr), d.neuron_count + 1)
        self.assertEqual(d.row_ptr[0], 0)
        self.assertEqual(d.row_ptr[-1], d.edge_count)
        self.assertTrue(all(a <= b for a, b in zip(d.row_ptr, d.row_ptr[1:])))
        self.assertTrue(all(0 <= target < d.neuron_count for target in d.target_indices))
        self.assertTrue(all(weight > 0 for weight in d.synapse_counts))

    def test_graph_orientation_against_source_representation(self):
        # load_malecns compares these packed CSR entries with graph_w3.bin using the
        # row as pre and target as post. Body IDs make the assertion unambiguous.
        self.assertGreaterEqual(len(self.data.orientation_examples), 3)
        for pre_body_id, post_body_id, weight in self.data.orientation_examples:
            pre = self.data.dense_index(pre_body_id)
            post = self.data.dense_index(post_body_id)
            row = range(self.data.row_ptr[pre], self.data.row_ptr[pre + 1])
            matches = [slot for slot in row if self.data.target_indices[slot] == post]
            self.assertEqual(len(matches), 1)
            self.assertEqual(self.data.synapse_counts[matches[0]], weight)

    def test_64_bit_body_id_round_trip(self):
        indices = (0, 1, 41280, 82561, 123841, self.data.neuron_count - 1)
        for index in indices:
            body_id = self.data.body_id(index)
            self.assertIsInstance(body_id, int)
            self.assertEqual(self.data.dense_index(body_id), index)
            self.assertEqual(self.data.body_id(self.data.dense_index(body_id)), body_id)
        with self.assertRaises(TypeError):
            self.data.dense_index(float(self.data.body_id(0)))

    def test_companion_array_lengths(self):
        self.assertEqual(len(self.data.neuron_sizes), self.data.neuron_count)
        self.assertEqual(len(self.data.nt_signs), self.data.neuron_count)
        self.assertTrue(all(math.isfinite(v) for v in self.data.neuron_sizes))
        self.assertTrue(all(math.isfinite(v) for v in self.data.nt_signs))

    def test_bodymap_id_resolution(self):
        self.assertGreater(len(self.data.bodymap_dense_indices), 0)
        for index in self.data.bodymap_dense_indices:
            body_id = self.data.body_id(index)
            self.assertEqual(self.data.dense_index(body_id), index)


if __name__ == "__main__":
    unittest.main()
