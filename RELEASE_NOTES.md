# zeocore 0.11.0

ZeoCore 0.11.0 adds a supervised Runtime capability host, Runtime-admitted meeting
operations, safer legacy plugin registration and searchable documentation.
Python 3.14 or newer remains required. See [CHANGELOG.md](CHANGELOG.md) for the
complete history.

## Runtime capability host

The optional `runtime-host` extra provides the `zeo-capability` CLI, explicit
provider factories, manifest inventories, canonical request validation and a
version-1 protocol over private inherited Unix descriptors. The host validates
provider bindings and invokes admitted capabilities; Runtime owns admission,
durable operations and accepted artifacts, while ZEOconnect owns protected
connector dispatch. Registration alone never authorizes execution.

This is a packaged implementation candidate. Joint Runtime/ZEOconnect wire
agreement, the Go adapter and real application/effect acceptance remain required.
The package release does not certify deployment interoperability. The exercised
host environments are macOS and Linux; no Windows launcher is provided.

Start with [provider registration](docs/how-to/provider-registration.md) and the
[Runtime host guide](docs/how-to/runtime-host.md). `runtime-host` is deliberately
separate from the `all` extra. Existing Python, HTTP and MCP paths remain available.

## Meeting operations

The base package includes `zeo_core.integrations.meetings` for six closed operations:
Notion page upsert, bounded Sheets reads, Calendar event reads, and Gmail draft
creation, retrieval and reconciliation. The existing meeting-v1 protocol binds the
exact request and resource to Runtime authority before dispatch and requires an
admitted receipt. It has separate bindings from the generic host protocol.

There is no Gmail send operation or Calendar mutation route. Lost or ambiguous
provider responses do not authorize another mutation. Credentials stay with the
host. See the [meeting guide](docs/integrations/meetings.md) for limits and setup.

## Registration fixes and documentation

Legacy plugin registration now publishes transactionally, restores surviving
shadowed contributions on unload, uses registration snapshots for cleanup, and
refuses ambiguous selected entry points before importing them.

The documentation adds searchable navigation, generated API references, a clear
provider/integration/adapter terminology guide and two offline examples. The
catalogue example constructs manifests and a normalized request; the meeting
example demonstrates exact resource and digest binding. Neither calls a provider
or manufactures Runtime authority.

## Install and upgrade

```bash
uv pip install --upgrade "zeocore==0.11.0"
uv pip install "zeocore[runtime-host]==0.11.0"
```

The first command includes meeting request/receipt APIs. The second adds canonical
wire validation and the supervised host. Install other provider extras only as
needed. To run the new examples, use the matching `v0.11.0` repository checkout:

```bash
python examples/runtime_host_catalogue_v1.py
python examples/meeting_request_v1.py
```

Examples are repository assets, not installed shell commands. A trusted Runtime
supervisor must provide the inherited descriptors for actual `zeo-capability`
invocation. The [example catalog](examples/README.md) and
[API reference](docs/reference/api.md) describe the supported public imports.
