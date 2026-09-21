"""Local enrollment and token lifecycle for one person's own Revolut account.

Enrollment is three explicit steps, because Revolut issues a client id only
after the certificate has been registered by hand:

1. ``setup``      generate a key and certificate; register the certificate.
2. ``authorize``  record the client id; open the consent URL it returns.
3. ``complete``   paste the URL Revolut redirected to; tokens are stored.

Local does not mean race-free. Two scripts can share these files, and a
process can die after Revolut has processed a refresh. Revolut invalidates the
previous access token on refresh, so a lost answer leaves this client unable
to say whether its stored token still works. Therefore:

* a marker is written durably BEFORE a refresh request is sent and removed
  only when a definite answer has been stored;
* a marker found afterwards means the outcome is UNKNOWN. That state is
  blocked: nothing here refreshes again, however much time passes. Waiting
  longer proves nothing about what the provider did;
* the stored token keeps serving reads while Revolut accepts it;
* NOTHING here clears that state. A fresh consent on the same registration
  authorizes new tokens; it does not settle what the provider did with the lost
  request, so it stores the new access token and leaves the marker in place:
  reads continue, refreshing stays blocked. A file lock is local and says
  nothing about the provider either.
* No QUALIFIED recovery procedure exists yet. ``setup(new_key=True)`` starts a
  new registration and records that it followed an unresolved outcome. Whether
  a new key and client id, or deleting the old certificate at Revolut, isolates
  the new registration from a late refresh of the old one is unverified, and
  this module does not claim it.

A stored enrollment is bound to the environment it was created for. It is never
reinterpreted: a store written for sandbox is refused by a production-selected
object before any client is built or any credential is sent.

Every error names what was observed, never a diagnosis: a rejected token does
not establish that consent was revoked.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TypeVar
from urllib.parse import parse_qs, urlsplit

from pydantic import SecretStr

from ..client import RevolutBusinessClient
from ..models import RevolutEnvironment
from ..transport import RevolutAPIError
from .auth import (
    HttpRevolutTokenGateway,
    RevolutTokenGateway,
    TokenFailure,
    consent_url,
    generate_client_key,
    public_certificate,
)
from .store import (
    CERTIFICATE_FILENAME,
    KEY_FILENAME,
    EnrollmentState,
    LocalCredentialStore,
    RefreshAttempt,
    default_directory,
)

T = TypeVar("T")
REFRESH_BEFORE_EXPIRY = timedelta(minutes=5)


class LocalEnrollmentError(RuntimeError):
    """``code`` is a fixed category; the message never contains a credential."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _not_enrolled() -> LocalEnrollmentError:
    return LocalEnrollmentError(
        "NOT_ENROLLED", "Run setup, authorize and complete before reading"
    )


class LocalRevolutEnrollment:
    """The explicitly selected local profile. Nothing falls back to it."""

    def __init__(
        self,
        environment: RevolutEnvironment,
        *,
        store: LocalCredentialStore | None = None,
        gateway: RevolutTokenGateway | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        client_factory: Callable[
            [SecretStr, RevolutEnvironment], RevolutBusinessClient
        ] = lambda token, environment: RevolutBusinessClient(
            token, environment=environment
        ),
    ) -> None:
        self.environment = RevolutEnvironment(environment)
        self._store = store or LocalCredentialStore(default_directory(self.environment))
        self._gateway = gateway or HttpRevolutTokenGateway()
        self._clock = clock
        self._client = client_factory

    @property
    def store(self) -> LocalCredentialStore:
        return self._store

    # -- enrollment -----------------------------------------------------

    def setup(self, *, redirect_uri: str, new_key: bool = False) -> str:
        """Create the key and certificate. Returns the certificate's path."""

        target = urlsplit(redirect_uri)
        if target.scheme != "https" or not target.hostname or target.fragment:
            raise LocalEnrollmentError(
                "REDIRECT_URI", "The redirect URI must be an https URL"
            )
        with self._store.locked():
            existing = self._store.read_private(KEY_FILENAME)
            if not new_key:
                self._load()  # another environment's files are never adopted
            if existing is not None and not new_key:
                raise LocalEnrollmentError(
                    "KEY_EXISTS",
                    "A client key already exists; pass new_key=True to replace "
                    "it, then register the new certificate with Revolut",
                )
            key = generate_client_key()
            self._store.write_private(KEY_FILENAME, key)
            certificate = public_certificate(
                key, common_name=target.hostname, now=self._clock()
            )
            # The certificate is public; it is meant to be uploaded.
            self._store.write_private(
                CERTIFICATE_FILENAME, certificate.encode(), mode=0o600
            )
            previous = self._store.load()  # may be another environment's
            # A new key is a new registration: no credential of the old one
            # survives. That it FOLLOWED an unresolved outcome is kept, because
            # a new local binding is not evidence the old request is settled.
            self._store.save(
                EnrollmentState(
                    environment=self.environment,
                    redirect_uri=redirect_uri,
                    follows_unresolved_refresh=previous is not None
                    and (
                        previous.refresh_attempt is not None
                        or previous.follows_unresolved_refresh
                    ),
                )
            )
        return str(self._store.certificate_path)

    def authorize(self, *, client_id: str) -> str:
        """Record the client id Revolut issued; return the consent URL to open."""

        if not client_id.strip():
            raise LocalEnrollmentError("CLIENT_ID", "A client id is required")
        with self._store.locked():
            state = self._require_state()
            consent_state = secrets.token_urlsafe(32)
            self._store.save(
                state.model_copy(
                    update={
                        "client_id": client_id.strip(),
                        "consent_state": consent_state,
                    }
                )
            )
        return consent_url(
            environment=self.environment,
            client_id=client_id.strip(),
            redirect_uri=state.redirect_uri,
            state=consent_state,
        )

    def complete(self, redirected_to: str) -> None:
        """Exchange the code in the URL Revolut redirected the browser to."""

        with self._store.locked():
            state = self._require_state()
            if state.client_id is None or state.consent_state is None:
                raise LocalEnrollmentError("NOT_AUTHORIZED", "Run authorize first")
            landed = urlsplit(redirected_to)
            expected = urlsplit(state.redirect_uri)
            query = parse_qs(landed.query)
            codes, states = query.get("code", []), query.get("state", [])
            if (
                (landed.scheme, landed.netloc, landed.path)
                != (expected.scheme, expected.netloc, expected.path)
                or len(codes) != 1
                or len(states) != 1
                or not secrets.compare_digest(states[0], state.consent_state)
            ):
                raise LocalEnrollmentError(
                    "CONSENT_MISMATCH",
                    "That URL does not answer the consent request that was opened",
                )
            grant = self._gateway.exchange(
                environment=self.environment,
                client_id=state.client_id,
                issuer=expected.hostname or "",
                private_key_pem=self._key(),
                code=SecretStr(codes[0]),
                now=self._clock(),
            )
            if isinstance(grant, TokenFailure):
                raise LocalEnrollmentError(
                    "EXCHANGE_" + grant.kind.upper(),
                    "Revolut did not issue tokens; open a fresh consent URL and retry",
                )
            if grant.refresh_token is None:
                raise LocalEnrollmentError(
                    "EXCHANGE_UNKNOWN", "Revolut issued no refresh token"
                )
            # Consent authorizes new tokens. It does NOT settle an earlier
            # refresh whose answer was lost, so an unresolved marker and its
            # block survive: the new access token serves reads, refreshing
            # stays blocked. A refused grant or a rejected token, with no
            # marker, IS answered by a new grant and is cleared.
            unresolved = state.refresh_attempt is not None
            self._store.save(
                state.model_copy(
                    update={
                        "consent_state": None,
                        "access_token": grant.access_token,
                        "refresh_token": grant.refresh_token,
                        "access_expires_at": self._clock()
                        + timedelta(seconds=grant.expires_in),
                        "blocked_reason": state.blocked_reason if unresolved else None,
                    }
                )
            )

    def status(self) -> EnrollmentState | None:
        return self._load()

    # -- use ------------------------------------------------------------

    def read(self, call: Callable[[RevolutBusinessClient], T]) -> T:
        """Run one logical read with at most ONE refresh and one repeat.

        Do not wrap this in a retry: the allowance is spent here, and the
        proactive refresh near expiry uses the same single allowance.
        """

        with self._store.locked():
            state = self._load()
            if state is None or state.access_token is None:
                raise _not_enrolled()
            refreshed = False
            if (
                state.access_expires_at is not None
                and state.access_expires_at - self._clock() < REFRESH_BEFORE_EXPIRY
            ):
                state, refreshed = self._refresh(state), True
            try:
                return self._call(state, call)
            except RevolutAPIError as error:
                if error.code != "AUTHENTICATION":
                    raise
                if refreshed:
                    raise self._block(state, "TOKEN_REJECTED") from None
            state = self._refresh(state)
            try:
                return self._call(state, call)
            except RevolutAPIError as error:
                if error.code != "AUTHENTICATION":
                    raise
                raise self._block(state, "TOKEN_REJECTED") from None

    def _call(
        self, state: EnrollmentState, call: Callable[[RevolutBusinessClient], T]
    ) -> T:
        if state.access_token is None:
            raise _not_enrolled()
        client = self._client(state.access_token, self.environment)
        try:
            return call(client)
        finally:
            client.close()

    def _refresh(self, state: EnrollmentState) -> EnrollmentState:
        """Caller holds the lock. Never sends over an unresolved attempt."""

        if state.blocked_reason is not None:
            raise _blocked(state.blocked_reason)
        if state.refresh_attempt is not None:
            # Holding the lock proves the sender is gone, not what it achieved.
            raise self._block(state, "OUTCOME_UNKNOWN")
        if state.refresh_token is None or state.client_id is None:
            raise _not_enrolled()
        attempt = RefreshAttempt(attempt_id=secrets.token_hex(8), sent_at=self._clock())
        sending = state.model_copy(update={"refresh_attempt": attempt})
        self._store.save(sending)  # durable BEFORE the request can leave
        grant = self._gateway.refresh(
            environment=self.environment,
            client_id=state.client_id,
            issuer=urlsplit(state.redirect_uri).hostname or "",
            private_key_pem=self._key(),
            refresh_token=state.refresh_token,
            now=self._clock(),
        )
        if isinstance(grant, TokenFailure):
            if grant.kind == "unknown":
                # The marker stays. The provider may have refreshed.
                raise self._block(sending, "OUTCOME_UNKNOWN")
            if grant.kind == "refused":
                raise self._block(state, "GRANT_REFUSED")
            self._store.save(state)  # nothing reached the provider
            raise LocalEnrollmentError(
                "UNAVAILABLE", "Revolut could not be reached; nothing changed"
            )
        current = state.model_copy(
            update={
                "access_token": grant.access_token,
                "refresh_token": grant.refresh_token or state.refresh_token,
                "access_expires_at": self._clock()
                + timedelta(seconds=grant.expires_in),
                "refresh_attempt": None,
            }
        )
        self._store.save(current)
        return current

    def _block(self, state: EnrollmentState, reason: str) -> LocalEnrollmentError:
        if state.blocked_reason is None:
            self._store.save(state.model_copy(update={"blocked_reason": reason}))
        return _blocked(state.blocked_reason or reason)

    def _load(self) -> EnrollmentState | None:
        """Every use of stored credentials goes through here.

        Refuses before any client is built or any credential leaves: an
        enrollment belongs to the environment it was created for.
        """

        state = self._store.load()
        if state is not None and state.environment is not self.environment:
            raise LocalEnrollmentError(
                "ENVIRONMENT_MISMATCH",
                f"These files hold a {state.environment.value} enrollment; they "
                f"are never used for {self.environment.value}. Enroll that "
                "environment separately",
            )
        return state

    def _require_state(self) -> EnrollmentState:
        state = self._load()
        if state is None:
            raise LocalEnrollmentError("NOT_SET_UP", "Run setup first")
        return state

    def _key(self) -> bytes:
        key = self._store.read_private(KEY_FILENAME)
        if key is None:
            raise LocalEnrollmentError("NOT_SET_UP", "Run setup first")
        return key


_BLOCKED = {
    "OUTCOME_UNKNOWN": (
        "A token refresh was sent and its answer was never recorded, so it is "
        "unknown whether the stored token still works. Nothing will refresh "
        "again; run authorize and complete to give a fresh consent"
    ),
    "GRANT_REFUSED": (
        "Revolut refused to refresh the tokens; run authorize and complete"
    ),
    "TOKEN_REJECTED": (
        "Revolut rejected a freshly issued token; run authorize and complete"
    ),
}


def _blocked(reason: str) -> LocalEnrollmentError:
    return LocalEnrollmentError(reason, _BLOCKED[reason])


__all__ = ["REFRESH_BEFORE_EXPIRY", "LocalEnrollmentError", "LocalRevolutEnrollment"]
