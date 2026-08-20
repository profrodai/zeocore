"""Tests that the Google Calendar integration is correctly wired into the
plugin mechanism (entry-points table + loader + registry), per
integrations/core's "real, documented, mature" plugin mechanism (see
integrations/core/loader.py, registry.py) -- the same mechanism
github/google.mail/google.drive/pandoc/llms/notion already use, per this
repo's own pyproject.toml [project.entry-points."zeo_core.integrations"]
table. Mirrors tests/test_integrations/notion/test_registration.py's
pattern exactly: drives the REAL load_enabled_entry_points() loader end to
end (not a grep/presence check on pyproject.toml)."""

import os
import shutil
from collections.abc import Iterator
from importlib.metadata import entry_points
from pathlib import Path
from unittest.mock import patch

import pytest

from zeo_core.integrations.core.protocols import IntegrationProtocol
from zeo_core.integrations.core.registry import IntegrationRegistry
from zeo_core.integrations.google.calendar import (
    GoogleCalendarService,
    create_integration,
)
from zeo_core.integrations.google.calendar.protocols import (
    CalendarIntegrationProtocol,
)
from zeo_core.integrations.loader import (
    DEFAULT_ENTRY_GROUP,
    list_available_entry_points,
    load_enabled_entry_points,
)


@pytest.fixture
def bare_construction_env() -> Iterator[None]:
    """`GoogleCalendarService.__init__` (following drive/service.py's own
    eager-config precedent exactly, unlike notion's deferred-to-initialize()
    shape) calls `GoogleConfigProvider.load_config()` immediately, which
    raises if no config file exists anywhere in the fs sandbox's default
    locations -- the identical, pre-existing constraint drive's own
    `create_integration()` has (verified directly: a bare
    `zeo_core.integrations.google.drive.create_integration()` call raises
    the same `ZeoConfigurationError` under the same condition, same repo
    root, same sandbox). This fixture writes a scratch config file INSIDE
    the repo's fs sandbox (RULING-237 s2.1 rejects absolute paths outside
    the configured base directory -- a tmp_path fixture's own /tmp location
    would be refused), matching examples/notion_usage.py's own
    `./tmp_notion_example` scratch-dir convention, and mocks
    `_verify_client_secrets_file` so the OAuth client-secrets file need not
    exist for real, mirroring drive/mail's own test convention exactly.
    Cleaned up in a finally so no scratch file leaks into the repo."""
    scratch_dir = Path("./tmp_calendar_registration_test")
    scratch_dir.mkdir(exist_ok=True)
    config_path = scratch_dir / "zeo_config.yaml"
    config_path.write_text(
        "integrations:\n"
        "  google:\n"
        "    calendar:\n"
        "      client_secrets_file: secrets.json\n"
        "      credentials_file: creds.json\n"
    )
    try:
        with (
            patch.dict(os.environ, {"ZEO_GOOGLECALENDAR_CONFIG": str(config_path)}),
            patch(
                "zeo_core.integrations.google.auth.GoogleAuthProvider."
                "_verify_client_secrets_file"
            ),
        ):
            yield
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


class TestEntryPointRegistration:
    """The declarative registration itself (pyproject.toml)."""

    def test_calendar_entry_point_is_discoverable(self) -> None:
        eps = entry_points().select(group=DEFAULT_ENTRY_GROUP)
        names = {ep.name for ep in eps}
        assert "google.calendar" in names

    def test_calendar_entry_point_resolves_to_create_integration(self) -> None:
        eps = entry_points().select(group=DEFAULT_ENTRY_GROUP)
        calendar_ep = next(ep for ep in eps if ep.name == "google.calendar")
        assert (
            calendar_ep.value
            == "zeo_core.integrations.google.calendar:create_integration"
        )

    def test_list_available_entry_points_includes_calendar(self) -> None:
        available = list_available_entry_points()
        ids = {item["integration_id"] for item in available}
        assert "google.calendar" in ids


@pytest.mark.usefixtures("bare_construction_env")
class TestFactoryFunction:
    """create_integration() -- the loader's actual call target."""

    def test_create_integration_returns_google_calendar_service(self) -> None:
        instance = create_integration()
        assert isinstance(instance, GoogleCalendarService)

    def test_created_instance_satisfies_integration_protocol(self) -> None:
        instance = create_integration()
        assert isinstance(instance, IntegrationProtocol)

    def test_created_instance_satisfies_calendar_protocol(self) -> None:
        instance = create_integration()
        assert isinstance(instance, CalendarIntegrationProtocol)

    def test_integration_id_and_name_before_init(self) -> None:
        """instance.integration_id is "googlecalendar", NOT "google.calendar"
        -- BaseIntegrationService.integration_id derives from
        `self.name.lower().replace(" ", ".")` (core/base.py), and "GoogleCalendar"
        (the `name` property, matching "GoogleDrive"/"GoogleMail"'s own
        one-word-no-space convention) has no space to replace. This is not
        a calendar-specific gap: verified directly (see this file's own
        registration-mismatch discovery, named in the SOW) that
        GoogleDriveService's real `integration_id` is likewise "googledrive",
        not "google.drive" -- the entry-points TABLE key ("google.drive"/
        "google.calendar" in pyproject.toml) and the instance's own
        `integration_id` property are two different strings by a
        pre-existing, faithfully-mirrored pattern, not a defect introduced
        here."""
        instance = create_integration()
        assert instance.integration_id == "googlecalendar"
        assert instance.name == "GoogleCalendar"


class TestLoaderIntegration:
    """The explicit loader (integrations/loader.py) actually loading+
    registering `google.calendar` end to end -- this is the real behavioral
    proof that registration works, not just that the entry-point string
    exists. This is also the mandated "MCP registration" proof: per this
    stream's own recon (see SOW prose), integrations in this repo become
    discoverable via THIS entry-points mechanism +
    load_enabled_entry_points(), never via register_tool()/BaseZeoTool
    (which is a separate, tool-shaped MCP-server registration path in
    adapters/mcp/, per RULING-323 s1's MCP-server work) -- so this class,
    not a register_tool() call, is the correct and complete behavioral
    proof of discoverability."""

    @pytest.mark.usefixtures("bare_construction_env")
    def test_load_enabled_entry_points_loads_calendar_without_initializing(
        self,
    ) -> None:
        """`enabled=` and `report.loaded` key on the entry-points TABLE
        name ("google.calendar", matching "google.drive"/"google.mail"'s
        own dotted convention), but `registry.register()` keys on the
        loaded INSTANCE's own `integration_id` property ("googlecalendar"
        -- see test_integration_id_and_name_before_init's docstring above
        for why these differ, and that this is a pre-existing pattern
        verified identical for GoogleDriveService, not introduced here).
        Both keys are asserted explicitly so this real double-naming is
        pinned rather than silently glossed over."""
        registry = IntegrationRegistry()

        report = load_enabled_entry_points(
            registry=registry,
            enabled=["google.calendar"],
            strict=True,
            initialize=False,  # avoid a real network call / OAuth requirement
        )

        assert report.success is True
        assert report.loaded == ["google.calendar"]
        assert report.errors == []
        assert registry.is_registered("googlecalendar")

        loaded = registry.get_integration("googlecalendar")
        assert isinstance(loaded, GoogleCalendarService)
