# QuackCore Documentation

## Introduction

**QuackCore** is the foundational library powering the **QuackVerse** ecosystem of tools. It provides shared infrastructure for path resolution, configuration management, plugin architecture, integration protocols, and CLI utilities. This modular core enables seamless interoperability between tools and consistent behavior across the QuackVerse.

QuackCore is designed for developers building internal tools, CLI agents, automation pipelines, and integrations within the QuackVerse ecosystem. It also powers educational content used in the **AI Product Engineer** learning platform.

This documentation helps you get started with QuackCore and use its features in your own applications or when building new tools in the ecosystem.

---

## Installation

### Prerequisites

- Python 3.13 or higher
- pip package manager

### Basic Installation

```bash
pip install quack-core
```

### Optional Dependencies

QuackCore provides optional dependency groups tailored to specific integrations:

```bash
# For Google Drive integration
pip install "quackcore[drive]"

# For Gmail integration
pip install "quackcore[gmail]"

# For Notion integration
pip install "quackcore[notion]"

# For Pandoc document conversion
pip install "quackcore[pandoc]"

# For development (includes testing tools)
pip install "quackcore[dev]"

# For all Google-related functionality
pip install "quackcore[google]"
```

---

## Core Modules Overview

QuackCore is organized into distinct modules that provide clear functionality:

### `quack_core.config`
Robust configuration system supporting YAML, environment variables, and runtime overrides.

### `quack_core.core.paths`
Standardized path resolution and project structure detection across environments.

### `quack_core.core.fs`
Safe and consistent filesystem operations with error handling and structured results.

### `quack_core.modules`
Extensible plugin discovery and registration framework to build modular CLI agents and tools.

### `quack_core.integrations`
Interfaces to third-party services (Google Drive, Gmail, Notion, Pandoc) through a clean adapter layer.

### `quack_core.core.errors`
Structured error handling system with typed exceptions for improved developer experience.

### `quack_core.cli`
Shared CLI environment initialization and I/O utilities for user-friendly tooling.

---

## Getting Started

### Basic Configuration Setup

```python
from quack_core.config import load_config, QuackConfig

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
from quack_core.core.paths import resolver

# Find the project root directory
project_root = resolver._get_project_root()

# Resolve a path relative to the project root
config_path = resolver._resolve_project_path("config/settings.yaml")

# Detect project context
context = resolver._detect_project_context()
source_dir = context._get_source_dir()
```

### File Operations

```python
from quack_core.core.fs import service as fs

# Read text from a file
result = fs._read_text("path/to/file.txt")
if result.success:
    content = result.content
else:
    print(f"Error: {result.error}")

# Write text to a file
fs._write_text("path/to/output.txt", "Hello, QuackCore!")

# Create a directory
fs._create_directory("path/to/new/directory")

# Read structured data
yaml_result = fs._read_yaml("config.yaml")
if yaml_result.success:
    config_data = yaml_result.data
```

### Using Plugins

```python
from quack_core.modules import registry

# Get a list of all registered modules
plugin_names = registry.list_plugins()

# Get a specific plugin
pandoc_plugin = registry.get_plugin("Pandoc")
if pandoc_plugin:
  pandoc_plugin.initialize()
  # Use the plugin's functionality
```

### Working with Google Drive Integration

```python
from quack_core.integrations.google.drive import GoogleDriveService

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
from quack_core.integrations.google.mail import GoogleMailService

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
from quack_core.core.errors import QuackError, QuackFileNotFoundError, wrap_io_errors


# Use decorator for automatic error handling
@wrap_io_errors
def read_important_file(path):
  with open(path, 'r') as f:
    return f.read()


# Handle specific errors
try:
  content = read_important_file("config.txt")
except QuackFileNotFoundError as e:
  print(f"File not found: {e.path}")
except QuackError as e:
  print(f"Error: {e}")
```

### CLI Application Setup

```python
from quack_core.cli import init_cli_env, print_info, print_error, ask

# Initialize CLI environment
context = init_cli_env(
    config_path="config.yaml",
    app_name="my_app"
)

# Use CLI utilities
print_info("Starting process...")

# Get user input
user_input = ask("Enter a value:", default="default_value")

# Access logger
context.logger.debug("Debug information")

# Handle errors nicely
try:
    # Your code here
    pass
except Exception as e:
    print_error(f"Error occurred: {e}", exit_code=1)
```

---

## Advanced Usage

### Creating a Custom Plugin

```python
from quack_core.modules.protocols import QuackPluginProtocol
from quack_core.integrations.core.results import IntegrationResult


class MyCustomPlugin(QuackPluginProtocol):
  @property
  def name(self) -> str:
    return "MyCustomPlugin"

  @property
  def version(self) -> str:
    return "1.0.0"

  def initialize(self) -> IntegrationResult:
    # Initialization logic here
    return IntegrationResult.success_result(message="Plugin initialized successfully")

  def is_available(self) -> bool:
    return True

  # Add custom methods for your plugin


# Register the plugin
from quack_core.modules import registry

registry.register(MyCustomPlugin())
```

### Working with Pandoc for Document Conversion

```python
from quack_core.integrations.pandoc import PandocIntegration
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
from quack_core.config.models import QuackConfig

# Define custom configuration model
class MyAppConfig(BaseModel):
    api_key: str = Field(..., description="API key for external service")
    endpoint: str = Field("https://api.example.com", description="API endpoint")
    timeout: int = Field(30, description="Request timeout in seconds")

# Add to QuackConfig
config = QuackConfig()
config.custom["my_app"] = MyAppConfig(api_key="your-api-key").model_dump()

# Save configuration
from quack_core.config.loader import merge_configs
merged_config = merge_configs(config, {})
```

## Configuration File Format

QuackCore uses YAML for configuration files. Here's an example of a basic configuration file:

```yaml
general:
  project_name: "MyQuackProject"
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

QuackCore supports configuration through environment variables with the prefix `QUACK_`:

```bash
# Set configuration values
export QUACK_ENV=production
export QUACK_GENERAL__DEBUG=false
export QUACK_LOGGING__LEVEL=WARNING
export QUACK_PATHS__BASE_DIR=/opt/quackverse

# Set Google integration configuration
export QUACK_GOOGLE__CLIENT_SECRETS_FILE=/etc/quack/client_secrets.json
export QUACK_GOOGLE__CREDENTIALS_FILE=/etc/quack/credentials.json
```

## Integration Authentication

### Google API Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the APIs you need (Drive API, Gmail API, etc.)
4. Create OAuth 2.0 credentials
5. Download the client secrets JSON file
6. Use the client secrets file path in your QuackCore configuration

```python
from quack_core.integrations.google.auth import GoogleAuthProvider

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

## QuackVerse Ecosystem Compatibility

QuackCore is the backbone of the **QuackVerse**—a suite of open and internal tools that power:
- Tutorial scaffolding
- Generative AI pipelines for content
- Educational workflows within the **AI Product Engineer** platform

Tools built with QuackCore gain immediate compatibility with:
- AIPE’s content pipeline
- The QuackTool CLI standard
- Plugin chaining and execution environments

To create your own tool:
- Follow QuackCore’s plugin or integration protocol
- Use `quack_core.config` and `quack_core.core.fs` for standard behavior
- Register your tool with `quack_core.modules.registry`

This ensures your tool can be consumed by orchestrators like **QuackBuddy** and exposed via upcoming standards such as **MCP**.

---


### Project Structure

Follow this recommended project structure when using QuackCore:

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

- Use the provided QuackError subclasses for specific error types
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

## Extending QuackCore

### Creating a New Tool in the QuackVerse Ecosystem

When creating a new tool that integrates with the QuackVerse ecosystem:

1. Use QuackCore as a dependency
2. Follow the architectural patterns established in QuackCore
3. Implement a plugin interface if your tool provides functionality that others might use
4. Use the standard error handling mechanisms
5. Leverage the configuration system for settings

Example of a new tool setup:

```python
# my_quack_tool/main.py
from quack_core.config import load_config
from quack_core.core.paths import resolver
from quack_core.core.fs import service as fs
from quack_core.cli import init_cli_env


def main():
  # Initialize the CLI environment
  context = init_cli_env(app_name="my_quack_tool")

  # Get configuration
  config = context.config

  # Set up logging
  logger = context.logger
  logger.info("Starting My Quack Tool")

  # Use QuackCore functionality
  project_root = resolver._get_project_root()
  output_dir = resolver._resolve_project_path("output")

  # Implement your tool's functionality
  # ...

  logger.info("Process completed successfully")


if __name__ == "__main__":
  main()
```

## Troubleshooting

### Common Issues

#### Configuration Not Found

```
QuackConfigurationError: Configuration file not found in default locations.
```

**Solution**: Create a configuration file in one of these locations:
- `./quack_config.yaml`
- `./config/quack_config.yaml`
- `~/.quack/config.yaml`

Or specify the configuration path explicitly:

```python
from quack_core.config import load_config
config = load_config("path/to/config.yaml")
```

#### Authentication Errors with Google Services

```
QuackAuthenticationError: Failed to authenticate with Google Drive
```

**Solution**:
1. Ensure your client secrets file is valid and has the required scopes
2. Check that your application has been authorized in Google Cloud Console
3. Delete the credentials file and re-authenticate
4. Verify network connectivity and firewall settings

#### Plugin Not Found

```
QuackPluginError: No plugin found in module quack_core.modules.my_plugin
```

**Solution**:
1. Ensure the plugin is properly installed
2. Check that the plugin follows the required protocol interface
3. Verify that the plugin is registered correctly

#### Path Resolution Errors

```
QuackFileNotFoundError: Could not find project root directory
```

**Solution**:
1. Ensure you're running from within a valid project directory
2. Create marker files (like `pyproject.toml` or `.quack`) in your project root
3. Explicitly specify the project root directory

## API Reference

For detailed API documentation, refer to the inline documentation in the code or generate API documentation using a tool like Sphinx.

---

## Contributing

We welcome contributors interested in extending the open-source core of quack_core.


If you're interested in contributing to QuackCore:

1. Fork the repository
2. Install development dependencies: `pip install -e ".[dev]"`
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

---

---

# 🦆 QuackVerse Licensing Overview

QuackVerse is a modular ecosystem with mixed licensing to balance community contribution and project protection.

### 🔓 Open Source (with strong copyleft)
- **Repositories**: `quackcore`, `ducktyper`
- **License**: [GNU Affero General Public License v3.0 (AGPL-3.0)](https://www.gnu.org/licenses/agpl-3.0.en.html)
- **Why?** This license ensures that any public use of these tools — including SaaS or hosted services — must release the source code and improvements back to the community.

### 🔐 Source-Available (with delayed open-source)
- **Repositories**: All `quacktools/*`
- **License**: [Business Source License 1.1 (BUSL-1.1)](https://mariadb.com/bsl11/)
- **What does this mean?**
  - You can **view, fork, and modify** the code.
  - **Production or commercial use is not allowed** unless you obtain a commercial license from us.
  - The license **automatically converts to Apache 2.0 after 3 years**, ensuring long-term openness.
- A short human summary is provided in each tool's README.

### 🎨 Brand and Creative Assets
- **Assets**: Logos, Mascot (Quackster), design elements
- **License**: [Creative Commons Attribution-NonCommercial-NoDerivs 4.0 (CC BY-NC-ND 4.0)](https://creativecommons.org/licenses/by-nc-nd/4.0/)
- **You may not** redistribute, remix, or use our branding for commercial purposes.

---

### 🧠 Why this setup?

We love open-source and education. However, to continue building high-quality learning tools, we need to protect our work from being commercialized or rebranded by others without contributing back. Our structure enables:
- A healthy developer community.
- Opportunities for contributors to shape the future.
- Commercial protection for sustainability.

We welcome pull requests, issues, and feedback. If you're interested in **commercial use**, please reach out via [rod@aip.engineer](mailto:rod@aip.engineer).


---

## 💬 Questions?

Tweet at [@aipengineer](https://twitter.com/aipengineer) or file an issue on GitHub!