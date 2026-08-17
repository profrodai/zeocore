# ZeoCore Documentation

## Introduction

**ZeoCore** is a capability-authoring framework and infrastructure library for Python. It provides a typed base for writing tools (`BaseZeoTool`, `ToolContext`, `CapabilityResult`), plus shared infrastructure for path resolution, filesystem operations, configuration management, plugin discovery, and integrations with third-party services (Google Drive, Gmail, Notion, Pandoc, LLM providers, GitHub).

ZeoCore is designed for developers building automation tools, content pipelines, and integrations that need consistent configuration, filesystem, and error-handling behavior without re-solving those problems per project.

This documentation helps you get started with ZeoCore and use its features in your own applications. See also [`examples/`](examples/) for runnable, verified example scripts.

---

## Installation

### Prerequisites

- Python 3.10 or higher
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

# For Notion integration
pip install "zeocore[notion]"

# For Pandoc document conversion
pip install "zeocore[pandoc]"

# For development (includes testing tools)
pip install "zeocore[dev]"

# For all Google-related functionality
pip install "zeocore[google]"
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
Interfaces to third-party services (Google Drive, Gmail, Notion, Pandoc, GitHub, LLM providers) through a clean adapter layer.

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

---

## Getting Started

### Basic Configuration Setup

```python
from zeo_core.config import load_config, ZeoConfig

# Load configuration from default locations
config = load_config()

# Access configuration values
project_name = config.general.project_name
log_level = config.logging.level

# Load configuration from specific file
custom_config = load_config("path/to/custom_config.yaml")
```

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
ZeoConfigurationError: Configuration file not found in default locations.
```

**Solution**: Create a configuration file in one of these locations:
- `./zeo_config.yaml`
- `./config/zeo_config.yaml`
- `~/.zeo/config.yaml`

Or specify the configuration path explicitly:

```python
from zeo_core.config import load_config
config = load_config("path/to/config.yaml")
```

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