"""Project isolation is separate from credential identity."""

from pathlib import Path
from unittest.mock import patch

import pytest

from zeo_core.integrations.environment import IntegrationMode
from zeo_core.integrations.environments import IntegrationEnvironment


def supabase_source(test_url: str, production_url: str) -> dict[str, str]:
    return {
        "ZEO_TEST_SUPABASE_URL": test_url,
        "ZEO_PRODUCTION_SUPABASE_URL": production_url,
        "ZEO_TEST_SUPABASE_PUBLISHABLE_KEY": "synthetic-test-key",
        "ZEO_PRODUCTION_SUPABASE_PUBLISHABLE_KEY": "synthetic-production-key",
    }


@pytest.mark.parametrize("mode", ["test", "production"])
@pytest.mark.parametrize(
    "url", ["https://shared.supabase.co", "http://127.0.0.1:54321"]
)
def test_shared_project_refused_before_side_effects(
    tmp_path: Path, mode: IntegrationMode, url: str
) -> None:
    environment = IntegrationEnvironment(mode, tmp_path / "state", ("supabase",))
    with patch("zeo_core.integrations.environments.launcher.subprocess.run") as run:
        with pytest.raises(ValueError, match="different SUPABASE_URL") as error:
            environment.run(["unused-command"], source=supabase_source(url, url))
    run.assert_not_called()
    assert not environment.root.exists()
    assert url not in str(error.value)
    assert "synthetic-test-key" not in str(error.value)
    assert "synthetic-production-key" not in str(error.value)


@pytest.mark.parametrize("mode", ["test", "production"])
def test_distinct_projects_select_the_requested_track(
    tmp_path: Path, mode: IntegrationMode
) -> None:
    environment = IntegrationEnvironment(mode, tmp_path, ("supabase",))
    source = supabase_source(
        "https://test.supabase.co", "https://production.supabase.co"
    )
    child = environment.child_environment(source)
    assert child["SUPABASE_URL"] == source[f"ZEO_{mode.upper()}_SUPABASE_URL"]
    assert (
        child["SUPABASE_PUBLISHABLE_KEY"]
        == source[f"ZEO_{mode.upper()}_SUPABASE_PUBLISHABLE_KEY"]
    )
    del source[f"ZEO_{'PRODUCTION' if mode == 'test' else 'TEST'}_SUPABASE_URL"]
    assert environment.child_environment(source) == child


@pytest.mark.parametrize("mode", ["test", "production"])
def test_shared_bluesky_endpoint_with_distinct_accounts_is_supported(
    tmp_path: Path, mode: IntegrationMode
) -> None:
    source = {
        f"ZEO_{track}_BLUESKY_{name}": value
        for track in ("TEST", "PRODUCTION")
        for name, value in {
            "SERVICE_URL": "https://bsky.social",
            "IDENTIFIER": f"{track.lower()}.bsky.social",
            "APP_PASSWORD": f"synthetic-{track.lower()}-password",
        }.items()
    }
    child = IntegrationEnvironment(
        mode, tmp_path, ("social.bluesky",)
    ).child_environment(source)
    assert child["BLUESKY_SERVICE_URL"] == "https://bsky.social"
    assert child["BLUESKY_IDENTIFIER"] == f"{mode}.bsky.social"
    assert child["BLUESKY_APP_PASSWORD"] == f"synthetic-{mode}-password"


def test_fixture_strips_shared_project_inputs(tmp_path: Path) -> None:
    child = IntegrationEnvironment(
        "test", tmp_path, ("supabase",), backend="fixture"
    ).child_environment(
        supabase_source("https://shared.supabase.co", "https://shared.supabase.co")
    )
    assert not any("SUPABASE" in name for name in child)


def test_unselected_provider_does_not_block_launch(tmp_path: Path) -> None:
    child = IntegrationEnvironment(
        "test", tmp_path, ("kit.marketing",)
    ).child_environment(
        supabase_source("https://shared.supabase.co", "https://shared.supabase.co")
    )
    assert not any("SUPABASE" in name for name in child)
