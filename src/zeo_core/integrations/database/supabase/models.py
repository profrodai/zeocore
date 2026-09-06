"""Secret-safe public models for the Supabase integration."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _StrictModel(BaseModel):
    """Reject silently ignored fields at public Supabase boundaries."""

    model_config = ConfigDict(extra="forbid")


class SupabaseKeyKind(StrEnum):
    """Key classes understood by the integration."""

    PUBLISHABLE = "publishable"
    ANON_LEGACY = "anon_legacy"
    PRIVILEGED = "privileged"
    SERVICE_ROLE_LEGACY = "service_role_legacy"
    UNKNOWN = "unknown"


class SupabaseFilterOperator(StrEnum):
    """Allow-listed PostgREST filter operations."""

    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    LIKE = "like"
    ILIKE = "ilike"
    IS = "is_"
    IN = "in_"
    CONTAINS = "contains"
    CONTAINED_BY = "contained_by"
    OVERLAPS = "overlaps"


class SupabaseFilter(_StrictModel):
    """One typed, allow-listed PostgREST filter."""

    field: str
    operator: SupabaseFilterOperator = SupabaseFilterOperator.EQ
    value: Any

    @field_validator("field")
    @classmethod
    def _field_is_identifier(cls, value: str) -> str:
        from .validation import require_identifier

        return require_identifier(value, label="filter field")


class SupabaseOrder(_StrictModel):
    """One deterministic result ordering."""

    field: str
    descending: bool = False
    nulls_first: bool = False

    @field_validator("field")
    @classmethod
    def _field_is_identifier(cls, value: str) -> str:
        from .validation import require_identifier

        return require_identifier(value, label="order field")


class SupabaseRowPage(_StrictModel):
    """A bounded page of PostgREST rows."""

    rows: list[dict[str, Any]] = Field(default_factory=list)
    count: int | None = None
    offset: int = 0
    limit: int | None = None


class SupabaseUser(_StrictModel):
    """Safe user identity; session credentials are deliberately absent."""

    id: str
    email: str | None = None
    phone: str | None = None
    app_metadata: dict[str, Any] = Field(default_factory=dict)
    user_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class SupabaseSessionStatus(_StrictModel):
    """Secret-free authentication disposition."""

    authenticated: bool
    user: SupabaseUser | None = None
    expires_at: int | None = None


class SupabaseOAuthStart(_StrictModel):
    """Browser redirect produced by a configured OAuth provider."""

    provider: str
    authorization_url: str


class SupabaseBucket(_StrictModel):
    """Safe Storage bucket metadata."""

    id: str
    name: str
    public: bool = False
    file_size_limit: int | None = None
    allowed_mime_types: list[str] = Field(default_factory=list)


class SupabaseObject(_StrictModel):
    """Safe Storage object metadata."""

    bucket: str
    path: str
    size: int | None = None
    content_type: str | None = None
    etag: str | None = None
    updated_at: datetime | None = None


class SupabaseFunctionResult(_StrictModel):
    """Bounded Edge Function response."""

    status_code: int
    data: Any = None


class SupabaseRealtimeEvent(StrEnum):
    """Postgres-change events accepted by Realtime."""

    ALL = "*"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class SupabaseRealtimeChange(BaseModel):
    """Typed Realtime database-change payload."""

    model_config = ConfigDict(extra="ignore")

    event: str
    schema_name: str | None = None
    table: str | None = None
    committed_at: datetime | None = None
    new: dict[str, Any] = Field(default_factory=dict)
    old: dict[str, Any] = Field(default_factory=dict)


class SupabaseRealtimeSubscription(_StrictModel):
    """Opaque local handle for one active Realtime subscription."""

    id: str
    topic: str
    schema_name: str
    table: str
    event: SupabaseRealtimeEvent
