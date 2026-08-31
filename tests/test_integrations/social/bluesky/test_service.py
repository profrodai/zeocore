"""Tests for BlueskyIntegration (service.py) -- the orchestration layer.

Mirrors notion/test_service.py's pattern: a mocked ConfigProviderProtocol
and an injected auth_provider double, so no real network/credential is
used. Mocks at the HTTP/SDK boundary (the session client), never the
function under test (RULING-235).
"""

from unittest.mock import MagicMock, patch

import pytest

from zeo_core.integrations.core.results import AuthResult, ConfigResult
from zeo_core.integrations.social.bluesky.facets import LinkSpan, MentionSpan
from zeo_core.integrations.social.bluesky.service import BlueskyIntegration


@pytest.fixture
def mock_config_provider() -> MagicMock:
    provider = MagicMock()
    provider.load_config.return_value = ConfigResult.success_result(
        content={
            "service_url": "https://bsky.social",
            "identifier": "alice.bsky.social",
            "app_password": "app-pw",
            "credentials_file": "unused-in-this-test.json",
        },
    )
    return provider


@pytest.fixture
def mock_auth_provider() -> MagicMock:
    provider = MagicMock()
    provider.authenticate.return_value = AuthResult.success_result(
        token="access-tok",  # noqa: S106 -- fake test value
        content={"did": "did:plc:abc123", "handle": "alice.bsky.social"},
    )
    provider.get_credentials.return_value = {
        "identifier": "alice.bsky.social",
        "did": "did:plc:abc123",
        "handle": "alice.bsky.social",
        "access_jwt": "access-tok",
        "refresh_jwt": "refresh-tok",
    }
    return provider


@pytest.fixture
def integration(
    mock_config_provider: MagicMock, mock_auth_provider: MagicMock
) -> BlueskyIntegration:
    svc = BlueskyIntegration(
        config_provider=mock_config_provider, auth_provider=mock_auth_provider
    )
    result = svc.initialize()
    assert result.success is True
    return svc


class TestBlueskyIntegrationLifecycle:
    def test_name_and_version(self, integration: BlueskyIntegration) -> None:
        assert integration.name == "Bluesky"
        assert integration.version == "1.0.0"
        assert integration.integration_id == "bluesky"

    def test_is_available_after_init(self, integration: BlueskyIntegration) -> None:
        assert integration.is_available() is True

    def test_not_available_before_init(self, mock_config_provider: MagicMock) -> None:
        svc = BlueskyIntegration(config_provider=mock_config_provider)
        assert svc.is_available() is False

    def test_post_errors_before_init(self, mock_config_provider: MagicMock) -> None:
        svc = BlueskyIntegration(config_provider=mock_config_provider)
        result = svc.post("hello")

        assert result.success is False
        assert result.error is not None
        assert "not initialized" in result.error.lower()

    def test_initialize_uses_injected_auth_provider_verbatim(
        self,
        mock_config_provider: MagicMock,
        mock_auth_provider: MagicMock,
    ) -> None:
        svc = BlueskyIntegration(
            config_provider=mock_config_provider, auth_provider=mock_auth_provider
        )
        svc.initialize()

        assert svc.auth_provider is mock_auth_provider
        mock_auth_provider.authenticate.assert_called_once_with(
            identifier="alice.bsky.social",
            app_password="app-pw",  # noqa: S106 -- fake test value
            service_url="https://bsky.social",
        )

    def test_initialize_config_load_failure(self) -> None:
        provider = MagicMock()
        provider.load_config.return_value = ConfigResult.error_result("boom")
        svc = BlueskyIntegration(config_provider=provider)

        result = svc.initialize()

        assert result.success is False
        assert result.error is not None
        assert "boom" in result.error

    def test_initialize_config_load_raises(self) -> None:
        provider = MagicMock()
        provider.load_config.side_effect = RuntimeError("config exploded")
        svc = BlueskyIntegration(config_provider=provider)

        result = svc.initialize()

        assert result.success is False
        assert result.error is not None
        assert "config exploded" in result.error

    def test_initialize_config_content_none_after_success_errors(self) -> None:
        # Defensive branch: config_result.success is True but .content is
        # None/falsy (config already set on the instance to a falsy value
        # so the `not self.config` guard lets us reach past load_config,
        # then load_config itself returns success with no content).
        provider = MagicMock()
        provider.load_config.return_value = ConfigResult.success_result(content=None)
        svc = BlueskyIntegration(config_provider=provider)

        result = svc.initialize()

        assert result.success is False
        assert result.error is not None
        assert "not available" in result.error.lower()

    def test_initialize_auth_failure_propagates(
        self, mock_config_provider: MagicMock
    ) -> None:
        auth_provider = MagicMock()
        auth_provider.authenticate.return_value = AuthResult.error_result(
            error="bad app password"
        )
        svc = BlueskyIntegration(
            config_provider=mock_config_provider, auth_provider=auth_provider
        )

        result = svc.initialize()

        assert result.success is False
        assert result.error is not None
        assert "bad app password" in result.error
        assert svc.is_available() is False

    def test_initialize_builds_default_auth_provider_when_none_injected(
        self, mock_config_provider: MagicMock
    ) -> None:
        svc = BlueskyIntegration(
            config_provider=mock_config_provider, auth_provider=None
        )

        # No injected auth provider and real network is not mocked here, so
        # this will genuinely try to authenticate against bsky.social and
        # fail (or hang without a timeout) -- assert only that a REAL
        # BlueskyAuthProvider was constructed, not that auth succeeded;
        # covered instead by the fresh-directory walkthrough test, which
        # mocks the client factory.
        from zeo_core.integrations.social.bluesky.auth import BlueskyAuthProvider

        with patch.object(BlueskyAuthProvider, "authenticate") as mock_authenticate:
            mock_authenticate.return_value = AuthResult.success_result(
                token="t"  # noqa: S106 -- fake test value
            )
            svc.initialize()

        assert isinstance(svc.auth_provider, BlueskyAuthProvider)


class TestBlueskyIntegrationPost:
    def test_post_success_calls_client_and_returns_result(
        self, integration: BlueskyIntegration, mock_auth_provider: MagicMock
    ) -> None:
        fake_client = MagicMock()
        fake_client.create_post_record.return_value = {
            "uri": "at://did:plc:abc/app.bsky.feed.post/xyz",
            "cid": "bafyabc",
        }
        mock_auth_provider.build_client.return_value = fake_client

        result = integration.post("hello world")

        assert result.success is True
        assert result.content is not None
        assert result.content["uri"] == "at://did:plc:abc/app.bsky.feed.post/xyz"
        fake_client.create_post_record.assert_called_once()
        call_kwargs = fake_client.create_post_record.call_args.kwargs
        assert call_kwargs["repo"] == "did:plc:abc123"
        assert call_kwargs["text"] == "hello world"
        assert call_kwargs["access_jwt"] == "access-tok"
        assert call_kwargs["facets"] is None

    def test_post_with_link_facet_computes_byte_offsets(
        self, integration: BlueskyIntegration, mock_auth_provider: MagicMock
    ) -> None:
        fake_client = MagicMock()
        fake_client.create_post_record.return_value = {"uri": "at://x", "cid": "y"}
        mock_auth_provider.build_client.return_value = fake_client

        text = "check https://example.com now"
        result = integration.post(
            text,
            links=[LinkSpan(text="https://example.com", uri="https://example.com")],
        )

        assert result.success is True
        facets = fake_client.create_post_record.call_args.kwargs["facets"]
        assert facets is not None
        assert len(facets) == 1
        assert facets[0]["features"][0]["uri"] == "https://example.com"

    def test_post_with_mention_facet(
        self, integration: BlueskyIntegration, mock_auth_provider: MagicMock
    ) -> None:
        fake_client = MagicMock()
        fake_client.create_post_record.return_value = {"uri": "at://x", "cid": "y"}
        mock_auth_provider.build_client.return_value = fake_client

        result = integration.post(
            "hi @alice.bsky.social",
            mentions=[MentionSpan(text="@alice.bsky.social", did="did:plc:abc")],
        )

        assert result.success is True
        facets = fake_client.create_post_record.call_args.kwargs["facets"]
        assert facets[0]["features"][0]["did"] == "did:plc:abc"

    def test_post_no_active_session_errors(
        self, mock_config_provider: MagicMock
    ) -> None:
        auth_provider = MagicMock()
        auth_provider.authenticate.return_value = AuthResult.success_result(token="t")  # noqa: S106 -- fake test value
        auth_provider.get_credentials.return_value = {}  # no did/identifier/access_jwt
        svc = BlueskyIntegration(
            config_provider=mock_config_provider, auth_provider=auth_provider
        )
        svc.initialize()

        result = svc.post("hello")

        assert result.success is False
        assert result.error is not None
        assert "no active bluesky session" in result.error.lower()

    def test_post_client_raises_returns_error_result(
        self, integration: BlueskyIntegration, mock_auth_provider: MagicMock
    ) -> None:
        fake_client = MagicMock()
        fake_client.create_post_record.side_effect = RuntimeError("network down")
        mock_auth_provider.build_client.return_value = fake_client

        result = integration.post("hello")

        assert result.success is False
        assert result.error is not None
        assert "network down" in result.error

    def test_post_uses_identifier_when_did_absent(
        self, mock_config_provider: MagicMock
    ) -> None:
        auth_provider = MagicMock()
        auth_provider.authenticate.return_value = AuthResult.success_result(token="t")  # noqa: S106 -- fake test value
        auth_provider.get_credentials.return_value = {
            "identifier": "alice.bsky.social",
            "did": None,
            "access_jwt": "tok",
        }
        fake_client = MagicMock()
        fake_client.create_post_record.return_value = {"uri": "at://x", "cid": "y"}
        auth_provider.build_client.return_value = fake_client

        svc = BlueskyIntegration(
            config_provider=mock_config_provider, auth_provider=auth_provider
        )
        svc.initialize()

        result = svc.post("hello")

        assert result.success is True
        assert (
            fake_client.create_post_record.call_args.kwargs["repo"]
            == "alice.bsky.social"
        )
