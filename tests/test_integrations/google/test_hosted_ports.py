"""Proofs for broker-memory Google construction and explicit hosted scopes."""

from __future__ import annotations

import logging

import pytest

from zeo_core.integrations.google import (
    GoogleApiClientFactory,
    GoogleCredentialSource,
)
from zeo_core.integrations.google.docs import GoogleDocsService
from zeo_core.integrations.google.drive import GoogleDriveService

DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
DOCS_READ_SCOPE = "https://www.googleapis.com/auth/documents.readonly"


class MemoryCredentialSource:
    def __init__(self, credentials: object) -> None:
        self.credentials = credentials
        self.calls = 0

    def get_credentials(self) -> object:
        self.calls += 1
        return self.credentials


class RecordingClientFactory:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, object]] = []
        self.client = object()

    def build(self, service: str, version: str, *, credentials: object) -> object:
        self.calls.append((service, version, credentials))
        return self.client


class FailingCredentialSource:
    def get_credentials(self) -> object:
        raise RuntimeError("ya29.CANARY-GOOGLE-OAUTH-TOKEN")


def test_drive_injected_construction_uses_memory_and_selected_file_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credentials = object()
    source = MemoryCredentialSource(credentials)
    factory = RecordingClientFactory()
    monkeypatch.setattr(
        "zeo_core.integrations.google.drive.service.GoogleAuthProvider",
        lambda **_kwargs: pytest.fail("installed-app auth must not be constructed"),
    )
    service = GoogleDriveService(
        credential_source=source,
        client_factory=factory,
        scope_profile="selected-file",
    )

    result = service.initialize()

    assert result.success
    assert service.scopes == [DRIVE_FILE_SCOPE]
    assert source.calls == 1
    assert factory.calls == [("drive", "v3", credentials)]
    assert service.drive_service is factory.client
    assert service.initialize().success
    assert source.calls == 1
    assert isinstance(source, GoogleCredentialSource)
    assert isinstance(factory, GoogleApiClientFactory)


def test_docs_injected_construction_requires_and_uses_explicit_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credentials = object()
    source = MemoryCredentialSource(credentials)
    factory = RecordingClientFactory()
    monkeypatch.setattr(
        "zeo_core.integrations.google.docs.service.GoogleAuthProvider",
        lambda **_kwargs: pytest.fail("installed-app auth must not be constructed"),
    )
    service = GoogleDocsService(
        scopes=[DOCS_READ_SCOPE],
        credential_source=source,
        client_factory=factory,
    )

    result = service.initialize()

    assert result.success
    assert service.scopes == [DOCS_READ_SCOPE]
    assert source.calls == 1
    assert factory.calls == [("docs", "v1", credentials)]
    assert service.docs_service is factory.client


def test_injected_credentials_never_inherit_broad_scope_implicitly() -> None:
    source = MemoryCredentialSource(object())

    with pytest.raises(ValueError, match="explicit scopes"):
        GoogleDriveService(credential_source=source)
    with pytest.raises(ValueError, match="explicit scopes"):
        GoogleDocsService(credential_source=source)
    with pytest.raises(ValueError, match="mutually exclusive"):
        GoogleDriveService(
            scopes=[DRIVE_FILE_SCOPE],
            scope_profile="selected-file",
            credential_source=source,
        )
    with pytest.raises(ValueError, match="unknown"):
        GoogleDriveService(scope_profile="not-a-profile")


@pytest.mark.parametrize("service_kind", ["drive", "docs"])
def test_injected_failure_does_not_echo_credential_exception(
    service_kind: str, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.ERROR)
    source = FailingCredentialSource()
    service: GoogleDriveService | GoogleDocsService
    if service_kind == "drive":
        service = GoogleDriveService(
            scopes=[DRIVE_FILE_SCOPE], credential_source=source
        )
    else:
        service = GoogleDocsService(scopes=[DOCS_READ_SCOPE], credential_source=source)

    result = service.initialize()
    disclosure = "\n".join((str(result), repr(result), caplog.text))

    assert not result.success
    assert "CANARY-GOOGLE-OAUTH-TOKEN" not in disclosure
