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
and construct a client with the current token. A `RevolutAPIError` with code
`AUTHENTICATION` means the supplied token was rejected; this client never
refreshes, retries or falls back to another credential source.

There is deliberately no local credential path. The setup catalogue reports the
local profile as unsupported, and a hosted failure never falls back to local
credentials. Start with [managed environments](environments.md): the
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

Revolut pages transactions backwards by `created_at` and has no cursor token.
`list_transactions` returns one page, newest first. When the page is full,
`next_to` is the oldest `created_at` in it; pass it as the next `to`.

- Adjacent pages can overlap at that instant, and whether Revolut treats `to`
  as inclusive is unverified. **Deduplicate by transaction `id`.**
- A full page that cannot move the cursor raises `PAGINATION_STALLED` instead
  of looping or silently dropping transactions. Narrow the window or raise
  `count` (maximum 1000).
- There is no collect-everything helper: a hosted operation must stay inside
  its response limit and a replay must be deterministic.

## Normalization

Results carry `normalization_version = "revolut-business-read-1"`.

- Amounts are parsed from JSON numbers directly into `Decimal`; they never pass
  through a binary float.
- Provider fields not declared by the models are dropped. From `card`, only the
  card `id` is kept: card number, holder name and phone are discarded.
- Provider enumerations (`type`, `state`, `account_type`) are kept as bounded
  lowercase tokens, so a new provider value does not fail a whole page.
- A response that repeats the request credential anywhere is refused.

This output is normalized application data. It is not raw provider evidence
and must not be stored or labelled as raw. Errors never retain provider
bodies, request URLs or validation detail.

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
