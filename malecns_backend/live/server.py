"""Nonblocking-to-science, single-client Live Fly pose publisher."""
from __future__ import annotations

import socket
import select
import threading
import time
import uuid
from typing import Any

from .protocol import encode, hello, pose


class PoseServer:
    """Move only the newest observational pose through a networking thread."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765,
                 publish_hz: float = 30.0, session_id: str | None = None):
        if publish_hz <= 0:
            raise ValueError("publish_hz must be positive")
        self.host, self.port = host, port
        self.publish_interval = 1.0 / publish_hz
        self.session_id = session_id or str(uuid.uuid4())
        self._lock = threading.Lock()
        self._newest: bytes | None = None
        self._generation = 0
        self._consumed_generation = 0
        self._sequence = 0
        self._last_publish = float("-inf")
        self.replaced_frames = 0
        self.sent_frames = 0
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None
        self._listener: socket.socket | None = None
        self.bound_port: int | None = None

    def start(self) -> "PoseServer":
        if self._thread is not None:
            raise RuntimeError("server already started")
        self._thread = threading.Thread(target=self._serve, name="live-fly-pose", daemon=True)
        self._thread.start()
        if not self._ready.wait(2.0):
            raise RuntimeError("pose server failed to start")
        return self

    def due(self, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        return current - self._last_publish >= self.publish_interval

    def publish(self, snapshot: Any, *, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        if not self.due(current):
            return False
        packet = pose(
            self.session_id, self._sequence, snapshot.time_ms / 1000.0,
            snapshot.root_position_xyz, snapshot.root_quaternion_wxyz,
            snapshot.joint_positions,
            physics_transitions=int(snapshot.diagnostics.get("physics_transition", 0)),
            neural_transitions=int(snapshot.diagnostics.get("neural_transition_count", 0)),
            finite=bool(snapshot.diagnostics.get("finite", True)),
        )
        encoded = encode(packet)
        with self._lock:
            if self._generation > self._consumed_generation:
                self.replaced_frames += 1
            self._newest = encoded
            self._generation += 1
        self._sequence += 1
        self._last_publish = current
        return True

    def _take(self, after: int) -> tuple[int, bytes | None]:
        with self._lock:
            if self._generation == after:
                return after, None
            self._consumed_generation = self._generation
            return self._generation, self._newest

    def _serve(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener = listener
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self.host, self.port))
        self.bound_port = listener.getsockname()[1]
        listener.listen(1)
        listener.settimeout(.1)
        self._ready.set()
        try:
            while not self._stop.is_set():
                try:
                    client, _ = listener.accept()
                except socket.timeout:
                    continue
                except OSError:
                    if self._stop.is_set():
                        break
                    raise
                self._handle(client)
        finally:
            listener.close()

    def _handle(self, client: socket.socket) -> None:
        client.settimeout(.1)
        generation = -1  # reconnect immediately receives the newest pose
        try:
            client.sendall(encode(hello(self.session_id)))
            while not self._stop.is_set():
                # Input is outside the Phase-3 boundary.  Reject it (and detect
                # orderly disconnects) without parsing or exposing it upstream.
                if select.select((client,), (), (), 0)[0]:
                    client.recv(1)
                    break
                generation, packet = self._take(generation)
                if packet is None:
                    self._stop.wait(.005)
                    continue
                try:
                    client.sendall(packet)
                    self.sent_frames += 1
                except (BrokenPipeError, ConnectionError, socket.timeout, OSError):
                    break
        except (BrokenPipeError, ConnectionError, socket.timeout, OSError):
            pass
        finally:
            client.close()

    @property
    def pending_capacity(self) -> int:
        return 1

    def close(self) -> None:
        self._stop.set()
        if self._listener is not None:
            try:
                self._listener.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(2.0)

    def __enter__(self) -> "PoseServer":
        return self.start()

    def __exit__(self, *_: Any) -> None:
        self.close()
