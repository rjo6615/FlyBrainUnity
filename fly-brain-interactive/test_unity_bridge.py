import json
import socket
import time
import unittest

from unity_bridge import EnvironmentStateAdapter, FlyStateAdapter, UnityStateServer


class FlyStateAdapterTests(unittest.TestCase):
    def test_environment_definition_uses_stable_ids_and_source_units(self):
        adapter = EnvironmentStateAdapter()
        message = adapter.definition()
        self.assertEqual(message["type"], "environment_definition")
        self.assertEqual(message["objects"][0]["id"], "substrate")
        self.assertEqual(message["objects"][0]["size"], [64.0, 64.0, 0.7])

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

    def test_full_terrarium_definition_contains_only_instantiated_objects(self):
        class Arena:
            ball_pos = [10.0, 2.0, 1.5]
            ball_radius = 6.0

        class Taste:
            def __init__(self, label, taste):
                self.label, self.taste = label, taste
                self.center, self.radius = [1.0, 2.0], 3.0

        class Odor:
            def __init__(self, label, odor_type):
                self.label, self.odor_type = label, odor_type
                self.position = [3.0, 4.0, 1.0]

        adapter = EnvironmentStateAdapter(
            Arena(), [Taste("sugar", "sugar"), Taste("bitter", "bitter")],
            [Odor("food", "attractive"), Odor("geosmin", "repulsive")])
        objects = adapter.definition()["objects"]
        self.assertEqual(len(objects), 10)
        self.assertEqual({item["id"] for item in objects}, {
            "substrate", "wall:0", "wall:1", "wall:2", "wall:3",
            "predator", "taste:sugar:0", "taste:bitter:1",
            "odor:food:0", "odor:geosmin:1",
        })
        self.assertEqual(len(objects), len({item["id"] for item in objects}))
        payload = json.dumps(adapter.definition())
        self.assertEqual(len(json.loads(payload)["objects"]), len(objects))

    def test_substrate_maps_to_horizontal_unity_dimensions(self):
        substrate = EnvironmentStateAdapter().definition()["objects"][0]
        x, y, z = substrate["size"]
        unity_dimensions = [x * .1, z * .1, y * .1]
        for actual, expected in zip(unity_dimensions, [6.4, .07, 6.4]):
            self.assertAlmostEqual(actual, expected)

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

    def test_tcp_server_sends_environment_on_connect(self):
        server = UnityStateServer(port=0, update_rate=1000)
        probe = socket.socket(); probe.bind(("127.0.0.1", 0))
        server.port = probe.getsockname()[1]; probe.close()
        server.set_environment(EnvironmentStateAdapter().definition())
        server.start()
        client = socket.create_connection(("127.0.0.1", server.port), timeout=2)
        try:
            payload = client.makefile("r", encoding="utf-8").readline()
            self.assertEqual(json.loads(payload)["type"], "environment_definition")
        finally:
            client.close(); server.close()

    def test_tcp_server_resends_complete_environment_on_reconnect(self):
        server = UnityStateServer(port=0, update_rate=1000)
        probe = socket.socket(); probe.bind(("127.0.0.1", 0))
        server.port = probe.getsockname()[1]; probe.close()
        definition = EnvironmentStateAdapter().definition()
        server.set_environment(definition); server.start()
        try:
            for _ in range(2):
                deadline = time.monotonic() + 2
                while True:
                    try:
                        client = socket.create_connection(
                            ("127.0.0.1", server.port), timeout=2)
                        break
                    except ConnectionRefusedError:
                        if time.monotonic() >= deadline:
                            raise
                        time.sleep(.01)
                payload = client.makefile("r", encoding="utf-8").readline()
                self.assertEqual(len(json.loads(payload)["objects"]),
                                 len(definition["objects"]))
                client.shutdown(socket.SHUT_RDWR)
                client.close()
                # Wake the connected-client loop so it observes the closed peer
                # and returns to accept the reconnect.
                for tick in range(3):
                    server._last_publish = 0
                    server.publish({"type": "fly_state", "time": tick})
                    time.sleep(.03)
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
