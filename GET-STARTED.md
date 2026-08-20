# ZeoCore Documentation

## Introduction

**ZeoCore** is a capability-authoring framework and infrastructure library for Python. It provides a typed base for writing tools (`BaseZeoTool`, `ToolContext`, `CapabilityResult`), plus shared infrastructure for path resolution, filesystem operations, configuration management, plugin discovery, integrations with third-party services (Google Drive, Gmail, Google Calendar, Notion, Pandoc, jupytext, ffmpeg, LLM providers, GitHub), and adapters for exposing your tools over HTTP or MCP (for Claude Code, Cursor, and other MCP-native coding agents). **Requires Python 3.13 or newer.**

ZeoCore is designed for developers building automation tools, content pipelines, and integrations that need consistent configuration, filesystem, and error-handling behavior without re-solving those problems per project.

This documentation helps you get started with ZeoCore and use its features in your own applications. See also [`examples/`](examples/) for runnable, verified example scripts.

---

## Installation

### Prerequisites

- Python 3.13 or higher
- pip package manager

### Basic Installation

```bash
pip install zeocore
```

### Optional Dependencies

ZeoCore provides optional dependency groups tailored to specific integrations:

```bash
# For Google Drive integration
pip install "zeocore[drive]"

# For Gmail integration
pip install "zeocore[gmail]"

# For Google Calendar integration
pip install "zeocore[calendar]"

# For Notion integration
pip install "zeocore[notion]"

# For Pandoc document conversion
pip install "zeocore[pandoc]"

# For development (includes testing tools)
pip install "zeocore[dev]"

# For all Google-related functionality
pip install "zeocore[google]"

# For the HTTP adapter (expose tools over REST)
pip install "zeocore[http]"

# For the MCP adapter (expose tools to Claude Code, Cursor, and other
# MCP-native coding agents)
pip install "zeocore[mcp]"
```

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
The capability-authoring framework itself: `BaseZeoTool`, `ToolContext`, and
optional mixins (`IntegrationEnabledMixin`, `LifecycleMixin`,
`ToolEnvInitializerMixin`) for building doctrine-compliant tools. See
[`examples/toolkit_usage.py`](examples/toolkit_usage.py) and
[`examples/minimal_tool.py`](examples/minimal_tool.py).

### `zeo_core.contracts`
The data contracts tools speak: `CapabilityResult`, artifact/manifest
models, and common enums/IDs used across the framework.

### `zeo_core.adapters`
Optional network-facing adapters, both reading from the same
`OperationRegistry` (`zeo_core.core.registry`): `adapters.http` (FastAPI,
`zeocore[http]`) exposes tools over REST; `adapters.mcp` (`zeocore[mcp]`)
exposes them as MCP tools for Claude Code, Cursor, and other MCP-native
agents. See "Exposing Tools as an MCP Server" below and
[`examples/mcp_server_usage.py`](examples/mcp_server_usage.py).

---

## Getting Started

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

### Working with Jupytext Integration (script <-> notebook conversion)

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
both the HTTP and MCP adapters, not just one.

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
from pydantic import BaseModel, Field
from zeo_core.config.models import ZeoConfig

# Define custom configuration model
class MyAppConfig(BaseModel):
    api_key: str = Field(..., description="API key for external service")
    endpoint: str = Field("https://api.example.com", description="API endpoint")
    timeout: int = Field(30, description="Request timeout in seconds")

# Add to ZeoConfig
config = ZeoConfig()
config.custom["my_app"] = MyAppConfig(api_key="your-api-key").model_dump()

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

# Custom application-specific configuration
custom:
  my_app:
    api_key: "your-api-key"
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

- Keep sensitive data (API keys, secrets) out of your configuration files
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

Tools are the primary extension point: subclass `BaseZeoTool`, implement
`run(request, ctx) -> CapabilityResult`, and optionally mix in
`IntegrationEnabledMixin` (for service lookup) or `LifecycleMixin` (for
pre/post-run hooks).

1. Define a Pydantic request model for your tool's input.
2. Subclass `BaseZeoTool`, set `name`/`version`, implement `run()`.
3. Return a `CapabilityResult` (via `.ok()`, `.fail()`, `.fail_from_exc()`,
   or `.skip()`) -- never raise for expected failure modes.
4. Use `zeo_core.core.errors`' `ZeoError` family for exceptional cases.
5. Leverage `zeo_core.config` for settings your tool needs.

See [`examples/minimal_tool.py`](examples/minimal_tool.py) for the smallest
complete version of this pattern, and
[`examples/toolkit_usage.py`](examples/toolkit_usage.py) for one that adds
lifecycle hooks and an optional integration.

## Troubleshooting

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

For detailed API documentation, refer to the inline documentation in the code or generate API documentation using a tool like Sphinx.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide: dev environment
setup (`make setup`), the verification gate (`make verify`), and code style
expectations.

## License

ZeoCore is released under the [MIT License](LICENSE).