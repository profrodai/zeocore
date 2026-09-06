"""First-class Zeocore integration for Supabase application services."""

# ruff: noqa: ANN401 -- typed public methods converge through one generic delegate.

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, TypeVar

from pydantic import SecretStr

from zeo_core.core.logging import LOG_LEVELS, LogLevel
from zeo_core.integrations.core import (
    AuthProviderProtocol,
    BaseIntegrationService,
    ConfigProviderProtocol,
    IntegrationResult,
)

from .auth import SupabaseAuthProvider
from .client import SupabaseClient
from .config import SupabaseConfigProvider
from .errors import SupabaseAPIError
from .models import (
    SupabaseBucket,
    SupabaseFilter,
    SupabaseFunctionResult,
    SupabaseOAuthStart,
    SupabaseOrder,
    SupabaseRowPage,
    SupabaseSessionStatus,
)
from .protocols import SupabaseIntegrationProtocol, SupabaseRealtimeProtocol
from .realtime import SupabaseRealtimeClient

T = TypeVar("T")


class SupabaseIntegration(BaseIntegrationService, SupabaseIntegrationProtocol):
    """Compose Database, Auth, Storage, Functions, and async Realtime."""

    def __init__(
        self,
        config_provider: ConfigProviderProtocol | None = None,
        auth_provider: AuthProviderProtocol | None = None,
        config_path: str | None = None,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
        client_factory: Callable[..., SupabaseClient] | None = None,
        client: SupabaseClient | None = None,
        realtime_client: SupabaseRealtimeProtocol | None = None,
    ) -> None:
        provider = config_provider or SupabaseConfigProvider(log_level=log_level)
        super().__init__(
            config_provider=provider,
            auth_provider=auth_provider,
            config=None,
            config_path=config_path,
            log_level=log_level,
        )
        self.client = client
        self._client_factory = client_factory or SupabaseClient
        self._realtime = realtime_client
        if client is not None:
            self._initialized = True

    @property
    def name(self) -> str:
        return "Supabase"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def realtime(self) -> SupabaseRealtimeProtocol:
        if self._realtime is None:
            raise RuntimeError("Supabase integration is not initialized")
        return self._realtime

    def initialize(self) -> IntegrationResult[object]:
        if self.client is not None and self._realtime is not None:
            self._initialized = True
            return IntegrationResult.success_result(
                message="Supabase integration already initialized"
            )
        if not self.config_provider:
            return IntegrationResult.error_result(
                "Supabase configuration is unavailable"
            )
        config_result = self.config_provider.load_config(self.config_path)
        if not config_result.success or config_result.content is None:
            return IntegrationResult.error_result(
                config_result.error or "Supabase configuration failed"
            )
        self.config = dict(config_result.content)
        allow_privileged = self.config.get("allow_privileged_key") is True
        provider = self.auth_provider or SupabaseAuthProvider.from_environment(
            allow_privileged_key=allow_privileged
        )
        auth_result = provider.authenticate()
        if not auth_result.success:
            return IntegrationResult.error_result(
                auth_result.error or "Supabase authentication failed"
            )
        secret = provider.get_credentials()
        if not isinstance(secret, SecretStr):
            return IntegrationResult.error_result(
                "Supabase auth provider did not supply an opaque key"
            )
        url = os.environ.get("SUPABASE_URL", "")
        key = secret.get_secret_value()
        try:
            self.client = self._client_factory(
                url=url,
                key=key,
                schema=self.config.get("schema", "public"),
                timeout_seconds=self.config.get("timeout_seconds", 30),
                max_rows=self.config.get("max_rows", 1_000),
                max_object_bytes=self.config.get("max_object_bytes", 10_000_000),
                allow_local_http=self.config.get("allow_local_http", False),
                persist_session=self.config.get("persist_session", False),
                auto_refresh_token=self.config.get("auto_refresh_token", False),
            )
            if self._realtime is None:
                self._realtime = SupabaseRealtimeClient(
                    url,
                    key,
                    allow_local_http=self.config.get("allow_local_http", False),
                )
        except Exception:
            self.client = None
            self._realtime = None
            self._initialized = False
            return IntegrationResult.error_result(
                "Failed to initialize Supabase without exposing provider data"
            )
        self.auth_provider = provider
        self._initialized = True
        return IntegrationResult.success_result(
            message="Supabase integration initialized successfully"
        )

    def is_available(self) -> bool:
        return self._initialized and self.client is not None

    def _call(
        self, function: Callable[..., T], *args: Any, **kwargs: Any
    ) -> IntegrationResult[T]:
        if not self.is_available() or self.client is None:
            return IntegrationResult.error_result(
                "Supabase integration is not initialized"
            )
        try:
            return IntegrationResult.success_result(content=function(*args, **kwargs))
        except SupabaseAPIError as error:
            return IntegrationResult.error_result(
                f"{error.code}: Supabase operation failed"
            )
        except ValueError, KeyError, OSError:
            return IntegrationResult.error_result("Invalid Supabase operation")

    def _call_client(
        self, method: str, *args: Any, **kwargs: Any
    ) -> IntegrationResult[Any]:
        """Resolve a client method only after the availability guard runs."""
        if self.client is None:
            return IntegrationResult.error_result(
                "Supabase integration is not initialized"
            )
        function = getattr(self.client, method)
        return self._call(function, *args, **kwargs)

    # Database
    def select(
        self,
        table: str,
        *,
        columns: Sequence[str] = ("*",),
        filters: Sequence[SupabaseFilter] = (),
        orders: Sequence[SupabaseOrder] = (),
        offset: int = 0,
        limit: int | None = None,
        count: str | None = None,
    ) -> IntegrationResult[SupabaseRowPage]:
        return self._call_client(
            "select",
            table,
            columns=columns,
            filters=filters,
            orders=orders,
            offset=offset,
            limit=limit,
            count=count,
        )

    def insert(
        self, table: str, rows: Mapping[str, Any] | Sequence[Mapping[str, Any]]
    ) -> IntegrationResult[SupabaseRowPage]:
        return self._call_client("insert", table, rows)

    def upsert(
        self,
        table: str,
        rows: Mapping[str, Any] | Sequence[Mapping[str, Any]],
        *,
        on_conflict: str | None = None,
        ignore_duplicates: bool = False,
    ) -> IntegrationResult[SupabaseRowPage]:
        return self._call_client(
            "upsert",
            table,
            rows,
            on_conflict=on_conflict,
            ignore_duplicates=ignore_duplicates,
        )

    def update(
        self,
        table: str,
        values: Mapping[str, Any],
        *,
        filters: Sequence[SupabaseFilter],
    ) -> IntegrationResult[SupabaseRowPage]:
        return self._call_client("update", table, values, filters=filters)

    def delete(
        self, table: str, *, filters: Sequence[SupabaseFilter]
    ) -> IntegrationResult[SupabaseRowPage]:
        return self._call_client("delete", table, filters=filters)

    def rpc(
        self,
        function: str,
        params: Mapping[str, Any] | None = None,
        *,
        read_only: bool = False,
    ) -> IntegrationResult[SupabaseRowPage]:
        return self._call_client("rpc", function, params, read_only=read_only)

    # Auth
    def sign_up(
        self, *, email: str, password: str
    ) -> IntegrationResult[SupabaseSessionStatus]:
        return self._call_client("sign_up", email=email, password=password)

    def sign_in_with_password(
        self, *, email: str, password: str
    ) -> IntegrationResult[SupabaseSessionStatus]:
        return self._call_client(
            "sign_in_with_password", email=email, password=password
        )

    def sign_in_with_otp(
        self, *, email: str, redirect_to: str | None = None
    ) -> IntegrationResult[SupabaseSessionStatus]:
        return self._call_client(
            "sign_in_with_otp", email=email, redirect_to=redirect_to
        )

    def begin_oauth(
        self,
        provider: str,
        *,
        redirect_to: str | None = None,
        scopes: str | None = None,
    ) -> IntegrationResult[SupabaseOAuthStart]:
        return self._call_client(
            "begin_oauth", provider, redirect_to=redirect_to, scopes=scopes
        )

    def get_user(
        self, access_token: str | None = None
    ) -> IntegrationResult[SupabaseSessionStatus]:
        return self._call_client("get_user", access_token)

    def refresh_session(
        self, refresh_token: str | None = None
    ) -> IntegrationResult[SupabaseSessionStatus]:
        return self._call_client("refresh_session", refresh_token)

    def sign_out(self, *, scope: str = "local") -> IntegrationResult[None]:
        return self._call_client("sign_out", scope=scope)

    def reset_password_email(
        self, email: str, *, redirect_to: str | None = None
    ) -> IntegrationResult[None]:
        return self._call_client("reset_password_email", email, redirect_to=redirect_to)

    # Storage
    def list_buckets(self) -> IntegrationResult[list[SupabaseBucket]]:
        return self._call_client("list_buckets")

    def create_bucket(
        self,
        bucket: str,
        *,
        public: bool = False,
        file_size_limit: int | None = None,
        allowed_mime_types: Sequence[str] = (),
    ) -> IntegrationResult[None]:
        return self._call_client(
            "create_bucket",
            bucket,
            public=public,
            file_size_limit=file_size_limit,
            allowed_mime_types=allowed_mime_types,
        )

    def delete_bucket(
        self, bucket: str, *, empty_first: bool = False
    ) -> IntegrationResult[None]:
        return self._call_client("delete_bucket", bucket, empty_first=empty_first)

    def upload_bytes(
        self,
        bucket: str,
        path: str,
        content: bytes,
        *,
        content_type: str = "application/octet-stream",
        upsert: bool = False,
    ) -> IntegrationResult[None]:
        return self._call_client(
            "upload_bytes",
            bucket,
            path,
            content,
            content_type=content_type,
            upsert=upsert,
        )

    def upload_file(
        self,
        bucket: str,
        path: str,
        local_path: str | Path,
        *,
        content_type: str = "application/octet-stream",
        upsert: bool = False,
    ) -> IntegrationResult[None]:
        return self._call_client(
            "upload_file",
            bucket,
            path,
            local_path,
            content_type=content_type,
            upsert=upsert,
        )

    def download_bytes(self, bucket: str, path: str) -> IntegrationResult[bytes]:
        return self._call_client("download_bytes", bucket, path)

    def list_objects(
        self,
        bucket: str,
        *,
        prefix: str | None = None,
        limit: int = 100,
        offset: int = 0,
        search: str | None = None,
    ) -> IntegrationResult[list[dict[str, Any]]]:
        return self._call_client(
            "list_objects",
            bucket,
            prefix=prefix,
            limit=limit,
            offset=offset,
            search=search,
        )

    def move_object(
        self, bucket: str, source: str, destination: str
    ) -> IntegrationResult[None]:
        return self._call_client("move_object", bucket, source, destination)

    def copy_object(
        self, bucket: str, source: str, destination: str
    ) -> IntegrationResult[None]:
        return self._call_client("copy_object", bucket, source, destination)

    def remove_objects(
        self, bucket: str, paths: Sequence[str]
    ) -> IntegrationResult[None]:
        return self._call_client("remove_objects", bucket, paths)

    # Functions
    def invoke_function(
        self,
        function: str,
        *,
        body: Any = None,
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> IntegrationResult[SupabaseFunctionResult]:
        return self._call_client(
            "invoke_function",
            function,
            body=body,
            headers=headers,
            timeout_seconds=timeout_seconds,
        )


def create_integration() -> SupabaseIntegration:
    """Create an uninitialized integration for entry-point discovery."""
    return SupabaseIntegration()
