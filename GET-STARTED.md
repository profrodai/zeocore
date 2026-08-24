# ZeoCore Manual

> **New to ZeoCore? Don't start here.** Read
> [QUICKSTART.md](QUICKSTART.md) first — it takes you from an empty folder
> to a running capability in about ten minutes, including installing
> Python 3.13 and creating a virtual environment, and explains every line
> of the code you write. This page is the reference manual you come back to
> afterwards.

Where each document fits: [README.md](README.md) is the one-page overview,
[QUICKSTART.md](QUICKSTART.md) is the hands-on first hour,
[docs/README.md](docs/README.md) is the guided learning path with tutorials,
and this manual covers everything in depth.

## Contents

- [Introduction](#introduction)
- [Installation](#installation)
- [Core Modules Overview](#core-modules-overview)
- [Capabilities](#capabilities) — the authoring surface, and the section to
  read if you only read one
  - [Status vs outcome](#status-vs-outcome)
  - [Request guards vs Pydantic](#request-guards-vs-pydantic)
  - [Manifests, LLM tools, HTTP/MCP](#manifests-llm-tools-httpmcp)
- [Getting Started](#getting-started) — configuration, paths, filesystem,
  plugins, and every integration
  - [Basic Configuration Setup](#basic-configuration-setup)
  - [Path Resolution](#path-resolution) ·
    [File Operations](#file-operations) ·
    [Using Plugins](#using-plugins)
  - Integrations:
    [Google Drive](#working-with-google-drive-integration) ·
    [Gmail](#working-with-gmail-integration) ·
    [Google Calendar](#working-with-google-calendar-integration) ·
    [Notion](#working-with-notion-integration) ·
    [Jupytext](#working-with-jupytext-integration-script-to-notebook-conversion) ·
    [FFmpeg](#working-with-ffmpeg-integration-media-probingtranscoding) ·
    [LLM providers](#working-with-llm-providers-chat-tool-calling-prompt-caching)
  - Adapters: [MCP server](#exposing-tools-as-an-mcp-server) ·
    [HTTP](#exposing-tools-over-http)
- [Advanced Usage](#advanced-usage) — custom plugins, Pandoc, custom config
- [Configuration File Format](#configuration-file-format)
- [Environment Variables](#environment-variables) — including
  [Secrets and `.env`](#secrets-and-env)
- [Integration Authentication](#integration-authentication)
- [Best Practices](#best-practices)
- [Extending ZeoCore](#extending-zeocore)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)
- [Contributing](#contributing)

---

## Introduction

**ZeoCore** is a capability-authoring framework and infrastructure library
for Python. It gives you a typed base for writing capabilities
(`@capability`, `BaseZeoTool`, `ToolContext`, `CapabilityResult`), plus the
shared infrastructure around them: path resolution, filesystem operations,
configuration management, plugin discovery, integrations with third-party
services (Google Drive, Gmail, Google Calendar, Notion, Pandoc, jupytext,
ffmpeg, LLM providers, GitHub), and adapters that expose your tools over
HTTP, MCP, or as OpenAI-compatible function tools.

It's aimed at developers building automation tools, content pipelines, and
integrations that need consistent configuration, filesystem, and
error-handling behavior without re-solving those problems in every project.

Most of what's documented here has a runnable counterpart in
[`examples/`](examples/), and those scripts are verified, not illustrative
fragments.

---

## Installation

**Requires Python 3.13 or newer**, and pip. If you need help installing
either one, or setting up a virtual environment,
[QUICKSTART.md](QUICKSTART.md) walks through it step by step for
macOS/Linux and Windows.

```bash
pip install zeocore
```

Integrations ship as optional extras, so you install only what you use:

```bash
pip install "zeocore[notion]"     # a single integration
pip install "zeocore[google]"     # Drive + Gmail auth plumbing
pip install "zeocore[http]"       # FastAPI adapter, expose tools over REST
pip install "zeocore[mcp]"        # MCP adapter for Claude Code, Cursor, etc.
pip install "zeocore[all,mcp]"    # everything (note: [all] excludes mcp)
```

The full extras table is in the
[README](README.md#optional-integrations). Each integration section below
names the extra it needs. Contributors additionally want the `dev` and
`lint` extras — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Core Modules Overview

ZeoCore is organized into distinct modules that provide clear functionality:

### `zeo_core.config`
Robust configuration system supporting YAML, environment variables, and runtime overrides.

### `zeo_core.core.paths`
Standardized path resolution and project structure detection across environments.

### `zeo_core.core.fs`
Safe and consistent filesystem operations with error handling and structured results.

### `zeo_core.modules`
Extensible plugin discovery and explicit-loading registration framework.

### `zeo_core.integrations`
Interfaces to third-party services (Google Drive, Gmail, Google Calendar, Notion, Pandoc, GitHub, jupytext, ffmpeg, LLM providers) through a clean adapter layer. Database integrations (BigQuery, Supabase, SQLite) were evaluated and explicitly not built -- see CHANGELOG.md.

### `zeo_core.core.errors`
Structured error handling system with typed exceptions for improved developer experience.

### `zeo_core.tools`
The capability-authoring framework: `@capability` functions,
`CapabilityRegistry`, `invoke_sync` / `invoke_async`, `BaseZeoTool`,
`ToolContext`, `tool_to_capability`, and optional mixins
(`IntegrationEnabledMixin`, `LifecycleMixin`, `ToolEnvInitializerMixin`).
See [Capabilities](#capabilities) below,
[`examples/capability_authoring.py`](examples/capability_authoring.py),
and [`examples/minimal_tool.py`](examples/minimal_tool.py).

### `zeo_core.contracts`
The data contracts tools speak: `CapabilityId`, `CapabilityDefinition`,
`CapabilityManifest`, `CapabilityResult`, `CapabilityOutcome`, request
guards, invocation records, plus artifact/manifest models. See
[`src/zeo_core/contracts/README.md`](src/zeo_core/contracts/README.md) and
[`src/zeo_core/contracts/EXAMPLES.md`](src/zeo_core/contracts/EXAMPLES.md).

### `zeo_core.adapters`
Optional adapters, both HTTP and MCP reading from the same
`OperationRegistry` (`zeo_core.core.registry`): `adapters.http` (FastAPI,
`zeocore[http]`) exposes tools over REST; `adapters.mcp` (`zeocore[mcp]`)
exposes them as MCP tools for Claude Code, Cursor, and other MCP-native
agents; `adapters.llm_tools` projects a `CapabilityManifest` to an
OpenAI-compatible function tool (and **refuses** unsupported JSON Schema
instead of silently stripping it). See
[`examples/http_adapter_usage.py`](examples/http_adapter_usage.py),
[`examples/mcp_server_usage.py`](examples/mcp_server_usage.py), and
[`examples/llm_tools_usage.py`](examples/llm_tools_usage.py).

---

## Capabilities

> Haven't written one yet? [QUICKSTART.md](QUICKSTART.md#step-5-write-your-first-capability)
> builds a working capability line by line and explains each piece. This
> section assumes you've done that, or can read the code below comfortably.

ZeoCore **defines** capabilities. A runner (for example Sovereign Agent)
invokes and supervises them. Organizational authorization lives in Zero
Employee — a capability's `effects` field is a **declaration**, not a
permission grant. Human approval is not a capability result state.

Identity is `namespace.name@semver` (`CapabilityId`). JSON Schema is
generated from Pydantic request/response models, not from shallow
annotations. Every capability needs at least one `CapabilityExample`.

Canonical function authoring:

```python
from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.tools import (
    CapabilityRegistry,
    ToolContext,
    bound_capability_of,
    capability,
    invoke_sync,
)
from pydantic import BaseModel


class GreetRequest(BaseModel):
    name: str


class GreetResponse(BaseModel):
    message: str


@capability(
    id="demo.greet@1.0.0",
    description="Greet a person by name.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            request={"name": "World"},
            response={"message": "Hello, World!"},
        ),
    ),
)
def greet(request: GreetRequest, ctx: ToolContext) -> CapabilityResult[GreetResponse]:
    return CapabilityResult.ok(data=GreetResponse(message=f"Hello, {request.name}!"))


cap = bound_capability_of(greet)
registry = CapabilityRegistry()
registry.register(cap)
result = invoke_sync(cap, GreetRequest(name="World"), ctx)
```

`invoke_async` is the same pipeline for `async def` handlers. Register
third-party capabilities via the `zeo_core.capabilities` entry-point group
(`CapabilityRegistry.load_entry_points()`).

Class tools remain supported: subclass `BaseZeoTool`, implement
`run(request, ctx) -> CapabilityResult`, and adapt with
`tool_to_capability` once the class declares examples. See
[`examples/tool_to_capability.py`](examples/tool_to_capability.py).

### Status vs outcome

Orchestrators still branch on three-way `CapabilityStatus`
(success / skipped / error). Fine-grained `CapabilityOutcome` layers on
top:

| Constructor | Typical outcome | Status |
|---|---|---|
| `.ok()` | `success` | success |
| `.skip()` | `policy_skipped` | skipped |
| `.unavailable()` | `unavailable` | skipped |
| `.fail()` / `.fail_from_exc()` | `integration_failure` (default) | error |

Guards and the invoke helper can also produce `guard_rejected`,
`invalid_return`, `unexpected_exception`, and `cancelled`. Existing
`.ok()` / `.skip()` / `.fail()` callers do not need to set `outcome`.

### Request guards vs Pydantic

Pydantic validates **shape**. A `RequestGuard` is a side-effect-free
policy check over an already-validated request model (`GuardResult.accept`
/ `.reject`). A rejected guard maps to `CapabilityOutcome.guard_rejected`
and the handler body does not run. See
[`examples/capability_guards.py`](examples/capability_guards.py).

### Manifests, LLM tools, HTTP/MCP

`CapabilityManifest.from_definition(cap.definition)` is the
provider-neutral discovery document. `project_openai_tool(manifest)` in
`zeo_core.adapters.llm_tools` projects it to an OpenAI function tool, or
returns a typed incompatibility instead of dropping keywords. See
[`examples/llm_tools_usage.py`](examples/llm_tools_usage.py).

`register_capability_operation` binds a `BoundCapability` into
`OperationRegistry` so HTTP and MCP can invoke the same request model.
See [`examples/http_adapter_usage.py`](examples/http_adapter_usage.py).

`zeo_core.tools.catalog` holds **reference** implementations (add,
checksum, GitHub read, calendar create, pandoc). It is not a public API.
`zeo_core.tools.compat.sovereign_style_capability` is a **transitional**
adapter for keyword-argument functions — not the canonical surface.

Ecosystem runners can pin `zeo_core.contract_pack` (`PACK_VERSION`,
`PACK_SCHEMA`) without importing Sovereign Agent.

Worked walkthrough:
[docs/tutorials/capability-authoring.md](docs/tutorials/capability-authoring.md).

---

## Getting Started

The sections below are task-oriented and independent — read the one you
need. They cover the infrastructure around your capabilities:
configuration, paths, filesystem, plugins, each integration, and the HTTP
and MCP adapters.

### Basic Configuration Setup

```python
from zeo_core.config import load_config, ZeoConfig

# Load configuration from default locations. This does NOT raise even if
# no config file exists anywhere (an empty project directory, a fresh
# clone, etc) -- it falls back to built-in defaults plus any environment
# variables, and returns a valid ZeoConfig.
config = load_config()

# Access configuration values
project_name = config.general.project_name
log_level = config.logging.level

# Load configuration from a specific file -- ONLY if that path actually
# exists. Unlike the no-argument form above, an explicit path is a
# promise the file is there: load_config() raises ZeoConfigurationError
# if it isn't. The line below is illustrative (a real path is needed, not
# this placeholder) -- see examples/config_usage.py for the same call
# made runnable end to end, including this exact failure mode caught on
# purpose.
custom_config = load_config("path/to/custom_config.yaml")  # illustrative path
```

Run [`examples/config_usage.py`](examples/config_usage.py) to see all
three real behaviors end to end from a fresh directory: the no-argument
default-locations lookup (doesn't raise), an explicit path that doesn't
exist (does raise, by design), and an explicit path to a real file this
script writes first (succeeds).

### Path Resolution

```python
from zeo_core.core.paths import get_path_service

path_service = get_path_service()

# Find the project root directory (returns a PathResult, not a bare string)
root_result = path_service.get_project_root()
if root_result.success:
    project_root = root_result.path

# Resolve a path relative to the project root
config_path_result = path_service.resolve_project_path("config/settings.yaml")

# Detect project context
context_result = path_service.detect_project_context()
if context_result.success:
    context = context_result.context
```

### File Operations

```python
from zeo_core.core.fs import get_service

fs = get_service()

# Read text from a file
result = fs.read_text("path/to/file.txt")
if result.success:
    content = result.content
else:
    print(f"Error: {result.error}")

# Write text to a file
fs.write_text("path/to/output.txt", "Hello, ZeoCore!")

# Create a directory
fs.create_directory("path/to/new/directory")

# Read structured data
yaml_result = fs.read_yaml("config.yaml")
if yaml_result.success:
    config_data = yaml_result.data
```

### Using Plugins

Importing `zeo_core.modules` has no side effects -- nothing is auto-loaded.
Plugins must be explicitly enabled, then looked up from the registry:

```python
from zeo_core.modules import load_enabled_entry_points, registry

# Explicitly load the modules you want (operator-controlled, not automatic)
result = load_enabled_entry_points(
    enabled=["fs", "paths", "config"],
    strict=True,        # fail fast if one of these isn't available
    auto_register=True, # register loaded plugins in the global registry
)
if result.success:
    print(f"Loaded: {result.loaded}")

# Look up a loaded plugin by id
fs_plugin = registry.get_plugin("fs")
if fs_plugin is not None:
    print(f"fs plugin: {fs_plugin}")
```

### Working with Google Drive Integration

```python
from zeo_core.integrations.google.drive import GoogleDriveService

# Initialize service
drive_service = GoogleDriveService(
    client_secrets_file="path/to/client_secrets.json",
    credentials_file="path/to/credentials.json"
)
drive_service.initialize()

# Upload a file
result = drive_service.upload_file("path/to/local/file.pdf")
if result.success:
    print(f"File uploaded: {result.content}")

# List files
list_result = drive_service.list_files()
if list_result.success:
    files = list_result.content
    for file in files:
        print(f"File: {file['name']}")
```

### Working with Gmail Integration

```python
from zeo_core.integrations.google.mail import GoogleMailService

# Initialize service
mail_service = GoogleMailService(
    client_secrets_file="path/to/client_secrets.json",
    credentials_file="path/to/credentials.json",
    storage_path="path/to/downloaded/emails"
)
mail_service.initialize()

# List emails with a specific query
emails_result = mail_service.list_emails("subject:Important")
if emails_result.success:
    emails = emails_result.content
    for email in emails:
        print(f"Email ID: {email['id']}")
        
        # Download an email as HTML
        download_result = mail_service.download_email(email['id'])
        if download_result.success:
            print(f"Email saved to: {download_result.content}")
```

### Working with Google Calendar Integration

```python
from zeo_core.integrations.google.calendar import GoogleCalendarService

# Initialize service
calendar_service = GoogleCalendarService(
    client_secrets_file="path/to/client_secrets.json",
    credentials_file="path/to/credentials.json",
)
calendar_service.initialize()

# List upcoming events on the primary calendar
events_result = calendar_service.list_events(time_min="2026-08-20T00:00:00Z")
if events_result.success:
    for event in events_result.content:
        print(f"Event: {event.summary} ({event.id})")

# Create an event
created = calendar_service.create_event(
    summary="Team sync",
    start={"dateTime": "2026-08-21T10:00:00-07:00", "timeZone": "America/Los_Angeles"},
    end={"dateTime": "2026-08-21T10:30:00-07:00", "timeZone": "America/Los_Angeles"},
)
if created.success:
    print(f"Created event: {created.content.id}")
```

Auth is the same OAuth (`InstalledAppFlow` + local-server) flow Drive and
Gmail already use -- no separate credential setup. Requires the `calendar`
extra (`pip install "zeocore[calendar]"`).

### Working with Notion Integration

Notion's own auth model is a single bearer **integration token** (not
OAuth) -- create one at
[notion.so/my-integrations](https://www.notion.so/my-integrations), then
share the specific page or database you want it to touch with that
integration from Notion's UI (a token with no pages shared to it can
authenticate but sees nothing). Set the token via the `NOTION_TOKEN`
environment variable.

Requires the `notion` extra (`pip install "zeocore[notion]"`).

**A real config file must exist** at one of `load_config()`'s default
locations (`./zeo_config.yaml`, `./config/zeo_config.yaml`,
`~/.zeo/config.yaml`) for `NotionIntegration.initialize()` to succeed --
unlike `load_config()` itself, this integration's config provider does
not fall back to defaults when no file is found at all. An empty
`notion: {}` block is enough; `NOTION_TOKEN` fills in the token value.

```python
from zeo_core.integrations.notion import NotionIntegration

# config_path is a constructor arg -- NotionIntegration(), not a bare
# create_integration() call, when you need to point at a specific file.
notion = NotionIntegration(config_path="path/to/zeo_config.yaml")
init_result = notion.initialize()
if not init_result.success:
    print(f"Failed to initialize: {init_result.error}")

# Read: search everything shared with this integration
search_result = notion.search(query="Project")
if search_result.success:
    for obj in search_result.content or []:
        print(f"{obj['object']}: {obj['id']}")

# Read: query a database (handles the 2025-09-03 database -> data-source
# API change internally -- you pass a database_id like always)
query_result = notion.query_database(
    "your-database-id",
    filter={"property": "Status", "select": {"equals": "Done"}},
)

# Write: create a page under an existing parent page
create_result = notion.create_page(
    parent={"type": "page_id", "page_id": "your-parent-page-id"},
    properties={"title": [{"text": {"content": "New page"}}]},
)
if create_result.success:
    new_page = create_result.content
    print(f"Created page: {new_page.id}")

    # Write: append a block to the page just created
    notion.append_blocks(
        new_page.id,
        children=[
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": "Hello."}}]
                },
            }
        ],
    )
```

Every method returns an `IntegrationResult` (`.success`, `.content`,
`.error`, `.message` -- the same shape `zeo_core.integrations.pandoc` and
every other integration in this table uses, distinct from the
`CapabilityResult` your own tools return). Errors from the Notion API
(bad token, page not found, rate limits) are caught and surfaced as
`.error` strings, not raised exceptions.

Two lower-level methods (`list_data_sources`, `query_data_source`) exist
only on the raw client (`zeo_core.integrations.notion.NotionClient`), not
on `NotionIntegration` -- needed only if a single database has more than
one data source, which `query_database`/`create_database_entry` handle
transparently for the common single-data-source case.

See [`examples/notion_usage.py`](examples/notion_usage.py) for a fully
runnable version, including the graceful-skip path when `NOTION_TOKEN`
isn't set.

### Working with Jupytext Integration (script to notebook conversion)

Converts between percent-format Python scripts (`# %%`-delimited cells,
diff-friendly, plain text) and Jupyter notebooks. This is the exact
operation the org's own `quackslides` app uses for its exercise content:
`script_to_notebook()` is the primary, most-used direction.

Requires the `jupytext` extra (`pip install "zeocore[jupytext]"`). No
external binary and no required config -- `initialize()` falls back to
defaults cleanly with zero config file present (unlike Notion/ffmpeg
above/below).

```python
from zeo_core.integrations.jupytext import create_integration

jupytext = create_integration()
init_result = jupytext.initialize()
if not init_result.success:
    print(f"Failed to initialize: {init_result.error}")

# script -> notebook (percent-format .py in, .ipynb out)
result = jupytext.script_to_notebook("exercise_01.py")
if result.success:
    print(f"Notebook written to: {result.content}")

# notebook -> script (the natural inverse; percent format by default)
result = jupytext.notebook_to_script("exercise_01.ipynb")
if result.success:
    print(f"Script written to: {result.content}")
```

`output_path` is optional on both methods -- when omitted, it's
synthesized from `input_path` (same directory, `.ipynb`/`.py` extension
swapped). See [`examples/jupytext_usage.py`](examples/jupytext_usage.py)
for a fully runnable round trip.

### Working with FFmpeg Integration (media probing/transcoding)

Wraps the org's own [`ffmpeg-zeo`](https://pypi.org/project/ffmpeg-zeo/)
PyPI package, not the raw `ffmpeg` binary directly -- `ffmpeg-zeo`
resolves real `ffmpeg`/`ffprobe` binaries (from `PATH`, or by downloading
them if configured to) and this integration calls a curated subset of its
"recipes."

Requires the `ffmpeg` extra (`pip install "zeocore[ffmpeg]"`).
`ffmpeg-zeo` itself needs Python >=3.12 -- comfortably under zeocore's own
`>=3.13` floor, so this installs cleanly with no version straddling.

Like Notion, a real config file must exist at a default location (or be
passed via `config_path=`) for `initialize()` to succeed -- an empty
`ffmpeg: {}` block is enough.

```python
from zeo_core.integrations.ffmpeg import FFmpegIntegration

ffmpeg = FFmpegIntegration(config_path="path/to/zeo_config.yaml")
init_result = ffmpeg.initialize()
if not init_result.success:
    print(f"Failed to initialize: {init_result.error}")

# Probe: real ffprobe under the hood -- raw ffprobe JSON plus derived
# convenience keys (has_video, width, height, video_codec, ...)
probe_result = ffmpeg.probe("input.mp4")
if probe_result.success:
    info = probe_result.content
    print(f"{info['width']}x{info['height']}, codec={info['video_codec']}")

# Transcode to H.264 at a given quality/preset
transcode_result = ffmpeg.transcode_h264("input.mp4", crf=23, preset="medium")

# Extract audio, generate a thumbnail
audio_result = ffmpeg.extract_audio("input.mp4", codec="copy")
thumb_result = ffmpeg.thumbnail("input.mp4", time=1.0)
```

All four operation methods return `IntegrationResult[str]` (`.content` is
the output file path); `probe()` returns `IntegrationResult[dict]`.
`ffmpeg.metrics` (a `RenderMetrics` instance) accumulates
`total_attempts`/`successful_renders`/`failed_renders` across calls on
the same integration instance. See
[`examples/ffmpeg_usage.py`](examples/ffmpeg_usage.py) for a fully
runnable version that generates its own synthetic test video via
ffmpeg's `lavfi` source, so it needs no external media file.

### Working with LLM Providers (chat, tool-calling, prompt caching)

`zeo_core.integrations.llms` is provider-agnostic at the call site: every
client (`anthropic`, `openai`, `ollama`, plus a `mock` for tests)
implements the same `LLMProviderProtocol` (`chat()`, `count_tokens()`,
`.model`). Requires the `llms` extra (`pip install "zeocore[llms]"`).

```python
from zeo_core.integrations.llms.registry import get_llm_client
from zeo_core.integrations.llms.models import (
    ChatMessage,
    RoleType,
    LLMOptions,
    ToolDefinition,
    FunctionDefinition,
)

client = get_llm_client(provider="anthropic")  # api_key defaults to
                                                # ANTHROPIC_API_KEY env var
print(client.model)  # "claude-sonnet-5" -- the current, non-retired default

messages = [
    ChatMessage(role=RoleType.SYSTEM, content="You are a helpful assistant."),
    ChatMessage(role=RoleType.USER, content="What's the weather in Boston?"),
]

options = LLMOptions(
    max_tokens=1024,
    # Marks the system prompt cacheable via Anthropic's cache_control:
    # ephemeral breakpoints -- a real cost/latency win on repeated calls
    # sharing the same system prompt. Provider-agnostic option; a no-op
    # on providers without caching support (OpenAI, Ollama).
    cache_system_prompt=True,
    tools=[
        ToolDefinition(
            type="function",
            function=FunctionDefinition(
                name="get_weather",
                description="Get current weather for a location",
                parameters={
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                },
            ),
        )
    ],
)

result = client.chat(messages, options)
if result.success:
    print(result.content)
else:
    print(result.error)
```

`chat()` returns `IntegrationResult[str]` -- always plain text, never a
raised exception (retries and error conversion happen internally).

**Known gap, stated plainly rather than glossed over:** tool definitions
sent via `LLMOptions.tools` reach the Anthropic API correctly (verified:
`ToolDefinition` is converted to Anthropic's flat
`{name, description, input_schema}` shape and appears in the real request
payload). But if the model responds with a `tool_use` content block
instead of plain text, `chat()`'s current response parsing only reads
`response.content[0].text` -- it does not extract or return the
`tool_use` block's `name`/`input`/`id`. There is a model
(`zeo_core.integrations.llms.models.LLMResult`, with a `tool_calls`
field) built for exactly this, but no client constructs one; `chat()`'s
return type is `IntegrationResult[str]`, with no field for a tool call.
**Request-side tool-calling works; response-side tool-call extraction
does not yet** -- a caller who needs the model's tool_use block has to
drop below the provider-agnostic protocol to the raw SDK client. Tracked
as follow-up work, not silently worked around here.

### Exposing Tools as an MCP Server

Every consuming app in this org is built by an MCP-native coding agent
(Claude Code, Cursor, etc.). `zeo_core.adapters.mcp` lets those agents call
your tools directly, with **zero MCP-specific code required in the tool
itself**: any ordinary `BaseZeoTool` becomes an MCP tool by registering it,
because `register_tool()` mechanically derives the MCP tool's schema from
the tool's own `run(request: <PydanticModel>, ctx)` type hint.

Requires the `mcp` extra (`pip install "zeocore[mcp]"`).

```python
from zeo_core.adapters.mcp import create_server, register_tool
from zeo_core.contracts import CapabilityResult
from zeo_core.tools import BaseZeoTool, ToolContext
from pydantic import BaseModel


class WordCountRequest(BaseModel):
    text: str


class WordCountTool(BaseZeoTool):
    name = "word_count"

    def run(self, request: WordCountRequest, ctx: ToolContext) -> CapabilityResult:
        return CapabilityResult.ok(data={"word_count": len(request.text.split())})


# Register your tool -- no MCP code in the tool class above.
register_tool(WordCountTool())

# Build the server and run it over stdio (the transport Claude Code,
# Cursor, and most MCP-native agents speak by default).
server = create_server(name="my-zeocore-app")
```

Save the snippet above (minus the last comment) to a file, e.g.
`mcp_entrypoint.py`, and add `server.run()` at the bottom so running the
file directly starts the server. Then point your agent's MCP client config
at it (Claude Code: `claude mcp add my-zeocore-app -- python
mcp_entrypoint.py`). See
[`examples/mcp_server_usage.py`](examples/mcp_server_usage.py) for a fully
runnable version, including calling the resulting tool through the real
`mcp` SDK client.

`create_server()` reads from the SAME `OperationRegistry`
(`zeo_core.core.registry`) that `zeo_core.adapters.http` reads from --
registering a tool once with `register_tool()` makes it reachable from
both the HTTP and MCP adapters, not just one. Capabilities registered
with `register_capability_operation` use that same registry.

### Exposing Tools over HTTP

Requires the `http` extra (`pip install "zeocore[http]"`). Bind a
capability (or keep using `OperationRegistry.register` for older
callables), then `create_app` / `run`:

```python
from zeo_core.adapters.http import HttpAdapterConfig, create_app, run
from zeo_core.core.registry import OperationRegistry
from zeo_core.tools import bound_capability_of, register_capability_operation

# greet is a @capability function; make_ctx returns ToolContext
ops = OperationRegistry()
register_capability_operation(
    bound_capability_of(greet),
    registry=ops,
    context_factory=make_ctx,
    name="greet",
)
# create_app(HttpAdapterConfig(auth_token=None), registry=ops, ...)
# run(HttpAdapterConfig(host="127.0.0.1", port=8080))
```

The runnable example uses FastAPI's `TestClient` so
`python examples/http_adapter_usage.py` returns instead of blocking on
uvicorn. Auth is off when `auth_token` is `None`; otherwise send
`Authorization: Bearer <token>`. OpenAPI is at `/openapi.json`.

### Error Handling

```python
from zeo_core.core.errors import ZeoError, ZeoFileNotFoundError, wrap_io_errors


# Use decorator for automatic error handling
@wrap_io_errors
def read_important_file(path):
  with open(path, 'r') as f:
    return f.read()


# Handle specific errors
try:
  content = read_important_file("config.txt")
except ZeoFileNotFoundError as e:
  print(f"File not found: {e.path}")
except ZeoError as e:
  print(f"Error: {e}")
```

---

## Advanced Usage

### Creating a Custom Plugin

`ZeoPluginProtocol` is a structural protocol (`typing.Protocol`, checked via
`isinstance()` at runtime) -- a plugin must expose `plugin_id`, `name`, and
`get_metadata()`:

```python
from zeo_core.modules import registry
from zeo_core.modules.protocols import ZeoPluginMetadata, ZeoPluginProtocol


class MyCustomPlugin:
    @property
    def plugin_id(self) -> str:
        return "my_custom_plugin"

    @property
    def name(self) -> str:
        return "My Custom Plugin"

    def get_metadata(self) -> ZeoPluginMetadata:
        return ZeoPluginMetadata(
            plugin_id=self.plugin_id,
            name=self.name,
            version="1.0.0",
            description="An example custom plugin",
        )


plugin = MyCustomPlugin()
assert isinstance(plugin, ZeoPluginProtocol)  # structural check passes

registry.register(plugin)
```

### Working with Pandoc for Document Conversion

```python
from zeo_core.integrations.pandoc import PandocIntegration
from pathlib import Path

# Initialize the service
pandoc = PandocIntegration()
pandoc.initialize()

# Convert HTML to Markdown
result = pandoc.html_to_markdown(
    Path("document.html"), 
    Path("output.md")
)

if result.success:
    print(f"Converted to: {result.content}")
else:
    print(f"Conversion failed: {result.error}")

# Convert Markdown to DOCX
docx_result = pandoc.markdown_to_docx(
    Path("document.md"),
    Path("output.docx")
)

# Convert all HTML files in a directory to Markdown
batch_result = pandoc.convert_directory(
    Path("html_files"), 
    "markdown",
    Path("output_dir")
)
if batch_result.success:
    print(f"Converted {len(batch_result.content)} files")
```

### Creating Custom Configuration

```python
import os

from pydantic import BaseModel, Field
from zeo_core.config.models import ZeoConfig

# Define custom configuration model
class MyAppConfig(BaseModel):
    api_key: str = Field(..., description="API key for external service")
    endpoint: str = Field("https://api.example.com", description="API endpoint")
    timeout: int = Field(30, description="Request timeout in seconds")

# Secrets are never constructed inline and never dumped to YAML/JSON --
# read them from the environment (see .env.example / "Environment
# Variables" below). Keep the MyAppConfig instance itself out of any
# model_dump() that gets persisted to disk.
my_app_config = MyAppConfig(api_key=os.environ["MY_APP_API_KEY"])

# Add ONLY non-secret settings to ZeoConfig.custom -- ZeoConfig gets
# committed as YAML, so a secret placed here is written to a tracked file.
config = ZeoConfig()
config.custom["my_app"] = {
    "endpoint": my_app_config.endpoint,
    "timeout": my_app_config.timeout,
}

# Save configuration
from zeo_core.config.loader import merge_configs
merged_config = merge_configs(config, {})
```

## Configuration File Format

ZeoCore uses YAML for configuration files. Here's an example of a basic configuration file:

```yaml
general:
  project_name: "MyZeoProject"
  environment: "development"
  debug: true
  verbose: true

paths:
  base_dir: "./project"
  output_dir: "./project/output"
  assets_dir: "./project/assets"
  data_dir: "./project/data"
  temp_dir: "./project/temp"

logging:
  level: "INFO"
  file: "logs/app.log"
  console: true

integrations:
  google:
    client_secrets_file: "config/google_client_secret.json"
    credentials_file: "config/google_credentials.json"
    drive:
      shared_folder_id: "your-folder-id"
    gmail:
      gmail_labels: ["INBOX", "IMPORTANT"]
      gmail_days_back: 7

plugins:
  enabled:
    - "Pandoc"
    - "GoogleDrive"
    - "GoogleMail"
  paths:
    - "./modules"

# Custom application-specific configuration.
# NOTE: no secrets here. This file is YAML and gets committed by default.
# Put settings here; put secrets in `.env` (copy `.env.example`, which IS
# gitignored) and read them from the environment at runtime -- see
# "Secrets and .env" below.
custom:
  my_app:
    endpoint: "https://api.example.com"
    timeout: 30
```

## Environment Variables

ZeoCore supports configuration through environment variables with the prefix
`ZEO_`, in the form `ZEO_SECTION__KEY=value` (double underscore separates
nesting levels). These are merged onto whatever `ZeoConfig` field they map
to -- unrecognized sections are silently dropped, since `ZeoConfig` validates
strictly against its own fields (`general`, `paths`, `logging`,
`integrations`, `plugins`, `custom`):

```bash
export ZEO_GENERAL__DEBUG=false
export ZEO_LOGGING__LEVEL=WARNING
export ZEO_PATHS__BASE_DIR=/opt/zeocore

# Nested keys under the `integrations` dict field:
export ZEO_INTEGRATIONS__GOOGLE__CLIENT_SECRETS_FILE=/etc/zeo/client_secrets.json
export ZEO_INTEGRATIONS__GOOGLE__CREDENTIALS_FILE=/etc/zeo/credentials.json
```

`ZEO_ENV` is separate: it's read by `zeo_core.config.utils.get_env()` (not by
`load_config()` itself) and defaults to `"development"`.

### Secrets and `.env`

**Secrets go in `.env`; settings go in YAML.** Copy the `.env.example` at the
repo root to `.env` and fill in real values -- `.env` (and `.env.*`) is
already gitignored, so a secret placed there is never committed, unlike a
YAML config file. This is the documented split for the whole library:
`NOTION_TOKEN`, `GITHUB_TOKEN`, `OPENAI_API_KEY`, and `ANTHROPIC_API_KEY` are
all read directly from the process environment by their respective
integrations, no `ZEO_` prefix needed.

ZeoCore does **not** load `.env` files on import -- that stays your
shell's/tooling's job (`uv run --env-file .env ...`, a `python-dotenv` call
in your own entrypoint, your process manager, or your deployment platform's
env injection). Once a variable is in the process environment, ZeoCore's
integrations and `ZEO_SECTION__KEY` overrides read it exactly the same way
regardless of how it got there.

## Integration Authentication

### Google API Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the APIs you need (Drive API, Gmail API, etc.)
4. Create OAuth 2.0 credentials
5. Download the client secrets JSON file
6. Use the client secrets file path in your ZeoCore configuration

```python
from zeo_core.integrations.google.auth import GoogleAuthProvider

auth_provider = GoogleAuthProvider(
    client_secrets_file="path/to/client_secrets.json",
    credentials_file="path/to/store/credentials.json",
    scopes=["https://www.googleapis.com/auth/drive.file"]
)

# Authenticate (this will open a browser window)
auth_result = auth_provider.authenticate()
if auth_result.success:
    print("Authentication successful!")
else:
    print(f"Authentication failed: {auth_result.error}")
```

---

## Best Practices

### Project Structure

Follow this recommended project structure when using ZeoCore:

```
my_project/
├── config/
│   ├── default.yaml       # Default configuration
│   ├── development.yaml   # Development environment overrides
│   └── production.yaml    # Production environment overrides
├── src/
│   └── my_app/
│       ├── __init__.py
│       └── main.py        # Application code
├── data/                  # Data files
├── assets/                # Media assets
├── output/                # Generated output
└── logs/                  # Log files
```

### Configuration Management

- Keep sensitive data (API keys, secrets) out of your configuration files --
  put them in `.env` (see "Secrets and `.env`" above), never in a YAML file
- Use environment variables for sensitive information and deployment-specific settings
- Create environment-specific configuration files for different environments (development, staging, production)
- Validate configuration at startup to catch issues early

### Error Handling

- Use the provided ZeoError subclasses for specific error types
- Add context to errors to make debugging easier
- Use the `wrap_io_errors` decorator for functions that perform IO operations
- Log errors with appropriate log levels

### Path Handling

- Always use the path resolver to handle paths in a cross-platform manner
- Use relative paths from the project root when possible
- Detect project structure with `detect_project_context()` instead of hardcoding paths

### Plugin Development

- Follow the plugin protocol interfaces for compatibility
- Implement proper initialization and cleanup
- Provide clear error messages
- Use the standard result objects for consistent return values

## Extending ZeoCore

### Creating a New Tool

ZeoCore defines reusable capabilities. A runner (for example Sovereign
Agent) invokes and supervises them. Organizational authorization lives
in Zero Employee — a capability's `effects` field is a **declaration**,
not a permission grant.

See [Capabilities](#capabilities) for the full authoring, guard, outcome,
and adapter walkthrough. Short checklist:

1. Define Pydantic request and response models (JSON Schema is generated
   from those models — not from shallow annotations).
2. Implement either `@capability` or `BaseZeoTool.run()`.
3. Return a `CapabilityResult` (via `.ok()`, `.fail()`, `.fail_from_exc()`,
   `.skip()`, or `.unavailable()`) -- never raise for expected failure
   modes.
4. Use `zeo_core.core.errors`' `ZeoError` family for exceptional cases.
5. Look up integrations with `ctx.require_service(...)`. Absence of a
   declared service fails closed; do not fall back to ambient host access.

See [`examples/capability_authoring.py`](examples/capability_authoring.py)
and [`examples/minimal_tool.py`](examples/minimal_tool.py).

## Troubleshooting

Installation and first-capability problems (wrong Python version, an
inactive virtual environment, `ModuleNotFoundError: No module named
'zeo_core'`, decorator errors) are covered in
[QUICKSTART.md's common errors table](QUICKSTART.md#common-errors). The
issues below are the runtime ones you hit later.

### Common Issues

#### Configuration Not Found

```
ZeoConfigurationError: Configuration file not found: <path>
```

This is raised only when you pass `load_config()` an **explicit** path
that doesn't exist -- `load_config()` called with no argument never
raises this; it silently falls back to built-in defaults (and any
environment variables) if none of the default locations have a file.
If you're seeing this error, you (or a caller) passed a specific path:

```python
from zeo_core.config import load_config

config = load_config("path/to/config.yaml")  # <-- this path must exist
```

**Solution**: Either drop the explicit path and let `load_config()` use
its defaults, or create a real configuration file at one of these
locations before passing it:
- `./zeo_config.yaml`
- `./config/zeo_config.yaml`
- `~/.zeo/config.yaml`

See [`examples/config_usage.py`](examples/config_usage.py) for all three
behaviors (default lookup, missing explicit path, real explicit path)
demonstrated end to end.

#### Authentication Errors with Google Services

```
ZeoAuthenticationError: Failed to authenticate with Google Drive
```

**Solution**:
1. Ensure your client secrets file is valid and has the required scopes
2. Check that your application has been authorized in Google Cloud Console
3. Delete the credentials file and re-authenticate
4. Verify network connectivity and firewall settings

#### Plugin Not Found

```
ZeoPluginError: No plugin found in module zeo_core.modules.my_plugin
```

**Solution**:
1. Ensure the plugin is properly installed
2. Check that the plugin follows the required protocol interface
3. Verify that the plugin is registered correctly

#### Path Resolution Errors

```
ZeoFileNotFoundError: Could not find project root directory
```

**Solution**:
1. Ensure you're running from within a valid project directory
2. Create marker files (like `pyproject.toml` or `.zeo`) in your project root
3. Explicitly specify the project root directory

## API Reference

There is no generated Sphinx site yet. Use inline docstrings,
[llms.txt](llms.txt) for a condensed import map, and
[`src/zeo_core/contracts/README.md`](src/zeo_core/contracts/README.md) /
[`EXAMPLES.md`](src/zeo_core/contracts/EXAMPLES.md) for the contracts
kernel.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide: dev environment
setup (`make setup`), the verification gate (`make verify`), and code style
expectations.

## License

ZeoCore is released under the [MIT License](LICENSE).