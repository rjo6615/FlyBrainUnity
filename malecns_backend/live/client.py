"""Small non-Unity diagnostic client for Live Fly Phase 3."""
from __future__ import annotations

import argparse
import socket

from .protocol import decode, validate_hello, validate_pose


def diagnose(host: str = "127.0.0.1", port: int = 8765, count: int = 10) -> None:
    with socket.create_connection((host, port), timeout=5.0) as connection:
        stream = connection.makefile("rb")
        greeting = decode(stream.readline())
        validate_hello(greeting)
        previous_sequence = -1
        previous_time = float("-inf")
        for _ in range(count):
            message = decode(stream.readline())
            validate_pose(message)
            if message["session_id"] != greeting["session_id"]:
                raise ValueError("session identity changed")
            if message["sequence"] <= previous_sequence:
                raise ValueError("sequence is not strictly increasing")
            if message["sim_time_seconds"] < previous_time:
                raise ValueError("simulation time decreased")
            previous_sequence = message["sequence"]
            previous_time = message["sim_time_seconds"]
    print(f"validated hello and {count} poses for session {greeting['session_id']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--count", type=int, default=10)
    args = parser.parse_args()
    diagnose(args.host, args.port, args.count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
