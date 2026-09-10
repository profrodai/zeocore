# Register a capability provider

Start with a typed [capability](../tutorials/capability-authoring.md), then choose
how its caller will discover and execute it. These names describe different jobs:

| Term | Job | Setup |
| --- | --- | --- |
| Capability | One versioned operation with typed input/output and declared effects | Use `@capability` and an ID such as `demo.greet@1.0.0` |
| Provider | An installed Python package supplying capabilities | Export a factory returning a fresh `CapabilityRegistry` |
| Registry | An explicit in-process catalogue | Register bound capabilities by exact canonical ID |
| Adapter | A boundary between interfaces or services | Choose HTTP, MCP, the Runtime host, or a provider-specific adapter |
| Integration | Code for an external service or local tool | Configure the required client and inject its service into context |
| Legacy plugin/module | A contribution to `zeo_core.modules` | Discover and explicitly load selected entry points; this does not admit a Runtime provider |

A package may contain several of these. Registration describes what exists;
the caller still supplies authorization, required services and account selection.

## 1. Export an explicit factory

The complete [catalogue example](../../examples/runtime_host_catalogue_v1.py)
defines `demo.greet@1.0.0` and exports `build_registry()`. Its factory creates a
new registry, registers the bound function and returns it without network or
credential access. Put the equivalent factory in your installed package, for
example `my_provider:build_registry`.

For direct Python use, the caller can use that registry with the existing
`invoke_sync` or `invoke_async` helpers. For HTTP/MCP, bind the capabilities into
the adapter's operation registry. See the [API map](../reference/api.md#adapters).

## 2. Prepare the Runtime inventory

The Runtime host and meeting APIs are available from 0.11.0. Install the package
and run this example from the matching `v0.11.0` checkout:

```bash
uv pip install "zeocore[runtime-host]==0.11.0"
python examples/runtime_host_catalogue_v1.py
```

The example constructs real manifests and validates/default-materializes a
request before hashing it. `name` becomes `World` before the digest is computed.
It performs no admission or invocation. Python 3.14+ is required; the supervised
host protocol uses inherited Unix descriptors on macOS/Linux.

The trusted Runtime launcher selects the installed provider version, interpreter,
factory and verified environment digest. It supplies the admitted static
`ProviderBinding`; model-generated request arguments cannot select a factory.
The host checks schemas, examples, identities, projection collisions and the
inventory digest without importing that factory during discovery. Empty
inventories are valid; duplicate canonical IDs refuse the candidate.

During execution, the host constructs and validates the full executable candidate
before publishing one generation. A failed candidate does not replace a working
generation, and cleanup from an older generation cannot remove its replacement.

## 3. Let Runtime admit the invocation

Follow the [Runtime host protocol](runtime-host.md) for inherited binding/context
FDs, private IPC, current attempt/fence checks, scoped requirements and artifact
acceptance. `zeo-capability` has no unauthenticated standalone invoke mode.
Installing the extra or validating a catalogue does not create a Runtime session.

A capability declaring `runtime.effects` can use the injected effect port for an
exact protected request. Runtime owns admission and durable effect accounting;
ZEOconnect owns credential custody and authorized dispatch. The host cannot fill
missing application services from ambient credentials. Unsupported service or
filesystem requirements are reported unavailable.

The version-1 host is an implementation candidate. Joint Runtime/ZEOconnect wire
agreement and real application proofs remain required. The earlier
[meeting-v1 API](../integrations/meetings.md) has its own socket methods, binding
models and request digest; sharing a four-byte frame prefix does not make the two
protocols interchangeable.

## Existing plugin users

`zeo_core.modules` remains an explicit legacy loading API. Importing it does not
load plugins. A selected duplicate entry-point name refuses before plugin import.
Registration callbacks must finish before their contributions are published;
unregistering restores the latest surviving owner of a shadowed name, using the
names captured at registration rather than asking the plugin to enumerate again.

Continue using the [plugin-loading example](../../examples/explicit_plugin_loading_example.py)
for that API. New Runtime providers use a trusted factory binding and
`CapabilityRegistry`; they do not self-admit through the legacy plugin registry.
