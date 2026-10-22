"""CLI routing checks using doubles; no neural or physics execution."""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ENTRYPOINT = Path(__file__).resolve().parents[1] / "malecns_backend/live/__main__.py"


class LiveCliTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("live_cli_under_test", ENTRYPOINT)
        self.cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.cli)

    def test_default_and_explicit_interfaces_route_observer_and_publisher(self):
        for arguments, selected, count in (
            ([], "v1", 11), (["--motor-interface", "v1"], "v1", 11),
            (["--motor-interface", "v2"], "v2", 17),
            (["--motor-interface", "v3"], "v3", 20),
            (["--motor-interface", "v3", "--upstream-diagnostics"], "v3", 20),
        ):
            with self.subTest(arguments=arguments):
                factories = {name: Mock(return_value=object()) for name in ("v1", "v2", "v3")}
                telemetry = object()
                publisher = SimpleNamespace(bound_port=8765, session_id="test")
                server = Mock()
                server.return_value.__enter__ = Mock(return_value=publisher)
                server.return_value.__exit__ = Mock(return_value=False)
                def run(**kwargs):
                    self.assertIs(kwargs["pose_publisher"], publisher)
                    self.assertIs(kwargs["live_telemetry"], telemetry)
                    self.assertIs(kwargs["session_factory"](), factories[selected].return_value)
                headless = SimpleNamespace(
                    create_live_session=factories["v1"], create_live_v2_session=factories["v2"],
                    create_live_v3_session=factories["v3"],
                    LatestLiveTelemetry=lambda: telemetry, run=Mock(side_effect=run),
                )
                package = ModuleType("malecns_backend.live")
                package.headless = headless
                modules = {
                    "malecns_backend": ModuleType("malecns_backend"),
                    "malecns_backend.live": package,
                    "malecns_backend.live.server": SimpleNamespace(PoseServer=server),
                }
                output = io.StringIO()
                with patch.dict(sys.modules, modules), contextlib.redirect_stdout(output):
                    self.assertEqual(self.cli.main(arguments), 0)
                options = {"upstream_diagnostics": True} if "--upstream-diagnostics" in arguments else {}
                factories[selected].assert_called_once_with(telemetry_observer=telemetry, **options)
                for name, factory in factories.items():
                    if name != selected:
                        factory.assert_not_called()
                self.assertIn(f"motor_interface={selected} motor_channels={count} sensory_channels=6", output.getvalue())
                server.return_value.__exit__.assert_called_once()

    def test_help_and_invalid_selection_exit_before_scientific_imports(self):
        import builtins
        original_import = builtins.__import__
        def guarded_import(name, *args, **kwargs):
            if name.startswith("malecns_backend"):
                self.fail("argument parsing imported scientific runtime")
            return original_import(name, *args, **kwargs)
        for arguments, expected_code in ((["--help"], 0), (["--motor-interface", "v4"], 2),
                (["--upstream-diagnostics"], 2),
                (["--motor-interface", "v2", "--upstream-diagnostics"], 2)):
            with self.subTest(arguments=arguments), patch("builtins.__import__", guarded_import):
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as result:
                        self.cli.main(arguments)
                self.assertEqual(result.exception.code, expected_code)


if __name__ == "__main__":
    unittest.main()
