# QuackCore Logging Documentation

## Overview

The `quack_core.core.logging` module provides a standardized approach to logging across all QuackCore components. It extends Python's built-in logging capabilities with features specifically designed for QuackCore applications, including:

- Consistent log formatting across all QuackCore modules
- Support for "Teaching Mode" with specialized log formatting
- Environment-based configuration
- Multiple output destinations (console and file)
- Color-coded console output based on log levels

This documentation will help you integrate and use the QuackCore logging system in your applications.

## Quick Start

### Basic Usage

The simplest way to use QuackCore logging is to import the default logger:

```python
from quack_core.core.logging import logger

# Standard log messages
logger.debug("Detailed information for debugging")
logger.info("General information about program execution")
logger.warning("Warning about potential issues")
logger.error("Error that prevents proper functioning")
logger.critical("Critical error that may cause program termination")
```

### Module-Specific Loggers

For better log organization, create a module-specific logger:

```python
from quack_core.core.logging import get_logger

# Create a logger with your module's name
logger = get_logger(__name__)

logger.info("This log will show the module name in the output")
```

### Teaching Mode Logs

To create logs that will be specially formatted when Teaching Mode is enabled:

```python
logger.info("[Teaching Mode] This explains how the algorithm works")
```

## Configuration

### Log Level

The log level can be set through:

1. Environment variable:
   ```bash
   export QUACKCORE_LOG_LEVEL=DEBUG
   ```

2. Programmatically when creating a logger:
   ```python
   import logging
   from quack_core.core.logging import configure_logger
   
   logger = configure_logger(name="my_module", level=logging.DEBUG)
   ```

Available log levels (from most to least verbose):
- `DEBUG`: Detailed information for diagnosing problems
- `INFO`: Confirmation that things are working as expected
- `WARNING`: Indication that something unexpected happened, but the program is still working
- `ERROR`: Due to a more serious problem, the program has not been able to perform some function
- `CRITICAL`: A serious error indicating the program may be unable to continue running

### Log File Output

To save logs to a file in addition to console output:

```python
from pathlib import Path
from quack_core.core.logging import configure_logger

log_path = Path("logs/my_application.log")
logger = configure_logger(name="my_module", log_file=log_path)

logger.info("This message will appear in both console and log file")
```

## Advanced Usage

### Creating Custom Loggers

For more specific configuration needs:

```python
from quack_core.core.logging import configure_logger

# Configure a custom logger
logger = configure_logger(
    name="custom_module",  # Module name
    level=None,  # Use environment variable or default
    log_file="logs/custom.log",  # Optional file output
    teaching_to_stdout=True  # Use stdout for Teaching Mode logs
)
```

### Log Level Constants

If you need to reference log level constants:

```python
from quack_core.core.logging import LOG_LEVELS, LogLevel

# Check current log level against a threshold
current_level = LOG_LEVELS[LogLevel.DEBUG]
if logger.level <= current_level:
    # Perform verbose logging _ops
    pass
```

## Teaching Mode Integration

The QuackCore logging system includes special support for "Teaching Mode," which provides educational information about the system's operation.

### Marking Teaching Mode Logs

To designate a log message as a Teaching Mode message:

```python
logger.info("[Teaching Mode] This is how the data processing works")
```

These messages will be specially formatted when Teaching Mode is enabled.

> Note: The Teaching Mode module is not yet implemented. Currently, Teaching Mode logs will receive basic formatting, but the full Teaching Mode functionality will be added in a future release.

### Using the Teaching Log Helper

You can also use the `log_teaching` helper function for Teaching Mode logs:

```python
from quack_core.core.logging import log_teaching

log_teaching(logger, "This is how the data processing works", level="INFO")
```

## Formatting

The QuackCore logging module uses a custom formatter (`TeachingAwareFormatter`) that:

1. Applies color coding based on log levels (in console output)
2. Enhances Teaching Mode logs with special formatting
3. Provides consistent timestamp formatting
4. Supports verbosity levels for Teaching Mode logs

The default format is: `YYYY-MM-DD HH:MM:SS [LEVEL] module_name: message`

### Colors in Console Output

Log level colors in console output:
- `DEBUG`: Blue
- `INFO`: Green
- `WARNING`: Yellow
- `ERROR`: Red
- `CRITICAL`: Bold Red

Teaching Mode logs have special color formatting:
- Standard Teaching Mode: Cyan with a duck emoji (🦆)
- Verbose Teaching Mode: Magenta with a duck emoji
- Debug Teaching Mode: Blue with a duck emoji

## Best Practices

### Use Module-Specific Loggers

Instead of using the general logger, create module-specific loggers to make log output more traceable:

```python
# In file: my_module/data_processor.py
from quack_core.core.logging import get_logger

logger = get_logger(__name__)  # Will create a logger named "my_module.data_processor"
```

### Choose Appropriate Log Levels

- `DEBUG`: Use for detailed troubleshooting information
- `INFO`: Use for general operational information
- `WARNING`: Use for unexpected situations that don't prevent operation
- `ERROR`: Use for failures that prevent specific operations
- `CRITICAL`: Use for severe failures that might lead to program termination

### Include Context in Log Messages

```python
# Less useful
logger.error("Failed to process data")

# More useful
logger.error(f"Failed to process data file {filename}: {str(error)}")
```

### Use Teaching Mode for Educational Content

When building components that would benefit from explaining their operation:

```python
logger.info("[Teaching Mode] Step 1: The algorithm sorts the input list")
logger.info("[Teaching Mode] Step 2: Binary search is applied to find the target value")
```

## Extending the Logger

### Custom Handlers

You can add additional handlers to a logger after it's configured:

```python
import logging
from quack_core.core.logging import get_logger
from quack_core.core.logging.formatter import TeachingAwareFormatter

logger = get_logger(__name__)

# Add a custom handler (e.g., for sending logs to a remote service)
custom_handler = logging.Handler()  # Replace with your actual handler
custom_handler.setFormatter(TeachingAwareFormatter())
logger.addHandler(custom_handler)
```

## Troubleshooting

### Multiple Log Messages

If you see duplicate log messages, check if you've added multiple handlers to the same logger or if logger propagation is enabled.

### Environment Variable Not Working

Ensure the environment variable is:
1. Correctly named (`QUACKCORE_LOG_LEVEL`)
2. Set to a valid level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`)
3. Set before your application starts

### No Colored Output

Colored output might not appear if:
1. Your terminal doesn't support ANSI color codes
2. You're viewing logs in a file (color codes are disabled for file output)
3. The formatter's `color_enabled` parameter was set to `False`

## API Reference

### Module: `quack_core.core.logging`

#### Functions

- `get_logger(name: str) -> logging.Logger`: Get a configured logger for a specific module
- `configure_logger(name: str | None = None, level: int | None = None, log_file: str | Path | None = None, teaching_to_stdout: bool = True) -> logging.Logger`: Configure and return a logger

#### Variables

- `logger`: Default logger for general quackcore usage
- `LOG_LEVELS`: Mapping from LogLevel enum values to logging module constants
- `LogLevel`: Enum for available log levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)

### Module: `quack_core.core.logging.config`

#### Functions

- `get_log_level() -> int`: Get the log level from environment variable or default to INFO
- `configure_logger(...)`: Configure and return a logger with the specified name
- `log_teaching(logger: Any, message: str, level: str = "INFO") -> None`: Log a teaching message with appropriate formatting

#### Classes

- `LogLevel(str, Enum)`: Enum for available log levels

### Module: `quack_core.core.logging.formatter`

#### Classes

- `TeachingAwareFormatter(logging.Formatter)`: Custom formatter that enhances log messages based on Teaching Mode status
- `Colors`: ANSI color codes for terminal output
- `VerbosityLevel(str, Enum)`: Enum for verbosity levels that may be used in Teaching Mode (`BASIC`, `VERBOSE`, `DEBUG`)

#### Functions

- `teaching_is_enabled() -> bool`: Check if Teaching Mode is enabled
- `teaching_get_level() -> VerbosityLevel`: Get the current Teaching Mode verbosity level