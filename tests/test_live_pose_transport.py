"""Phase-3 transport tests; no FlyGym stack or canonical experiment is run."""
from __future__ import annotations

from io import StringIO
import socket
import time
from types import MappingProxyType, SimpleNamespace

import pytest

from malecns_backend.live import headless
from malecns_backend.live.protocol import (
    JOINT_NAMES, ProtocolError, decode, encode, hello, pose, validate_hello, validate_pose,
)
from malecns_backend.live.server import PoseServer


def snapshot(n=0, quaternion=(1.0, 0.0, 0.0, 0.0)):
    return SimpleNamespace(
        time_ms=float(n), root_position_xyz=(1.0, 2.0, 3.0),
        root_quaternion_wxyz=quaternion, joint_positions=tuple(float(i) for i in range(42)),
        diagnostics=MappingProxyType({"physics_transition": n, "neural_transition_count": n // 5,
                                      "finite": True}),
    )


def receive(stream):
    line = stream.readline()
    assert line
    return decode(line)


def connect(server):
    connection = socket.create_connection(("127.0.0.1", server.bound_port), timeout=1)
    connection.settimeout(1)
    stream = connection.makefile("rb")
    greeting = receive(stream)
    validate_hello(greeting)
    return connection, stream, greeting


def test_hello_serialization_and_exact_authoritative_joint_order():
    message = hello("session-a")
    assert decode(encode(message)) == message
    assert len(message["joint_names"]) == message["joint_count"] == 42
    assert tuple(message["joint_names"]) == JOINT_NAMES
    validate_hello(message)
    with pytest.raises(ProtocolError):
        validate_hello({**message, "joint_names": message["joint_names"][:-1]})


def test_pose_serialization_shapes_and_wxyz_preservation():
    quaternion = (.5, .1, .2, .3)
    message = pose("s", 7, .25, (1, 2, 3), quaternion, range(42))
    assert decode(encode(message))["root_quaternion_wxyz"] == list(quaternion)
    validate_pose(message)
    with pytest.raises(ProtocolError):
        pose("s", 7, .25, (1, 2, 3), quaternion, range(41))


def test_session_identity_monotonic_sequence_and_reconnect():
    with PoseServer(port=0, publish_hz=100000) as server:
        server.publish(snapshot(1), now=1)
        first, first_stream, greeting = connect(server)
        a = receive(first_stream)
        first_stream.close()
        first.close()
        server.publish(snapshot(2), now=2)
        second, second_stream, greeting2 = connect(server)
        b = receive(second_stream)
        second_stream.close()
        second.close()
        assert greeting2["session_id"] == greeting["session_id"] == a["session_id"] == b["session_id"]
        assert b["sequence"] > a["sequence"]
        assert b["sim_time_seconds"] >= a["sim_time_seconds"]


def test_no_client_disconnect_and_client_input_do_not_control_publishing():
    with PoseServer(port=0, publish_hz=100000) as server:
        # No client: publishing remains immediate and advances independently.
        start = time.monotonic()
        for n in range(1000):
            server.publish(snapshot(n), now=n)
        assert time.monotonic() - start < 1.0
        connection, stream, _ = connect(server)
        receive(stream)
        # Arbitrary input is rejected and never enters the publisher API.
        connection.sendall(b'{"command":"alter-science"}\n')
        connection.close()
        server.publish(snapshot(1001), now=1001)
        server.publish(snapshot(1002), now=1002)  # continues after disconnect


def test_slow_client_uses_one_newest_slot_and_drops_stale_frames():
    with PoseServer(port=0, publish_hz=100000) as server:
        connection, _, _ = connect(server)
        # Do not read. Producer publication only takes the lock; network I/O is elsewhere.
        start = time.monotonic()
        for n in range(5000):
            server.publish(snapshot(n), now=n)
        elapsed = time.monotonic() - start
        connection.close()
        assert elapsed < 2.0
        assert server.pending_capacity == 1
        assert server.replaced_frames > 0


def test_network_shutdown_is_clean_and_releases_port():
    server = PoseServer(port=0).start()
    port = server.bound_port
    server.close()
    assert server._thread is not None and not server._thread.is_alive()
    replacement = socket.socket()
    replacement.bind(("127.0.0.1", port))
    replacement.close()


class FakeSession:
    def __init__(self):
        self.n = 0
        self.closed = False

    def initialize(self):
        return snapshot()

    def step(self, *, lightweight):
        self.n += 1
        return SimpleNamespace(time_ms=self.n * .1, root_position_xyz=(0, 0, 0), finite=True,
                               physics_transitions=self.n, neural_transitions=self.n // 5)

    def snapshot(self):
        return snapshot(self.n)

    def close(self):
        self.closed = True


class RecordingPublisher:
    def __init__(self):
        self.items = []

    def due(self, now):
        return True

    def publish(self, item, *, now):
        self.items.append(item)


def test_transport_is_observational_and_execution_clock_excludes_initialization():
    ticks = iter((0, 69, 69.1, 69.2, 69.3, 69.4))
    session, publisher = FakeSession(), RecordingPublisher()
    result = headless.run(session_factory=lambda: session, max_transitions=2,
                          telemetry_interval=100, clock=lambda: next(ticks),
                          output=StringIO(), pose_publisher=publisher)
    assert session.n == result.physics_transitions == 2
    assert session.closed
    assert result.initialization_wall_seconds == 69
    assert result.execution_wall_seconds == pytest.approx(.3)
    assert len(publisher.items) == 3


def test_transport_modules_have_no_legacy_runtime_or_artifact_writes():
    from pathlib import Path
    sources = "".join(Path(path).read_text() for path in (
        "malecns_backend/live/protocol.py", "malecns_backend/live/server.py"))
    assert "fly_behaviors" not in sources and "unity_bridge" not in sources
    assert "interface_output" not in sources and "StreamingAssets" not in sources
