"""Command-line entry point for continuous headless Live Fly."""
import argparse


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--motor-interface", choices=("v1", "v2", "v3"), default="v1",
        help="motor inventory: v1=11 (default), v2=17, v3=20; all use six tibia sensory channels",
    )
    parser.add_argument("--upstream-diagnostics", action="store_true",
                        help="verify v3 candidate identities/readout and sample neuron state")
    args = parser.parse_args(argv)
    if args.upstream_diagnostics and args.motor_interface != "v3":
        parser.error("--upstream-diagnostics requires --motor-interface v3")

    # Parse before selecting a factory, constructing a session, or opening
    # a socket. Package-level imports still follow the existing live API.
    from malecns_backend.live import headless
    from malecns_backend.live.server import PoseServer

    factories = {
        "v1": (headless.create_live_session, 11),
        "v2": (headless.create_live_v2_session, 17),
        "v3": (headless.create_live_v3_session, 20),
    }
    factory, motor_count = factories[args.motor_interface]
    factory_options = {"upstream_diagnostics": True} if args.upstream_diagnostics else {}
    telemetry = headless.LatestLiveTelemetry()
    print(f"LIVE motor_interface={args.motor_interface} motor_channels={motor_count} sensory_channels=6")
    with PoseServer() as publisher:
        print(f"LIVE pose server=127.0.0.1:{publisher.bound_port} session={publisher.session_id}")
        headless.run(
            session_factory=lambda: factory(telemetry_observer=telemetry, **factory_options),
            pose_publisher=publisher,
            live_telemetry=telemetry,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
