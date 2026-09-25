"""Command-line entry point for continuous headless Live Fly."""
from .headless import run
from .server import PoseServer


def main() -> int:
    with PoseServer() as publisher:
        print(f"LIVE pose server=127.0.0.1:{publisher.bound_port} session={publisher.session_id}")
        run(pose_publisher=publisher)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
