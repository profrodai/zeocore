"""Validation shared by all Supabase surfaces."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PROVIDER = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_FUNCTION = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,127}$")


def require_identifier(value: str, *, label: str) -> str:
    """Require an unqualified PostgreSQL identifier."""
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{label} must be an unqualified identifier")
    return value


def require_provider(value: str) -> str:
    """Require a simple Auth provider name."""
    if not _PROVIDER.fullmatch(value):
        raise ValueError("provider must be a simple lower-case identifier")
    return value


def require_function_name(value: str) -> str:
    """Require an Edge Function name, never a URL or path."""
    if not _FUNCTION.fullmatch(value):
        raise ValueError("function name must be a simple identifier")
    return value


def require_object_path(value: str) -> str:
    """Reject traversal, absolute paths, backslashes, and control characters."""
    if not value or value.startswith(("/", "\\")) or "\\" in value:
        raise ValueError("storage path must be a non-empty relative POSIX path")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("storage path contains an empty or traversal segment")
    if any(ord(char) < 32 for char in value):
        raise ValueError("storage path contains a control character")
    return value


def require_project_url(value: str, *, allow_local_http: bool = False) -> str:
    """Accept only an origin URL with no credentials, path, query, or fragment."""
    parsed = urlsplit(value)
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    valid_scheme = parsed.scheme == "https" or (
        allow_local_http and local and parsed.scheme == "http"
    )
    if not valid_scheme:
        raise ValueError("Supabase URL must use HTTPS (HTTP is local-test only)")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Supabase URL must be a credential-free origin")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("Supabase URL must not include a path, query, or fragment")
    return value.rstrip("/")


def require_project_authorization_url(value: str, *, project_url: str) -> str:
    """Require an OAuth URL to remain on the configured Supabase origin."""
    candidate = urlsplit(value)
    project = urlsplit(project_url)
    if (
        candidate.scheme != project.scheme
        or candidate.hostname != project.hostname
        or candidate.port != project.port
        or candidate.username is not None
        or candidate.password is not None
        or not candidate.path.startswith("/auth/v1/")
    ):
        raise ValueError("OAuth authorization URL is outside the Supabase project")
    return value
