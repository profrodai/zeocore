# QuackCore Integrations Guide for QuackTool Developers

## Introduction

QuackCore provides a powerful integration framework that allows QuackTools to easily connect with external services such as Google Drive, Gmail, and Large Language Models (LLMs). This guide will walk you through:

1. How to register your QuackTool as a plugin
2. How to configure and use the integrations
3. Best practices and common anti-patterns
4. Configuration templates for your users

Let's start with understanding how QuackTools fit into the QuackCore ecosystem.

## QuackTool Registration

QuackTools are plugins that extend QuackCore's functionality. To create a QuackTool, you need to:

1. Implement the `QuackPluginProtocol` interface
2. Register your tool with QuackCore's plugin registry

### Basic QuackTool Implementation

```python
from quack_core.modules.protocols import QuackPluginProtocol


class MyQuackTool(QuackPluginProtocol):
    @property
    def name(self) -> str:
        return "my-quack-tool"

    # Add your tool's functionality here


def create_plugin() -> QuackPluginProtocol:
    """This factory function is discovered by quack_core."""
    return MyQuackTool()
```

### Automatic Registration

QuackCore discovers plugins through:

1. Entry points in your package's `setup.py`
2. The `create_plugin()` or `create_integration()` factory function
3. Direct registration with the registry

```python
# Manual registration example
from quack_core.modules import registry

registry.register(MyQuackTool())
```

## Using Integrations in Your QuackTool

Now, let's explore how to use the three main integrations: Google Drive, Gmail, and LLMs.

## 1. Google Drive Integration

### Initializing Google Drive

```python
from quack_core.integrations.google.drive import GoogleDriveService

class MyDriveQuackTool(QuackPluginProtocol):
    @property
    def name(self) -> str:
        return "drive-tool"
    
    def __init__(self):
        # Initialize with parameters or from config
        self.drive_service = GoogleDriveService(
            client_secrets_file="config/google_client_secret.json",
            credentials_file="config/google_credentials.json",
            shared_folder_id="your_shared_folder_id"  # Optional
        )
        
        # Initialize the service
        init_result = self.drive_service.initialize()
        if not init_result.success:
            raise Exception(f"Failed to initialize Google Drive: {init_result.error}")
```

### Uploading Files

```python
def upload_file(self, file_path: str, description: str = None) -> str:
    """Upload a file to Google Drive and return the sharing link."""
    result = self.drive_service.upload_file(
        file_path=file_path,
        description=description,
        public=True  # Make the file publicly accessible
    )
    
    if result.success:
        return result.content  # This is the sharing link
    else:
        raise Exception(f"Failed to upload file: {result.error}")
```

### Downloading Files

```python
def download_file(self, file_id: str, download_path: str = None) -> str:
    """Download a file from Google Drive."""
    result = self.drive_service.download_file(
        remote_id=file_id,
        local_path=download_path
    )
    
    if result.success:
        return result.content  # This is the local file path
    else:
        raise Exception(f"Failed to download file: {result.error}")
```

### Listing Files

```python
def list_files(self, folder_id: str = None, pattern: str = None) -> list:
    """List files in Google Drive, optionally filtering by pattern."""
    result = self.drive_service.list_files(
        remote_path=folder_id,
        pattern=pattern
    )
    
    if result.success:
        return result.content  # List of file metadata
    else:
        raise Exception(f"Failed to list files: {result.error}")
```

### Creating Folders

```python
def create_folder(self, folder_name: str, parent_id: str = None) -> str:
    """Create a folder in Google Drive."""
    result = self.drive_service.create_folder(
        folder_name=folder_name,
        parent_path=parent_id
    )
    
    if result.success:
        return result.content  # Folder ID
    else:
        raise Exception(f"Failed to create folder: {result.error}")
```

## 2. Gmail Integration

### Initializing Gmail

```python
from quack_core.integrations.google.mail import GoogleMailService

class MyMailQuackTool(QuackPluginProtocol):
    @property
    def name(self) -> str:
        return "mail-tool"
    
    def __init__(self):
        # Initialize with parameters or from config
        self.mail_service = GoogleMailService(
            client_secrets_file="config/google_client_secret.json",
            credentials_file="config/google_credentials.json",
            storage_path="emails_output",  # Where to save downloaded emails
            include_subject=True,
            include_sender=True
        )
        
        # Initialize the service
        init_result = self.mail_service.initialize()
        if not init_result.success:
            raise Exception(f"Failed to initialize Gmail: {init_result.error}")
```

### Listing Emails

```python
def list_recent_emails(self, query: str = None, days_back: int = 7) -> list:
    """List recent emails, optionally filtering by query."""
    # If no query is provided, a default one will be built using days_back
    result = self.mail_service.list_emails(query=query)
    
    if result.success:
        return result.content  # List of message metadata
    else:
        raise Exception(f"Failed to list emails: {result.error}")
```

### Downloading Emails

```python
def download_email(self, message_id: str) -> str:
    """Download an email and save it as HTML."""
    result = self.mail_service.download_email(msg_id=message_id)
    
    if result.success:
        return result.content  # Path to the downloaded HTML file
    else:
        raise Exception(f"Failed to download email: {result.error}")
```

## 3. LLM Integration

### Initializing LLM Service

```python
from quack_core.integrations.llms import LLMIntegration
from quack_core.integrations.llms.models import ChatMessage, LLMOptions, RoleType

class MyLLMQuackTool(QuackPluginProtocol):
    @property
    def name(self) -> str:
        return "llm-tool"
    
    def __init__(self):
        # Initialize LLM service
        self.llm_service = LLMIntegration(
            provider="openai",  # or "anthropic"
            model="gpt-4o",     # or specify a different model
            api_key="your_api_key_here"  # Better loaded from config
        )
        
        # Initialize the service
        init_result = self.llm_service.initialize()
        if not init_result.success:
            raise Exception(f"Failed to initialize LLM: {init_result.error}")
```

### Using the LLM for Chat

```python
def generate_chat_response(self, prompt: str, system_message: str = None) -> str:
    """Generate a response using the LLM."""
    # Prepare messages
    messages = []
    
    # Add system message if provided
    if system_message:
        messages.append(ChatMessage(role=RoleType.SYSTEM, content=system_message))
    
    # Add user message
    messages.append(ChatMessage(role=RoleType.USER, content=prompt))
    
    # Set options (optional)
    options = LLMOptions(
        temperature=0.7,
        max_tokens=2000
    )
    
    # Generate response
    result = self.llm_service.chat(messages=messages, options=options)
    
    if result.success:
        return result.content  # The model's response
    else:
        raise Exception(f"Failed to generate response: {result.error}")
```

### Streaming LLM Responses

```python
def stream_chat_response(self, prompt: str, callback) -> str:
    """Stream a response from the LLM with real-time updates."""
    messages = [ChatMessage(role=RoleType.USER, content=prompt)]
    
    options = LLMOptions(
        temperature=0.7,
        stream=True  # Enable streaming
    )
    
    # Generate streamed response
    result = self.llm_service.chat(
        messages=messages, 
        options=options,
        callback=callback  # Function that receives each chunk
    )
    
    if result.success:
        return result.content  # The complete response
    else:
        raise Exception(f"Failed to generate response: {result.error}")
```

### Token Counting

```python
def count_tokens(self, prompt: str) -> int:
    """Count tokens in a prompt."""
    messages = [ChatMessage(role=RoleType.USER, content=prompt)]
    
    result = self.llm_service.count_tokens(messages=messages)
    
    if result.success:
        return result.content  # Token count
    else:
        raise Exception(f"Failed to count tokens: {result.error}")
```

## Configuration Management

QuackCore provides a robust configuration system that your QuackTool should leverage.

### Configuration File Structure

Below is a template for a QuackCore configuration file that includes settings for all the integrations:

```yaml
# quack_config.yaml
general:
  project_name: MyQuackTool
  environment: development
  debug: false

logging:
  level: INFO
  file: logs/myquacktool.log
  console: true

paths:
  base_dir: ./
  output_dir: ./output
  assets_dir: ./assets
  data_dir: ./data
  temp_dir: ./temp

integrations:
  google:
    client_secrets_file: config/google_client_secret.json
    credentials_file: config/google_credentials.json
    shared_folder_id: your_shared_folder_id
    gmail_labels: []
    gmail_days_back: 7

  llm:
    default_provider: openai
    openai:
      api_key: your_openai_api_key
      default_model: gpt-4o
    anthropic:
      api_key: your_anthropic_api_key
      default_model: claude-3-opus-20240229
    timeout: 60
    retry_count: 3
    initial_retry_delay: 1.0
    max_retry_delay: 30.0

plugins:
  enabled:
    - my-quack-tool
  disabled: []
  paths: []

custom:
  # Your tool-specific configuration goes here
  my_setting: value
```

### Loading Configuration in Your QuackTool

```python
from quack_core.config import load_config, QuackConfig

class ConfiguredQuackTool(QuackPluginProtocol):
    @property
    def name(self) -> str:
        return "configured-tool"
    
    def __init__(self, config_path: str = None):
        # Load configuration
        self.config = load_config(config_path)
        
        # Set up logging based on configuration
        self.config.setup_logging()
        
        # Access specific configuration values
        google_config = self.config.integrations.google
        
        # Initialize services with configuration
        self.drive_service = GoogleDriveService(
            client_secrets_file=google_config.client_secrets_file,
            credentials_file=google_config.credentials_file,
            shared_folder_id=google_config.shared_folder_id
        )
        
        # Initialize other services...
```

## Best Practices

Here are some best practices for using QuackCore integrations in your QuackTools:

### 1. Error Handling

Always check the success status of integration results and handle errors gracefully:

```python
def safe_operation(self):
    result = self.drive_service.list_files()
    
    if not result.success:
        # Log the error
        logger.error(f"Operation failed: {result.error}")
        
        # Provide useful error message to the user
        return {"success": False, "error": str(result.error)}
    
    # Process successful results
    return {"success": True, "data": result.content}
```

### 2. Configuration Management

1. **Never hardcode credentials** in your code
2. Use environment variables as a fallback for sensitive information
3. Store configuration in standard locations

```python
def get_api_key(self):
    # Priority: 1. Config file 2. Environment variable 3. User prompt
    if hasattr(self.config.integrations.llm.openai, "api_key"):
        return self.config.integrations.llm.openai.api_key
    
    import os
    if api_key := os.environ.get("OPENAI_API_KEY"):
        return api_key
    
    # As a last resort, prompt the user (not recommended for production)
    return input("Please enter your OpenAI API key: ")
```

### 3. Lazy Initialization

Initialize services only when needed to improve startup performance:

```python
class EfficientQuackTool(QuackPluginProtocol):
    @property
    def name(self) -> str:
        return "efficient-tool"
    
    def __init__(self):
        self.config = load_config()
        self._drive_service = None
    
    @property
    def drive_service(self):
        """Lazy initialization of Google Drive service."""
        if self._drive_service is None:
            self._drive_service = GoogleDriveService(
                client_secrets_file=self.config.integrations.google.client_secrets_file,
                credentials_file=self.config.integrations.google.credentials_file
            )
            init_result = self._drive_service.initialize()
            if not init_result.success:
                raise Exception(f"Failed to initialize Drive: {init_result.error}")
        
        return self._drive_service
```

### 4. Resource Cleanup

Make sure you handle resource cleanup properly:

```python
def process_large_files(self, folder_id):
    try:
        # List files
        files_result = self.drive_service.list_files(remote_path=folder_id)
        if not files_result.success:
            return {"success": False, "error": files_result.error}
        
        # Process files...
        results = []
        for file in files_result.content:
            # Download to a temporary location
            download_result = self.drive_service.download_file(
                remote_id=file["id"],
                local_path=self.config.paths.temp_dir
            )
            
            if download_result.success:
                # Process file
                # ...
                
                # Clean up temporary file
                import os
                os.remove(download_result.content)
                
                results.append({"file": file["name"], "success": True})
            else:
                results.append({"file": file["name"], "success": False})
        
        return {"success": True, "results": results}
        
    except Exception as e:
        # Handle unexpected errors
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
```

### 5. Logging

Use QuackCore's logging system for consistent logs:

```python
from quack_core.core.logging import get_logger

logger = get_logger(__name__)


def my_function(self):
    logger.debug("Starting operation")

    try:
        # Operation
        logger.info("Operation completed successfully")
    except Exception as e:
        logger.error(f"Operation failed: {e}")
```

## Common Anti-Patterns to Avoid

### 1. Ignoring Result Status

❌ **Bad**:
```python
def upload_document(self, path):
    result = self.drive_service.upload_file(path)
    return result.content  # Might be None if failed!
```

✅ **Good**:
```python
def upload_document(self, path):
    result = self.drive_service.upload_file(path)
    if result.success:
        return result.content
    else:
        raise ValueError(f"Upload failed: {result.error}")
```

### 2. Hardcoded Credentials

❌ **Bad**:
```python
self.llm_service = LLMIntegration(
    provider="openai",
    api_key="sk-1234567890abcdef1234567890abcdef"  # Hardcoded!
)
```

✅ **Good**:
```python
api_key = self.config.integrations.llm.openai.api_key or os.environ.get("OPENAI_API_KEY")
self.llm_service = LLMIntegration(provider="openai", api_key=api_key)
```

### 3. Ignoring Configuration System

❌ **Bad**:
```python
class MyTool(QuackPluginProtocol):
    def __init__(self):
        self.output_dir = "./my_output"  # Hardcoded path
```

✅ **Good**:
```python
class MyTool(QuackPluginProtocol):
    def __init__(self):
        self.config = load_config()
        self.output_dir = self.config.paths.output_dir
```

### 4. Missing Initialization

❌ **Bad**:
```python
def __init__(self):
    self.drive_service = GoogleDriveService()
    # Missing initialization!
```

✅ **Good**:
```python
def __init__(self):
    self.drive_service = GoogleDriveService()
    init_result = self.drive_service.initialize()
    if not init_result.success:
        raise Exception(f"Failed to initialize: {init_result.error}")
```

### 5. Poor Error Handling

❌ **Bad**:
```python
def list_emails(self):
    return self.mail_service.list_emails().content
```

✅ **Good**:
```python
def list_emails(self):
    result = self.mail_service.list_emails()
    if result.success:
        return result.content
    else:
        logger.error(f"Failed to list emails: {result.error}")
        return []  # Or raise an exception, or return a default value
```

## Setup Instructions for Users

Provide these instructions to users of your QuackTool for setting up the necessary configurations:

### Google Integration Setup

1. **Create a Google Cloud Project**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Drive API and Gmail API

2. **Create OAuth Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Create an "OAuth client ID" credential
   - Choose "Desktop application" as the application type
   - Download the client secrets JSON file

3. **Configure Your QuackTool**:
   - Save the client secrets JSON file to `config/google_client_secret.json`
   - Create the configuration file at `quack_config.yaml` using the template above
   - Update the `client_secrets_file` path in the configuration

4. **First Run**:
   - On first run, the tool will open a browser window for authentication
   - Log in to your Google account and grant the required permissions
   - The tool will save OAuth tokens to the `credentials_file` location

### LLM Integration Setup

1. **Get API Keys**:
   - For OpenAI: Sign up at [OpenAI](https://platform.openai.com/) and create an API key
   - For Anthropic: Sign up at [Anthropic](https://www.anthropic.com/) and create an API key

2. **Configure Your QuackTool**:
   - Add the API keys to your `quack_config.yaml` file
   - Alternatively, set the `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` environment variables

## Configuration Template

Here's a minimal configuration template for users to get started with your QuackTool:

```yaml
# quack_config.yaml

general:
  project_name: MyQuackTool

logging:
  level: INFO
  file: logs/myquacktool.log

integrations:
  google:
    client_secrets_file: config/google_client_secret.json
    credentials_file: config/google_credentials.json
    
  llm:
    default_provider: openai
    openai:
      api_key: YOUR_OPENAI_API_KEY
      default_model: gpt-4o
```

## Conclusion

This guide has covered the essentials of working with QuackCore integrations in your QuackTools. By following these patterns and best practices, you'll be able to create powerful tools that leverage Google Drive, Gmail, and LLMs effectively.

Remember to:
- Always check the success status of integration results
- Keep credentials secure and out of your code
- Leverage QuackCore's configuration system
- Handle errors gracefully
- Initialize services properly

Happy QuackTool development!