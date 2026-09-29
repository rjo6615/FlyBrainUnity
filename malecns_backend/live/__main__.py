"""Command-line entry point for continuous headless Live Fly."""
from .headless import LatestLiveTelemetry, create_live_session, run
from .server import PoseServer


def main() -> int:
    telemetry = LatestLiveTelemetry()
    with PoseServer() as publisher:
        print(f"LIVE pose server=127.0.0.1:{publisher.bound_port} session={publisher.session_id}")
        run(
            session_factory=lambda: create_live_session(
                telemetry_observer=telemetry,
            ),
            pose_publisher=publisher,
            live_telemetry=telemetry,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
