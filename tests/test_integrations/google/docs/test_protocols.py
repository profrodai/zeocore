"""Tests for Google Docs protocol definitions -- mirrors
tests/test_integrations/google/calendar/test_protocols.py's structural-
conformance shape (a MagicMock built with the right attrs satisfies
isinstance() against the runtime_checkable Protocols)."""

from unittest.mock import MagicMock

from zeo_core.integrations.google.docs.protocols import (
    DocsDocumentsResource,
    DocsRequest,
    DocsService,
    GoogleCredentials,
)


class TestDocsRequest:
    def test_mock_satisfies_protocol(self) -> None:
        mock = MagicMock()
        mock.execute = MagicMock(return_value={})
        assert isinstance(mock, DocsRequest)


class TestDocsDocumentsResource:
    def test_mock_satisfies_protocol(self) -> None:
        mock = MagicMock()
        mock.get = MagicMock()
        mock.create = MagicMock()
        mock.batchUpdate = MagicMock()
        assert isinstance(mock, DocsDocumentsResource)


class TestDocsService:
    def test_mock_satisfies_protocol(self) -> None:
        mock = MagicMock()
        mock.documents = MagicMock()
        assert isinstance(mock, DocsService)


class TestGoogleCredentials:
    def test_mock_satisfies_protocol(self) -> None:
        mock = MagicMock()
        mock.token = "tok"  # noqa: S105 -- test fixture, fake credential value
        mock.refresh_token = "refresh"  # noqa: S105 -- test fixture
        mock.token_uri = "https://oauth2.googleapis.com/token"  # noqa: S105 -- test fixture, fake credential value
        mock.client_id = "id"
        mock.client_secret = "secret"  # noqa: S105 -- test fixture
        mock.scopes = ["scope"]
        assert isinstance(mock, GoogleCredentials)
