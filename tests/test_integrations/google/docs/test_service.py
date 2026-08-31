"""
Tests for GoogleDocsService.

Mocks at the Google SDK boundary: `googleapiclient.discovery.build`'s
return value is a `MagicMock()` shaped like the real Docs v1 Resource
(`.documents().get/create/batchUpdate(...).execute()`), matching
`calendar/test_service.py`'s house style -- NOT `patch.object(service,
"get_document")`, which the spawn brief explicitly calls out as a weak
anti-pattern (seen in drive/test_drive_service_download.py) that proves
nothing about the real implementation. No real Google API token or network
access is required to pass.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from zeo_core.integrations.google.docs.protocols import DocsIntegrationProtocol
from zeo_core.integrations.google.docs.service import GoogleDocsService


def _make_initialized_service(mock_build: MagicMock) -> GoogleDocsService:
    """Construct a GoogleDocsService and drive it through initialize()
    with the Docs API client mocked, returning the initialized service
    with its mock docs_service attached for assertion.

    `GoogleDocsService.__init__` (deferred-config, like `google.mail`'s own
    precedent) leaves `self.config == {}` even when `custom_config` is set
    -- `custom_config` is only consulted inside this class's own
    `_initialize_config()`. `BaseIntegrationService.initialize()` (the
    `super().initialize()` call at the top of `GoogleDocsService.
    initialize()`) runs BEFORE that and has its own, separate eager check
    (`if not self.config and self.config_provider: ...load_config...`)
    that would try to load a real config file and fail in a bare test
    environment with no config file on disk. `google/mail/test_mail_
    service.py::test_initialize` hits this identical shape and fixes it by
    patching `BaseIntegrationService.initialize` directly -- matched here
    rather than inventing a different workaround.
    """
    mock_docs_service = MagicMock()
    mock_build.return_value = mock_docs_service

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

        service = GoogleDocsService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.initialize()
        assert result.success is True
        assert service.docs_service is mock_docs_service
    return service


# ---------------------------------------------------------------------
# Construction / deferred config (RULING-408 item 4)
# ---------------------------------------------------------------------


class TestGoogleDocsServiceFreshDirectoryConstruction:
    """The required acceptance test for the deferred-config pattern:
    constructing the service from a directory with NO config file and NO
    repo must never raise. Only initialize() may fail later."""

    def test_fresh_directory_construction_does_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        # No client_secrets_file/credentials_file, no config_path, no
        # zeo_config.yaml anywhere in this fresh tmp_path -- construction
        # must still succeed by deferred-config construction.
        service = GoogleDocsService()
        assert service._initialized is False
        assert service.docs_service is None
        assert service.auth_provider is None

    def test_fresh_directory_construction_with_explicit_params(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        service = GoogleDocsService(
            client_secrets_file="secrets.json",
            credentials_file="creds.json",
        )
        assert service.custom_config["client_secrets_file"] == "secrets.json"
        assert service._initialized is False


class TestGoogleDocsServiceInit:
    """Tests for GoogleDocsService construction (not fresh-directory
    specific)."""

    def test_init_basic_properties(self) -> None:
        service = GoogleDocsService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        assert service.name == "GoogleDocs"
        assert service.version == "1.0.0"
        assert service._initialized is False
        assert service.scopes == GoogleDocsService.SCOPES

    def test_init_scope_is_narrower_than_drive(self) -> None:
        """RULING-408 item 5: the default scope must be narrower than
        Drive's `.../auth/drive` -- specifically the read-write documents
        scope, not the Drive-wide scope."""
        service = GoogleDocsService()
        assert service.scopes == ["https://www.googleapis.com/auth/documents"]
        assert "https://www.googleapis.com/auth/drive" not in service.scopes

    def test_init_custom_scopes(self) -> None:
        custom_scopes = ["https://www.googleapis.com/auth/documents.readonly"]
        service = GoogleDocsService(scopes=custom_scopes)
        assert service.scopes == custom_scopes

    def test_init_no_eager_config_provider_calls(self) -> None:
        """Deferred config: __init__ constructs a real config_provider
        object but never CALLS load_config()/get_default_config() on it --
        those calls happen only inside initialize()."""
        with patch(
            "zeo_core.integrations.google.config.GoogleConfigProvider.load_config"
        ) as mock_load_config:
            GoogleDocsService()
            mock_load_config.assert_not_called()

    def test_init_always_constructs_real_config_provider(self) -> None:
        service = GoogleDocsService()
        assert service.config_provider is not None
        assert type(service.config_provider).__name__ == "GoogleConfigProvider"
        # Unlike drive/calendar's eager pattern, auth_provider is NOT
        # constructed in __init__ -- only inside initialize().
        assert service.auth_provider is None

    def test_is_docs_integration_protocol(self) -> None:
        service = GoogleDocsService()
        assert isinstance(service, DocsIntegrationProtocol)

    def test_custom_config_short_circuits_file_loading(self) -> None:
        service = GoogleDocsService(
            client_secrets_file="/a/secrets.json",
            credentials_file="/a/creds.json",
        )
        assert service.custom_config == {
            "client_secrets_file": "/a/secrets.json",
            "credentials_file": "/a/creds.json",
        }

    def test_no_custom_config_when_only_one_param_given(self) -> None:
        service = GoogleDocsService(client_secrets_file="/a/secrets.json")
        assert service.custom_config == {}


# ---------------------------------------------------------------------
# initialize() lifecycle
# ---------------------------------------------------------------------


class TestGoogleDocsServiceInitializeLifecycle:
    """`GoogleDocsService.__init__` leaves `self.config == {}` (deferred
    config, matching `google/mail/service.py`'s own precedent -- see
    `_make_initialized_service`'s docstring above for the full mechanics).
    `BaseIntegrationService.initialize()` -- the `super().initialize()`
    call at the top of `GoogleDocsService.initialize()` -- has its own
    eager `if not self.config and self.config_provider: ...load_config...`
    check that would otherwise try to load a real config file in every
    test below; each test here patches it to succeed so the assertions
    focus on what THIS class's own `initialize()` does afterward, exactly
    matching `google/mail/test_mail_service.py::test_initialize`'s shape.
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
        mock_docs_service = MagicMock()
        mock_build.return_value = mock_docs_service

        service = GoogleDocsService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.initialize()

        assert result.success is True
        assert service._initialized is True
        assert service.docs_service is mock_docs_service
        mock_build.assert_called_once_with("docs", "v1", credentials=mock_credentials)

    def test_initialize_config_failure_returns_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No config file anywhere and no explicit params: initialize()
        fails gracefully with an error_result, not an exception."""
        monkeypatch.chdir(tmp_path)
        service = GoogleDocsService()
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
        """Unlike calendar/drive's eager pattern (where `auth_provider`
        exists at `super().initialize()` time and that base-class method
        has its own early auth check that fires first), this service's
        `auth_provider` is `None` until THIS class's own `initialize()`
        constructs it -- so the failure surfaces from THIS class's own
        `get_credentials()` call, wrapped in its own generic `except
        Exception` branch (```GoogleAuthProvider.get_credentials()`` raises
        `ZeoIntegrationError`, not `ZeoBaseAuthError`, when `authenticate()`
        reports failure -- so the `except ZeoBaseAuthError` branch does not
        apply here either)."""
        from zeo_core.integrations.core.results import IntegrationResult

        mock_base_init.return_value = IntegrationResult.success_result()
        mock_verify.return_value = None
        mock_authenticate.return_value.success = False
        mock_authenticate.return_value.error = "Auth error"

        service = GoogleDocsService(
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

        service = GoogleDocsService(
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
        """Covers service.py:202-206 -- `_initialize_config()` returning
        `None` (its own broad-exception-swallowing failure path) makes
        `initialize()` return an error_result and reset `_initialized` to
        False, without ever reaching auth/build."""
        from zeo_core.integrations.core.results import IntegrationResult

        mock_base_init.return_value = IntegrationResult.success_result()

        service = GoogleDocsService(
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
        """Covers service.py:225-229 -- the inner `except ZeoBaseAuthError`
        branch specifically (distinct from the generic-Exception path
        `test_initialize_credentials_error` above covers): when
        `get_credentials()` raises `ZeoBaseAuthError` itself (rather than a
        bare `Exception`), the message is prefixed with "Failed to
        authenticate with Google Docs"."""
        from zeo_core.core.errors import ZeoBaseAuthError
        from zeo_core.integrations.core.results import IntegrationResult

        mock_base_init.return_value = IntegrationResult.success_result()
        mock_verify.return_value = None
        mock_authenticate.return_value.success = True
        mock_get_credentials.side_effect = ZeoBaseAuthError("bad auth")

        service = GoogleDocsService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.initialize()

        assert result.success is False
        assert result.error is not None
        assert "Failed to authenticate with Google Docs" in result.error
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

        service = GoogleDocsService(
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
        """A method called before initialize() auto-initializes via
        _ensure_initialized, and a real init failure (no credentials file
        wired up in this test) surfaces as an error_result rather than an
        unhandled exception."""
        mock_verify.return_value = None
        service = GoogleDocsService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.get_document("doc1")
        assert result.success is False

    def test_require_config_provider_raises_when_none(self) -> None:
        """__init__ always constructs a real GoogleConfigProvider before
        super().__init__ runs, so _require_config_provider's own `if
        self.config_provider is None` guard can never fire in production.
        Directly force the structurally-impossible state to exercise the
        guard's own raise, same defensive-branch-testing discipline as
        mail/test_mail_service.py's identical test."""
        from zeo_core.core.errors import ZeoIntegrationError

        service = GoogleDocsService(config_path="/path/to/config.yaml")
        service.config_provider = None
        with pytest.raises(ZeoIntegrationError, match="no config_provider configured"):
            service._require_config_provider()

    def test_initialize_config_load_from_file_failure(self) -> None:
        from zeo_core.core.errors import ZeoIntegrationError

        service = GoogleDocsService(config_path="/path/to/config.yaml")
        with patch.object(service.config_provider, "load_config") as mock_load_config:
            mock_load_config.return_value = MagicMock(success=False, content=None)
            with pytest.raises(
                ZeoIntegrationError, match="Failed to load configuration"
            ):
                service._initialize_config()

    def test_initialize_config_unexpected_exception_returns_none(self) -> None:
        service = GoogleDocsService(config_path="/path/to/config.yaml")
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
        """`BaseIntegrationService.initialize()` (the un-mocked
        `super().initialize()` call) itself short-circuits to a success
        result when `self._initialized` is already True -- but per this
        class's own `initialize()` body (matching `google/mail/service.py`
        exactly), a truthy `init_result.success` does not itself skip the
        rest of THIS class's own initialize() body; it re-runs
        `_initialize_config()`/auth/build again on every call. This is a
        pre-existing characteristic of the deferred-config `initialize()`
        shape (already present in `google/mail/service.py`, not introduced
        here), so this test pins the real (non-idempotent-body) behavior:
        calling initialize() a second time, with the same mocks still
        active, re-authenticates and re-builds the client but still
        succeeds."""
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

            service = GoogleDocsService(
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
        """Covers service.py:180 -- when custom_config is empty (no
        explicit client_secrets_file/credentials_file passed to __init__),
        `_initialize_config` loads via `config_provider.load_config(...)`
        and assigns the loaded content to `self.config`."""
        service = GoogleDocsService(config_path="/path/to/config.yaml")
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
# get_document / get_document_text (recursive text extraction)
# ---------------------------------------------------------------------


class TestGoogleDocsServiceGetDocument:
    @patch("googleapiclient.discovery.build")
    def test_get_document_calls_sdk_with_document_id(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        service.docs_service.documents().get().execute.return_value = {
            "documentId": "doc123",
            "title": "Test Doc",
            "body": {"content": []},
        }

        result = service.get_document("doc123")

        assert result.success is True
        assert result.content is not None
        assert result.content["documentId"] == "doc123"
        service.docs_service.documents().get.assert_called_with(documentId="doc123")

    @patch("googleapiclient.discovery.build")
    def test_get_document_api_error(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.docs_service.documents().get().execute.side_effect = Exception(
            "not found"
        )

        result = service.get_document("missing")

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error

    def test_get_document_service_none(self) -> None:
        service = GoogleDocsService()
        service._initialized = True
        service.docs_service = None

        result = service.get_document("doc1")
        assert result.success is False
        assert result.error is not None
        assert "not initialized" in result.error


class TestGoogleDocsServiceTextExtraction:
    """The recursive body-walk logic -- the one genuinely nontrivial piece
    named in the spawn brief. Tested with a NESTED fixture (a table with
    paragraphs inside, not just flat top-level paragraphs) to prove the
    recursion actually descends."""

    def test_extract_text_flat_paragraphs(self) -> None:
        document = {
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "Hello, "}},
                                {"textRun": {"content": "world!\n"}},
                            ]
                        }
                    },
                    {
                        "paragraph": {
                            "elements": [{"textRun": {"content": "Second line.\n"}}]
                        }
                    },
                ]
            }
        }
        text = GoogleDocsService._extract_text(document)
        assert text == "Hello, world!\nSecond line.\n"

    def test_extract_text_nested_table_descends_recursively(self) -> None:
        """A document whose body has a paragraph, then a TABLE containing
        paragraphs inside its cells, then a trailing paragraph. Proves the
        walk descends into tableRows -> tableCells -> content rather than
        skipping non-paragraph StructuralElements."""
        document = {
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [{"textRun": {"content": "Before table.\n"}}]
                        }
                    },
                    {
                        "table": {
                            "rows": 2,
                            "columns": 2,
                            "tableRows": [
                                {
                                    "tableCells": [
                                        {
                                            "content": [
                                                {
                                                    "paragraph": {
                                                        "elements": [
                                                            {
                                                                "textRun": {
                                                                    "content": "R1C1\n"
                                                                }
                                                            }
                                                        ]
                                                    }
                                                }
                                            ]
                                        },
                                        {
                                            "content": [
                                                {
                                                    "paragraph": {
                                                        "elements": [
                                                            {
                                                                "textRun": {
                                                                    "content": "R1C2\n"
                                                                }
                                                            }
                                                        ]
                                                    }
                                                }
                                            ]
                                        },
                                    ]
                                },
                                {
                                    "tableCells": [
                                        {
                                            "content": [
                                                {
                                                    "paragraph": {
                                                        "elements": [
                                                            {
                                                                "textRun": {
                                                                    "content": "R2C1\n"
                                                                }
                                                            }
                                                        ]
                                                    }
                                                }
                                            ]
                                        },
                                        {
                                            "content": [
                                                {
                                                    "paragraph": {
                                                        "elements": [
                                                            {
                                                                "textRun": {
                                                                    "content": "R2C2\n"
                                                                }
                                                            }
                                                        ]
                                                    }
                                                }
                                            ]
                                        },
                                    ]
                                },
                            ],
                        }
                    },
                    {
                        "paragraph": {
                            "elements": [{"textRun": {"content": "After table.\n"}}]
                        }
                    },
                ]
            }
        }
        text = GoogleDocsService._extract_text(document)
        assert text == ("Before table.\nR1C1\nR1C2\nR2C1\nR2C2\nAfter table.\n")

    def test_extract_text_nested_table_of_contents(self) -> None:
        document = {
            "body": {
                "content": [
                    {
                        "tableOfContents": {
                            "content": [
                                {
                                    "paragraph": {
                                        "elements": [
                                            {"textRun": {"content": "TOC entry\n"}}
                                        ]
                                    }
                                }
                            ]
                        }
                    },
                ]
            }
        }
        text = GoogleDocsService._extract_text(document)
        assert text == "TOC entry\n"

    def test_extract_text_empty_body(self) -> None:
        assert GoogleDocsService._extract_text({"body": {"content": []}}) == ""
        assert GoogleDocsService._extract_text({}) == ""
        assert GoogleDocsService._extract_text({"body": {}}) == ""
        assert GoogleDocsService._extract_text({"body": "not-a-dict"}) == ""

    def test_extract_text_paragraph_element_without_text_run(self) -> None:
        """Elements can carry other kinds (e.g. inline objects/page breaks)
        without a textRun -- these must be skipped, not raise."""
        document = {
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [
                                {"pageBreak": {}},
                                {"textRun": {"content": "kept\n"}},
                            ]
                        }
                    }
                ]
            }
        }
        text = GoogleDocsService._extract_text(document)
        assert text == "kept\n"

    def test_extract_text_ignores_non_dict_elements(self) -> None:
        document = {"body": {"content": ["not-a-dict", None]}}
        text = GoogleDocsService._extract_text(document)
        assert text == ""

    def test_extract_text_body_content_not_a_list(self) -> None:
        """Covers service.py:406 -- a malformed document where
        body.content is present but not a list returns "" rather than
        raising."""
        document = {"body": {"content": "not-a-list"}}
        assert GoogleDocsService._extract_text(document) == ""

    def test_extract_table_text_ignores_non_dict_rows_and_cells(self) -> None:
        """Covers service.py:323/326 -- a table with a non-dict tableRow
        and a non-dict tableCell (malformed API response) is walked
        without raising, simply skipping the malformed entries."""
        table = {
            "tableRows": [
                "not-a-dict-row",
                {
                    "tableCells": [
                        "not-a-dict-cell",
                        {
                            "content": [
                                {
                                    "paragraph": {
                                        "elements": [
                                            {"textRun": {"content": "valid cell\n"}}
                                        ]
                                    }
                                }
                            ]
                        },
                    ]
                },
            ]
        }
        text = GoogleDocsService._extract_table_text(table)
        assert text == "valid cell\n"

    def test_extract_paragraph_text_ignores_non_dict_element(self) -> None:
        """Covers service.py:289 -- a paragraph whose `elements` list
        contains a non-dict entry (malformed API response) is skipped
        rather than raising."""
        paragraph = {"elements": ["not-a-dict", {"textRun": {"content": "ok\n"}}]}
        text = GoogleDocsService._extract_paragraph_text(paragraph)
        assert text == "ok\n"

    @patch("googleapiclient.discovery.build")
    def test_get_document_text_success(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.docs_service.documents().get().execute.return_value = {
            "documentId": "doc1",
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [{"textRun": {"content": "Plain text.\n"}}]
                        }
                    }
                ]
            },
        }

        result = service.get_document_text("doc1")

        assert result.success is True
        assert result.content == "Plain text.\n"

    @patch("googleapiclient.discovery.build")
    def test_get_document_text_propagates_get_document_error(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        service.docs_service.documents().get().execute.side_effect = Exception("boom")

        result = service.get_document_text("doc1")

        assert result.success is False
        assert result.error is not None

    @patch("googleapiclient.discovery.build")
    def test_get_document_text_extraction_exception_returns_error_result(
        self, mock_build: MagicMock
    ) -> None:
        """If _extract_text somehow raises (malformed document), the error
        is caught and returned as an error_result, not propagated."""
        service = _make_initialized_service(mock_build)
        service.docs_service.documents().get().execute.return_value = {
            "documentId": "doc1",
            "body": {"content": []},
        }
        with patch.object(
            GoogleDocsService, "_extract_text", side_effect=RuntimeError("boom")
        ):
            result = service.get_document_text("doc1")
            assert result.success is False
            assert result.error is not None
            assert "boom" in result.error


# ---------------------------------------------------------------------
# create_document
# ---------------------------------------------------------------------


class TestGoogleDocsServiceCreateDocument:
    @patch("googleapiclient.discovery.build")
    def test_create_document_calls_sdk_with_title(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.docs_service.documents().create().execute.return_value = {
            "documentId": "new-doc",
            "title": "My Title",
        }

        result = service.create_document("My Title")

        assert result.success is True
        assert result.content is not None
        assert result.content["documentId"] == "new-doc"
        service.docs_service.documents().create.assert_called_with(
            body={"title": "My Title"}
        )

    @patch("googleapiclient.discovery.build")
    def test_create_document_api_error(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.docs_service.documents().create().execute.side_effect = Exception(
            "create failed"
        )

        result = service.create_document("Title")

        assert result.success is False
        assert result.error is not None
        assert "create failed" in result.error

    def test_create_document_service_none(self) -> None:
        service = GoogleDocsService()
        service._initialized = True
        service.docs_service = None

        result = service.create_document("Title")
        assert result.success is False
        assert "not initialized" in (result.error or "")

    def test_create_document_auto_initialize_error_surfaces(self) -> None:
        """Covers service.py:507-508 -- calling create_document() before
        initialize(), with no credentials wired up, auto-initializes via
        _ensure_initialized and surfaces the real init failure as an
        error_result rather than an unhandled exception."""
        service = GoogleDocsService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.create_document("Title")
        assert result.success is False


# ---------------------------------------------------------------------
# batch_update -- reverse-sort-by-index policy (required specific test)
# ---------------------------------------------------------------------


class TestGoogleDocsServiceBatchUpdate:
    @patch("googleapiclient.discovery.build")
    def test_batch_update_reverse_sorts_requests_by_index(
        self, mock_build: MagicMock
    ) -> None:
        """Construct requests with insert/delete at multiple different
        indices in ASCENDING order as input; assert the mocked
        batchUpdate(body={"requests": [...]}) call received them in
        DESCENDING-index order (required specific test per the spawn
        brief)."""
        service = _make_initialized_service(mock_build)
        service.docs_service.documents().batchUpdate().execute.return_value = {
            "documentId": "doc1",
            "replies": [],
        }

        ascending_requests: list[dict[str, Any]] = [
            {"insertText": {"location": {"index": 5}, "text": "a"}},
            {"deleteContentRange": {"range": {"startIndex": 10, "endIndex": 15}}},
            {"insertText": {"location": {"index": 20}, "text": "b"}},
        ]

        result = service.batch_update("doc1", ascending_requests)

        assert result.success is True
        _, kwargs = service.docs_service.documents().batchUpdate.call_args
        assert kwargs["documentId"] == "doc1"
        sent_requests = kwargs["body"]["requests"]

        assert sent_requests[0]["insertText"]["location"]["index"] == 20
        assert sent_requests[1]["deleteContentRange"]["range"]["startIndex"] == 10
        assert sent_requests[2]["insertText"]["location"]["index"] == 5

    @patch("googleapiclient.discovery.build")
    def test_batch_update_api_error(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.docs_service.documents().batchUpdate().execute.side_effect = Exception(
            "batch failed"
        )

        result = service.batch_update(
            "doc1", [{"insertText": {"location": {"index": 1}, "text": "x"}}]
        )

        assert result.success is False
        assert result.error is not None
        assert "batch failed" in result.error

    def test_batch_update_service_none(self) -> None:
        service = GoogleDocsService()
        service._initialized = True
        service.docs_service = None

        result = service.batch_update("doc1", [])
        assert result.success is False
        assert "not initialized" in (result.error or "")

    def test_batch_update_auto_initialize_error_surfaces(self) -> None:
        """Covers service.py:567-568 -- calling batch_update() before
        initialize(), with no credentials wired up, auto-initializes via
        _ensure_initialized and surfaces the real init failure as an
        error_result rather than an unhandled exception."""
        service = GoogleDocsService(
            client_secrets_file="/path/to/secrets.json",
            credentials_file="/path/to/credentials.json",
        )
        result = service.batch_update("doc1", [])
        assert result.success is False


# ---------------------------------------------------------------------
# replace_text / append_text -- index-free convenience methods
# ---------------------------------------------------------------------


class TestGoogleDocsServiceReplaceText:
    @patch("googleapiclient.discovery.build")
    def test_replace_text_builds_replace_all_text_request(
        self, mock_build: MagicMock
    ) -> None:
        service = _make_initialized_service(mock_build)
        service.docs_service.documents().batchUpdate().execute.return_value = {
            "documentId": "doc1"
        }

        result = service.replace_text("doc1", find="TODO", replace="DONE")

        assert result.success is True
        _, kwargs = service.docs_service.documents().batchUpdate.call_args
        sent_requests = kwargs["body"]["requests"]
        assert len(sent_requests) == 1
        replace_all = sent_requests[0]["replaceAllText"]
        assert replace_all["containsText"] == {"text": "TODO", "matchCase": False}
        assert replace_all["replaceText"] == "DONE"

    @patch("googleapiclient.discovery.build")
    def test_replace_text_match_case_true(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.docs_service.documents().batchUpdate().execute.return_value = {}

        service.replace_text("doc1", find="Foo", replace="Bar", match_case=True)

        _, kwargs = service.docs_service.documents().batchUpdate.call_args
        sent_requests = kwargs["body"]["requests"]
        assert sent_requests[0]["replaceAllText"]["containsText"]["matchCase"] is True

    @patch("googleapiclient.discovery.build")
    def test_replace_text_never_requires_caller_supplied_index(
        self, mock_build: MagicMock
    ) -> None:
        """replace_text's signature has no index/location parameter at
        all -- this test documents and pins that index-free-by-
        construction contract."""
        import inspect

        signature = inspect.signature(GoogleDocsService.replace_text)
        param_names = set(signature.parameters.keys())
        assert "index" not in param_names
        assert "location" not in param_names


class TestGoogleDocsServiceAppendText:
    @patch("googleapiclient.discovery.build")
    def test_append_text_uses_end_of_segment_location(
        self, mock_build: MagicMock
    ) -> None:
        """append_text must use endOfSegmentLocation (no segmentId, no
        prior get() call needed) rather than requiring a computed index."""
        service = _make_initialized_service(mock_build)
        service.docs_service.documents().batchUpdate().execute.return_value = {
            "documentId": "doc1"
        }

        result = service.append_text("doc1", "New paragraph.\n")

        assert result.success is True
        # No prior documents().get() call should have been made to compute
        # an end index -- append_text is a single API call.
        service.docs_service.documents().get.assert_not_called()

        _, kwargs = service.docs_service.documents().batchUpdate.call_args
        sent_requests = kwargs["body"]["requests"]
        assert len(sent_requests) == 1
        insert_text = sent_requests[0]["insertText"]
        assert insert_text["endOfSegmentLocation"] == {}
        assert insert_text["text"] == "New paragraph.\n"
        assert "location" not in insert_text

    @patch("googleapiclient.discovery.build")
    def test_append_text_never_requires_caller_supplied_index(
        self, mock_build: MagicMock
    ) -> None:
        import inspect

        signature = inspect.signature(GoogleDocsService.append_text)
        param_names = set(signature.parameters.keys())
        assert "index" not in param_names
        assert "location" not in param_names

    @patch("googleapiclient.discovery.build")
    def test_append_text_api_error(self, mock_build: MagicMock) -> None:
        service = _make_initialized_service(mock_build)
        service.docs_service.documents().batchUpdate().execute.side_effect = Exception(
            "append failed"
        )

        result = service.append_text("doc1", "text")

        assert result.success is False
        assert result.error is not None
        assert "append failed" in result.error


# ---------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------


class TestGoogleDocsServiceValidateConfig:
    def test_validate_config_success(self) -> None:
        service = GoogleDocsService()
        valid, errors = service.validate_config(
            {
                "client_secrets_file": "/secrets.json",
                "credentials_file": "/creds.json",
            }
        )
        assert valid is True
        assert errors == []

    def test_validate_config_failure(self) -> None:
        service = GoogleDocsService()
        valid, errors = service.validate_config({})
        assert valid is False
        assert len(errors) == 1
        assert "Configuration validation failed" in errors[0]
