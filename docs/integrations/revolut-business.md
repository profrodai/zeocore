# Revolut Business read client

Created 2026-09-20. Doctrine Rev 17 with the active operator delegation.

`zeo_core.integrations.revolut.RevolutBusinessClient` performs two reviewed,
read-only Revolut Business API operations: list accounts and read one bounded
page of transactions. It is a library client. It holds no credentials of its
own, reads no environment variable and is not a package entry point.

**Live behaviour is unverified.** The models and routes are derived from
Revolut's published Business OpenAPI description and exercised against offline
fixtures only. No sandbox or production request has been made with this client.

## Who owns what

| Concern | Owner |
|---|---|
| Typed operations, fixed-origin transport, normalization | This client |
| Certificate registration, client-assertion signing, consent, token exchange and refresh, custody, revocation | The credential owner: ZEOconnect for hosted use |
| Paging loop, checkpoints, deduplication, evidence storage, matching | The consuming application |

The access token is a constructor argument valid for the life of the object.
Revolut access tokens last about 40 minutes and refreshing invalidates the
previous token, so the credential owner must coordinate refresh per connection
and construct a client with the current token. This client never refreshes,
retries or falls back to another credential source.

Error codes are sanitized categories, not diagnoses. `AUTHENTICATION` (401)
does not establish that a token expired, and `ACCESS` (403) does not establish
that a connection was revoked. The credential owner combines the category with
its own credential state and refresh evidence, and must bound and account for
any refresh-and-repeat it performs.

There is deliberately no supported local enrollment flow. The setup catalogue
reports the local profile as unsupported, and a hosted failure never falls back
to local credentials. The class can still be constructed anywhere a token is
injected, which the Broker and tests rely on. Start with [managed environments](environments.md): the
`revolut.business` selection forwards no provider variables.

## Use

```python
from pydantic import SecretStr
from zeo_core.integrations.revolut import (
    RevolutBusinessClient,
    RevolutEnvironment,
    TransactionQuery,
)

client = RevolutBusinessClient(token, environment=RevolutEnvironment.SANDBOX)
try:
    accounts = client.list_accounts()
    page = client.list_transactions(TransactionQuery(from_=since, count=200))
    while page.next_to is not None:
        page = client.list_transactions(
            TransactionQuery(from_=since, to=page.next_to, count=200)
        )
finally:
    client.close()
```

`token` is a `SecretStr` supplied by the credential owner. `environment`
selects one of two fixed origins; a caller can never supply a provider URL.

## Paging contract

Revolut's published description pages transactions by a `from`/`to` window on
`created_at` with a `count`, and has no cursor token. `list_transactions`
returns one page. When the page is full, `next_to` is the oldest `created_at`
in it, computed without assuming any provider ordering; pass it as the next `to`.

**A page is an observation, not a snapshot.** The same window and cursor can
return different records later: transactions change state, and new ones can
appear inside a window already read. Each page carries `observed_at`.

- Key stored transactions by `id`. A projection with a later `updated_at`
  replaces the earlier one; keep earlier observations as history, do not
  discard them as duplicates.
- Adjacent pages can overlap at `next_to`. Whether Revolut treats `to` as
  inclusive, how it orders results and how it breaks `created_at` ties are
  **unverified against the live API**; replacement by `id` is what makes the
  loop safe under any of those answers.
- Progress is detected, not assumed: a full page whose oldest instant does not
  move below the requested `to` raises `PAGINATION_STALLED`. Narrow the window
  or raise `count` (maximum 1000).
- Any error means the window was **not** fully read. Record an incomplete sync
  with the last good cursor; never report completion.
- There is no collect-everything helper.

## Size bounds

A bounded count does not bound bytes, so both sides are bounded explicitly.

- The upstream body is streamed and abandoned once it passes
  `MAX_UPSTREAM_BYTES` (8 MiB), before any parsing. Error bodies are never read.
- The normalized, serialized result must fit `MAX_RESULT_BYTES` (768 KiB, below
  the 1 MiB hosted JSON limit with room for its envelope).

Either breach raises `RESPONSE_TOO_LARGE` and returns nothing. Results are never
truncated: a silently shortened page would lose evidence needed for matching.
Lower `count` or narrow the window and read again.

## Normalization

Results carry `normalization_version = "revolut-business-read-1"`.

- Amounts are parsed from JSON numbers directly into `Decimal`; they never pass
  through a binary float.
- Provider fields not declared by the models are dropped. From `card`, only the
  card `id` is kept: card number, holder name and phone are discarded.
- Provider enumerations (`type`, `state`, `account_type`) are kept as bounded
  lowercase tokens, so a new provider value does not fail a whole page.

This output is normalized application data. It is not raw provider evidence
and must not be stored or labelled as raw.

## What the credential tests do and do not show

Only declared, typed fields leave the client, errors carry fixed messages with
no provider body, URL or validation detail, and representations of the client,
transport and errors omit the token. Tests plant a canary credential and check
those outputs, malformed and undecodable responses, and debug-level logs.

That shows the **supplied credential** does not leak through the exercised
paths. It does not show that provider text can never contain some other
token-like value: free-text fields such as `reference` are passed through as
data. As defence in depth, a response containing the request's own token is
refused; this is not a general secret scanner.

## Test account track

Use a Revolut Business **sandbox** account and `RevolutEnvironment.SANDBOX`.
The sandbox has its own certificate registration, client ID and consent, fully
separate from production. A developer may construct the client with a sandbox
access token to exercise the transport; that is implementation evidence for
this client only, not a supported way to run an application.

## Production account track

Production access is obtained only through the credential owner's assisted
enrollment: register that connection's public certificate in Revolut Business
settings, complete consent, and verify the business and account binding before
activation. Request read access only. If the Revolut account enforces an IP
allowlist, the credential owner's egress addresses must be registered.

## Bounded E2E

Not yet run. The first live check should be: list accounts, read one page of
at most ten transactions from a one-day window, and confirm that amounts match
the Revolut web interface to the minor unit. Record the environment, date and
outcome alongside the change that claims it.
