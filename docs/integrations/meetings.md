# Runtime-admitted meeting operations

<!-- Teaches CLAUDE.md Rev 17; reviewed 2026-09-09. -->

This source-only API is newer than Zeocore 0.10.0. Install the reviewed source
revision to use `zeo_core.integrations.meetings`; the published 0.10.0 wheel does
not contain it. It connects a host's meeting invocation to the existing local
meeting runtime and host-configured provider clients.

The host supplies the confirmed meeting action and current lease/attempt. The
runtime validates and durably consumes authority before a provider operation.
Zeocore validates the exact request and resource, dispatches once, and admits a
receipt. It creates no second scheduler, execution ledger, lease, or approval.

## Closed operations and resource bindings

| Operation | Exact resource | Payload |
|---|---|---|
| `notion.page.upsert` | `notion:<destination_parent_id>` | Existing `NotionPageUpsertRequest`; meeting ID must match authority |
| `sheets.values.read` | `sheets:<spreadsheet_id>:<range_a1>` | Spreadsheet ID and finite A1 cell/rectangle, at most 10,000 cells |
| `calendar.events.list` | `calendar:<calendar_id>` | Calendar ID, aware `time_min` and `time_max`, `max_results` |
| `gmail.draft.create` | `gmail:<mailbox>:drafts` | Mailbox, 1–20 unique recipients, subject, plain text body |
| `gmail.draft.get` | `gmail:<mailbox>:draft:<draft_id>` | Mailbox and exact draft ID |
| `gmail.draft.reconcile` | `gmail:<mailbox>:drafts` | Original create payload plus `creation_idempotency_key` |

No extra payload fields are accepted. Calendar intervals must be positive and at
most 31 days, with 1–250 returned events. Sheets requires uppercase A1 column
letters and explicit positive row numbers; named ranges and entire columns are
refused. Empty successful read results are valid. Gmail has no send route and
Calendar has no mutation adapter.

`request_digest(payload)` hashes UTF-8 JSON with sorted keys, compact separators,
Unicode preserved and non-finite numbers refused. The host must use that digest
and the table's exact resource string when obtaining the lease. Changing even
an optional field after admission changes the request. Provider credentials are
host-owned and never belong in the payload or runtime receipt.

## Prepare a request offline

From the current checkout, install the source and run the complete example:

```bash
uv pip install -e .
python examples/meeting_request_v1.py
```

The [script](../../examples/meeting_request_v1.py) prepares a bounded Sheets
resource and its exact request digest. It shows that changing the range changes
the digest. It creates no lease, contacts no runtime and makes no Google call.

This meeting-v1 API predates the [generic capability host](../how-to/runtime-host.md).
Its method names, authorization/receipt models and sorted-JSON digest are distinct
from that host's versioned attempt bindings and RFC 8785 `sha256:` digests. Do not
connect one client's frames to the other's endpoint.

## Host composition

```python
from pathlib import Path
from zeo_core.integrations.meetings import (
    GoogleMeetingReads, InvocationAuthorization, MeetingAdapters,
    MeetingRunner, UnixMeetingRuntime,
)
from zeo_core.integrations.google.sheets import GoogleSheetsService
from zeo_core.integrations.google.calendar import GoogleCalendarService

# Configure these existing services through the host's test/production setup.
# Construction performs no authentication; reads initialize after admission.
reads = GoogleMeetingReads(
    sheets=GoogleSheetsService(scopes=[
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ]),
    calendar=GoogleCalendarService(scopes=[
        "https://www.googleapis.com/auth/calendar.readonly",
    ]),
)
runtime = UnixMeetingRuntime(Path("/private/host/runtime/service/zeo.sock"))
runner = MeetingRunner(runtime=runtime, adapters=MeetingAdapters(reads=reads))
# authority_document and payload come from the host's admitted meeting action:
# receipt = runner.execute(InvocationAuthorization.model_validate(authority_document), payload)
```

Use [Google account setup](google.md) for a dedicated test account and disposable
Sheet/Calendar before production. The example path is a host-supplied runtime
location, not a created socket. A socket and parent owned by the current UID
with no group/other permissions are required. Calls use API version 1 with a
four-byte big-endian length prefix and a 1 MiB frame limit. The methods are
`meeting.capability.authorize`, `meeting.capability.receipt.admit` and
`meeting.capability.reconcile`. A wrong request ID, unavailable socket, protocol
error or mismatched authority prevents dispatch.

For Notion, pass the configured `NotionClientPageUpsertProvider` as
`MeetingAdapters(notion=provider)`; see [Notion setup](notion.md). The adapter
keeps the existing marker-based lookup, exact title/content read-back and stable
page identity on replacement. Conflicting or duplicate markers refuse mutation.

For Gmail, pass `GmailDraftClient(http_client)` as `MeetingAdapters(gmail=...)`.
The host must supply an authenticated `httpx.Client` with a finite timeout and
without transport retries for POST. Use a dedicated test mailbox, designated
recipients and the Gmail draft permission appropriate to your OAuth application.
Identity is checked using `users/me/profile` before creation. One POST creates
a draft, followed by an exact ID/content read-back. HTTP redirects are refused
and each response is limited to 1 MiB. No token store or OAuth browser flow is
created by this adapter. Official API contracts:
[draft create](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.drafts/create),
[draft get](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.drafts/get),
[draft list](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.drafts/list).

The optional `MeetingRunner(observe=callback, ...)` delivers successful response
data to the host only after the exact receipt is admitted. The callback receives
`(receipt, data)`. Read data is ephemeral; the host owns any approved persistence.
A replay returns the runtime's receipt and does not redeliver data or repeat the
provider call. A callback failure also leaves the admitted invocation final.

## Ambiguity and reconciliation

A proven refusal before mutation produces `REFUSED`. A mutation with an uncertain
outcome produces `AMBIGUOUS`. If receipt admission itself fails after a provider
call, surface that failure and reconcile against the runtime's existing invocation;
never assume the provider operation failed. Provider exception text, message
bodies and credentials are excluded from the receipt.

`RECONCILE` never dispatches again. `REPLAY_FINAL` returns a matching recorded
receipt. If the runtime has admitted a reconciliation record, the returned receipt
is a projection of those two records, marked `reconciled=True`; it is not a new
receipt submitted to the runtime.

For an ambiguous Gmail create, obtain a separately admitted
`gmail.draft.reconcile` invocation covering the original payload and creation key.
It searches for a deterministic Message-ID bound to mailbox plus original key,
reads at most two candidates and requires one exact content match. No match,
multiple matches, pagination or content differences remain ambiguous. Absence
from a search index never authorizes recreation. This adapter does not delete drafts.

After a successful observation, the trusted host can construct an
`InvocationReconciliation` for the **original** invocation, with the observed draft
ID and evidence digest, and call `runtime.reconcile(record)`. The runtime owns
whether that evidence may close the original invocation. The adapter does not
invent a terminal refusal from missing search results.

## Verification boundary

Run `make verify`. Tests exercise all six routes, exact binding, receipt mismatch,
ambiguous outcomes, replay, response delivery after admission, real Unix framing,
and HTTP serialization. Provider responses and runtime authority are fixtures;
these tests establish no deployed tenant, valid live lease, OAuth entitlement or
recipient delivery. Qualify those with the host's designated test resources before
promoting the composition to production.
