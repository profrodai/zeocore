"""
Tests for zeo_core.integrations.loader.

Boundary-mock rule (RULING-235): the only external boundary this module has
is importlib.metadata.entry_points() (a stdlib/OS-level lookup of installed
package entry points) -- that is what gets mocked. IntegrationRegistry,
IntegrationLoadReport, and the loader's own control flow are exercised for
real, using small real IntegrationProtocol-shaped stub instances.
"""

from unittest.mock import MagicMock, patch

from zeo_core.integrations.core.registry import IntegrationRegistry
from zeo_core.integrations.core.results import (
    IntegrationLoadReport,
    IntegrationResult,
)
from zeo_core.integrations.loader import (
    DEFAULT_ENTRY_GROUP,
    _load_one_entry_point,
    list_available_entry_points,
    load_enabled_entry_points,
)


class _FakeIntegration:
    """A minimal real object satisfying IntegrationProtocol structurally."""

    def __init__(self, integration_id: str, init_success: bool = True) -> None:
        self.integration_id = integration_id
        self.name = integration_id
        self.version = "1.0.0"
        self._init_success = init_success
        self.initialized = False

    def initialize(self) -> IntegrationResult:
        self.initialized = True
        if self._init_success:
            return IntegrationResult.success_result(message="ok")
        return IntegrationResult.error_result("init failed")

    def is_available(self) -> bool:
        return True


def _make_entry_point(name: str, value: str = "pkg.module:factory") -> MagicMock:
    """A stand-in for importlib.metadata.EntryPoint."""
    ep = MagicMock()
    ep.name = name
    ep.value = value
    ep.module = value.split(":")[0]
    return ep


class TestListAvailableEntryPoints:
    def test_lists_entry_points_metadata(self) -> None:
        ep1 = _make_entry_point("github", "zeo_core.integrations.github:factory")
        ep2 = _make_entry_point("drive", "zeo_core.integrations.google.drive:factory")

        mock_eps = MagicMock()
        mock_eps.select.return_value = [ep1, ep2]

        with patch("zeo_core.integrations.loader.entry_points", return_value=mock_eps):
            result = list_available_entry_points()

        assert result == [
            {
                "integration_id": "github",
                "value": "zeo_core.integrations.github:factory",
                "module": "zeo_core.integrations.github",
            },
            {
                "integration_id": "drive",
                "value": "zeo_core.integrations.google.drive:factory",
                "module": "zeo_core.integrations.google.drive",
            },
        ]
        mock_eps.select.assert_called_once_with(group=DEFAULT_ENTRY_GROUP)

    def test_empty_when_no_entry_points(self) -> None:
        mock_eps = MagicMock()
        mock_eps.select.return_value = []

        with patch("zeo_core.integrations.loader.entry_points", return_value=mock_eps):
            result = list_available_entry_points()

        assert result == []

    def test_custom_group_is_forwarded(self) -> None:
        mock_eps = MagicMock()
        mock_eps.select.return_value = []

        with patch("zeo_core.integrations.loader.entry_points", return_value=mock_eps):
            list_available_entry_points(group="custom.group")

        mock_eps.select.assert_called_once_with(group="custom.group")


class TestLoadOneEntryPoint:
    """Direct tests of the extracted single-entry-point helper."""

    def _report(self) -> IntegrationLoadReport:
        return IntegrationLoadReport(success=True)

    def test_success_path_registers_and_records_loaded(self) -> None:
        registry = IntegrationRegistry()
        report = self._report()
        integration = _FakeIntegration("gh")
        ep = _make_entry_point("gh")
        ep.load.return_value = lambda: integration

        keep_going = _load_one_entry_point(
            "gh", ep, registry, report, strict=True, initialize=True
        )

        assert keep_going is True
        assert report.loaded == ["gh"]
        assert report.success is True
        assert integration.initialized is True
        assert registry.get_integration("gh") is integration

    def test_non_callable_factory_records_error_and_continues(self) -> None:
        registry = IntegrationRegistry()
        report = self._report()
        ep = _make_entry_point("bad")
        ep.load.return_value = "not-callable"

        keep_going = _load_one_entry_point(
            "bad", ep, registry, report, strict=True, initialize=True
        )

        assert keep_going is True
        assert report.success is False
        assert any("not callable" in e for e in report.errors)
        assert report.loaded == []

    def test_instance_failing_protocol_duck_type_records_error(self) -> None:
        registry = IntegrationRegistry()
        report = self._report()
        ep = _make_entry_point("odd")

        class NotAnIntegration:
            pass

        ep.load.return_value = NotAnIntegration

        keep_going = _load_one_entry_point(
            "odd", ep, registry, report, strict=True, initialize=True
        )

        assert keep_going is True
        assert report.success is False
        assert any("does not satisfy" in e for e in report.errors)

    def test_duck_typed_instance_without_isinstance_match_still_registers(
        self,
    ) -> None:
        """An object with initialize()/name but that isn't nominally
        IntegrationProtocol-typed should still pass the duck-typing
        fallback and register successfully."""
        registry = IntegrationRegistry()
        report = self._report()
        ep = _make_entry_point("duck")
        integration = _FakeIntegration("duck")
        ep.load.return_value = lambda: integration

        keep_going = _load_one_entry_point(
            "duck", ep, registry, report, strict=True, initialize=False
        )

        assert keep_going is True
        assert report.loaded == ["duck"]
        assert integration.initialized is False  # initialize=False, never called

    def test_init_failure_non_strict_continues(self) -> None:
        registry = IntegrationRegistry()
        report = self._report()
        integration = _FakeIntegration("flaky", init_success=False)
        ep = _make_entry_point("flaky")
        ep.load.return_value = lambda: integration

        keep_going = _load_one_entry_point(
            "flaky", ep, registry, report, strict=False, initialize=True
        )

        assert keep_going is True
        assert report.success is False
        assert any("Failed to initialize flaky" in e for e in report.errors)
        assert report.loaded == []

    def test_init_failure_strict_aborts(self) -> None:
        registry = IntegrationRegistry()
        report = self._report()
        integration = _FakeIntegration("flaky", init_success=False)
        ep = _make_entry_point("flaky")
        ep.load.return_value = lambda: integration

        keep_going = _load_one_entry_point(
            "flaky", ep, registry, report, strict=True, initialize=True
        )

        assert keep_going is False
        assert report.success is False

    def test_unexpected_exception_strict_aborts(self) -> None:
        registry = IntegrationRegistry()
        report = self._report()
        ep = _make_entry_point("boom")
        ep.load.side_effect = RuntimeError("kaboom")

        keep_going = _load_one_entry_point(
            "boom", ep, registry, report, strict=True, initialize=True
        )

        assert keep_going is False
        assert report.success is False
        assert any("Unexpected error loading boom" in e for e in report.errors)

    def test_unexpected_exception_non_strict_continues(self) -> None:
        registry = IntegrationRegistry()
        report = self._report()
        ep = _make_entry_point("boom")
        ep.load.side_effect = RuntimeError("kaboom")

        keep_going = _load_one_entry_point(
            "boom", ep, registry, report, strict=False, initialize=True
        )

        assert keep_going is True
        assert report.success is False


class TestLoadEnabledEntryPoints:
    def test_loads_all_requested_integrations(self) -> None:
        registry = IntegrationRegistry()
        gh = _FakeIntegration("gh")
        drive = _FakeIntegration("drive")

        ep_gh = _make_entry_point("gh")
        ep_gh.load.return_value = lambda: gh
        ep_drive = _make_entry_point("drive")
        ep_drive.load.return_value = lambda: drive

        mock_eps = MagicMock()
        mock_eps.select.return_value = [ep_gh, ep_drive]

        with patch("zeo_core.integrations.loader.entry_points", return_value=mock_eps):
            report = load_enabled_entry_points(registry, ["gh", "drive"])

        assert report.success is True
        assert sorted(report.loaded) == ["drive", "gh"]
        assert registry.get_integration("gh") is gh
        assert registry.get_integration("drive") is drive

    def test_missing_integration_strict_returns_immediately(self) -> None:
        registry = IntegrationRegistry()
        mock_eps = MagicMock()
        mock_eps.select.return_value = []

        with patch("zeo_core.integrations.loader.entry_points", return_value=mock_eps):
            report = load_enabled_entry_points(registry, ["missing"], strict=True)

        assert report.success is False
        assert any("not found in entry points" in e for e in report.errors)
        assert report.loaded == []

    def test_missing_integration_non_strict_skips_and_continues(self) -> None:
        registry = IntegrationRegistry()
        present = _FakeIntegration("present")
        ep_present = _make_entry_point("present")
        ep_present.load.return_value = lambda: present

        mock_eps = MagicMock()
        mock_eps.select.return_value = [ep_present]

        with patch("zeo_core.integrations.loader.entry_points", return_value=mock_eps):
            report = load_enabled_entry_points(
                registry, ["missing", "present"], strict=False
            )

        assert report.skipped == ["missing"]
        assert any("not found in entry points" in w for w in report.warnings)
        assert report.loaded == ["present"]

    def test_strict_abort_on_init_failure_stops_loop_early(self) -> None:
        registry = IntegrationRegistry()
        flaky = _FakeIntegration("flaky", init_success=False)
        never_reached = _FakeIntegration("never_reached")

        ep_flaky = _make_entry_point("flaky")
        ep_flaky.load.return_value = lambda: flaky
        ep_never = _make_entry_point("never_reached")
        ep_never.load.return_value = lambda: never_reached

        mock_eps = MagicMock()
        mock_eps.select.return_value = [ep_flaky, ep_never]

        with patch("zeo_core.integrations.loader.entry_points", return_value=mock_eps):
            report = load_enabled_entry_points(
                registry, ["flaky", "never_reached"], strict=True
            )

        assert report.success is False
        assert report.loaded == []
        # the second integration was never attempted -- strict abort mid-loop
        assert never_reached.initialized is False

    def test_initialize_false_skips_calling_initialize(self) -> None:
        registry = IntegrationRegistry()
        integration = _FakeIntegration("noinit")
        ep = _make_entry_point("noinit")
        ep.load.return_value = lambda: integration

        mock_eps = MagicMock()
        mock_eps.select.return_value = [ep]

        with patch("zeo_core.integrations.loader.entry_points", return_value=mock_eps):
            report = load_enabled_entry_points(registry, ["noinit"], initialize=False)

        assert report.loaded == ["noinit"]
        assert integration.initialized is False

    def test_empty_enabled_list_returns_empty_success_report(self) -> None:
        registry = IntegrationRegistry()
        mock_eps = MagicMock()
        mock_eps.select.return_value = []

        with patch("zeo_core.integrations.loader.entry_points", return_value=mock_eps):
            report = load_enabled_entry_points(registry, [])

        assert report.success is True
        assert report.loaded == []
        assert report.skipped == []

    def test_custom_group_forwarded_to_entry_points_select(self) -> None:
        registry = IntegrationRegistry()
        mock_eps = MagicMock()
        mock_eps.select.return_value = []

        with patch("zeo_core.integrations.loader.entry_points", return_value=mock_eps):
            load_enabled_entry_points(registry, [], group="custom.group")

        mock_eps.select.assert_called_once_with(group="custom.group")
