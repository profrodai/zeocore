"""AT Protocol HTTP client wrapper for zeo_core's Bluesky integration.

Talks directly to the AT Protocol XRPC HTTP surface over `requests`
(`github/client.py`'s own transport choice; no first-party or well-known
third-party `atproto` SDK is a declared zeocore dependency, so this follows
the already-established in-repo pattern of a thin hand-rolled HTTP wrapper
rather than adding a new SDK dependency for two endpoints).

**Every shape below is read from the OFFICIAL AT Protocol lexicon JSON
schemas in `bluesky-social/atproto` (github.com/bluesky-social/atproto,
`lexicons/`), never from Postiz.** RULING-409 s1/s6b A: Postiz is
AGPL-3.0 and zeocore is MIT; Postiz is a specification and test oracle at
most, never a source, and that boundary extends to translation -- so this
module's shapes are independently re-derived from the protocol's own
canonical schema definitions, not read off Postiz's TypeScript.

- **`com.atproto.server.createSession`**
  (`lexicons/com/atproto/server/createSession.json`): a `POST` taking
  `{identifier, password}`, returning `{accessJwt, refreshJwt, did, handle,
  ...}` -- all four response fields are declared `required` in the lexicon.
- **`com.atproto.repo.createRecord`**
  (`lexicons/com/atproto/repo/createRecord.json`): a `POST` taking
  `{repo, collection, record}` (all three required; `record` "must contain
  a $type field"), returning `{uri, cid, ...}`.
- **`app.bsky.feed.post`** (`lexicons/app/bsky/feed/post.json`): the record
  shape itself -- `text` (required, <=300 graphemes/3000 bytes),
  `createdAt` (required, ISO-8601), `facets` (optional, rich-text
  annotations), `langs`, `reply`, `embed` (all optional, none implemented
  here -- out of this SOW's scope).
"""

from datetime import UTC, datetime
from typing import Any

import requests

from zeo_core.core.logging import get_logger

logger = get_logger(__name__)

_TIMEOUT_SECONDS = 30.0


class BlueskyAPIError(Exception):
    """Raised when the Bluesky/AT Protocol API returns an error response."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class BlueskyClient:
    """Thin client over the AT Protocol XRPC HTTP surface.

    Only the two calls this integration needs: creating a session (auth)
    and creating a post record. Both endpoint shapes are read directly from
    the official AT Protocol lexicon schemas (see module docstring) rather
    than from any third-party implementation.
    """

    def __init__(
        self,
        service_url: str = "https://bsky.social",
        session: requests.Session | None = None,
        timeout: float = _TIMEOUT_SECONDS,
    ) -> None:
        """Initialize the AT Protocol client.

        Args:
            service_url: The PDS host to talk to (e.g. `https://bsky.social`).
            session: Optional `requests.Session` (or a test double
                satisfying the same `.post()` surface), for testing.
            timeout: Per-request timeout in seconds.
        """
        self.service_url = service_url.rstrip("/")
        self._session = session or requests.Session()
        self.timeout = timeout
        self._access_jwt: str | None = None

    def _xrpc_url(self, method: str) -> str:
        return f"{self.service_url}/xrpc/{method}"

    def _raise_for_error(self, response: requests.Response) -> None:
        if response.status_code < 400:
            return
        try:
            body = response.json()
            message = body.get("message") or body.get("error") or response.text
        except ValueError:
            message = response.text
        raise BlueskyAPIError(
            f"AT Protocol request failed ({response.status_code}): {message}",
            status=response.status_code,
        )

    def create_session(self, identifier: str, password: str) -> dict[str, Any]:
        """Call `com.atproto.server.createSession`.

        Args:
            identifier: Bluesky handle or email.
            password: App password.

        Returns:
            The session response dict: `accessJwt`, `refreshJwt`, `did`,
            `handle`, and any other fields the server includes.

        Raises:
            BlueskyAPIError: On a non-2xx response.
        """
        response = self._session.post(
            self._xrpc_url("com.atproto.server.createSession"),
            json={"identifier": identifier, "password": password},
            timeout=self.timeout,
        )
        self._raise_for_error(response)
        session: dict[str, Any] = response.json()
        self._access_jwt = session.get("accessJwt")
        return session

    def create_post_record(
        self,
        repo: str,
        text: str,
        access_jwt: str,
        facets: list[dict[str, Any]] | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        """Call `com.atproto.repo.createRecord` with an `app.bsky.feed.post`
        record.

        Args:
            repo: The handle or DID of the posting account.
            text: Post text (<=300 graphemes / 3000 bytes per the
                `app.bsky.feed.post` lexicon -- not independently
                re-validated here; the server is the source of truth and
                returns an error for an oversized post).
            access_jwt: A live `accessJwt` from `create_session`.
            facets: Optional rich-text facets (link/mention/tag
                annotations), each shaped per `app.bsky.richtext.facet`.
            created_at: ISO-8601 timestamp; defaults to now (UTC) if omitted.

        Returns:
            The createRecord response dict: `uri`, `cid`, and any other
            fields the server includes.

        Raises:
            BlueskyAPIError: On a non-2xx response.
        """
        record: dict[str, Any] = {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": created_at or datetime.now(UTC).isoformat(),
        }
        if facets:
            record["facets"] = facets

        response = self._session.post(
            self._xrpc_url("com.atproto.repo.createRecord"),
            json={
                "repo": repo,
                "collection": "app.bsky.feed.post",
                "record": record,
            },
            headers={"Authorization": f"Bearer {access_jwt}"},
            timeout=self.timeout,
        )
        self._raise_for_error(response)
        result: dict[str, Any] = response.json()
        return result
