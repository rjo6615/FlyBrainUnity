"""Optional, output-only TCP adapter for the Unity visualization.

This module has no FlyGym, MuJoCo, or PyTorch dependencies.  The simulation
thread only calls :meth:`UnityStateServer.publish`; accepting clients and
socket writes happen on a daemon thread so a missing/slow Unity client cannot
stall a neural or physics step.
"""

from __future__ import annotations

import json
import math
import queue
import socket
import threading
import time


PROTOCOL_VERSION = 1


class FlyStateAdapter:
    """Turn authoritative FlyGym observations into transport-only values."""

    def __init__(self):
        self._last_time = None
        self._last_position = None

    def make_message(self, simulation_time, position, forward, behavior,
                     left_drive, right_drive):
        pos = [float(value) for value in position[:3]]
        direction = [float(value) for value in forward[:3]]
        yaw_degrees = math.degrees(math.atan2(direction[1], direction[0]))
        speed = 0.0
        if self._last_time is not None and simulation_time > self._last_time:
            distance = math.sqrt(sum(
                (pos[i] - self._last_position[i]) ** 2 for i in range(3)))
            speed = distance / (simulation_time - self._last_time)
        self._last_time = float(simulation_time)
        self._last_position = pos
        return {
            "type": "fly_state",
            "protocol_version": PROTOCOL_VERSION,
            "time": float(simulation_time),
            # FlyGym/MuJoCo coordinates: millimetres, right-handed, Z-up.
            "position": pos,
            "orientation": direction,
            "rotation": [0.0, 0.0, yaw_degrees],
            "behavior": str(behavior),
            "movement": {
                "left_drive": float(left_drive),
                "right_drive": float(right_drive),
                "speed_mm_s": speed,
            },
        }


class UnityStateServer:
    """Single-client newline-delimited JSON server with bounded buffering."""

    def __init__(self, host="127.0.0.1", port=8765, update_rate=30.0):
        self.host = host
        self.port = int(port)
        self.update_rate = float(update_rate)
        self._queue = queue.Queue(maxsize=1)
        self._stop = threading.Event()
        self._thread = None
        self._last_publish = 0.0

    def start(self):
        if self._thread is not None:
            return
        print(f"[Unity bridge] enabled tcp://{self.host}:{self.port} "
              f"target={self.update_rate:g} Hz", flush=True)
        self._thread = threading.Thread(
            target=self._serve, name="unity-state-server", daemon=True)
        self._thread.start()

    def publish(self, message):
        """Offer the newest state without ever waiting for the network."""
        now = time.monotonic()
        if now - self._last_publish < 1.0 / self.update_rate:
            return False
        self._last_publish = now
        try:
            self._queue.put_nowait(message)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            self._queue.put_nowait(message)
        return True

    def close(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def _serve(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind((self.host, self.port))
                listener.listen(1)
                listener.settimeout(0.5)
                while not self._stop.is_set():
                    try:
                        client, address = listener.accept()
                    except socket.timeout:
                        continue
                    print(f"[Unity bridge] client connected: {address[0]}:{address[1]}",
                          flush=True)
                    self._send_to_client(client)
                    print("[Unity bridge] client disconnected", flush=True)
        except OSError as error:
            print(f"[Unity bridge] disabled after socket error: {error}", flush=True)

    def _send_to_client(self, client):
        sent = 0
        report_started = time.monotonic()
        with client:
            client.settimeout(1.0)
            while not self._stop.is_set():
                try:
                    message = self._queue.get(timeout=0.25)
                    payload = json.dumps(message, separators=(",", ":")) + "\n"
                    client.sendall(payload.encode("utf-8"))
                    sent += 1
                except queue.Empty:
                    continue
                except (BrokenPipeError, ConnectionResetError, socket.timeout,
                        OSError):
                    return
                now = time.monotonic()
                if now - report_started >= 5.0:
                    print(f"[Unity bridge] outgoing rate "
                          f"{sent / (now - report_started):.1f} Hz", flush=True)
                    sent = 0
                    report_started = now
