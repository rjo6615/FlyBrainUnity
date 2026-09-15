import json
import socket
import time
import unittest

from unity_bridge import FlyStateAdapter, UnityStateServer


class FlyStateAdapterTests(unittest.TestCase):
    def test_message_contains_source_pose_behavior_and_movement(self):
        adapter = FlyStateAdapter()
        adapter.make_message(1.0, [0, 0, 1], [1, 0, 0], "walking", .4, .5)
        message = adapter.make_message(
            1.5, [3, 4, 1], [0, 1, 0], "escape", 1.0, .2)
        self.assertEqual(message["protocol_version"], 1)
        self.assertEqual(message["position"], [3.0, 4.0, 1.0])
        self.assertAlmostEqual(message["rotation"][2], 90.0)
        self.assertEqual(message["behavior"], "escape")
        self.assertAlmostEqual(message["movement"]["speed_mm_s"], 10.0)

    def test_tcp_server_emits_newline_delimited_json(self):
        server = UnityStateServer(port=0, update_rate=1000)
        # Bind an ephemeral port explicitly because port=0 is not discoverable
        # from the server's intentionally tiny public interface.
        probe = socket.socket()
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        server.port = port
        server.start()
        client = socket.create_connection(("127.0.0.1", port), timeout=2)
        try:
            server.publish({"type": "fly_state", "time": 2.0})
            payload = client.makefile("r", encoding="utf-8").readline()
            self.assertEqual(json.loads(payload)["time"], 2.0)
        finally:
            client.close()
            server.close()


if __name__ == "__main__":
    unittest.main()
