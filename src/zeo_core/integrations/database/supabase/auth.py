"""Secret-owning authentication provider for Supabase project keys."""

from __future__ import annotations

import os

from pydantic import SecretStr

from zeo_core.core.logging import LOG_LEVELS, LogLevel
from zeo_core.integrations.core import AuthResult, BaseAuthProvider

from .models import SupabaseKeyKind


def classify_key(value: str) -> SupabaseKeyKind:
    """Classify current and legacy Supabase keys without decoding them."""
    if value.startswith("sb_publishable_"):
        return SupabaseKeyKind.PUBLISHABLE
    if value.startswith("sb_secret_"):
        return SupabaseKeyKind.PRIVILEGED
    # Legacy JWTs cannot be safely decoded here. The source variable determines
    # their authority class in from_environment().
    return SupabaseKeyKind.UNKNOWN


class SupabaseAuthProvider(BaseAuthProvider):
    """Own a project key without placing it in AuthResult or configuration."""

    def __init__(
        self,
        key: SecretStr | str | None = None,
        *,
        key_kind: SupabaseKeyKind | None = None,
        allow_privileged_key: bool = False,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
    ) -> None:
        super().__init__(credentials_file=None, log_level=log_level)
        self._key = SecretStr(key) if isinstance(key, str) else key
        raw = self._key.get_secret_value() if self._key else ""
        self.key_kind = key_kind or classify_key(raw)
        self.allow_privileged_key = allow_privileged_key

    @classmethod
    def from_environment(
        cls, *, allow_privileged_key: bool = False
    ) -> "SupabaseAuthProvider":
        """Resolve publishable/legacy anon first; privileged keys require opt-in."""
        if value := os.environ.get("SUPABASE_PUBLISHABLE_KEY"):
            return cls(value, key_kind=SupabaseKeyKind.PUBLISHABLE)
        if value := os.environ.get("SUPABASE_KEY"):
            return cls(value, key_kind=SupabaseKeyKind.ANON_LEGACY)
        if allow_privileged_key and (value := os.environ.get("SUPABASE_SECRET_KEY")):
            return cls(
                value,
                key_kind=SupabaseKeyKind.PRIVILEGED,
                allow_privileged_key=True,
            )
        return cls(allow_privileged_key=allow_privileged_key)

    @property
    def name(self) -> str:
        return "Supabase"

    def __repr__(self) -> str:
        return f"SupabaseAuthProvider(key=<redacted>, key_kind={self.key_kind.value!r})"

    def __str__(self) -> str:
        return self.__repr__()

    def authenticate(self) -> AuthResult:
        if self._key is None or not self._key.get_secret_value().strip():
            return AuthResult.error_result(error="No Supabase project key configured")
        privileged = self.key_kind in {
            SupabaseKeyKind.PRIVILEGED,
            SupabaseKeyKind.SERVICE_ROLE_LEGACY,
        }
        if privileged and not self.allow_privileged_key:
            return AuthResult.error_result(
                error="Privileged Supabase keys require explicit server-only opt-in"
            )
        self.authenticated = True
        return AuthResult.success_result(
            message="Supabase project key admitted",
            content={"key_kind": self.key_kind.value},
        )

    def refresh_credentials(self) -> AuthResult:
        return self.authenticate()

    def get_credentials(self) -> object:
        """Return a SecretStr only to the integration's client-construction seam."""
        return self._key

    def save_credentials(self) -> bool:
        """Project keys are supplied by environment or a caller-owned secret store."""
        return False
