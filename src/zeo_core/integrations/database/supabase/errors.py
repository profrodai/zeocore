"""Credential-free Supabase error normalization."""

from __future__ import annotations

import re

_SAFE_CODE = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")


class SupabaseAPIError(RuntimeError):
    """Bounded failure that cannot retain an upstream exception or payload."""

    def __init__(
        self,
        message: str = "Supabase operation failed",
        *,
        code: str = "supabase_error",
        status: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.retryable = retryable


def normalize_supabase_error(error: Exception) -> SupabaseAPIError:
    """Discard upstream text and payloads, retaining only bounded metadata."""
    raw_status = getattr(error, "status_code", getattr(error, "status", None))
    status = raw_status if isinstance(raw_status, int) else None
    raw_code = getattr(error, "code", None)
    code = (
        raw_code
        if isinstance(raw_code, str) and _SAFE_CODE.fullmatch(raw_code)
        else "supabase_error"
    )
    retryable = status in {408, 425, 429, 500, 502, 503, 504}
    return SupabaseAPIError(code=code, status=status, retryable=retryable)
