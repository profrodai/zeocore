# QuackCore Errors Documentation

This guide provides comprehensive documentation for the `quack_core.core.errors` module, which offers robust error handling capabilities for QuackTools and plugins in the QuackVerse ecosystem.

## Table of Contents

1. [Introduction](#introduction)
2. [Error Hierarchy](#error-hierarchy)
3. [Basic Error Usage](#basic-error-usage)
4. [Common Error Types](#common-error-types)
5. [Error Handlers](#error-handlers)
6. [Decorators](#decorators)
7. [Best Practices](#best-practices)
8. [Advanced Usage](#advanced-usage)
9. [Full Examples](#full-examples)

## Introduction

The `quack_core.core.errors` module provides consistent, informative error handling across the QuackVerse. It allows you to:

- Create descriptive, context-rich errors
- Properly handle and display errors to users
- Wrap standard Python exceptions with QuackVerse-specific information
- Create decorators for consistent error handling behavior

By using this module, you'll ensure that your QuackTool integrates seamlessly with the larger QuackVerse ecosystem, providing users with consistent and helpful error messages.

## Error Hierarchy

All QuackCore errors inherit from a common base class, creating a unified error system:

```
Exception (Python built-in)
└── QuackError
    ├── QuackIOError
    │   ├── QuackFileNotFoundError
    │   ├── QuackPermissionError
    │   ├── QuackFileExistsError
    │   └── QuackFormatError
    ├── QuackValidationError
    ├── QuackConfigurationError
    ├── QuackPluginError
    ├── QuackBaseAuthError
    └── QuackIntegrationError
        ├── QuackAuthenticationError
        ├── QuackApiError
        │   └── QuackQuotaExceededError
```

This hierarchy allows you to catch errors at different levels of specificity, depending on your needs.

## Basic Error Usage

### Importing Error Classes

You can import all error classes directly from the top-level `quack_core.core.errors` module:

```python
from quack_core.core.errors import (
    QuackError,
    QuackIOError,
    QuackFileNotFoundError,
    # and other specific errors as needed
)
```

### Raising Basic Errors

Here's how to raise a basic `QuackError`:

```python
from quack_core.core.errors import QuackError


def my_function():
    if something_went_wrong:
        raise QuackError("Something went wrong")
```

### Adding Context to Errors

One of the key benefits of QuackCore errors is the ability to attach context:

```python
from quack_core.core.errors import QuackError


def process_data(data_id, user_id):
    if data_not_found:
        raise QuackError(
            "Could not find the requested data",
            context={"data_id": data_id, "user_id": user_id}
        )
```

### Wrapping Original Exceptions

You can wrap original exceptions to provide more context while preserving the original error:

```python
from quack_core.core.errors import QuackError


def safe_process():
    try:
        result = some_risky_operation()
        return result
    except Exception as e:
        raise QuackError("Failed during data processing", original_error=e)
```

## Common Error Types

### IO Errors

For file-related operations:

```python
from quack_core.core.errors import QuackFileNotFoundError, QuackPermissionError


def read_config(path):
    if not path.exists():
        raise QuackFileNotFoundError(path)

    if not os.access(path, os.R_OK):
        raise QuackPermissionError(path, "read")

    # Read the file...
```

### Validation Errors

For data validation failures:

```python
from quack_core.core.errors import QuackValidationError


def validate_user_data(data):
    errors = {}

    if "username" not in data:
        errors.setdefault("username", []).append("Username is required")

    if "email" in data and "@" not in data["email"]:
        errors.setdefault("email", []).append("Invalid email format")

    if errors:
        raise QuackValidationError(
            "Validation failed for user data",
            errors=errors
        )
```

### Configuration Errors

For configuration issues:

```python
from quack_core.core.errors import QuackConfigurationError


def load_settings(config_path):
    try:
    # Load config...
    except YAMLError as e:
        raise QuackConfigurationError(
            "Invalid YAML in configuration file",
            config_path=config_path,
            original_error=e
        )

    if "required_setting" not in config:
        raise QuackConfigurationError(
            "Missing required configuration",
            config_path=config_path,
            config_key="required_setting"
        )
```

### Integration Errors

For external API and service interactions:

```python
from quack_core.core.errors import QuackApiError, QuackAuthenticationError


def call_external_api(service_name, endpoint):
    try:
        response = requests.get(f"https://api.example.com/{endpoint}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise QuackAuthenticationError(
                "Authentication failed",
                service=service_name,
                original_error=e
            )
        elif e.response.status_code == 429:
            raise QuackQuotaExceededError(
                "API rate limit exceeded",
                service=service_name,
                original_error=e
            )
        else:
            raise QuackApiError(
                f"API request failed: {str(e)}",
                service=service_name,
                status_code=e.response.status_code,
                api_method=endpoint,
                original_error=e
            )
```

## Error Handlers

The `ErrorHandler` class provides utilities for formatting and displaying errors:

### Creating an Error Handler

```python
from quack_core.core.errors.handlers import ErrorHandler
from rich.console import Console

# Create with default settings (outputs to stderr)
handler = ErrorHandler()

# Or create with a custom console
my_console = Console(width=100)
custom_handler = ErrorHandler(console=my_console)
```

### Formatting Errors

```python
from quack_core.core.errors import QuackError
from quack_core.core.errors.handlers import ErrorHandler

try:
    # Some code that might raise an error
    raise QuackError("Something went wrong", context={"important_value": 42})
except Exception as e:
    handler = ErrorHandler()

    # Get formatted error string
    formatted = handler.format_error(e)
    print(formatted)
```

### Printing Errors

```python
from quack_core.core.errors.handlers import ErrorHandler


def my_function():
    handler = ErrorHandler()

    try:
        # Code that might fail
        risky_operation()
    except Exception as e:
        # Print error with a custom title and traceback
        handler.print_error(
            e,
            title="Error in my_function",
            show_traceback=True
        )
```

### Handling Errors (Print and Optionally Exit)

```python
from quack_core.core.errors.handlers import ErrorHandler


def critical_operation():
    handler = ErrorHandler()

    try:
        # Important code that should not fail
        result = risky_but_important_operation()
        return result
    except Exception as e:
        # Handle error, show traceback, and exit with code 1
        handler.handle_error(
            e,
            title="Critical Failure",
            show_traceback=True,
            exit_code=1
        )
```

### Using the Global Error Handler

For convenience, a global error handler instance is provided:

```python
from quack_core.core.errors.handlers import global_error_handler

try:
    # Some operation
    result = risky_operation()
except Exception as e:
    global_error_handler.print_error(e)
```

## Decorators

### The `handle_errors` Decorator

The module provides a handy decorator for consistent error handling:

```python
from quack_core.core.errors.handlers import handle_errors


# Basic usage - catches all exceptions
@handle_errors()
def simple_function():
    # Code that might fail...
    return result


# Catch specific errors, with custom title and traceback
@handle_errors(
    error_types=(ValueError, TypeError),
    title="Input Error",
    show_traceback=True
)
def process_input(data):
    # Process the data...
    return processed_data


# Critical function that exits on error
@handle_errors(exit_code=1)
def critical_function():
    # Important code that shouldn't fail
    return result
```

### The `wrap_io_errors` Decorator

This decorator specifically wraps standard IO exceptions with QuackCore equivalents:

```python
from quack_core.core.errors.base import wrap_io_errors


@wrap_io_errors
def read_file(path):
    with open(path, 'r') as f:
        return f.read()
```

If `read_file` encounters a `FileNotFoundError`, it will be converted to a `QuackFileNotFoundError`, etc.

## Best Practices

### Use Specific Error Types

Always use the most specific error type available:

```python
# Good - provides specific error type and context
raise QuackPermissionError(path, "write")

# Less helpful - generic error with less context
raise QuackError("Permission denied")
```

### Include Contextual Information

Always include relevant context with your errors:

```python
# Good - includes all relevant information
raise QuackApiError(
    "Failed to fetch user data",
    service="User API",
    status_code=404,
    api_method="get_user"
)

# Less helpful - missing important context
raise QuackError("API call failed")
```

### Preserve Original Exceptions

When catching and re-raising exceptions, preserve the original:

```python
try:
    # Some operation
    result = api_client.get_data()
except ClientError as e:
    # Good - preserves original error
    raise QuackApiError("API request failed", original_error=e)
```

### Use Rich for Terminal Output

The `ErrorHandler` class uses Rich for formatted output. Take advantage of this for error display:

```python
try:
    # Complex operation
    result = complex_operation()
except Exception as e:
    handler = ErrorHandler()
    handler.print_error(e, show_traceback=True)
    # No need for additional print statements
```

## Advanced Usage

### Getting Caller Information

The `ErrorHandler` can retrieve information about the calling function:

```python
from quack_core.core.errors.handlers import ErrorHandler


def troubleshoot_function():
    handler = ErrorHandler()
    caller_info = handler.get_caller_info()
    print(f"Called from {caller_info['function']} in {caller_info['file']}")
```

### Custom Error Formatting

You can extend the `ErrorHandler` class to customize error formatting:

```python
from quack_core.core.errors.handlers import ErrorHandler


class MyErrorHandler(ErrorHandler):
    def format_error(self, error):
        # Get the standard formatting
        formatted = super().format_error(error)

        # Add custom formatting
        if hasattr(error, 'custom_attribute'):
            formatted += f"\nCustom info: {error.custom_attribute}"

        return formatted
```

### Creating Custom QuackErrors

For your plugin-specific errors, inherit from the appropriate QuackError base class:

```python
from quack_core.core.errors import QuackPluginError


class MyPluginConfigError(QuackPluginError):
    def __init__(
            self,
            message,
            config_option=None,
            original_error=None
    ):
        context = {}
        if config_option:
            context["config_option"] = config_option

        super().__init__(
            message,
            plugin_name="my_plugin",
            original_error=original_error
        )
        self.context.update(context)
        self.config_option = config_option
```

## Full Examples

### Example 1: File Processing with Error Handling

```python
from pathlib import Path
from quack_core.core.errors import QuackFileNotFoundError, QuackFormatError
from quack_core.core.errors.handlers import handle_errors


@handle_errors(show_traceback=True)
def process_json_file(file_path):
    path = Path(file_path)

    # Check if file exists
    if not path.exists():
        raise QuackFileNotFoundError(path)

    # Try to parse JSON
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise QuackFormatError(
            path,
            "JSON",
            message="Invalid JSON format",
            original_error=e
        )

    # Process the data
    return transform_data(data)
```

### Example 2: API Integration with Error Handling

```python
import requests
from quack_core.core.errors import (
    QuackAuthenticationError,
    QuackApiError,
    QuackQuotaExceededError
)
from quack_core.core.errors.handlers import ErrorHandler


class ApiClient:
    def __init__(self, api_key, service_name):
        self.api_key = api_key
        self.service_name = service_name
        self.error_handler = ErrorHandler()

    def get_data(self, endpoint, params=None):
        try:
            response = requests.get(
                f"https://api.example.com/{endpoint}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code

            if status_code == 401:
                raise QuackAuthenticationError(
                    "Authentication failed - check API key",
                    service=self.service_name,
                    original_error=e
                )
            elif status_code == 429:
                raise QuackQuotaExceededError(
                    "API rate limit exceeded",
                    service=self.service_name,
                    resource=endpoint,
                    original_error=e
                )
            else:
                raise QuackApiError(
                    f"API request failed: {e.response.text}",
                    service=self.service_name,
                    status_code=status_code,
                    api_method=endpoint,
                    original_error=e
                )
        except requests.exceptions.RequestException as e:
            raise QuackApiError(
                f"API connection error: {str(e)}",
                service=self.service_name,
                api_method=endpoint,
                original_error=e
            )

    def process_with_error_handling(self, endpoint, params=None):
        try:
            return self.get_data(endpoint, params)
        except Exception as e:
            self.error_handler.print_error(
                e,
                title=f"Error accessing {self.service_name}",
                show_traceback=True
            )
            return None
```

### Example 3: Configuration Validation with Error Handling

```python
import yaml
from pathlib import Path
from quack_core.core.errors import (
    QuackConfigurationError,
    QuackFileNotFoundError,
    QuackFormatError,
    QuackValidationError
)
from quack_core.core.errors.base import wrap_io_errors


class ConfigManager:
    @wrap_io_errors
    def load_config(self, config_path):
        path = Path(config_path)

        if not path.exists():
            raise QuackFileNotFoundError(path)

        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise QuackFormatError(
                path,
                "YAML",
                message="Invalid YAML format in configuration file",
                original_error=e
            )

        return config

    def validate_config(self, config, config_path):
        errors = {}

        # Check required sections
        if "api" not in config:
            errors.setdefault("api", []).append("Missing API section")
        elif "key" not in config["api"]:
            errors.setdefault("api.key", []).append("Missing API key")

        if "settings" not in config:
            errors.setdefault("settings", []).append("Missing settings section")

        # Validate specific settings
        if "settings" in config:
            settings = config["settings"]

            if "max_retries" in settings and not isinstance(settings["max_retries"], int):
                errors.setdefault("settings.max_retries", []).append(
                    "max_retries must be an integer"
                )

        if errors:
            raise QuackValidationError(
                "Configuration validation failed",
                path=config_path,
                errors=errors
            )

        return True

    def get_validated_config(self, config_path):
        try:
            config = self.load_config(config_path)
            self.validate_config(config, config_path)
            return config
        except (QuackFileNotFoundError, QuackFormatError) as e:
            raise QuackConfigurationError(
                f"Failed to load configuration: {str(e)}",
                config_path=config_path,
                original_error=e
            )
```