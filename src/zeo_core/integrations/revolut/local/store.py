"""Private, per-user files for one local Revolut Business enrollment.

The private key and the rotating tokens live here, never in ``.env`` and never
inside a repository. Writes are atomic and fsynced, because the refresh
protocol depends on a marker being durable *before* a request is sent.
"""

from __future__ import annotations

import json
import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, SecretStr, field_serializer

from zeo_core.integrations.environment import managed_state_dir

from ..models import RevolutEnvironment

KEY_FILENAME = "client-private-key.pem"
CERTIFICATE_FILENAME = "client-certificate.pem"
STATE_FILENAME = "enrollment.json"
_LOCK_FILENAME = "enrollment.lock"


class LocalStoreError(RuntimeError):
    """The private store is unusable; the message never contains a secret."""


class RefreshAttempt(BaseModel):
    """Written durably BEFORE a refresh request is sent.

    If it is still present when nobody holds the lock, the process that sent
    the request did not record an answer: the provider may have refreshed and
    invalidated the stored access token. That outcome is unknown, and no
    amount of elapsed time makes it known.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    attempt_id: str
    sent_at: datetime


class EnrollmentState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    environment: RevolutEnvironment
    redirect_uri: str
    client_id: str | None = None
    consent_state: str | None = None
    access_token: SecretStr | None = None
    refresh_token: SecretStr | None = None
    access_expires_at: datetime | None = None
    refresh_attempt: RefreshAttempt | None = None
    # What this client observed when it stopped, never a diagnosis.
    blocked_reason: str | None = None

    @field_serializer("access_token", "refresh_token", when_used="json")
    def _reveal_for_private_file(self, value: SecretStr | None) -> str | None:
        return None if value is None else value.get_secret_value()


def default_directory(environment: RevolutEnvironment) -> Path:
    """Inside the managed environment when one is selected, else per-user config."""

    managed = managed_state_dir()
    if managed is not None:
        return managed / "credentials" / "revolut" / environment.value
    import platformdirs

    return (
        Path(platformdirs.user_config_dir("zeocore", appauthor=False))
        / "revolut"
        / environment.value
    )


class LocalCredentialStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def prepare(self) -> None:
        if _inside_a_repository(self.directory):
            raise LocalStoreError(
                "Revolut credentials must not be stored inside a repository"
            )
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)

    @property
    def key_path(self) -> Path:
        return self.directory / KEY_FILENAME

    @property
    def certificate_path(self) -> Path:
        return self.directory / CERTIFICATE_FILENAME

    def read_private(self, name: str) -> bytes | None:
        path = self.directory / name
        try:
            info = path.lstat()
        except FileNotFoundError:
            return None
        if stat.S_ISLNK(info.st_mode) or info.st_mode & 0o077:
            raise LocalStoreError(
                f"{name} must be a regular file readable only by its owner"
            )
        return path.read_bytes()

    def write_private(self, name: str, content: bytes, *, mode: int = 0o600) -> None:
        """Atomic and durable: temp file, fsync, rename, fsync the directory."""

        path = self.directory / name
        temporary = path.with_name(f".{name}.{os.getpid()}.tmp")
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        directory = os.open(self.directory, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def load(self) -> EnrollmentState | None:
        content = self.read_private(STATE_FILENAME)
        return None if content is None else EnrollmentState.model_validate_json(content)

    def save(self, state: EnrollmentState) -> None:
        self.write_private(
            STATE_FILENAME, state.model_dump_json(indent=2).encode() + b"\n"
        )

    @contextmanager
    def locked(self) -> Iterator[None]:
        """One process at a time, held across the provider call.

        The lock stops two local scripts refreshing at once. It cannot say what
        happened to a request whose answer was lost; ``RefreshAttempt`` does.
        """

        try:
            import fcntl
        except ImportError:  # pragma: no cover - Windows
            raise LocalStoreError(
                "local Revolut enrollment needs POSIX file locking"
            ) from None
        self.prepare()
        descriptor = os.open(
            self.directory / _LOCK_FILENAME, os.O_CREAT | os.O_RDWR, 0o600
        )
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            os.close(descriptor)


def _inside_a_repository(directory: Path) -> bool:
    resolved = directory.expanduser().resolve()
    return any((parent / ".git").exists() for parent in (resolved, *resolved.parents))


def dump_public(state: EnrollmentState) -> str:
    """For status output: no token ever appears."""

    return json.dumps(
        {
            "environment": state.environment.value,
            "redirect_uri": state.redirect_uri,
            "client_id_set": state.client_id is not None,
            "enrolled": state.refresh_token is not None,
            "access_expires_at": state.access_expires_at.isoformat()
            if state.access_expires_at
            else None,
            "refresh_outcome_unknown": state.refresh_attempt is not None,
            "blocked_reason": state.blocked_reason,
        },
        indent=2,
    )


__all__ = [
    "CERTIFICATE_FILENAME",
    "KEY_FILENAME",
    "EnrollmentState",
    "LocalCredentialStore",
    "LocalStoreError",
    "RefreshAttempt",
    "default_directory",
    "dump_public",
]
