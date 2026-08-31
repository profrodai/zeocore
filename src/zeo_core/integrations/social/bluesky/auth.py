"""Authentication provider for the Bluesky integration.

Bluesky's own auth model (verified against the official AT Protocol lexicon,
`com.atproto.server.createSession` -- see this package's `client.py` module
docstring for the exact source read) is a single POST carrying `identifier`
(handle or email) and `password` (an **app password**, pasted from ordinary
Bluesky account settings -- Settings > App Passwords -- never the account's
main password). There is no OAuth dance, no developer app, no approval
step: RULING-409 s6c names this as the asymmetry the whole phase-one
sequencing is built on.

The session response carries a short-lived `accessJwt` and a longer-lived
`refreshJwt`, plus the account's `did` and `handle`. This provider persists
the app password (not the JWTs, which expire in minutes) as the durable
credential -- re-authenticating with the stored app password is simpler and
more robust than a refresh-token dance for a credential class that itself
never expires, and matches `NotionAuthProvider`'s own choice to persist the
long-lived integration token rather than any derived short-lived value.

Structurally this mirrors `NotionAuthProvider` (integrations/notion/auth.py)
closely: a static-credential auth model backed by an SDK-shaped client
Protocol, an injectable client factory for testing, and the same
`_load_credentials`/`_save_token_data` pair -- rather than
`GoogleAuthProvider`'s OAuth-flow shape, which does not apply here.
"""

import time
from pathlib import Path
from typing import Any, Protocol

from zeo_core.core.logging import LOG_LEVELS, LogLevel, get_logger
from zeo_core.integrations.core import AuthResult, BaseAuthProvider
from zeo_core.integrations.social.bluesky.credential_paths import (
    create_directory_with_fallback,
    get_file_info_with_fallback,
    read_json_with_fallback,
    write_json_with_fallback,
)

logger = get_logger(__name__)


class _BlueskySessionClient(Protocol):
    """Minimal protocol for the AT Protocol session client used by this
    package. Named `_BlueskySessionClient` (not `_AuthClient`) because
    `BlueskyIntegration.post()` also uses this same protocol via
    `BlueskyAuthProvider.build_client()` -- only the surface actually called
    across the package is named, so a test double needs to implement
    nothing else, mirroring `NotionAuthProvider`'s own `_NotionSDKClient`
    Protocol shape one file over."""

    def create_session(self, identifier: str, password: str) -> dict[str, Any]: ...

    def create_post_record(
        self,
        repo: str,
        text: str,
        access_jwt: str,
        facets: list[dict[str, Any]] | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]: ...


class BlueskyAuthProvider(BaseAuthProvider):
    """Bluesky authentication provider using a pasted app password.

    Persists the app password (RULING-356/RULING-409 s6c/s6e: 0600, atomic,
    following `notion/auth.py:225` exactly) rather than the session JWTs,
    which expire in minutes and are re-derived on each `authenticate()`
    call via a fresh `createSession`.
    """

    def __init__(
        self,
        credentials_file: str | None = None,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
        session_client_factory: Any = None,  # noqa: ANN401 -- injectable factory for testing; real default is a thin wrapper over httpx, built lazily in _build_client()
    ) -> None:
        """Initialize the Bluesky authentication provider.

        Args:
            credentials_file: Path to credentials file for storing the app
                password. Defaults are resolved by the caller
                (`BlueskyIntegration.initialize()`), matching how
                `NotionAuthProvider` is constructed with no default either.
            log_level: Logging level.
            session_client_factory: Optional factory
                `(service_url) -> _BlueskySessionClient`-shaped callable, for
                testing. Defaults to the real HTTP-backed client.
        """
        super().__init__(credentials_file=credentials_file, log_level=log_level)
        self.identifier: str | None = None
        self.app_password: str | None = None
        self.service_url: str = "https://bsky.social"
        self.did: str | None = None
        self.handle: str | None = None
        self._access_jwt: str | None = None
        self._refresh_jwt: str | None = None
        self._session_client_factory = session_client_factory

    @property
    def name(self) -> str:
        """Name of the authentication provider."""
        return "Bluesky"

    def build_client(self, service_url: str | None = None) -> _BlueskySessionClient:
        """Build (or fetch, via the injected factory) a session client for
        `service_url` (defaults to `self.service_url`, the host this
        provider last authenticated against).

        Public (not `_`-prefixed) because `BlueskyIntegration.post()`
        deliberately reuses the same client construction path to issue the
        `createRecord` call with the session this provider already
        authenticated -- a real collaboration between the two classes in
        this package, not an internal implementation detail being reached
        into from outside.
        """
        return self._build_client(service_url or self.service_url)

    def _build_client(self, service_url: str) -> _BlueskySessionClient:
        """Build (or fetch, via the injected factory) a session client for
        `service_url`."""
        if self._session_client_factory is not None:
            client: _BlueskySessionClient = self._session_client_factory(service_url)
            return client

        from zeo_core.integrations.social.bluesky.client import BlueskyClient

        return BlueskyClient(service_url=service_url)

    def authenticate(
        self,
        identifier: str | None = None,
        app_password: str | None = None,
        service_url: str | None = None,
    ) -> AuthResult:
        """Authenticate with Bluesky using a pasted app password.

        Args:
            identifier: Bluesky handle or email.
            app_password: The pasted app password (never the main account
                password -- Bluesky's own docs are explicit that app
                passwords, not the primary password, are for third-party
                use).
            service_url: The PDS host to authenticate against (defaults to
                `https://bsky.social`).

        Returns:
            Authentication result.
        """
        if service_url:
            self.service_url = service_url

        if identifier and app_password:
            self.identifier = identifier
            self.app_password = app_password
            logger.debug("Using provided identifier/app_password for authentication")
        elif not self.identifier or not self.app_password:
            credentials = self._load_credentials()
            if (
                credentials
                and credentials.get("identifier")
                and credentials.get("app_password")
            ):
                self.identifier = credentials.get("identifier")
                self.app_password = credentials.get("app_password")
                if credentials.get("service_url"):
                    self.service_url = credentials["service_url"]
                logger.debug("Loaded identifier/app_password from credentials file")

        if not self.identifier or not self.app_password:
            logger.error(
                "No Bluesky identifier/app_password available for authentication"
            )
            return AuthResult.error_result(
                error="No Bluesky identifier/app_password provided",
                message=(
                    "Please provide a Bluesky handle and app password via "
                    "parameters or a credentials file. An app password is "
                    "created at Settings > App Passwords on bsky.app -- "
                    "never use the main account password."
                ),
            )

        try:
            session_client = self._build_client(self.service_url)
            session = session_client.create_session(self.identifier, self.app_password)

            self.did = session.get("did")
            self.handle = session.get("handle")
            self._access_jwt = session.get("accessJwt")
            self._refresh_jwt = session.get("refreshJwt")

            self._save_token_data()
            self.authenticated = True

            return AuthResult.success_result(
                token=self._access_jwt,
                message="Successfully authenticated with Bluesky",
                credentials_path=self.credentials_file,
                content={"did": self.did, "handle": self.handle},
            )
        except Exception as e:
            error_message = str(e)
            status = getattr(e, "status", None)
            if status == 401:
                return AuthResult.error_result(
                    error="Invalid Bluesky identifier or app password (unauthorized)",
                    message=error_message,
                )
            return AuthResult.error_result(
                error=f"Bluesky authentication failed: {error_message}",
                message=error_message,
            )

    def refresh_credentials(self) -> AuthResult:
        """Refresh Bluesky credentials.

        Bluesky's `accessJwt` expires in minutes, but re-running
        `authenticate()` with the stored app password is simpler and just
        as correct as implementing the `com.atproto.server.refreshSession`
        flow -- the app password itself does not expire, so this is not a
        no-op the way `NotionAuthProvider.refresh_credentials` is (a
        personal-access-token credential with genuinely no refresh flow at
        all); it is a real re-authentication using the durable credential.
        """
        if not self.identifier or not self.app_password:
            return AuthResult.error_result(
                error="No Bluesky identifier/app_password available to refresh",
            )
        return self.authenticate(
            identifier=self.identifier,
            app_password=self.app_password,
            service_url=self.service_url,
        )

    def get_credentials(self) -> object:
        """Get the current Bluesky credentials.

        Returns:
            Dictionary with identifier, session identity, and JWTs.
        """
        if not self.identifier or not self.app_password:
            credentials = self._load_credentials()
            if credentials:
                self.identifier = credentials.get("identifier")
                self.app_password = credentials.get("app_password")

        return {
            "identifier": self.identifier,
            "did": self.did,
            "handle": self.handle,
            "access_jwt": self._access_jwt,
            "refresh_jwt": self._refresh_jwt,
        }

    def save_credentials(self) -> bool:
        """Save Bluesky credentials to file.

        Returns:
            True if credentials were saved, False otherwise.
        """
        return self._save_token_data()

    def _load_credentials(self) -> dict[str, Any] | None:
        """Load Bluesky credentials from file.

        Routed through the sandbox-escape-aware
        `get_file_info_with_fallback`/`read_json_with_fallback` rather than
        calling `standalone` directly, for the same reason `_save_token_data`
        does: the default credentials path is outside the CWD-anchored
        sandbox from most working directories.
        """
        if not self.credentials_file:
            logger.debug("No credentials file specified")
            return None

        file_info = get_file_info_with_fallback(self.credentials_file)
        if not file_info.ok or not file_info.exists:
            logger.debug(f"Credentials file does not exist: {self.credentials_file}")
            return None

        result = read_json_with_fallback(self.credentials_file)
        if not result.ok:
            logger.warning(f"Failed to read credentials file: {result.error}")
            return None

        data: dict[str, Any] | None = result.data
        logger.debug("Successfully loaded credentials from file")
        return data

    def _save_token_data(self) -> bool:
        """Save the app password credential to disk.

        0600, atomic -- RULING-356 / RULING-409 s6c/s6e, following
        `notion/auth.py:225` exactly (`fs.write_json(..., atomic=True,
        mode=0o600)`), routed through `write_json_with_fallback` because the
        default credentials path (platformdirs-based) sits outside the
        FileSystemService singleton's CWD-anchored sandbox from most working
        directories -- the same reason Google's own credential writes need
        the identical fallback (see `credential_paths.py`'s module
        docstring).

        Directory creation goes through `create_directory_with_fallback`
        directly rather than the base class's `_ensure_credentials_directory`
        (which calls `standalone.create_directory` with no sandbox-escape
        fallback and would silently fail -- return `False`, not raise -- for
        this exact platformdirs path from a fresh directory). This mirrors
        `GoogleAuthProvider._save_credentials_to_file`, which makes the same
        substitution for the same reason.
        """
        if not self.identifier or not self.app_password or not self.credentials_file:
            return False

        directory_path = str(Path(self.credentials_file).parent)
        dir_result = create_directory_with_fallback(directory_path, exist_ok=True)
        if not dir_result.ok:
            logger.error(
                f"Failed to create credentials directory {directory_path}: "
                f"{dir_result.error}"
            )
            return False

        credentials: dict[str, Any] = {
            "identifier": self.identifier,
            "app_password": self.app_password,
            "service_url": self.service_url,
            "saved_at": int(time.time()),
        }
        if self.did:
            credentials["did"] = self.did
        if self.handle:
            credentials["handle"] = self.handle

        # 0600: this file holds a live app password (RULING-356 s4.4 item 4 /
        # RULING-409 s6c/s6e).
        result = write_json_with_fallback(
            self.credentials_file, credentials, mode=0o600
        )
        return bool(result.ok)
