"""Tests for Google Slides protocol definitions -- mirrors
tests/test_integrations/google/docs/test_protocols.py's structural-
conformance shape (a MagicMock built with the right attrs satisfies
isinstance() against the runtime_checkable Protocols)."""

from unittest.mock import MagicMock

from zeo_core.integrations.google.slides.protocols import (
    GoogleCredentials,
    SlidesPresentationsResource,
    SlidesRequest,
    SlidesService,
)


class TestSlidesRequest:
    def test_mock_satisfies_protocol(self) -> None:
        mock = MagicMock()
        mock.execute = MagicMock(return_value={})
        assert isinstance(mock, SlidesRequest)


class TestSlidesPresentationsResource:
    def test_mock_satisfies_protocol(self) -> None:
        mock = MagicMock()
        mock.get = MagicMock()
        mock.create = MagicMock()
        mock.batchUpdate = MagicMock()
        assert isinstance(mock, SlidesPresentationsResource)


class TestSlidesService:
    def test_mock_satisfies_protocol(self) -> None:
        mock = MagicMock()
        mock.presentations = MagicMock()
        assert isinstance(mock, SlidesService)


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
