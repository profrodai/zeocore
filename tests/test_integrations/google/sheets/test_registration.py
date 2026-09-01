"""Tests that the Google Sheets integration is correctly wired into the
plugin mechanism (entry-points table + loader + registry), per
integrations/core's "real, documented, mature" plugin mechanism (see
integrations/core/loader.py, registry.py) -- the same mechanism
github/google.mail/google.drive/google.calendar/google.docs/pandoc/llms/
notion already use, per this repo's own pyproject.toml
[project.entry-points."zeo_core.integrations"] table. Mirrors
tests/test_integrations/google/docs/test_registration.py's pattern: drives
the REAL load_enabled_entry_points() loader end to end (not a grep/presence
check on pyproject.toml).

Like GoogleDocsService, GoogleSheetsService.__init__ follows the DEFERRED
config pattern, so bare construction never touches the config provider or
raises -- no scratch config file or env var patching is needed for these
tests to pass.
"""

from importlib.metadata import entry_points

from zeo_core.integrations.core.protocols import IntegrationProtocol
from zeo_core.integrations.core.registry import IntegrationRegistry
from zeo_core.integrations.google.sheets import GoogleSheetsService, create_integration
from zeo_core.integrations.google.sheets.protocols import SheetsIntegrationProtocol
from zeo_core.integrations.loader import (
    DEFAULT_ENTRY_GROUP,
    list_available_entry_points,
    load_enabled_entry_points,
)


class TestEntryPointRegistration:
    """The declarative registration itself (pyproject.toml)."""

    def test_sheets_entry_point_is_discoverable(self) -> None:
        eps = entry_points().select(group=DEFAULT_ENTRY_GROUP)
        names = {ep.name for ep in eps}
        assert "google.sheets" in names

    def test_sheets_entry_point_resolves_to_create_integration(self) -> None:
        eps = entry_points().select(group=DEFAULT_ENTRY_GROUP)
        sheets_ep = next(ep for ep in eps if ep.name == "google.sheets")
        assert (
            sheets_ep.value == "zeo_core.integrations.google.sheets:create_integration"
        )

    def test_list_available_entry_points_includes_sheets(self) -> None:
        available = list_available_entry_points()
        ids = {item["integration_id"] for item in available}
        assert "google.sheets" in ids


class TestFactoryFunction:
    """create_integration() -- the loader's actual call target."""

    def test_create_integration_returns_google_sheets_service(self) -> None:
        instance = create_integration()
        assert isinstance(instance, GoogleSheetsService)

    def test_created_instance_satisfies_integration_protocol(self) -> None:
        instance = create_integration()
        assert isinstance(instance, IntegrationProtocol)

    def test_created_instance_satisfies_sheets_protocol(self) -> None:
        instance = create_integration()
        assert isinstance(instance, SheetsIntegrationProtocol)

    def test_integration_id_and_name_before_init(self) -> None:
        """instance.integration_id is "googlesheets", NOT "google.sheets" --
        BaseIntegrationService.integration_id derives from
        `self.name.lower().replace(" ", ".")` (core/base.py), and
        "GoogleSheets" (the `name` property, matching "GoogleDrive"/
        "GoogleMail"/"GoogleCalendar"/"GoogleDocs"'s own one-word-no-space
        convention) has no space to replace. Same pre-existing
        double-naming pattern documented in calendar/test_registration.py
        and docs/test_registration.py, not introduced here."""
        instance = create_integration()
        assert instance.integration_id == "googlesheets"
        assert instance.name == "GoogleSheets"


class TestLoaderIntegration:
    """The explicit loader (integrations/loader.py) actually loading+
    registering `google.sheets` end to end -- this is the real behavioral
    proof that registration works, not just that the entry-point string
    exists."""

    def test_load_enabled_entry_points_loads_sheets_without_initializing(
        self,
    ) -> None:
        registry = IntegrationRegistry()

        report = load_enabled_entry_points(
            registry=registry,
            enabled=["google.sheets"],
            strict=True,
            initialize=False,  # avoid a real network call / OAuth requirement
        )

        assert report.success is True
        assert report.loaded == ["google.sheets"]
        assert report.errors == []
        assert registry.is_registered("googlesheets")

        loaded = registry.get_integration("googlesheets")
        assert isinstance(loaded, GoogleSheetsService)
