# QuackCore Integrations - Comprehensive Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Core Concepts](#core-concepts)
3. [Architecture Overview](#architecture-overview)
4. [Protocols](#protocols)
5. [Base Classes](#base-classes)
6. [Results](#results)
7. [Integration Registry](#integration-registry)
8. [Creating Your First Integration](#creating-your-first-integration)
9. [Authentication in Integrations](#authentication-in-integrations)
10. [Configuration Management](#configuration-management)
11. [Storage Integrations](#storage-integrations)
12. [Testing Integrations](#testing-integrations)
13. [Best Practices](#best-practices)
14. [Common Pitfalls](#common-pitfalls)
15. [Integration Discovery](#integration-discovery)
16. [Frequently Asked Questions](#frequently-asked-questions)

## Introduction

The `quack_core.integrations.core` module provides a robust framework for connecting QuackCore to external services and platforms. This guide will walk you through the fundamentals and advanced concepts needed to build effective, maintainable integrations.

**What is an integration?**

In QuackCore, an integration is a self-contained module that connects the core system to an external service or platform. Integrations provide standardized ways to:

- Authenticate with external services
- Configure connection parameters
- Interact with external APIs
- Handle responses and errors consistently

This guide is intended for developers who want to create new integrations for quack_core. By following these patterns, your integrations will maintain consistency with the rest of the ecosystem and be easily discoverable by users.

## Core Concepts

Before diving into implementation details, let's understand the core concepts that make up the QuackCore integration framework:

### Key Components

1. **Protocols**: Define the interfaces that integrations must implement
2. **Base Classes**: Provide common functionality for different types of integrations
3. **Results**: Standardized return value classes that handle success and error cases
4. **Registry**: Central system for discovering and accessing integrations

### Design Philosophy

The QuackCore integration framework follows these principles:

- **Separation of Concerns**: Authentication, configuration, and service functionality are distinct components
- **Consistent Error Handling**: All operations return standardized result objects
- **Discoverability**: Integrations can be automatically discovered and registered
- **Type Safety**: Extensive use of typing for better development experience

## Architecture Overview

The QuackCore integration system uses a modular architecture consisting of several interconnected components:

```
┌─────────────────────────┐
│  Integration Registry   │
└───────────┬─────────────┘
            │
            │ manages
            ▼
┌─────────────────────────┐
│     Integrations        │
└───────────┬─────────────┘
            │
            │ may use
  ┌─────────┴─────────────┐
  │                       │
  ▼                       ▼
┌────────────┐    ┌───────────────┐
│   Auth     │    │  Config       │
│ Providers  │    │  Providers    │
└────────────┘    └───────────────┘
```

### Component Relationships

- The **Integration Registry** maintains references to all available integrations
- **Integrations** implement specific functionality for external services
- **Auth Providers** handle authentication with external services
- **Config Providers** manage loading and validating configuration

This architecture allows for flexible composition where integrations can be standalone or leverage common auth and config providers.

## Protocols

Protocols define the interfaces that different components must implement. They allow for consistent behavior across different implementations and enable dependency injection patterns.

### IntegrationProtocol

This is the base protocol that all integrations must implement:

```python
@runtime_checkable
class IntegrationProtocol(Protocol):
    """Base protocol for all integrations."""

    @property
    def name(self) -> str:
        """Name of the integration."""
        ...

    @property
    def version(self) -> str:
        """Version of the integration."""
        ...

    def initialize(self) -> IntegrationResult:
        """Initialize the integration."""
        ...

    def is_available(self) -> bool:
        """Check if the integration is available."""
        ...
```

### AuthProviderProtocol

Defines the interface for authentication providers:

```python
@runtime_checkable
class AuthProviderProtocol(Protocol):
    """Protocol for authentication providers."""

    @property
    def name(self) -> str:
        """Name of the authentication provider."""
        ...

    def authenticate(self) -> AuthResult:
        """Authenticate with the external service."""
        ...

    def refresh_credentials(self) -> AuthResult:
        """Refresh authentication credentials if expired."""
        ...

    def get_credentials(self) -> object:
        """Get the current authentication credentials."""
        ...

    def save_credentials(self) -> bool:
        """Save the current authentication credentials."""
        ...
```

### ConfigProviderProtocol

Defines the interface for configuration providers:

```python
@runtime_checkable
class ConfigProviderProtocol(Protocol):
    """Protocol for configuration providers."""

    @property
    def name(self) -> str:
        """Name of the configuration provider."""
        ...

    def load_config(self, config_path: str | None = None) -> ConfigResult:
        """Load configuration from a file."""
        ...

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration data."""
        ...

    def get_default_config(self) -> dict[str, Any]:
        """Get default configuration values."""
        ...
```

### StorageIntegrationProtocol

Extends the base integration protocol for storage-specific operations:

```python
@runtime_checkable
class StorageIntegrationProtocol(IntegrationProtocol, Protocol):
    """Protocol for storage integrations."""

    def upload_file(
        self, file_path: str, remote_path: str | None = None
    ) -> IntegrationResult[str]:
        """Upload a file to the storage service."""
        ...

    def download_file(
        self, remote_id: str, local_path: str | None = None
    ) -> IntegrationResult[str]:
        """Download a file from the storage service."""
        ...

    def list_files(
        self, remote_path: str | None = None, pattern: str | None = None
    ) -> IntegrationResult[list[Mapping]]:
        """List files in the storage service."""
        ...

    def create_folder(
        self, folder_name: str, parent_path: str | None = None
    ) -> IntegrationResult[str]:
        """Create a folder in the storage service."""
        ...
```

### Using Protocols

Protocols enable flexible implementation patterns. For example, you can create functions that accept any object implementing a specific protocol:

```python
def list_available_files(
    storage_integration: StorageIntegrationProtocol,
    folder: str | None = None
) -> list[str]:
    """List available files using any storage integration."""
    result = storage_integration.list_files(remote_path=folder)
    if result.success:
        return [file["name"] for file in result.content]
    return []
```

## Base Classes

QuackCore provides abstract base classes that implement common functionality for different types of integrations. These base classes implement the corresponding protocols and provide useful defaults.

### BaseAuthProvider

This base class implements common functionality for authentication providers:

```python
class BaseAuthProvider(ABC, AuthProviderProtocol):
    """Base class for authentication providers."""

    def __init__(
        self,
        credentials_file: str | None = None,
        log_level: int = logging.INFO,
    ) -> None:
        """Initialize the base authentication provider."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.setLevel(log_level)

        self.credentials_file = (
            self._resolve_path(credentials_file) if credentials_file else None
        )
        self.authenticated = False

    # ... other methods
```

To implement an authentication provider, extend this class and implement the required abstract methods:

```python
class MyServiceAuthProvider(BaseAuthProvider):
    """Authentication provider for MyService."""

    @property
    def name(self) -> str:
        """Name of the authentication provider."""
        return "MyService"

    def authenticate(self) -> AuthResult:
        """Authenticate with MyService."""
        try:
            # Authentication logic here
            token = "example_token"
            self.authenticated = True
            return AuthResult.success_result(
                token=token,
                message="Successfully authenticated with MyService",
            )
        except Exception as e:
            return AuthResult.error_result(
                error=f"Authentication failed: {str(e)}"
            )

    def refresh_credentials(self) -> AuthResult:
        """Refresh MyService credentials."""
        # Refresh logic here
        return AuthResult.success_result(token="new_token")

    def get_credentials(self) -> object:
        """Get the current credentials."""
        # Return credentials
        return {"token": "example_token"}

    def save_credentials(self) -> bool:
        """Save credentials to file."""
        if not self.credentials_file:
            return False
        
        # Ensure directory exists
        self._ensure_credentials_directory()
        
        # Save credentials logic
        try:
            with open(self.credentials_file, "w") as f:
                json.dump({"token": "example_token"}, f)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save credentials: {e}")
            return False
```

### BaseConfigProvider

This base class implements common functionality for configuration providers:

```python
class BaseConfigProvider(ABC, ConfigProviderProtocol):
    """Base class for configuration providers."""

    DEFAULT_CONFIG_LOCATIONS = [
        "./config/integration_config.yaml",
        "./quack_config.yaml",
        "~/.quack/config.yaml",
    ]
    
    # ... implementation details
```

Implementing a configuration provider:

```python
class MyServiceConfigProvider(BaseConfigProvider):
    """Configuration provider for MyService."""

    @property
    def name(self) -> str:
        """Name of the configuration provider."""
        return "MyService"

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate MyService configuration."""
        required_keys = ["api_key", "endpoint_url"]
        return all(key in config for key in required_keys)

    def get_default_config(self) -> dict[str, Any]:
        """Get default MyService configuration."""
        return {
            "api_key": "",
            "endpoint_url": "https://api.myservice.com/v1",
            "timeout_seconds": 30,
        }
        
    def _extract_config(self, config_data: dict[str, Any]) -> dict[str, Any]:
        """Extract MyService-specific configuration."""
        # Look for myservice or MyService section in config file
        for key in ["myservice", "MyService"]:
            if key in config_data:
                return config_data[key]
        
        # Fall back to default implementation
        return super()._extract_config(config_data)
```

### BaseIntegrationService

This base class implements common functionality for integrations:

```python
class BaseIntegrationService(ABC, IntegrationProtocol):
    """Base class for integration services."""

    def __init__(
        self,
        config_provider: ConfigProviderProtocol | None = None,
        auth_provider: AuthProviderProtocol | None = None,
        config_path: str | None = None,
        log_level: int = logging.INFO,
    ) -> None:
        """Initialize the base integration service."""
        # ... implementation details
```

Implementing an integration service:

```python
class MyServiceIntegration(BaseIntegrationService):
    """Integration for MyService."""

    def __init__(
        self,
        config_provider: ConfigProviderProtocol | None = None,
        auth_provider: AuthProviderProtocol | None = None,
        config_path: str | None = None,
        log_level: int = logging.INFO,
    ) -> None:
        """Initialize the MyService integration."""
        # Create default providers if not provided
        if config_provider is None:
            config_provider = MyServiceConfigProvider(log_level=log_level)
        
        if auth_provider is None:
            auth_provider = MyServiceAuthProvider(log_level=log_level)
            
        super().__init__(
            config_provider=config_provider,
            auth_provider=auth_provider,
            config_path=config_path,
            log_level=log_level,
        )
        
        self.client = None

    @property
    def name(self) -> str:
        """Name of the integration."""
        return "MyService"
        
    @property
    def version(self) -> str:
        """Version of the integration."""
        return "1.0.0"
        
    def initialize(self) -> IntegrationResult:
        """Initialize the MyService integration."""
        # First, call the base initialization
        init_result = super().initialize()
        if not init_result.success:
            return init_result
            
        try:
            # Initialize service-specific client
            if self.config:
                api_key = self.config.get("api_key")
                endpoint = self.config.get("endpoint_url")
                
                if not api_key:
                    return IntegrationResult.error_result("API key not configured")
                    
                self.client = MyServiceClient(api_key=api_key, endpoint=endpoint)
                return IntegrationResult.success_result(
                    message="MyService integration initialized successfully"
                )
        except Exception as e:
            return IntegrationResult.error_result(
                f"Failed to initialize MyService client: {str(e)}"
            )
            
    def is_available(self) -> bool:
        """Check if the MyService integration is available."""
        return super().is_available() and self.client is not None
        
    def perform_action(self, action_type: str, params: dict) -> IntegrationResult:
        """Perform an action using MyService."""
        # Ensure integration is initialized
        if not self.is_available():
            return IntegrationResult.error_result(
                "MyService integration is not available"
            )
            
        try:
            # Perform action using client
            result = self.client.perform_action(action_type, params)
            return IntegrationResult.success_result(
                content=result,
                message=f"Successfully performed {action_type}"
            )
        except Exception as e:
            return IntegrationResult.error_result(
                f"Error performing {action_type}: {str(e)}"
            )
```

## Results

The QuackCore integration framework uses standardized result classes to provide consistent error handling and return values.

### IntegrationResult

This is the base result class used for most integration operations:

```python
class IntegrationResult(BaseModel, Generic[T]):
    """Base result for integration _ops."""

    success: bool = Field(
        default=True,
        description="Whether the operation was successful",
    )

    message: str | None = Field(
        default=None,
        description="Additional message about the operation",
    )

    error: str | None = Field(
        default=None,
        description="Error message if operation failed",
    )

    content: T | None = Field(
        default=None,
        description="Result content if operation was successful",
    )
```

The `IntegrationResult` class includes class methods for creating success and error results:

```python
# Creating a success result
result = IntegrationResult.success_result(
    content={"key": "value"},
    message="Operation completed successfully"
)

# Creating an error result
result = IntegrationResult.error_result(
    error="Operation failed due to network error",
    message="Please try again later"
)
```

### AuthResult

Specialized result class for authentication operations:

```python
class AuthResult(BaseModel):
    """Result for authentication _ops."""

    success: bool = Field(
        default=True,
        description="Whether the authentication was successful",
    )

    message: str | None = Field(
        default=None,
        description="Additional message about the authentication",
    )

    error: str | None = Field(
        default=None,
        description="Error message if authentication failed",
    )

    token: str | None = Field(
        default=None,
        description="Authentication token if available",
    )

    expiry: int | None = Field(
        default=None,
        description="Token expiry timestamp",
    )

    credentials_path: str | None = Field(
        default=None,
        description="Path where credentials are stored",
    )

    content: dict | None = Field(
        default=None,
        description="Additional authentication content or metadata",
    )
```

### ConfigResult

Specialized result class for configuration operations:

```python
class ConfigResult(IntegrationResult[dict]):
    """Result for configuration _ops."""

    config_path: str | None = Field(
        default=None,
        description="Path to the configuration file",
    )

    validation_errors: list[str] | None = Field(
        default=None,
        description="Validation errors if any",
    )
```

### Working with Results

When implementing integration methods, always return the appropriate result type:

```python
def upload_document(self, file_path: str) -> IntegrationResult[str]:
    """Upload a document to the service."""
    if not os.path.exists(file_path):
        return IntegrationResult.error_result(
            error=f"File not found: {file_path}"
        )
        
    try:
        # Upload logic here
        file_id = "12345"
        return IntegrationResult.success_result(
            content=file_id,
            message=f"Successfully uploaded {os.path.basename(file_path)}"
        )
    except ConnectionError:
        return IntegrationResult.error_result(
            error="Connection failed during upload"
        )
    except Exception as e:
        return IntegrationResult.error_result(
            error=f"Upload failed: {str(e)}"
        )
```

When handling results, check the success flag:

```python
def process_document(integration, file_path):
    # Upload the document
    upload_result = integration.upload_document(file_path)
    
    if not upload_result.success:
        print(f"Error: {upload_result.error}")
        return
        
    document_id = upload_result.content
    print(f"Uploaded document with ID: {document_id}")
    
    # Continue processing...
```

## Integration Registry

The integration registry provides a central system for discovering and accessing integrations.

### Key Features

- **Registration**: Add integrations to the registry
- **Discovery**: Automatically find integrations via entry points
- **Lookup**: Get integrations by name or type

### Using the Registry

```python
from quack_core.integrations.core import registry

# Get a specific integration by name
my_service = registry.get_integration("MyService")
if my_service:
    result = my_service.initialize()
    
# Get all integrations of a specific type
storage_integrations = list(registry.get_integration_by_type(StorageIntegrationProtocol))
for storage in storage_integrations:
    print(f"Available storage: {storage.name}")
    
# Check if an integration is registered
if registry.is_registered("MyService"):
    print("MyService is available")
    
# List all registered integrations
available_integrations = registry.list_integrations()
print(f"Available integrations: {', '.join(available_integrations)}")
```

### Manual Registration

You can manually register integrations:

```python
from quack_core.integrations.core import registry
from my_module.integrations import MyCustomIntegration

# Create and register an integration
integration = MyCustomIntegration()
registry.register(integration)
```

### Automatic Discovery

The registry can automatically discover integrations via entry points:

```python
# Discover integrations
discovered = registry.discover_integrations()
print(f"Discovered {len(discovered)} integrations")
```

For this to work, your package must define entry points in its `setup.py` or `pyproject.toml`:

```python
# setup.py
setup(
    # ...
    entry_points={
        "quack_core.integrations": [
            "my_service = my_package.my_module:create_integration",
        ],
    },
)
```

```toml
# pyproject.toml
[project.entry-points."quack_core.integrations"]
my_service = "my_package.my_module:create_integration"
```

## Creating Your First Integration

Let's walk through the process of creating a complete integration for a fictional REST API service.

### Step 1: Set Up the Project Structure

```
my_integration/
├── __init__.py
├── auth.py
├── config.py
├── service.py
└── client.py
```

### Step 2: Implement the Authentication Provider

```python
# auth.py
import json
import os
from typing import Any

import requests

from quack_core.integrations.core import BaseAuthProvider, AuthResult


class ExampleServiceAuth(BaseAuthProvider):
    """Authentication provider for ExampleService."""

    @property
    def name(self) -> str:
        """Name of the authentication provider."""
        return "ExampleService"

    def authenticate(self) -> AuthResult:
        """Authenticate with ExampleService."""
        # First, try to load existing credentials
        credentials = self._load_credentials()
        if credentials and self._validate_token(credentials.get("token")):
            self.authenticated = True
            return AuthResult.success_result(
                token=credentials.get("token"),
                expiry=credentials.get("expiry"),
                message="Using existing credentials",
                credentials_path=self.credentials_file,
            )

        # Otherwise, authenticate with service
        try:
            # In a real implementation, you would get these from user input or config
            username = os.environ.get("EXAMPLE_SERVICE_USERNAME", "")
            password = os.environ.get("EXAMPLE_SERVICE_PASSWORD", "")
            
            if not username or not password:
                return AuthResult.error_result(
                    error="Missing authentication credentials",
                    message="Please set EXAMPLE_SERVICE_USERNAME and EXAMPLE_SERVICE_PASSWORD",
                )
            
            # Make authentication request
            response = requests.post(
                "https://api.example.com/auth",
                json={"username": username, "password": password},
            )
            
            if response.status_code != 200:
                return AuthResult.error_result(
                    error=f"Authentication failed with status {response.status_code}",
                    message=response.text,
                )
                
            # Extract token information
            auth_data = response.json()
            token = auth_data.get("access_token")
            expiry = auth_data.get("expires_at")
            
            if not token:
                return AuthResult.error_result(
                    error="No token in authentication response",
                )
                
            # Save credentials for future use
            self._save_token_data(token, expiry)
            
            self.authenticated = True
            return AuthResult.success_result(
                token=token,
                expiry=expiry,
                message="Successfully authenticated",
                credentials_path=self.credentials_file,
            )
        except requests.RequestException as e:
            return AuthResult.error_result(
                error=f"Authentication request failed: {str(e)}",
            )
        except Exception as e:
            return AuthResult.error_result(
                error=f"Authentication failed: {str(e)}",
            )

    def refresh_credentials(self) -> AuthResult:
        """Refresh ExampleService credentials."""
        credentials = self._load_credentials()
        if not credentials or not credentials.get("refresh_token"):
            return AuthResult.error_result(
                error="No refresh token available",
            )
            
        try:
            # Make refresh request
            response = requests.post(
                "https://api.example.com/auth/refresh",
                json={"refresh_token": credentials.get("refresh_token")},
            )
            
            if response.status_code != 200:
                return AuthResult.error_result(
                    error=f"Token refresh failed with status {response.status_code}",
                    message=response.text,
                )
                
            # Extract token information
            auth_data = response.json()
            token = auth_data.get("access_token")
            expiry = auth_data.get("expires_at")
            
            if not token:
                return AuthResult.error_result(
                    error="No token in refresh response",
                )
                
            # Save new tokens
            self._save_token_data(
                token, 
                expiry,
                auth_data.get("refresh_token", credentials.get("refresh_token")),
            )
            
            return AuthResult.success_result(
                token=token,
                expiry=expiry,
                message="Successfully refreshed token",
                credentials_path=self.credentials_file,
            )
        except requests.RequestException as e:
            return AuthResult.error_result(
                error=f"Refresh request failed: {str(e)}",
            )
        except Exception as e:
            return AuthResult.error_result(
                error=f"Token refresh failed: {str(e)}",
            )

    def get_credentials(self) -> object:
        """Get the current authentication credentials."""
        return self._load_credentials() or {}

    def save_credentials(self) -> bool:
        """Save credentials to file."""
        # This is usually handled by _save_token_data
        return True
        
    def _load_credentials(self) -> dict[str, Any] | None:
        """Load credentials from file."""
        if not self.credentials_file or not os.path.exists(self.credentials_file):
            return None
            
        try:
            with open(self.credentials_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, OSError) as e:
            self.logger.error(f"Failed to load credentials: {e}")
            return None
            
    def _save_token_data(
        self, token: str, expiry: int | None = None, refresh_token: str | None = None
    ) -> bool:
        """Save token data to credentials file."""
        if not self.credentials_file:
            self.logger.warning("No credentials file specified, cannot save tokens")
            return False
            
        # Ensure directory exists
        self._ensure_credentials_directory()
        
        # Prepare credentials data
        credentials = {
            "token": token,
            "expiry": expiry,
        }
        
        if refresh_token:
            credentials["refresh_token"] = refresh_token
            
        try:
            with open(self.credentials_file, "w") as f:
                json.dump(credentials, f)
            return True
        except (IOError, OSError) as e:
            self.logger.error(f"Failed to save credentials: {e}")
            return False
            
    def _validate_token(self, token: str | None) -> bool:
        """Validate that a token is still valid."""
        if not token:
            return False
            
        # In a real implementation, you might check expiry time
        # or make a test request to the API
        
        # For this example, just check that the token exists
        return True
```

### Step 3: Implement the Configuration Provider

```python
# config.py
from typing import Any

from quack_core.integrations.core import BaseConfigProvider


class ExampleServiceConfig(BaseConfigProvider):
    """Configuration provider for ExampleService."""

    @property
    def name(self) -> str:
        """Name of the configuration provider."""
        return "ExampleService"

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate ExampleService configuration."""
        required_keys = ["api_url"]
        
        if not all(key in config for key in required_keys):
            self.logger.error(
                f"Missing required configuration keys: "
                f"{[key for key in required_keys if key not in config]}"
            )
            return False
            
        # Validate API URL format
        api_url = config.get("api_url", "")
        if not api_url.startswith(("http://", "http://")):
            self.logger.error(f"Invalid API URL format: {api_url}")
            return False
            
        return True

    def get_default_config(self) -> dict[str, Any]:
        """Get default ExampleService configuration."""
        return {
            "api_url": "https://api.example.com/v1",
            "timeout_seconds": 30,
            "max_retries": 3,
            "retry_delay": 1.0,
        }
```

### Step 4: Implement the API Client

```python
# client.py
import time
from typing import Any, Dict, List, Optional

import requests


class ExampleServiceClient:
    """Client for the ExampleService API."""

    def __init__(
        self,
        api_url: str,
        token: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize the ExampleService client."""
        self.api_url = api_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def set_token(self, token: str) -> None:
        """Set the authentication token."""
        self.token = token
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def list_resources(self, resource_type: str) -> List[Dict[str, Any]]:
        """List resources of a specific type."""
        endpoint = f"{self.api_url}/{resource_type}"
        response = self._make_request("GET", endpoint)
        return response.json().get("items", [])

    def get_resource(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        """Get a specific resource by ID."""
        endpoint = f"{self.api_url}/{resource_type}/{resource_id}"
        response = self._make_request("GET", endpoint)
        return response.json()

    def create_resource(
        self, resource_type: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new resource."""
        endpoint = f"{self.api_url}/{resource_type}"
        response = self._make_request("POST", endpoint, json=data)
        return response.json()

    def update_resource(
        self, resource_type: str, resource_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing resource."""
        endpoint = f"{self.api_url}/{resource_type}/{resource_id}"
        response = self._make_request("PUT", endpoint, json=data)
        return response.json()

    def delete_resource(self, resource_type: str, resource_id: str) -> bool:
        """Delete a resource."""
        endpoint = f"{self.api_url}/{resource_type}/{resource_id}"
        response = self._make_request("DELETE", endpoint)
        return response.status_code in (200, 204)

    def _make_request(
        self, method: str, url: str, **kwargs: Any
    ) -> requests.Response:
        """Make an HTTP request with retries."""
        kwargs.setdefault("timeout", self.timeout)

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.request(method, url, **kwargs)
                
                # Check for successful response
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                # Last attempt, re-raise the exception
                if attempt == self.max_retries:
                    raise
                    
                # For certain status codes, don't retry
                if isinstance(e, requests.HTTPError) and e.response.status_code in (401, 403, 404):
                    raise
                    
                # Wait before retrying
                time.sleep(self.retry_delay * attempt)
                
                        # This should never be reached due to the raise in the loop
        raise RuntimeError("Unexpected error in request retry logic")


### Step 5: Implement the Integration Service

```python
# service.py
from typing import Any, Dict, List, Optional

from quack_core.integrations.core import (
    AuthProviderProtocol,
    BaseIntegrationService, 
    ConfigProviderProtocol,
    IntegrationResult,
)

from .auth import ExampleServiceAuth
from .client import ExampleServiceClient
from .config import ExampleServiceConfig


class ExampleServiceIntegration(BaseIntegrationService):
    """Integration for ExampleService."""

    def __init__(
        self,
        config_provider: Optional[ConfigProviderProtocol] = None,
        auth_provider: Optional[AuthProviderProtocol] = None,
        config_path: Optional[str] = None,
        log_level: int = None,
    ) -> None:
        """Initialize the ExampleService integration."""
        # Create default providers if not provided
        if config_provider is None:
            config_provider = ExampleServiceConfig(log_level=log_level)
            
        if auth_provider is None:
            auth_provider = ExampleServiceAuth(log_level=log_level)
        
        super().__init__(
            config_provider=config_provider,
            auth_provider=auth_provider,
            config_path=config_path,
            log_level=log_level,
        )
        
        self.client = None

    @property
    def name(self) -> str:
        """Name of the integration."""
        return "ExampleService"
    
    @property
    def version(self) -> str:
        """Version of the integration."""
        return "1.0.0"
    
    def initialize(self) -> IntegrationResult:
        """Initialize the ExampleService integration."""
        # Call the base initialization first
        init_result = super().initialize()
        if not init_result.success:
            return init_result
            
        try:
            # Validate configuration
            if not self.config:
                return IntegrationResult.error_result(
                    "Configuration is not available"
                )
                
            api_url = self.config.get("api_url")
            if not api_url:
                return IntegrationResult.error_result(
                    "API URL is not configured"
                )
                
            # Get authentication token
            if self.auth_provider:
                auth_result = self.auth_provider.get_credentials()
                token = getattr(auth_result, "token", None)
                
                if not token and hasattr(auth_result, "get"):
                    # Handle the case where get_credentials returns a dict
                    token = auth_result.get("token")
            else:
                token = None
                
            # Initialize API client
            self.client = ExampleServiceClient(
                api_url=api_url,
                token=token,
                timeout=self.config.get("timeout_seconds", 30),
                max_retries=self.config.get("max_retries", 3),
                retry_delay=self.config.get("retry_delay", 1.0),
            )
            
            self._initialized = True
            return IntegrationResult.success_result(
                message="ExampleService integration initialized successfully"
            )
        except Exception as e:
            return IntegrationResult.error_result(
                f"Failed to initialize ExampleService integration: {str(e)}"
            )
    
    def is_available(self) -> bool:
        """Check if the ExampleService integration is available."""
        return self._initialized and self.client is not None
    
    def list_resources(self, resource_type: str) -> IntegrationResult[List[Dict[str, Any]]]:
        """List resources of a specific type."""
        # Ensure integration is initialized
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
            
        try:
            resources = self.client.list_resources(resource_type)
            return IntegrationResult.success_result(
                content=resources,
                message=f"Listed {len(resources)} {resource_type} resources"
            )
        except Exception as e:
            return IntegrationResult.error_result(
                f"Failed to list {resource_type} resources: {str(e)}"
            )
    
    def get_resource(
        self, resource_type: str, resource_id: str
    ) -> IntegrationResult[Dict[str, Any]]:
        """Get a specific resource by ID."""
        # Ensure integration is initialized
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
            
        try:
            resource = self.client.get_resource(resource_type, resource_id)
            return IntegrationResult.success_result(
                content=resource,
                message=f"Retrieved {resource_type} with ID {resource_id}"
            )
        except Exception as e:
            return IntegrationResult.error_result(
                f"Failed to get {resource_type} {resource_id}: {str(e)}"
            )
    
    def create_resource(
        self, resource_type: str, data: Dict[str, Any]
    ) -> IntegrationResult[Dict[str, Any]]:
        """Create a new resource."""
        # Ensure integration is initialized
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
            
        try:
            resource = self.client.create_resource(resource_type, data)
            return IntegrationResult.success_result(
                content=resource,
                message=f"Created new {resource_type}"
            )
        except Exception as e:
            return IntegrationResult.error_result(
                f"Failed to create {resource_type}: {str(e)}"
            )
    
    def update_resource(
        self, resource_type: str, resource_id: str, data: Dict[str, Any]
    ) -> IntegrationResult[Dict[str, Any]]:
        """Update an existing resource."""
        # Ensure integration is initialized
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
            
        try:
            resource = self.client.update_resource(resource_type, resource_id, data)
            return IntegrationResult.success_result(
                content=resource,
                message=f"Updated {resource_type} with ID {resource_id}"
            )
        except Exception as e:
            return IntegrationResult.error_result(
                f"Failed to update {resource_type} {resource_id}: {str(e)}"
            )
    
    def delete_resource(
        self, resource_type: str, resource_id: str
    ) -> IntegrationResult[bool]:
        """Delete a resource."""
        # Ensure integration is initialized
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
            
        try:
            success = self.client.delete_resource(resource_type, resource_id)
            if success:
                return IntegrationResult.success_result(
                    content=True,
                    message=f"Deleted {resource_type} with ID {resource_id}"
                )
            else:
                return IntegrationResult.error_result(
                    f"Failed to delete {resource_type} {resource_id}"
                )
        except Exception as e:
            return IntegrationResult.error_result(
                f"Failed to delete {resource_type} {resource_id}: {str(e)}"
            )
```

### Step 6: Register the Integration with QuackCore

```python
# __init__.py
from quack_core.integrations.core import registry

from .service import ExampleServiceIntegration


def create_integration():
    """Create and return an instance of the ExampleService integration."""
    return ExampleServiceIntegration()


# Automatically register the integration if imported directly
try:
    integration = create_integration()
    registry.register(integration)
except Exception as e:
    # Log error but don't crash on import
    import logging
    logging.getLogger(__name__).error(f"Failed to register integration: {e}")
```

### Step 7: Configure Package Discovery

In your `pyproject.toml` or `setup.py`:

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="example-service-integration",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "quack-core>=1.0.0",
        "requests>=2.25.0",
    ],
    entry_points={
        "quack_core.integrations": [
            "example_service = example_service_integration:create_integration",
        ],
    },
)
```

## Authentication in Integrations

Authentication is a critical part of most integrations. QuackCore provides a standardized way to handle different authentication methods.

### Common Authentication Methods

1. **Token-based Authentication**: Most APIs use token-based authentication
2. **OAuth**: For more complex authentication flows
3. **API Keys**: Simple key-based authentication
4. **Username/Password**: Basic authentication

### Implementing an OAuth Authentication Provider

Here's an example of implementing OAuth authentication:

```python
import json
import os
import time
import webbrowser
from typing import Any, Dict, Optional

import requests

from quack_core.integrations.core import BaseAuthProvider, AuthResult


class OAuthProvider(BaseAuthProvider):
    """OAuth-based authentication provider."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        auth_url: str,
        token_url: str,
        redirect_uri: str = "http://localhost:8080/callback",
        scope: str = "",
        credentials_file: Optional[str] = None,
        log_level: int = None,
    ) -> None:
        """Initialize the OAuth provider."""
        super().__init__(credentials_file=credentials_file, log_level=log_level)
        
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_url = auth_url
        self.token_url = token_url
        self.redirect_uri = redirect_uri
        self.scope = scope
        
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = 0
        
    @property
    def name(self) -> str:
        """Name of the authentication provider."""
        return "OAuth"
        
    def authenticate(self) -> AuthResult:
        """Authenticate with OAuth."""
        # First try to load existing tokens
        if self._load_tokens_from_file():
            # Check if the token is still valid
            if self.token_expiry > time.time() + 60:  # Add buffer
                self.authenticated = True
                return AuthResult.success_result(
                    token=self.access_token,
                    expiry=self.token_expiry,
                    message="Using existing OAuth token",
                    credentials_path=self.credentials_file,
                )
            
            # Token expired, try to refresh
            if self.refresh_token:
                refresh_result = self.refresh_credentials()
                if refresh_result.success:
                    return refresh_result
        
        # Need to perform OAuth flow
        try:
            # Step 1: Redirect to authorization URL
            auth_params = {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "scope": self.scope,
            }
            
            auth_query = "&".join(f"{k}={v}" for k, v in auth_params.items())
            auth_uri = f"{self.auth_url}?{auth_query}"
            
            print(f"Please visit the following URL to authorize the application:")
            print(auth_uri)
            
            # Try to open in browser if possible
            try:
                webbrowser.open(auth_uri)
            except Exception:
                pass
                
            # Step 2: Get authorization code from user
            auth_code = input("Enter the authorization code from the redirect URL: ")
            
            if not auth_code:
                return AuthResult.error_result(
                    error="No authorization code provided",
                )
            
            # Step 3: Exchange code for tokens
            token_data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": auth_code,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
            }
            
            response = requests.post(self.token_url, data=token_data)
            
            if response.status_code != 200:
                return AuthResult.error_result(
                    error=f"Token exchange failed with status {response.status_code}",
                    message=response.text,
                )
                
            token_response = response.json()
            
            # Step 4: Save tokens
            self.access_token = token_response.get("access_token")
            self.refresh_token = token_response.get("refresh_token")
            
            # Calculate expiry time
            expires_in = token_response.get("expires_in", 3600)
            self.token_expiry = int(time.time()) + expires_in
            
            if not self.access_token:
                return AuthResult.error_result(
                    error="No access token in response",
                )
                
            # Save tokens to file
            self._save_tokens_to_file()
            
            self.authenticated = True
            return AuthResult.success_result(
                token=self.access_token,
                expiry=self.token_expiry,
                message="OAuth authentication successful",
                credentials_path=self.credentials_file,
            )
        except Exception as e:
            return AuthResult.error_result(
                error=f"OAuth authentication failed: {str(e)}",
            )
            
    def refresh_credentials(self) -> AuthResult:
        """Refresh OAuth tokens."""
        if not self.refresh_token:
            return AuthResult.error_result(
                error="No refresh token available",
            )
            
        try:
            token_data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            }
            
            response = requests.post(self.token_url, data=token_data)
            
            if response.status_code != 200:
                return AuthResult.error_result(
                    error=f"Token refresh failed with status {response.status_code}",
                    message=response.text,
                )
                
            token_response = response.json()
            
            self.access_token = token_response.get("access_token")
            
            # Some providers return a new refresh token
            new_refresh_token = token_response.get("refresh_token")
            if new_refresh_token:
                self.refresh_token = new_refresh_token
                
            # Calculate expiry time
            expires_in = token_response.get("expires_in", 3600)
            self.token_expiry = int(time.time()) + expires_in
            
            if not self.access_token:
                return AuthResult.error_result(
                    error="No access token in refresh response",
                )
                
            # Save tokens to file
            self._save_tokens_to_file()
            
            return AuthResult.success_result(
                token=self.access_token,
                expiry=self.token_expiry,
                message="Token refreshed successfully",
                credentials_path=self.credentials_file,
            )
        except Exception as e:
            return AuthResult.error_result(
                error=f"Token refresh failed: {str(e)}",
            )
            
    def get_credentials(self) -> object:
        """Get the current authentication credentials."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expiry": self.token_expiry,
        }
        
    def save_credentials(self) -> bool:
        """Save credentials to file."""
        return self._save_tokens_to_file()
        
    def _load_tokens_from_file(self) -> bool:
        """Load tokens from file."""
        if not self.credentials_file or not os.path.exists(self.credentials_file):
            return False
            
        try:
            with open(self.credentials_file, "r") as f:
                tokens = json.load(f)
                
            self.access_token = tokens.get("access_token")
            self.refresh_token = tokens.get("refresh_token")
            self.token_expiry = tokens.get("expiry", 0)
            
            return bool(self.access_token)
        except (json.JSONDecodeError, IOError, OSError) as e:
            self.logger.error(f"Failed to load tokens: {e}")
            return False
            
    def _save_tokens_to_file(self) -> bool:
        """Save tokens to file."""
        if not self.credentials_file:
            self.logger.warning("No credentials file specified, cannot save tokens")
            return False
            
        # Ensure directory exists
        self._ensure_credentials_directory()
        
        tokens = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expiry": self.token_expiry,
        }
        
        try:
            with open(self.credentials_file, "w") as f:
                json.dump(tokens, f)
            return True
        except (IOError, OSError) as e:
            self.logger.error(f"Failed to save tokens: {e}")
            return False
```

### Securely Storing Credentials

QuackCore integrations should store credentials securely:

1. **Store in User Directory**: Use ~/.quack/ for credential storage
2. **Set Proper Permissions**: Restrict permissions on credential files
3. **Environment Variables**: For sensitive information like API keys
4. **Keyring Integration**: Consider using system keyring for sensitive tokens

## Configuration Management

Configuration management is another critical aspect of integrations. Here are some best practices:

### Configuration Hierarchy

QuackCore looks for configuration in the following order:

1. **Environment Variables**: `QUACK_INTEGRATION_CONFIG`
2. **Explicitly Provided Path**: Path provided to `load_config()`
3. **Project Directory**: `./config/integration_config.yaml`
4. **Working Directory**: `./quack_config.yaml`
5. **User Home Directory**: `~/.quack/config.yaml`

### Configuration Format

QuackCore uses YAML for configuration files. A typical configuration might look like:

```yaml
# quack_config.yaml
myservice:
  api_url: "https://api.example.com/v1"
  timeout_seconds: 60
  max_retries: 5

another_service:
  endpoint: "https://api.anotherservice.com"
  api_key: "${ANOTHER_SERVICE_API_KEY}"  # Environment variable reference
```

### Configuration Validation

Always validate configuration to provide helpful error messages:

```python
def validate_config(self, config: dict[str, Any]) -> bool:
    """Validate configuration data."""
    validation_errors = []
    
    # Check required fields
    required_fields = ["api_url", "api_key"]
    for field in required_fields:
        if field not in config:
            validation_errors.append(f"Missing required field: {field}")
    
    # Validate field formats
    if "api_url" in config:
        url = config["api_url"]
        if not url.startswith(("http://", "http://")):
            validation_errors.append(f"Invalid API URL format: {url}")
    
    # Log validation errors
    if validation_errors:
        for error in validation_errors:
            self.logger.error(f"Configuration validation error: {error}")
        return False
    
    return True
```

## Storage Integrations

Storage integrations provide standardized access to different storage backends. Here's an example of implementing a storage integration for AWS S3:

```python
import os
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from quack_core.integrations.core import (
    BaseIntegrationService,
    ConfigProviderProtocol,
    IntegrationResult,
    StorageIntegrationProtocol,
)
from quack_core.integrations.core.protocols import AuthProviderProtocol


class S3Integration(BaseIntegrationService, StorageIntegrationProtocol):
    """AWS S3 storage integration."""

    def __init__(
        self,
        config_provider: Optional[ConfigProviderProtocol] = None,
        auth_provider: Optional[AuthProviderProtocol] = None,
        config_path: Optional[str] = None,
        log_level: int = None,
    ) -> None:
        """Initialize the S3 integration."""
        super().__init__(
            config_provider=config_provider,
            auth_provider=auth_provider,
            config_path=config_path,
            log_level=log_level,
        )
        
        self.s3_client = None
        self.bucket_name = None
        
    @property
    def name(self) -> str:
        """Name of the integration."""
        return "S3Storage"
        
    @property
    def version(self) -> str:
        """Version of the integration."""
        return "1.0.0"
        
    def initialize(self) -> IntegrationResult:
        """Initialize the S3 integration."""
        # First, call the base initialization
        init_result = super().initialize()
        if not init_result.success:
            return init_result
            
        try:
            # Get configuration
            if not self.config:
                return IntegrationResult.error_result(
                    "S3 configuration is not available"
                )
                
            self.bucket_name = self.config.get("bucket_name")
            if not self.bucket_name:
                return IntegrationResult.error_result(
                    "S3 bucket name is not configured"
                )
                
            # Initialize S3 client
            session_kwargs = {}
            
            # Use configured region if available
            if region := self.config.get("region"):
                session_kwargs["region_name"] = region
                
            # Create session - this will use AWS credentials from environment
            # or ~/.aws/credentials
            session = boto3.Session(**session_kwargs)
            
            # Create S3 client
            client_kwargs = {}
            
            # Use configured endpoint if available (for S3-compatible services)
            if endpoint := self.config.get("endpoint_url"):
                client_kwargs["endpoint_url"] = endpoint
                
            self.s3_client = session.client("s3", **client_kwargs)
            
            # Test connection by checking if bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            
            return IntegrationResult.success_result(
                message=f"S3 integration initialized successfully with bucket {self.bucket_name}"
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "404":
                return IntegrationResult.error_result(
                    f"Bucket {self.bucket_name} does not exist"
                )
            elif error_code == "403":
                return IntegrationResult.error_result(
                    f"Forbidden access to bucket {self.bucket_name}"
                )
            else:
                return IntegrationResult.error_result(
                    f"S3 error: {str(e)}"
                )
        except Exception as e:
            return IntegrationResult.error_result(
                f"Failed to initialize S3 integration: {str(e)}"
            )
            
    def is_available(self) -> bool:
        """Check if the S3 integration is available."""
        return super().is_available() and self.s3_client is not None
        
    def upload_file(
        self, file_path: str, remote_path: Optional[str] = None
    ) -> IntegrationResult[str]:
        """Upload a file to S3."""
        # Ensure integration is initialized
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
            
        try:
            # Verify file exists
            if not os.path.exists(file_path):
                return IntegrationResult.error_result(
                    f"File not found: {file_path}"
                )
                
            # Determine remote path/key
            if not remote_path:
                remote_path = os.path.basename(file_path)
                
            # Upload file
            self.s3_client.upload_file(file_path, self.bucket_name, remote_path)
            
            # Generate S3 URL
            s3_url = f"s3://{self.bucket_name}/{remote_path}"
            
            return IntegrationResult.success_result(
                content=s3_url,
                message=f"File uploaded to {s3_url}"
            )
        except ClientError as e:
            return IntegrationResult.error_result(
                f"S3 upload error: {str(e)}"
            )
        except Exception as e:
            return IntegrationResult.error_result(
                f"Failed to upload file: {str(e)}"
            )
            
    def download_file(
        self, remote_id: str, local_path: Optional[str] = None
    ) -> IntegrationResult[str]:
        """Download a file from S3."""
        # Ensure integration is initialized
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
            
        try:
            # Parse S3 URL if provided
            if remote_id.startswith("s3://"):
                parts = remote_id.replace("s3://", "").split("/", 1)
                
                if len(parts) < 2:
                    return IntegrationResult.error_result(
                        f"Invalid S3 URL: {remote_id}"
                    )
                    
                bucket, key = parts
                
                if bucket != self.bucket_name:
                    self.logger.warning(
                        f"URL bucket {bucket} differs from configured bucket {self.bucket_name}"
                    )
            else:
                # Treat as key directly
                key = remote_id
                
            # Determine local path
            if not local_path:
                local_path = os.path.basename(key)
                
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
            
            # Download file
            self.s3_client.download_file(self.bucket_name, key, local_path)
            
            return IntegrationResult.success_result(
                content=local_path,
                message=f"File downloaded to {local_path}"
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "404":
                return IntegrationResult.error_result(
                    f"Object {remote_id} not found"
                )
            else:
                return IntegrationResult.error_result(
                    f"S3 download error: {str(e)}"
                )
        except Exception as e:
            return IntegrationResult.error_result(
                f"Failed to download file: {str(e)}"
            )
            
    def list_files(
        self, remote_path: Optional[str] = None, pattern: Optional[str] = None
    ) -> IntegrationResult[List[Dict[str, Any]]]:
        """List files in S3 bucket."""
        # Ensure integration is initialized
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
            
        try:
            # Prepare list objects parameters
            params = {"Bucket": self.bucket_name}
            
            if remote_path:
                # Ensure path ends with "/" for prefix
                if not remote_path.endswith("/"):
                    remote_path += "/"
                    
                params["Prefix"] = remote_path
                
            # List objects
            response = self.s3_client.list_objects_v2(**params)
            
            # Extract file information
            files = []
            for obj in response.get("Contents", []):
                # Skip directories (objects ending with /)
                key = obj.get("Key", "")
                if key.endswith("/"):
                    continue
                    
                # Apply pattern filter if provided
                if pattern and not self._match_pattern(key, pattern):
                    continue
                    
                files.append({
                    "name": os.path.basename(key),
                    "path": key,
                    "size": obj.get("Size", 0),
                    "last_modified": obj.get("LastModified"),
                    "url": f"s3://{self.bucket_name}/{key}",
                })
                
            return IntegrationResult.success_result(
                content=files,
                message=f"Listed {len(files)} files"
            )
        except ClientError as e:
            return IntegrationResult.error_result(
                f"S3 list error: {str(e)}"
            )
        except Exception as e:
            return IntegrationResult.error_result(
                f"Failed to list files: {str(e)}"
            )
            
    def create_folder(
        self, folder_name: str, parent_path: Optional[str] = None
    ) -> IntegrationResult[str]:
        """Create a folder in S3 bucket."""
        # Ensure integration is initialized
        init_error = self._ensure_initialized()
        if init_error:
            return init_error
            
        try:
            # Prepare folder path
            if parent_path:
                # Ensure parent path ends with "/"
                if not parent_path.endswith("/"):
                    parent_path += "/"
                    
                folder_path = f"{parent_path}{folder_name}/"
            else:
                folder_path = f"{folder_name}/"
                
            # Create an empty object with the folder path
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=folder_path,
                Body="",
            )
            
            return IntegrationResult.success_result(
                content=folder_path,
                message=f"Created folder {folder_path}"
            )
        except ClientError as e:
            return IntegrationResult.error_result(
                f"S3 create folder error: {str(e)}"
            )
        except Exception as e:
            return IntegrationResult.error_result(
                f"Failed to create folder: {str(e)}"
            )
            
    def _match_pattern(self, filename: str, pattern: str) -> bool:
        """Match a filename against a glob pattern."""
        import fnmatch
        return fnmatch.fnmatch(filename, pattern)
```

## Testing Integrations

Testing is essential for reliable integrations. Here's how to effectively test QuackCore integrations:

### Unit Testing

Unit tests should test individual components in isolation:

```python
import unittest
from unittest.mock import MagicMock, patch

from quack_core.integrations.core import IntegrationResult

from myintegration.service import MyServiceIntegration


class TestMyServiceIntegration(unittest.TestCase):
    """Tests for MyServiceIntegration."""
    
    def setUp(self):
        """Set up test environment."""
        # Create mock config provider
        self.mock_config = MagicMock()
        self.mock_config.name = "MyService"
        self.mock_config.load_config.return_value.success = True
        self.mock_config.load_config.return_value.content = {
            "api_url": "https://api.example.com",
            "timeout_seconds": 10,
        }
        
        # Create mock auth provider
        self.mock_auth = MagicMock()
        self.mock_auth.name = "MyService"
        self.mock_auth.authenticate.return_value.success = True
        self.mock_auth.get_credentials.return_value = {"token": "test_token"}
        
        # Create integration with mocked dependencies
        self.integration = MyServiceIntegration(
            config_provider=self.mock_config,
            auth_provider=self.mock_auth,
        )
        
    def test_initialization(self):
        """Test initialization process."""
        # Call initialize
        result = self.integration.initialize()
        
        # Check result
        self.assertTrue(result.success)
        self.assertIsNotNone(result.message)
        
        # Verify config provider was called
        self.mock_config.load_config.assert_called_once()
        
        # Verify auth provider was called
        self.mock_auth.authenticate.assert_called_once()
        
    def test_list_resources_success(self):
        """Test successful resource listing."""
        # Mock the API client
        self.integration.initialize()
        self.integration.client = MagicMock()
        self.integration.client.list_resources.return_value = [
            {"id": "1", "name": "Resource 1"},
            {"id": "2", "name": "Resource 2"},
        ]
        
        # Call the method
        result = self.integration.list_resources("items")
        
        # Check result
        self.assertTrue(result.success)
        self.assertEqual(len(result.content), 2)
        self.assertEqual(result.content[0]["name"], "Resource 1")
        
        # Verify client method was called
        self.integration.client.list_resources.assert_called_once_with("items")
        
    def test_list_resources_error(self):
        """Test error handling in resource listing."""
        # Mock the API client
        self.integration.initialize()
        self.integration.client = MagicMock()
        self.integration.client.list_resources.side_effect = Exception("API error")
        
        # Call the method
        result = self.integration.list_resources("items")
        
        # Check result
        self.assertFalse(result.success)
        self.assertIsNone(result.content)
        self.assertIn("API error", result.error)
        
    def test_not_initialized(self):
        """Test behavior when not initialized."""
        # Create new integration without initialization
        integration = MyServiceIntegration()
        
        # Call a method without initializing
        result = integration.list_resources("items")
        
        # Check result
        self.assertFalse(result.success)
```

### Integration Testing

Integration tests verify interactions with actual external services:

```python
import os
import unittest

from quack_core.integrations.core import registry

from myintegration.service import MyServiceIntegration


class TestMyServiceIntegrationLive(unittest.TestCase):
    """Live integration tests for MyServiceIntegration.
    
    These tests require actual credentials and will access the live API.
    Skip them unless you have proper test credentials.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Skip tests if no credentials
        if not os.environ.get("MY_SERVICE_API_KEY"):
            raise unittest.SkipTest("Missing MY_SERVICE_API_KEY env variable")
            
        # Create and initialize integration
        cls.integration = MyServiceIntegration()
        result = cls.integration.initialize()
        
        if not result.success:
            raise unittest.SkipTest(f"Failed to initialize integration: {result.error}")
            
    def test_list_resources_live(self):
        """Test listing resources from the live API."""
        # Call the method
        result = self.integration.list_resources("items")
        
        # Check result
        self.assertTrue(result.success)
        self.assertIsNotNone(result.content)
        
    def test_create_and_delete_resource_live(self):
        """Test creating and deleting a resource on the live API."""
        # Create a resource
        test_data = {"name": "Test Resource", "description": "Created by test"}
        create_result = self.integration.create_resource("items", test_data)
        
        # Check create result
        self.assertTrue(create_result.success)
        self.assertIsNotNone(create_result.content)
        
        # Get the resource ID
        resource_id = create_result.content.get("id")
        self.assertIsNotNone(resource_id)
        
        try:
            # Verify resource exists
            get_result = self.integration.get_resource("items", resource_id)
            self.assertTrue(get_result.success)
            
            # Verify resource data
            self.assertEqual(get_result.content.get("name"), "Test Resource")
        finally:
            # Clean up - delete the resource
            delete_result = self.integration.delete_resource("items", resource_id)
            self.assertTrue(delete_result.success)
```

### Mock and Patch

Use mock or patching to test without hitting real services:

```python
@patch("requests.Session.request")
def test_api_error_handling(self, mock_request):
    """Test handling of API errors."""
    # Configure the mock to return an error
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"
    mock_response.raise_for_status.side_effect = requests.HTTPError("Forbidden")
    
    mock_request.return_value = mock_response
    
    # Initialize and call method
    self.integration.initialize()
    result = self.integration.list_resources("items")
    
    # Verify error was handled properly
    self.assertFalse(result.success)
    self.assertIn("Forbidden", result.error)
```

## Best Practices

Follow these best practices for creating robust QuackCore integrations:

### Error Handling

Always use proper error handling:

```python
def perform_operation(self) -> IntegrationResult:
    """Perform a complex operation."""
    # Ensure initialization
    init_error = self._ensure_initialized()
    if init_error:
        return init_error
        
    try:
        # Perform the operation
        # ...
    except ConnectionError as e:
        # Network-specific error
        return IntegrationResult.error_result(
            f"Connection error: {str(e)}"
        )
    except TimeoutError as e:
        # Timeout-specific error
        return IntegrationResult.error_result(
            f"Operation timed out: {str(e)}"
        )
    except Exception as e:
        # Generic fallback
        self.logger.exception("Unexpected error during operation")
        return IntegrationResult.error_result(
            f"Operation failed: {str(e)}"
        )
```

### Logging

Use logging appropriately:

```python
def initialize(self) -> IntegrationResult:
    """Initialize the integration."""
    self.logger.info(f"Initializing {self.name} integration")
    
    # Debug level for configuration details (omit sensitive info)
    self.logger.debug(f"Using API URL: {self.config.get('api_url')}")
    
    try:
        # Initialization code...
        
        self.logger.info(f"{self.name} integration initialized successfully")
        return IntegrationResult.success_result(
            message=f"{self.name} integration initialized successfully"
        )
    except Exception as e:
        self.logger.error(f"Initialization failed: {e}")
        # For debugging, include more details
        self.logger.debug(f"Initialization error details", exc_info=True)
        return IntegrationResult.error_result(
            f"Failed to initialize {self.name} integration: {str(e)}"
        )
```

### Dependency Injection

Use dependency injection for better testability:

```python
def create_example_integration(
    config_path: Optional[str] = None,
    custom_auth_provider: Optional[AuthProviderProtocol] = None,
    custom_config_provider: Optional[ConfigProviderProtocol] = None,
) -> ExampleIntegration:
    """Create an instance of the Example integration with customizable dependencies."""
    # Use custom providers if provided, otherwise create defaults
    auth_provider = custom_auth_provider or ExampleAuthProvider()
    config_provider = custom_config_provider or ExampleConfigProvider()
    
    # Create integration with specified dependencies
    return ExampleIntegration(
        auth_provider=auth_provider,
        config_provider=config_provider,
        config_path=config_path,
    )
```

### Retry Logic

Implement retry logic for transient failures:

```python
def api_request_with_retry(self, method: str, endpoint: str, **kwargs) -> dict:
    """Make an API request with retry logic."""
    max_retries = self.config.get("max_retries", 3)
    retry_delay = self.config.get("retry_delay", 1.0)
    
    for attempt in range(1, max_retries + 1):
        try:
            response = self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json()
        except (requests.ConnectionError, requests.Timeout) as e:
            # Network errors are retryable
            if attempt == max_retries:
                raise
                
            self.logger.warning(
                f"Request failed (attempt {attempt}/{max_retries}): {e}"
            )
            
            # Exponential backoff
            sleep_time = retry_delay * (2 ** (attempt - 1))
            time.sleep(sleep_time)
        except requests.HTTPError as e:
            # Only retry specific HTTP status codes
            if e.response.status_code in (429, 500, 502, 503, 504):
                if attempt == max_retries:
                    raise
                    
                self.logger.warning(
                    f"Request failed with status {e.response.status_code} "
                    f"(attempt {attempt}/{max_retries})"
                )
                
                # Check for Retry-After header
                retry_after = e.response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    time.sleep(int(retry_after))
                else:
                    time.sleep(retry_delay * (2 ** (attempt - 1)))
            else:
                # Non-retryable status code
                raise
```

## Common Pitfalls

Avoid these common mistakes when creating integrations:

### Not Checking Initialization

Always check if the integration is initialized before performing operations:

```python
# Bad - No initialization check
def perform_action(self, data: dict) -> IntegrationResult:
    """Perform an action without checking initialization."""
    try:
        # This will fail if the client is not initialized
        result = self.client.do_something(data)
        return IntegrationResult.success_result(content=result)
    except Exception as e:
        return IntegrationResult.error_result(str(e))

# Good - With initialization check
def perform_action(self, data: dict) -> IntegrationResult:
    """Perform an action with initialization check."""
    # Ensure integration is initialized
    init_error = self._ensure_initialized()
    if init_error:
        return init_error
        
    try:
        result = self.client.do_something(data)
        return IntegrationResult.success_result(content=result)
    except Exception as e:
        return IntegrationResult.error_result(str(e))
```

### Inconsistent Error Handling

Maintain consistent error handling across all methods:

```python
# Bad - Inconsistent error handling
def method1(self) -> IntegrationResult:
    """Method with proper error handling."""
    try:
        # Do something
        return IntegrationResult.success_result(content="Success")
    except Exception as e:
        return IntegrationResult.error_result(str(e))
        
def method2(self) -> dict:
    """Method without proper error handling."""
    # Directly returns dict or raises exception
    return self.client.do_something()

# Good - Consistent error handling
def method1(self) -> IntegrationResult:
    """Method with proper error handling."""
    try:
        # Do something
        return IntegrationResult.success_result(content="Success")
    except Exception as e:
        return IntegrationResult.error_result(str(e))
        
def method2(self) -> IntegrationResult:
    """Method with proper error handling."""
    try:
        result = self.client.do_something()
        return IntegrationResult.success_result(content=result)
    except Exception as e:
        return IntegrationResult.error_result(str(e))
```

### Ignoring Authentication Refresh

Remember to handle credential refreshing:

```python
# Bad - No token refresh handling
def perform_authenticated_action(self) -> IntegrationResult:
    """Perform an action without handling token refresh."""
    try:
        # This will fail if the token is expired
        result = self.client.authenticated_action()
        return IntegrationResult.success_result(content=result)
    except Exception as e:
        return IntegrationResult.error_result(str(e))

# Good - With token refresh handling
def perform_authenticated_action(self) -> IntegrationResult:
    """Perform an action with token refresh handling."""
    try:
        try:
            # First attempt
            result = self.client.authenticated_action()
            return IntegrationResult.success_result(content=result)
        except AuthenticationError:
            # Token might be expired, try to refresh
            if self.auth_provider:
                refresh_result = self.auth_provider.refresh_credentials()
                if refresh_result.success and refresh_result.token:
                    # Update client with new token
                    self.client.set_token(refresh_result.token)
                    
                    # Retry the operation
                    result = self.client.authenticated_action()
                    return IntegrationResult.success_result(content=result)
            
            # If we get here, refresh failed or no auth provider
            return IntegrationResult.error_result("Authentication failed")
    except Exception as e:
        return IntegrationResult.error_result(str(e))
```

### Exposing Sensitive Information

Be careful not to expose sensitive information:

```python
# Bad - Logging sensitive information
def authenticate(self) -> AuthResult:
    """Authenticate with sensitive information exposed."""
    token = "secret_token_12345"
    self.logger.info(f"Authenticated with token: {token}")
    return AuthResult.success_result(token=token)

# Good - Not logging sensitive information
def authenticate(self) -> AuthResult:
    """Authenticate without exposing sensitive information."""
    token = "secret_token_12345"
    self.logger.info("Authentication successful")
    self.logger.debug("Authentication successful with token: ***")
    return AuthResult.success_result(token=token)
```

## Integration Discovery

QuackCore provides multiple ways to discover and register integrations:

### Entry Points

The preferred way is using Python entry points:

```python
# setup.py
from setuptools import setup

setup(
    name="my-integration",
    version="1.0.0",
    packages=["my_integration"],
    entry_points={
        "quack_core.integrations": [
            "my_service = my_integration:create_integration",
        ],
    },
)
```

### Module Loading

You can also load integrations from modules:

```python
from quack_core.integrations.core import registry

# Load integrations from a module
integrations = registry.load_integration_module("my_integration.service")
```

### Manual Registration

For testing or special cases, register manually:

```python
from quack_core.integrations.core import registry
from my_integration.service import MyServiceIntegration

# Create integration instance
integration = MyServiceIntegration()

# Register with registry
registry.register(integration)

# Check if registered
if registry.is_registered("MyService"):
    print("MyService integration is registered!")
```

## Frequently Asked Questions

### How do I access registered integrations?

You can access integrations through the registry:

```python
from quack_core.integrations.core import registry

# Get integration by name
storage = registry.get_integration("S3Storage")
if storage:
    print(f"Found {storage.name} v{storage.version}")
    
# Get all storage integrations
storage_integrations = list(registry.get_integration_by_type(StorageIntegrationProtocol))
print(f"Found {len(storage_integrations)} storage integrations")
```

### How do I handle different authentication types?

Implement different authentication providers for different auth types:

- `OAuthProvider` for OAuth authentication
- `ApiKeyProvider` for API key authentication
- `BasicAuthProvider` for username/password authentication

Then use the appropriate provider when creating your integration.

### How do I create a configuration schema?

You can use Pydantic models to define configuration schemas:

```python
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class S3Config(BaseModel):
    """Configuration schema for S3 storage integration."""
    
    bucket_name: str = Field(
        description="S3 bucket name for storage",
    )
    
    region: Optional[str] = Field(
        default=None,
        description="AWS region for the bucket",
    )
    
    endpoint_url: Optional[str] = Field(
        default=None,
        description="Custom endpoint URL for S3-compatible services",
    )
    
    prefix: Optional[str] = Field(
        default="",
        description="Prefix for all stored objects",
    )
    
    @field_validator("bucket_name")
    def validate_bucket_name(cls, v: str) -> str:
        """Validate S3 bucket name."""
        if not v:
            raise ValueError("Bucket name cannot be empty")
        if len(v) < 3 or len(v) > 63:
            raise ValueError("Bucket name must be between 3 and 63 characters")
        return v
```

### How do I test an integration?

See the [Testing Integrations](#testing-integrations) section for detailed examples.

### How do I debug integration issues?

Enable debug logging to see detailed information:

```python
import logging
from quack_core.core.logging import LogLevel, LOG_LEVELS
from quack_core.integrations.core import registry

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Create registry with debug logging
integration_registry = registry.IntegrationRegistry(log_level=LOG_LEVELS[LogLevel.DEBUG])

# Or enable debug on an existing integration
integration = registry.get_integration("MyService")
if integration:
    integration.logger.setLevel(logging.DEBUG)
```

### Can I create custom integration types?

Yes, you can define new protocols by extending the base protocols:

```python
from typing import Protocol, runtime_checkable
from quack_core.integrations.core.protocols import IntegrationProtocol
from quack_core.integrations.core.results import IntegrationResult

@runtime_checkable
class MessagingIntegrationProtocol(IntegrationProtocol, Protocol):
    """Protocol for messaging integrations."""

    def send_message(self, recipient: str, message: str) -> IntegrationResult[str]:
        """Send a message to a recipient."""
        ...

    def receive_messages(self, limit: int = 10) -> IntegrationResult[list[dict]]:
        """Receive messages."""
        ...
```