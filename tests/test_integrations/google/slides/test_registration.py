"""Tests that the Google Slides integration is correctly wired into the
plugin mechanism (entry-points table + loader + registry). Mirrors
tests/test_integrations/google/docs/test_registration.py's pattern:
drives the REAL load_enabled_entry_points() loader end to end (not a
grep/presence check on pyproject.toml).

The `"google.slides"` entry-point line in pyproject.toml is SHARED-FILE
territory (landed on the `prep/sheets-slides-shared-files` branch this
stream builds on top of, alongside the concurrent Sheets stream) -- this
test file verifies it resolves correctly, it does not add or edit that
line.

Like `GoogleDocsService`, `GoogleSlidesService.__init__` follows the
DEFERRED config pattern, so bare construction never touches the config
provider or raises -- no scratch config file or env var patching is
needed for these tests to pass.
"""

from importlib.metadata import entry_points

from zeo_core.integrations.core.protocols import IntegrationProtocol
from zeo_core.integrations.core.registry import IntegrationRegistry
from zeo_core.integrations.google.slides import (
    GoogleSlidesService,
    create_integration,
)
from zeo_core.integrations.google.slides.protocols import SlidesIntegrationProtocol
from zeo_core.integrations.loader import (
    DEFAULT_ENTRY_GROUP,
    list_available_entry_points,
    load_enabled_entry_points,
)


class TestEntryPointRegistration:
    """The declarative registration itself (pyproject.toml)."""

    def test_slides_entry_point_is_discoverable(self) -> None:
        eps = entry_points().select(group=DEFAULT_ENTRY_GROUP)
        names = {ep.name for ep in eps}
        assert "google.slides" in names

    def test_slides_entry_point_resolves_to_create_integration(self) -> None:
        eps = entry_points().select(group=DEFAULT_ENTRY_GROUP)
        slides_ep = next(ep for ep in eps if ep.name == "google.slides")
        assert (
            slides_ep.value == "zeo_core.integrations.google.slides:create_integration"
        )

    def test_list_available_entry_points_includes_slides(self) -> None:
        available = list_available_entry_points()
        ids = {item["integration_id"] for item in available}
        assert "google.slides" in ids


class TestFactoryFunction:
    """create_integration() -- the loader's actual call target."""

    def test_create_integration_returns_google_slides_service(self) -> None:
        instance = create_integration()
        assert isinstance(instance, GoogleSlidesService)

    def test_created_instance_satisfies_integration_protocol(self) -> None:
        instance = create_integration()
        assert isinstance(instance, IntegrationProtocol)

    def test_created_instance_satisfies_slides_protocol(self) -> None:
        instance = create_integration()
        assert isinstance(instance, SlidesIntegrationProtocol)

    def test_integration_id_and_name_before_init(self) -> None:
        """instance.integration_id is "googleslides", NOT "google.slides"
        -- BaseIntegrationService.integration_id derives from
        `self.name.lower().replace(" ", ".")` (core/base.py), and
        "GoogleSlides" (the `name` property, matching "GoogleDocs"/
        "GoogleDrive"'s own one-word-no-space convention) has no space to
        replace. Same pre-existing double-naming pattern documented in
        docs/test_registration.py, not introduced here."""
        instance = create_integration()
        assert instance.integration_id == "googleslides"
        assert instance.name == "GoogleSlides"


class TestLoaderIntegration:
    """The explicit loader (integrations/loader.py) actually loading+
    registering `google.slides` end to end -- this is the real behavioral
    proof that registration works, not just that the entry-point string
    exists."""

    def test_load_enabled_entry_points_loads_slides_without_initializing(
        self,
    ) -> None:
        registry = IntegrationRegistry()

        report = load_enabled_entry_points(
            registry=registry,
            enabled=["google.slides"],
            strict=True,
            initialize=False,  # avoid a real network call / OAuth requirement
        )

        assert report.success is True
        assert report.loaded == ["google.slides"]
        assert report.errors == []
        assert registry.is_registered("googleslides")

        loaded = registry.get_integration("googleslides")
        assert isinstance(loaded, GoogleSlidesService)
