"""
Tests for GoogleSlidesService.

Mocks at the Google SDK boundary: `googleapiclient.discovery.build`'s
return value is a `MagicMock()` shaped like the real Slides v1 Resource
(`.presentations().get/create/batchUpdate(...).execute()`), matching
`docs/test_service.py`'s house style -- NOT `patch.object(service,
"get_presentation")`, which the spawn brief explicitly calls out (via the
docs precedent) as a weak anti-pattern that proves nothing about the real
implementation. No real Google API token or network access is required to
pass.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from zeo_core.integrations.google.slides.protocols import SlidesIntegrationProtocol
from zeo_core.integrations.google.slides.service import GoogleSlidesService


def _make_initialized_service(mock_build: MagicMock) -> GoogleSlidesService:
    """Construct a GoogleSlidesService and drive it through initialize()
    with the Slides API client mocked, returning the initialized service
    with its mock slides_service attached for assertion.

    Mirrors `docs/test_service.py::_make_initialized_service` exactly --
    see that function's docstring for why `BaseIntegrationService.
    initialize` must be patched directly (its own eager config-loading
    check would otherwise try to load a real config file in a bare test
    environment).
    """
    mock_slides_service = MagicMock()
    mock_build.return_value = mock_slides_service

    with (
        patch(
            "zeo_core.integrations.core.base.BaseIntegrationService.initialize"
        ) as mock_base_init,
        patch(
            "zeo_core.integrations.google.auth.GoogleAuthProvider."
            "_verify_client_secrets_file"
        ),
        patch(
            "zeo_core.integrations.google.auth.GoogleAuthProvider.authenticate"
        ) as mock_auth,
        patch(
            "zeo_core.integrations.google.auth.GoogleAuthProvider.get_credentials"
        ) as mock_creds,
    ):
        from zeo_core.integrations.core.results import IntegrationResult

        mock_base_init.return_value = IntegrationResult.success_result()
        mock_auth.return_value.success = True
        mock_creds.return_value = MagicMock()

        service = GoogleSlidesService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.initialize()
        assert result.success is True
        assert service.slides_service is mock_slides_service
    return service


# ---------------------------------------------------------------------
# Construction / deferred config (RULING-408 item 4)
# ---------------------------------------------------------------------


class TestGoogleSlidesServiceFreshDirectoryConstruction:
    """The required RELEASE-BAR acceptance test for the deferred-config
    pattern: constructing the service from a directory with NO config
    file and NO repo must never raise. Only initialize() may fail later.
    `HOME` is also redirected to a fresh, empty tmp_path, per the spawn
    brief's explicit instruction that this must never touch the real home
    directory."""

    def test_fresh_directory_construction_does_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        fake_cwd = tmp_path / "cwd"
        fake_cwd.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))
        monkeypatch.chdir(fake_cwd)
        # No client_secrets_file/credentials_file, no config_path, no
        # zeo_config.yaml anywhere in this fresh tmp_path, no real HOME --
        # construction must still succeed by deferred-config construction.
        service = GoogleSlidesService()
        assert service._initialized is False
        assert service.slides_service is None
        assert service.auth_provider is None

    def test_fresh_directory_construction_with_explicit_params(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        fake_cwd = tmp_path / "cwd"
        fake_cwd.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))
        monkeypatch.chdir(fake_cwd)
        service = GoogleSlidesService(
            client_secrets_file="secrets.json",
            credentials_file="creds.json",
        )
        assert service.custom_config["client_secrets_file"] == "secrets.json"
        assert service._initialized is False


class TestGoogleSlidesServiceInit:
    """Tests for GoogleSlidesService construction (not fresh-directory
    specific)."""

    def test_init_basic_properties(self) -> None:
        service = GoogleSlidesService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        assert service.name == "GoogleSlides"
        assert service.version == "1.0.0"
        assert service._initialized is False
        assert service.scopes == GoogleSlidesService.SCOPES

    def test_init_scope_is_narrower_than_drive(self) -> None:
        """RULING-405/406's narrower-than-Drive clause, verified live
        against the Slides discovery document: the default scope must be
        `auth/presentations`, not Drive's broader `.../auth/drive`."""
        service = GoogleSlidesService()
        assert service.scopes == ["https://www.googleapis.com/auth/presentations"]
        assert "https://www.googleapis.com/auth/drive" not in service.scopes

    def test_init_custom_scopes(self) -> None:
        custom_scopes = ["https://www.googleapis.com/auth/presentations.readonly"]
        service = GoogleSlidesService(scopes=custom_scopes)
        assert service.scopes == custom_scopes

    def test_init_no_eager_config_provider_calls(self) -> None:
        """Deferred config: __init__ constructs a real config_provider
        object but never CALLS load_config()/get_default_config() on it --
        those calls happen only inside initialize()."""
        with patch(
            "zeo_core.integrations.google.config.GoogleConfigProvider.load_config"
        ) as mock_load_config:
            GoogleSlidesService()
            mock_load_config.assert_not_called()

    def test_init_always_constructs_real_config_provider(self) -> None:
        service = GoogleSlidesService()
        assert service.config_provider is not None
        assert type(service.config_provider).__name__ == "GoogleConfigProvider"
        # Unlike drive/calendar's eager pattern, auth_provider is NOT
        # constructed in __init__ -- only inside initialize().
        assert service.auth_provider is None

    def test_is_slides_integration_protocol(self) -> None:
        service = GoogleSlidesService()
        assert isinstance(service, SlidesIntegrationProtocol)

    def test_custom_config_short_circuits_file_loading(self) -> None:
        service = GoogleSlidesService(
            client_secrets_file="/a/secrets.json",
            credentials_file="/a/creds.json",
        )
        assert service.custom_config == {
            "client_secrets_file": "/a/secrets.json",
            "credentials_file": "/a/creds.json",
        }

    def test_no_custom_config_when_only_one_param_given(self) -> None:
        service = GoogleSlidesService(client_secrets_file="/a/secrets.json")
        assert service.custom_config == {}


# ---------------------------------------------------------------------
# initialize() lifecycle
# ---------------------------------------------------------------------


class TestGoogleSlidesServiceInitializeLifecycle:
    """`GoogleSlidesService.__init__` leaves `self.config == {}` (deferred
    config). `BaseIntegrationService.initialize()` -- the `super().
    initialize()` call at the top of `GoogleSlidesService.initialize()` --
    has its own eager `if not self.config and self.config_provider: ...
    load_config...` check that would otherwise try to load a real config
    file in every test below; each test here patches it to succeed so the
    assertions focus on what THIS class's own `initialize()` does
    afterward, exactly matching `docs/test_service.py`'s identical shape.
    """

    @patch("zeo_core.integrations.core.base.BaseIntegrationService.initialize")
    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.authenticate")
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.get_credentials")
    @patch("googleapiclient.discovery.build")
    def test_initialize_success(
        self,
        mock_build: MagicMock,
        mock_get_credentials: MagicMock,
        mock_authenticate: MagicMock,
        mock_verify: MagicMock,
        mock_base_init: MagicMock,
    ) -> None:
        from zeo_core.integrations.core.results import IntegrationResult

        mock_base_init.return_value = IntegrationResult.success_result()
        mock_verify.return_value = None
        mock_authenticate.return_value.success = True
        mock_credentials = MagicMock()
        mock_get_credentials.return_value = mock_credentials
        mock_slides_service = MagicMock()
        mock_build.return_value = mock_slides_service

        service = GoogleSlidesService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.initialize()

        assert result.success is True
        assert service._initialized is True
        assert service.slides_service is mock_slides_service
        mock_build.assert_called_once_with("slides", "v1", credentials=mock_credentials)

    def test_initialize_config_failure_returns_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No config file anywhere and no explicit params: initialize()
        fails gracefully with an error_result, not an exception."""
        monkeypatch.chdir(tmp_path)
        service = GoogleSlidesService()
        result = service.initialize()
        assert result.success is False
        assert result.error is not None

    @patch("zeo_core.integrations.core.base.BaseIntegrationService.initialize")
    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.authenticate")
    def test_initialize_auth_error(
        self,
        mock_authenticate: MagicMock,
        mock_verify: MagicMock,
        mock_base_init: MagicMock,
    ) -> None:
        from zeo_core.integrations.core.results import IntegrationResult

        mock_base_init.return_value = IntegrationResult.success_result()
        mock_verify.return_value = None
        mock_authenticate.return_value.success = False
        mock_authenticate.return_value.error = "Auth error"

        service = GoogleSlidesService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.initialize()

        assert result.success is False
        assert result.error is not None
        assert "No valid Google credentials available" in result.error

    @patch("zeo_core.integrations.core.base.BaseIntegrationService.initialize")
    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.authenticate")
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.get_credentials")
    def test_initialize_credentials_error(
        self,
        mock_get_credentials: MagicMock,
        mock_authenticate: MagicMock,
        mock_verify: MagicMock,
        mock_base_init: MagicMock,
    ) -> None:
        from zeo_core.integrations.core.results import IntegrationResult

        mock_base_init.return_value = IntegrationResult.success_result()
        mock_verify.return_value = None
        mock_authenticate.return_value.success = True
        mock_get_credentials.side_effect = Exception("Creds error")

        service = GoogleSlidesService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.initialize()

        assert result.success is False
        assert result.error is not None
        assert "Creds error" in result.error

    @patch("zeo_core.integrations.core.base.BaseIntegrationService.initialize")
    def test_initialize_config_none_returns_error(
        self, mock_base_init: MagicMock
    ) -> None:
        from zeo_core.integrations.core.results import IntegrationResult

        mock_base_init.return_value = IntegrationResult.success_result()

        service = GoogleSlidesService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        with patch.object(service, "_initialize_config", return_value=None):
            result = service.initialize()

        assert result.success is False
        assert result.error is not None
        assert "Failed to initialize configuration" in result.error
        assert service._initialized is False

    @patch("zeo_core.integrations.core.base.BaseIntegrationService.initialize")
    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.authenticate")
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.get_credentials")
    def test_initialize_get_credentials_raises_zeo_base_auth_error(
        self,
        mock_get_credentials: MagicMock,
        mock_authenticate: MagicMock,
        mock_verify: MagicMock,
        mock_base_init: MagicMock,
    ) -> None:
        from zeo_core.core.errors import ZeoBaseAuthError
        from zeo_core.integrations.core.results import IntegrationResult

        mock_base_init.return_value = IntegrationResult.success_result()
        mock_verify.return_value = None
        mock_authenticate.return_value.success = True
        mock_get_credentials.side_effect = ZeoBaseAuthError("bad auth")

        service = GoogleSlidesService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.initialize()

        assert result.success is False
        assert result.error is not None
        assert "Failed to authenticate with Google Slides" in result.error
        assert "bad auth" in result.error

    @patch("zeo_core.integrations.core.base.BaseIntegrationService.initialize")
    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.authenticate")
    @patch("zeo_core.integrations.google.auth.GoogleAuthProvider.get_credentials")
    @patch("googleapiclient.discovery.build")
    def test_initialize_api_build_error(
        self,
        mock_build: MagicMock,
        mock_get_credentials: MagicMock,
        mock_authenticate: MagicMock,
        mock_verify: MagicMock,
        mock_base_init: MagicMock,
    ) -> None:
        from zeo_core.integrations.core.results import IntegrationResult

        mock_base_init.return_value = IntegrationResult.success_result()
        mock_verify.return_value = None
        mock_authenticate.return_value.success = True
        mock_get_credentials.return_value = MagicMock()
        mock_build.side_effect = Exception("API error")

        service = GoogleSlidesService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.initialize()

        assert result.success is False
        assert result.error is not None
        assert "API error" in result.error

    @patch(
        "zeo_core.integrations.google.auth.GoogleAuthProvider._verify_client_secrets_file"
    )
    def test_auto_initialize_error_surfaces_from_read_call(
        self, mock_verify: MagicMock
    ) -> None:
        mock_verify.return_value = None
        service = GoogleSlidesService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.get_presentation("pres1")
        assert result.success is False

    def test_require_config_provider_raises_when_none(self) -> None:
        from zeo_core.core.errors import ZeoIntegrationError

        service = GoogleSlidesService(config_path="/path/to/config.yaml")
        service.config_provider = None
        with pytest.raises(ZeoIntegrationError, match="no config_provider configured"):
            service._require_config_provider()

    def test_initialize_config_load_from_file_failure(self) -> None:
        from zeo_core.core.errors import ZeoIntegrationError

        service = GoogleSlidesService(config_path="/path/to/config.yaml")
        with patch.object(service.config_provider, "load_config") as mock_load_config:
            mock_load_config.return_value = MagicMock(success=False, content=None)
            with pytest.raises(
                ZeoIntegrationError, match="Failed to load configuration"
            ):
                service._initialize_config()

    def test_initialize_config_unexpected_exception_returns_none(self) -> None:
        service = GoogleSlidesService(config_path="/path/to/config.yaml")
        with (
            patch.object(service.config_provider, "load_config") as mock_load_config,
            patch.object(service.logger, "error") as mock_error,
        ):
            mock_load_config.side_effect = RuntimeError("unexpected boom")

            result = service._initialize_config()

            assert result is None
            mock_error.assert_called_once()

    @patch("googleapiclient.discovery.build")
    def test_initialize_called_twice_reruns_body_but_still_succeeds(
        self, mock_build: MagicMock
    ) -> None:
        from zeo_core.integrations.core.results import IntegrationResult

        with (
            patch(
                "zeo_core.integrations.core.base.BaseIntegrationService.initialize"
            ) as mock_base_init,
            patch(
                "zeo_core.integrations.google.auth.GoogleAuthProvider."
                "_verify_client_secrets_file"
            ),
            patch(
                "zeo_core.integrations.google.auth.GoogleAuthProvider.authenticate"
            ) as mock_auth,
            patch(
                "zeo_core.integrations.google.auth.GoogleAuthProvider.get_credentials"
            ) as mock_creds,
        ):
            mock_base_init.return_value = IntegrationResult.success_result()
            mock_auth.return_value.success = True
            mock_creds.return_value = MagicMock()
            mock_build.return_value = MagicMock()

            service = GoogleSlidesService(
                client_secrets_file="/path/to/secrets.json",
                credentials_file="/path/to/credentials.json",
            )
            first_result = service.initialize()
            assert first_result.success is True

            second_result = service.initialize()
            assert second_result.success is True
            # Re-ran, not short-circuited: build() was called again.
            assert mock_build.call_count == 2

    def test_initialize_config_loaded_from_file_success_path(self) -> None:
        service = GoogleSlidesService(config_path="/path/to/config.yaml")
        with patch.object(service.config_provider, "load_config") as mock_load_config:
            mock_load_config.return_value = MagicMock(
                success=True,
                content={
                    "client_secrets_file": "/config/secrets.json",
                    "credentials_file": "/config/credentials.json",
                },
            )
            result = service._initialize_config()
            assert result is not None
            assert result["client_secrets_file"] == "/config/secrets.json"
            assert service.config["credentials_file"] == "/config/credentials.json"


# ---------------------------------------------------------------------
# get_presentation
# ---------------------------------------------------------------------


class TestGoogleSlidesServiceGetPresentation:
    @patch("googleapiclient.discovery.build")
    def test_get_presentation_calls_sdk_with_presentation_id(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        service.slides_service.presentations().get().execute.return_value = {
            "presentationId": "pres123",
            "title": "Test Deck",
            "slides": [],
        }

        result = service.get_presentation("pres123")

        assert result.success is True
        assert result.content is not None
        assert result.content["presentationId"] == "pres123"
        service.slides_service.presentations().get.assert_called_with(
            presentationId="pres123"
        )

    @patch("googleapiclient.discovery.build")
    def test_get_presentation_api_error(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.slides_service.presentations().get().execute.side_effect = Exception(
            "not found"
        )

        result = service.get_presentation("missing")

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error

    def test_get_presentation_service_none(self) -> None:
        service = GoogleSlidesService()
        service._initialized = True
        service.slides_service = None

        result = service.get_presentation("pres1")
        assert result.success is False
        assert result.error is not None
        assert "not initialized" in result.error


# ---------------------------------------------------------------------
# create_presentation
# ---------------------------------------------------------------------


class TestGoogleSlidesServiceCreatePresentation:
    @patch("googleapiclient.discovery.build")
    def test_create_presentation_calls_sdk_with_title(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        service.slides_service.presentations().create().execute.return_value = {
            "presentationId": "new-pres",
            "title": "My Title",
        }

        result = service.create_presentation("My Title")

        assert result.success is True
        assert result.content is not None
        assert result.content["presentationId"] == "new-pres"
        service.slides_service.presentations().create.assert_called_with(
            body={"title": "My Title"}
        )

    @patch("googleapiclient.discovery.build")
    def test_create_presentation_api_error(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.slides_service.presentations().create().execute.side_effect = Exception(
            "create failed"
        )

        result = service.create_presentation("Title")

        assert result.success is False
        assert result.error is not None
        assert "create failed" in result.error

    def test_create_presentation_service_none(self) -> None:
        service = GoogleSlidesService()
        service._initialized = True
        service.slides_service = None

        result = service.create_presentation("Title")
        assert result.success is False
        assert "not initialized" in (result.error or "")

    def test_create_presentation_auto_initialize_error_surfaces(self) -> None:
        service = GoogleSlidesService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.create_presentation("Title")
        assert result.success is False


# ---------------------------------------------------------------------
# batch_update -- ORDER-PRESERVING policy (required specific test,
# opposite of Docs' reverse-sort -- see request_builder.py's docstring)
# ---------------------------------------------------------------------


class TestGoogleSlidesServiceBatchUpdate:
    @patch("googleapiclient.discovery.build")
    def test_batch_update_preserves_caller_order_for_create_then_reference_chain(
        self, mock_build: MagicMock
    ) -> None:
        """THE required specific test per the spawn brief: build a batch
        where request N+1 references an objectId created by request N,
        and assert the emitted order is UNCHANGED -- i.e. NOT reordered
        the way DocsRequestBuilder would reorder by index. This is the
        single most important behavioral test in this package: it is what
        proves this service did not copy the Docs builder's sort."""
        service = _make_initialized_service(mock_build)
        service.slides_service.presentations().batchUpdate().execute.return_value = {
            "presentationId": "pres1",
            "replies": [],
        }

        slide_id = "slide_1"
        shape_id = "shape_1"
        ordered_input: list[dict[str, Any]] = [
            {"createSlide": {"objectId": slide_id}},
            {
                "createShape": {
                    "objectId": shape_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {"pageObjectId": slide_id},
                }
            },
            {"insertText": {"objectId": shape_id, "text": "Q3 review"}},
        ]

        result = service.batch_update("pres1", ordered_input)

        assert result.success is True
        _, kwargs = service.slides_service.presentations().batchUpdate.call_args
        assert kwargs["presentationId"] == "pres1"
        sent_requests = kwargs["body"]["requests"]

        # Exact order preserved -- not sorted by any key.
        assert sent_requests == ordered_input
        assert "createSlide" in sent_requests[0]
        assert "createShape" in sent_requests[1]
        assert "insertText" in sent_requests[2]

    @patch("googleapiclient.discovery.build")
    def test_batch_update_api_error(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.slides_service.presentations().batchUpdate().execute.side_effect = (
            Exception("batch failed")
        )

        result = service.batch_update(
            "pres1", [{"createSlide": {"objectId": "slide_1"}}]
        )

        assert result.success is False
        assert result.error is not None
        assert "batch failed" in result.error

    def test_batch_update_service_none(self) -> None:
        service = GoogleSlidesService()
        service._initialized = True
        service.slides_service = None

        result = service.batch_update("pres1", [])
        assert result.success is False
        assert "not initialized" in (result.error or "")

    def test_batch_update_auto_initialize_error_surfaces(self) -> None:
        service = GoogleSlidesService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.batch_update("pres1", [])
        assert result.success is False


# ---------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------


class TestGoogleSlidesServiceValidateConfig:
    def test_validate_config_success(self) -> None:
        service = GoogleSlidesService()
        valid, errors = service.validate_config(
            {
                "client_secrets_file": "/secrets.json",
                "credentials_file": "/creds.json",
            }
        )
        assert valid is True
        assert errors == []

    def test_validate_config_failure(self) -> None:
        service = GoogleSlidesService()
        valid, errors = service.validate_config({})
        assert valid is False
        assert len(errors) == 1
        assert "Configuration validation failed" in errors[0]
