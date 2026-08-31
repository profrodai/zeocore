"""
Fresh-directory construction regression (RULING-409 s6c step 1 /
SOW social-connectors-SOW-01-fresh-directory-alignment): from a directory
with NO repo and NO config file anywhere, all three registered Google entry
points (pyproject.toml:188-190 -- google.mail, google.drive, google.calendar)
must CONSTRUCT without raising.

Reproduction this closes, run by Master and independently by Sparring before
this SOW existed:

    drive      *** ZeoConfigurationError: Configuration file not found
    mail       OK
    calendar   *** ZeoConfigurationError: Configuration file not found

Root cause, confirmed at the bytes: mail/service.py resolved config INSIDE
initialize(); drive/service.py and calendar/service.py resolved it in
__init__, so construction died before a caller could supply anything. mail
was always correct and is the in-repo reference this fix makes drive and
calendar agree with -- untouched here.

Every assertion below runs against REAL disk (a tmp_path standing in for "a
fresh directory," never the real developer machine's home directory or repo
checkout) so this test cannot pass merely because the machine running it
happens to have a config file already. That blindness -- a test that only
passes on a developer machine with a config file present -- is exactly what
this SOW exists to remove: every developer machine has a config file, so the
defect was invisible everywhere except to a genuinely fresh user, who is the
customer.

This is deliberately a CONSTRUCTION test, not an initialize() test. The
charter's done_when predicate is "construct without raising" -- initialize()
itself calling out to a real (or absent) config file is the separate,
pre-existing base.py:124 ZeoConfigurationError raise (BaseConfigProvider
.load_config), reported and explicitly out of this charter's scope, and
must not be swept in here. mail's own initialize() from a fresh directory
also fails gracefully (returns an IntegrationResult error, does not raise)
for the identical, pre-existing reason -- construction succeeding while
initialize() reports a graceful config error is the correct, matching
behavior for all three services, not a gap.
"""

from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _fresh_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[None]:
    """A directory with no repo and no config: cwd is real, empty disk
    under tmp_path, and HOME is redirected so no default config-search
    location (including `~/.zeo/config.yaml`) can resolve to the real
    developer machine's actual home directory. Clears the fs-service
    caches so a previous test's resolved sandbox root cannot leak in --
    the same isolation discipline test_fresh_directory_walkthrough.py's
    own `_isolated_singleton` fixture uses."""
    from zeo_core.core.fs.service import get_service
    from zeo_core.integrations.google import credential_paths as cp

    fresh_home = tmp_path / "fresh-home"
    fresh_home.mkdir()
    monkeypatch.setenv("HOME", str(fresh_home))
    monkeypatch.chdir(tmp_path)
    get_service.cache_clear()
    cp._scoped_service_cache.clear()
    yield
    get_service.cache_clear()
    cp._scoped_service_cache.clear()


class TestFreshDirectoryEntryPointConstruction:
    """The done_when predicate itself: bare create_integration() for all
    three registered entry points, from a fresh directory, must not raise.
    """

    def test_mail_entry_point_constructs_from_fresh_directory(
        self, tmp_path: Path
    ) -> None:
        """The in-repo reference. Was already correct; asserted here so a
        regression in mail would be caught by the same test that catches
        one in drive/calendar, rather than assumed forever."""
        assert list(tmp_path.iterdir()) == [Path(tmp_path / "fresh-home")]

        from zeo_core.integrations.google.mail import create_integration

        service = create_integration()
        assert service.name == "GoogleMail"

    def test_drive_entry_point_constructs_from_fresh_directory(
        self, tmp_path: Path
    ) -> None:
        """Was RAISING before this fix (ZeoConfigurationError, __init__
        called _initialize_config directly, service.py:71)."""
        from zeo_core.integrations.google.drive import create_integration

        service = create_integration()
        assert service.name == "GoogleDrive"

    def test_calendar_entry_point_constructs_from_fresh_directory(
        self, tmp_path: Path
    ) -> None:
        """Was RAISING before this fix (ZeoConfigurationError, __init__
        called _initialize_config directly, service.py:82)."""
        from zeo_core.integrations.google.calendar import create_integration

        service = create_integration()
        assert service.name == "GoogleCalendar"

    def test_all_three_construct_together_matching_the_original_repro(self) -> None:
        """Runs all three back to back in one process, mirroring exactly
        the loop Master and Sparring each ran independently to reproduce
        the original defect (drive raise, mail OK, calendar raise)."""
        from zeo_core.integrations.google.calendar import (
            create_integration as calendar_ci,
        )
        from zeo_core.integrations.google.drive import (
            create_integration as drive_ci,
        )
        from zeo_core.integrations.google.mail import (
            create_integration as mail_ci,
        )

        results: dict[str, bool] = {}
        for name, ci in (
            ("drive", drive_ci),
            ("mail", mail_ci),
            ("calendar", calendar_ci),
        ):
            try:
                ci()
                results[name] = True
            except Exception:  # noqa: BLE001 -- proving NO exception of any kind
                results[name] = False

        assert results == {"drive": True, "mail": True, "calendar": True}

    def test_drive_construction_does_not_touch_disk(self, tmp_path: Path) -> None:
        """A stricter form of the same regression: not only must
        construction not raise, it must not have created any config/
        credential scaffolding under the fresh directory either --
        construction is inert until initialize() is explicitly called."""
        before = set(tmp_path.iterdir())

        from zeo_core.integrations.google.drive import create_integration

        create_integration()

        after = set(tmp_path.iterdir())
        assert after == before, (
            "GoogleDriveService() wrote something to the fresh directory "
            "merely by constructing -- construction must be inert"
        )

    def test_calendar_construction_does_not_touch_disk(self, tmp_path: Path) -> None:
        before = set(tmp_path.iterdir())

        from zeo_core.integrations.google.calendar import create_integration

        create_integration()

        after = set(tmp_path.iterdir())
        assert after == before, (
            "GoogleCalendarService() wrote something to the fresh directory "
            "merely by constructing -- construction must be inert"
        )


class TestFreshDirectoryConstructionWithExplicitParams:
    """The other half of the contract: a caller who DOES have credentials
    to hand explicitly (the common real-world shape -- e.g. environment-
    supplied secrets rather than a YAML file) must also be able to
    construct from a fresh directory, matching mail's existing behavior."""

    def test_drive_constructs_with_explicit_params_from_fresh_directory(self) -> None:
        from zeo_core.integrations.google.drive.service import GoogleDriveService

        service = GoogleDriveService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        assert service.name == "GoogleDrive"
        # Deferred, not resolved yet -- confirms this is genuinely the
        # deferred-to-initialize() shape, not merely "happens not to raise."
        assert service.config == {}
        assert service.auth_provider is None

    def test_calendar_constructs_with_explicit_params_from_fresh_directory(
        self,
    ) -> None:
        from zeo_core.integrations.google.calendar.service import (
            GoogleCalendarService,
        )

        service = GoogleCalendarService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        assert service.name == "GoogleCalendar"
        assert service.config == {}
        assert service.auth_provider is None
