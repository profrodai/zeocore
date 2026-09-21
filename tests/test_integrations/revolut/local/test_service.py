"""The entry point selects the local profile from configuration only."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from pydantic import SecretStr

from zeo_core.integrations.revolut import (
    RevolutBusinessIntegration,
    RevolutEnvironment,
    create_integration,
)
from zeo_core.integrations.revolut.local import LocalRevolutEnrollment, TokenGrant


def test_initialize_needs_an_explicit_environment_and_a_completed_enrollment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "zeo_core.integrations.revolut.local.session.default_directory",
        lambda environment: tmp_path / environment.value,
    )
    integration = create_integration()
    assert isinstance(integration, RevolutBusinessIntegration)
    assert not integration.is_available()
    with pytest.raises(ValueError, match="not initialized"):
        _ = integration.enrollment

    monkeypatch.delenv("REVOLUT_ENVIRONMENT", raising=False)
    assert "REVOLUT_ENVIRONMENT" in (integration.initialize().error or "")
    monkeypatch.setenv("REVOLUT_ENVIRONMENT", "staging")
    assert not integration.initialize().success
    monkeypatch.setenv("REVOLUT_ENVIRONMENT", "sandbox")
    assert "Not enrolled" in (integration.initialize().error or "")
    assert not integration.is_available()

    # No token variable exists: a secret in the environment is never consulted.
    monkeypatch.setenv("REVOLUT_ACCESS_TOKEN", "ignored")
    assert not integration.initialize().success


class _Gateway:
    def exchange(self, **_: object) -> TokenGrant:
        return TokenGrant(
            access_token=SecretStr("access"),
            refresh_token=SecretStr("refresh"),
            expires_in=2400,
        )

    def refresh(self, **_: object) -> TokenGrant:
        raise AssertionError("initialization must not contact the provider")


def test_initialize_succeeds_once_enrolled_without_contacting_the_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "zeo_core.integrations.revolut.local.session.default_directory",
        lambda environment: tmp_path / environment.value,
    )
    redirect = "https://example.test/callback"
    enrollment = LocalRevolutEnrollment(RevolutEnvironment.SANDBOX, gateway=_Gateway())
    enrollment.setup(redirect_uri=redirect)
    url = enrollment.authorize(client_id="client-id")
    state = parse_qs(urlsplit(url).query)["state"][0]
    enrollment.complete(f"{redirect}?code=c&state={state}")

    monkeypatch.setenv("REVOLUT_ENVIRONMENT", "sandbox")
    integration = create_integration()
    result = integration.initialize()
    assert result.success and "unverified" in (result.message or "")
    assert integration.is_available()
    assert isinstance(integration.enrollment, LocalRevolutEnrollment)
    # Production is a separate enrollment; sandbox tokens never serve it.
    monkeypatch.setenv("REVOLUT_ENVIRONMENT", "production")
    assert not create_integration().initialize().success
