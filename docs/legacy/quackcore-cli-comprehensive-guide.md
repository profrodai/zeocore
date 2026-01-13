# QuackCore CLI Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
   - [Installation](#installation)
   - [Basic Usage](#basic-usage)
3. [Core Concepts](#core-concepts)
   - [CLI Context](#cli-context)
   - [CLI Options](#cli-options)
   - [CLI Bootstrapping](#cli-bootstrapping)
   - [Logging](#logging)
   - [Configuration](#configuration)
4. [User Interaction](#user-interaction)
   - [Text Formatting](#text-formatting)
   - [User Input](#user-input)
   - [Progress Reporting](#progress-reporting)
5. [Error Handling](#error-handling)
6. [Terminal Utilities](#terminal-utilities)
7. [Practical Examples](#practical-examples)
   - [Creating a Basic QuackTool](#creating-a-basic-quacktool)
   - [Working with Configuration](#working-with-configuration)
   - [Implementing Interactive Features](#implementing-interactive-features)
   - [Displaying Progress](#displaying-progress)
8. [Anti-Patterns and Best Practices](#anti-patterns-and-best-practices)
9. [Complete API Reference](#complete-api-reference)

## Introduction

The `quack_core.cli` package provides a comprehensive set of utilities for building command-line interface (CLI) applications that integrate with the QuackVerse ecosystem. This package ensures a consistent user experience across all QuackTools by providing standardized components for:

- Command-line argument handling
- Configuration management
- Logging setup
- User interaction (prompts, confirmations, progress reporting)
- Error handling
- Terminal operations

Whether you're building a simple CLI tool or a complex application with multiple commands, `quack_core.cli` provides the foundation you need to create professional-grade tools that adhere to QuackVerse standards.

## Getting Started

### Installation

The `quack_core.cli` module is part of the main `quackcore` package. To use it, you need to have QuackCore installed:

```bash
pip install quack-core
```

### Basic Usage

Here's a minimal example of creating a QuackTool using the QuackCore CLI framework:

```python
#!/usr/bin/env python3
from quack_core.cli import init_cli_env, print_success

def main():
    # Initialize the CLI environment
    ctx = init_cli_env(app_name="my-first-quacktool")
    
    # Access the logger
    ctx.logger.info("Starting my first QuackTool")
    
    # Perform your tool's functionality
    # ...
    
    # Display success message
    print_success("Operation completed successfully!")
    
if __name__ == "__main__":
    main()
```

This simple script:
1. Initializes the CLI environment with a proper context
2. Sets up logging with the application name
3. Uses the configured logger to output information
4. Displays a formatted success message

## Core Concepts

### CLI Context

The `QuackContext` class is the central hub for QuackCore CLI applications. It encapsulates all the runtime information needed by CLI commands, including:

- Configuration (`QuackConfig`)
- Logger (`logging.Logger`)
- Base directory (`Path`)
- Current environment (development, test, production)
- Debug and verbose flags
- Working directory (`Path`)
- Extra data (additional context that might be needed by specific commands)

The context object is created during bootstrap and is immutable, ensuring that your application's state remains consistent throughout its execution.

#### Example: Working with the CLI Context

```python
from quack_core.cli import init_cli_env

def my_command(ctx):
    # Access configuration
    database_url = ctx.config.database.url
    
    # Use the logger
    ctx.logger.info(f"Connecting to database at: {database_url}")
    
    # Check environment
    if ctx.environment == "production":
        ctx.logger.warning("Running in production mode")
    
    # Add extra data to the context without modifying the original
    new_ctx = ctx.with_extra(command_start_time=time.time())
    
    # Access the new data
    start_time = new_ctx.extra["command_start_time"]
```

### CLI Options

The `CliOptions` class provides a structured way to define and handle command-line options that affect bootstrapping behavior. It includes common options like:

- `config_path`: Path to the configuration file
- `log_level`: Logging level
- `debug`: Enable debug mode
- `verbose`: Enable verbose output
- `quiet`: Suppress non-error output
- `environment`: Override the environment
- `base_dir`: Override the base directory
- `no_color`: Disable colored output

You can use this class with the `from_cli_options` function to initialize the CLI environment from parsed options.

#### Example: Handling CLI Options

```python
import argparse
from quack_core.cli import CliOptions, from_cli_options

def parse_args():
    parser = argparse.ArgumentParser(description="My QuackTool")
    parser.add_argument("--config", dest="config_path", help="Path to config file")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Convert argparse namespace to CliOptions
    options = CliOptions(
        config_path=args.config_path,
        log_level=args.log_level,
        debug=args.debug,
        verbose=args.verbose
    )
    
    # Initialize CLI environment from options
    ctx = from_cli_options(options, app_name="my-quacktool")
    
    # Now use the context
    # ...
```

Alternatively, you can use the utility function `resolve_cli_args` to parse common CLI arguments directly:

```python
import sys
from quack_core.cli import resolve_cli_args, CliOptions, from_cli_options

def main():
    # Parse CLI arguments
    args_dict = resolve_cli_args(sys.argv[1:])
    
    # Convert to CliOptions
    options = CliOptions(
        config_path=args_dict.get("config-path"),
        log_level=args_dict.get("log-level"),
        debug=args_dict.get("debug", False),
        verbose=args_dict.get("verbose", False),
        quiet=args_dict.get("quiet", False)
    )
    
    # Initialize CLI environment
    ctx = from_cli_options(options)
    
    # Now use the context
    # ...
```

### CLI Bootstrapping

The bootstrap process sets up the CLI environment, including configuration loading, logging setup, and context creation. The main entry point is the `init_cli_env` function, which accepts various parameters to customize the bootstrapping process.

#### Example: Bootstrapping with Different Parameters

```python
from quack_core.cli import init_cli_env

# Basic initialization with default settings
ctx = init_cli_env()

# Initialization with custom settings
ctx = init_cli_env(
    config_path="./config/myapp.yaml",
    log_level="DEBUG",
    debug=True,
    verbose=True,
    environment="development",
    app_name="my-advanced-quacktool"
)

# Initialization with CLI argument overrides
ctx = init_cli_env(
    cli_args={"database": {"host": "custom-host", "port": 5432}}
)
```

The bootstrap process follows a specific precedence order when resolving settings:
1. Command-line overrides (highest priority)
2. Environment variables
3. Configuration file settings
4. Default values (lowest priority)

### Logging

QuackCore CLI includes a comprehensive logging system that integrates with Python's standard logging module. The `setup_logging` function configures logging based on CLI flags and configuration settings.

Key features of the logging system:
- Consistent log formatting across all QuackTools
- Support for log files and console output
- Dynamic log level adjustment based on flags (debug, quiet)
- Named logger creation for component-specific logging

#### Example: Setting Up Logging

```python
from quack_core.cli import setup_logging
from quack_core.interfaces.cli.utils.options import LogLevel

# Set up logging with explicit parameters
root_logger, get_logger = setup_logging(
    log_level=LogLevel("DEBUG"),
    debug=True,
    quiet=False,
    logger_name="my-quacktool"
)

# Create a component-specific logger
component_logger = get_logger("database")
component_logger.info("Database component initialized")

# The main logger is also available
root_logger.warning("This is a warning message")
```

In most cases, you don't need to call `setup_logging` directly, as it's handled by `init_cli_env`. Instead, you use the logger provided by the context:

```python
from quack_core.cli import init_cli_env

def main():
    ctx = init_cli_env(app_name="my-quacktool")
    
    # Use the main logger
    ctx.logger.info("Application started")
    
    # Create component loggers as needed
    db_logger = ctx.logger.getChild("database")
    db_logger.debug("Connecting to database...")
```

### Configuration

QuackCore CLI provides utilities for loading and managing configuration in CLI applications. The configuration system handles precedence between CLI options, environment variables, and configuration files.

The main configuration functions:
- `load_config`: Load configuration with standard precedence
- `find_project_root`: Find the project root directory

#### Example: Working with Configuration

```python
from quack_core.cli import load_config, find_project_root
from pathlib import Path

# Find the project root
project_root = find_project_root()

# Load configuration with a specific path
config = load_config(config_path=project_root / "config" / "app.yaml")

# Load configuration with environment override
config = load_config(environment="production")

# Load configuration with CLI argument overrides
config = load_config(cli_overrides={"database": {"port": 5432}})
```

As with logging, you typically don't need to call these functions directly, as they're handled by `init_cli_env`. Instead, you access the configuration through the context:

```python
from quack_core.cli import init_cli_env

def main():
    ctx = init_cli_env()
    
    # Access configuration
    db_url = ctx.config.database.url
    log_file = ctx.config.logging.file
    debug_mode = ctx.config.general.debug
    
    # Use the configuration
    # ...
```

## User Interaction

### Text Formatting

QuackCore CLI includes utilities for formatting text output in CLI applications, including color formatting, tables, and styled messages.

#### Key Formatting Functions:

- `colorize`: Add ANSI color and style to text
- `print_error`: Print an error message
- `print_warning`: Print a warning message
- `print_success`: Print a success message
- `print_info`: Print an informational message
- `print_debug`: Print a debug message
- `table`: Format data as a text table
- `dict_to_table`: Convert a dictionary to a table

#### Example: Formatting Text

```python
from quack_core.cli import colorize, print_error, print_success, table

# Colorize text
highlighted = colorize("Important information", fg="blue", bold=True)
print(f"Please note: {highlighted}")

# Print formatted messages
print_success("Operation completed successfully!")
print_error("Failed to connect to the server")

# Create a table
headers = ["Name", "Age", "Role"]
rows = [
    ["Alice", "28", "Developer"],
    ["Bob", "34", "Manager"],
    ["Charlie", "22", "Intern"]
]
user_table = table(headers, rows, title="Team Members")
print(user_table)

# Convert dictionary to table
user_info = {
    "Name": "Alice",
    "Email": "alice@example.com",
    "Role": "Developer",
    "Team": "Backend"
}
info_table = dict_to_table(user_info, title="User Information")
print(info_table)
```

### User Input

QuackCore CLI provides functions for interactive CLI features like prompts, confirmations, and user input collection.

#### Key User Input Functions:

- `confirm`: Ask for user confirmation
- `ask`: Ask the user for input with optional validation
- `ask_choice`: Ask the user to select from a list of choices
- `with_spinner`: Decorator to show a spinner while a function is running

#### Example: User Input

```python
from quack_core.cli import confirm, ask, ask_choice, with_spinner
import time

# Get confirmation
if confirm("Do you want to proceed?", default=True):
    print("Proceeding...")
else:
    print("Aborting...")

# Get user input with validation
def validate_email(email):
    return "@" in email and "." in email.split("@")[1]

email = ask(
    prompt="Enter your email",
    validate=validate_email,
    required=True
)

# Get a password (hidden input)
password = ask(
    prompt="Enter your password",
    hide_input=True,
    required=True
)

# Ask user to select from choices
role = ask_choice(
    prompt="Select your role:",
    choices=["Developer", "Manager", "Admin"],
    default=0
)

# Use a spinner for a long-running function
@with_spinner(desc="Processing data")
def process_data():
    # Simulate a long operation
    time.sleep(3)
    return "Data processed successfully"

result = process_data()
print(result)
```

### Progress Reporting

QuackCore CLI includes classes and functions for displaying progress information in CLI applications.

#### Key Progress Reporting Components:

- `ProgressReporter`: Simple progress reporter for loops and iterative processes
- `SimpleProgress`: Simple progress tracker for iterables
- `show_progress`: Show a progress bar for an iterable

#### Example: Progress Reporting

```python
from quack_core.cli import ProgressReporter, show_progress
import time

# Using ProgressReporter directly
reporter = ProgressReporter(total=100, desc="Downloading", unit="MB")
reporter.start()

for i in range(100):
    # Simulate work
    time.sleep(0.05)
    reporter.update(i + 1, message=f"Downloading file {i+1}")

reporter.finish(message="Download completed")

# Using show_progress with an iterable
items = range(50)
for item in show_progress(items, desc="Processing", unit="items"):
    # Simulate work
    time.sleep(0.1)
```

## Error Handling

QuackCore CLI provides utilities for handling and formatting errors in CLI applications, with proper output formatting and consistent error messaging.

#### Key Error Handling Functions:

- `format_cli_error`: Format an error for CLI display
- `handle_errors`: Decorator to handle errors in a function
- `ensure_single_instance`: Ensure only one instance of a CLI application is running
- `get_cli_info`: Get information about the CLI environment

#### Example: Error Handling

```python
from quack_core.cli import handle_errors, get_cli_info, format_cli_error
from quack_core.core.errors import QuackError


# Use the handle_errors decorator to catch exceptions
@handle_errors(error_types=QuackError, title="Database Error", exit_code=1)
def connect_to_database(url):
    # Simulate a connection error
    if "invalid" in url:
        raise QuackError("Failed to connect to the database")
    return True


# Try to connect
connect_to_database("invalid-url")  # Will catch the error and exit

# Get CLI environment information
cli_info = get_cli_info()
for key, value in cli_info.items():
    print(f"{key}: {value}")

# Format an error for display
try:
    # Some operation that might fail
    raise ValueError("Invalid input")
except Exception as e:
    formatted_error = format_cli_error(e)
    print(formatted_error)
```

### Ensuring Single Instance

Sometimes you want to make sure only one instance of your CLI application is running:

```python
from quack_core.cli import ensure_single_instance

def main():
    # Ensure this is the only instance running
    if not ensure_single_instance("my-quacktool"):
        print("Another instance is already running!")
        return
    
    # Continue with normal execution
    # ...
```

## Terminal Utilities

QuackCore CLI provides functions for working with terminal capabilities, such as getting terminal size and checking for color support.

#### Key Terminal Utilities:

- `get_terminal_size`: Get the terminal size
- `supports_color`: Check if the terminal supports color output
- `truncate_text`: Truncate text to a maximum length with an indicator

#### Example: Terminal Utilities

```python
from quack_core.cli import get_terminal_size, supports_color, truncate_text

# Get terminal dimensions
columns, lines = get_terminal_size()
print(f"Terminal size: {columns}x{lines}")

# Check if color is supported
if supports_color():
    print("This terminal supports color output")
else:
    print("This terminal does not support color output")

# Truncate long text
long_text = "This is a very long text that needs to be truncated to fit in the available space"
truncated = truncate_text(long_text, 30)
print(truncated)  # "This is a very long text that..."
```

## Practical Examples

### Creating a Basic QuackTool

Let's create a simple QuackTool that demonstrates the basic concepts of the `quack_core.cli` module:

```python
#!/usr/bin/env python3
"""
hello_quack.py - A simple QuackTool example
"""

import sys
from quack_core.cli import (
    init_cli_env,
    print_success,
    print_error,
    confirm,
    ask,
    handle_errors
)
from quack_core.core.errors import QuackError


@handle_errors(error_types=Exception, title="Hello Quack Error", exit_code=1)
def main():
    # Initialize the CLI environment
    ctx = init_cli_env(app_name="hello-quack")

    # Log that we're starting
    ctx.logger.info("Hello Quack starting up")

    # Check if we're in debug mode
    if ctx.debug:
        ctx.logger.debug("Running in debug mode")

    # Get user input
    name = ask("What's your name", default="Anonymous Quacker")

    # Print a greeting
    print_success(f"Hello, {name}! Welcome to the QuackVerse!")

    # Confirm if user wants to continue
    if not confirm("Do you want to see the configuration?", default=True):
        print("Goodbye!")
        return

    # Show configuration info
    log_level = ctx.config.logging.level or "INFO"
    print(f"Current log level: {log_level}")
    print(f"Running in environment: {ctx.environment}")
    print(f"Base directory: {ctx.base_dir}")

    # Demonstrate an error
    if confirm("Do you want to see an error?", default=False):
        raise QuackError("This is a test error")

    print_success("Operation completed successfully!")


if __name__ == "__main__":
    main()
```

### Working with Configuration

This example demonstrates more advanced configuration usage:

```python
#!/usr/bin/env python3
"""
config_example.py - Demonstrates configuration capabilities
"""

import argparse
import sys
from pathlib import Path
from quack_core.cli import (
    init_cli_env,
    CliOptions,
    from_cli_options,
    print_info,
    print_success,
    dict_to_table
)

def parse_args():
    parser = argparse.ArgumentParser(description="Configuration Example")
    parser.add_argument("--config", dest="config_path", help="Path to config file")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--environment", help="Set environment")
    parser.add_argument("--list", action="store_true", help="List configuration")
    parser.add_argument("--section", help="Show specific config section")
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Create CliOptions from arguments
    options = CliOptions(
        config_path=args.config_path and Path(args.config_path),
        debug=args.debug,
        environment=args.environment
    )
    
    # Bootstrap CLI environment
    ctx = from_cli_options(options, app_name="config-example")
    
    # Log startup information
    ctx.logger.info(f"Configuration loaded from: {ctx.config.source_path or 'defaults'}")
    ctx.logger.info(f"Running in environment: {ctx.environment}")
    
    if args.list:
        # Convert config to dict and display as table
        config_dict = ctx.config.model_dump()
        print_info("Current Configuration:")
        
        if args.section and args.section in config_dict:
            # Show only requested section
            section_dict = config_dict[args.section]
            print(dict_to_table(section_dict, title=f"Section: {args.section}"))
        else:
            # Show all sections
            for section, values in config_dict.items():
                if isinstance(values, dict):
                    print(dict_to_table(values, title=f"Section: {section}"))
    
    print_success("Configuration example completed")

if __name__ == "__main__":
    main()
```

### Implementing Interactive Features

This example demonstrates various interactive features:

```python
#!/usr/bin/env python3
"""
interactive_example.py - Demonstrates interactive features
"""

import time
from quack_core.cli import (
    init_cli_env,
    ask,
    ask_choice,
    confirm,
    with_spinner,
    print_success,
    print_error,
    print_info,
    colorize,
    table
)

# Function with a spinner
@with_spinner(desc="Processing")
def long_running_task():
    time.sleep(3)
    return "Task completed"

def main():
    # Initialize CLI environment
    ctx = init_cli_env(app_name="interactive-example")
    
    print_info("Welcome to the Interactive Example!")
    
    # Get user input
    name = ask("What's your name", required=True)
    
    # Validate user input
    def validate_age(age_str):
        try:
            age = int(age_str)
            return 0 < age < 120
        except ValueError:
            return False
    
    age = ask(
        "How old are you",
        validate=validate_age,
        required=True
    )
    
    # Ask for a choice
    role = ask_choice(
        "Select your role:",
        choices=["Developer", "Admin", "User", "Manager"],
        default=0
    )
    
    # Ask for confirmation
    if not confirm(f"Confirm: You are {name}, {age} years old, and a {role}?", default=True):
        print_error("User information not confirmed")
        return
    
    # Show collected information in a table
    headers = ["Field", "Value"]
    rows = [
        ["Name", name],
        ["Age", age],
        ["Role", role]
    ]
    
    user_table = table(headers, rows, title="User Information")
    print(user_table)
    
    # Demonstrate spinner
    if confirm("Run a long task with spinner?", default=True):
        result = long_running_task()
        print_success(result)
    
    # Show colorized output
    print("\nHere's some " + 
          colorize("colorized", fg="red") + " " +
          colorize("output", fg="green", bold=True) + " " +
          colorize("for", fg="blue", underline=True) + " " +
          colorize("you!", fg="magenta", italic=True))
    
    print_success("Interactive example completed!")

if __name__ == "__main__":
    main()
```

### Displaying Progress

This example demonstrates progress reporting for long-running operations:

```python
#!/usr/bin/env python3
"""
progress_example.py - Demonstrates progress reporting
"""

import time
import random
from quack_core.cli import (
    init_cli_env,
    ProgressReporter,
    show_progress,
    ask_choice,
    print_success
)

def simulate_file_processing(reporter, num_files):
    """Simulate processing multiple files with detailed progress updates."""
    for i in range(num_files):
        # Simulate variable processing time
        process_time = random.uniform(0.1, 0.5)
        time.sleep(process_time)
        
        # Update progress with message
        file_name = f"file_{i+1}.data"
        reporter.update(i + 1, message=f"Processing {file_name}")

def simulate_download(reporter, total_size):
    """Simulate downloading a large file with byte updates."""
    downloaded = 0
    
    while downloaded < total_size:
        # Simulate variable download speed
        chunk_size = random.randint(1, 5)
        downloaded = min(downloaded + chunk_size, total_size)
        
        # Calculate percentage and simulate some delay
        percentage = int(downloaded * 100 / total_size)
        time.sleep(0.1)
        
        # Update progress with download information
        reporter.update(
            downloaded, 
            message=f"{downloaded}/{total_size} MB ({percentage}%)"
        )

def main():
    # Initialize CLI environment
    ctx = init_cli_env(app_name="progress-example")
    
    # Let user choose the example
    example = ask_choice(
        "Select an example:",
        choices=[
            "File processing with detailed progress",
            "Download simulation with byte tracking",
            "Simple iterable progress"
        ],
        default=0
    )
    
    if example == "File processing with detailed progress":
        # Create a progress reporter for file processing
        num_files = 20
        reporter = ProgressReporter(
            total=num_files,
            desc="Processing files",
            unit="files"
        )
        
        reporter.start()
        simulate_file_processing(reporter, num_files)
        reporter.finish(message="All files processed")
    
    elif example == "Download simulation with byte tracking":
        # Create a progress reporter for download
        total_size = 100  # MB
        reporter = ProgressReporter(
            total=total_size,
            desc="Downloading",
            unit="MB"
        )
        
        reporter.start()
        simulate_download(reporter, total_size)
        reporter.finish(message="Download complete")
    
    else:  # Simple iterable progress
        # Use show_progress with a range
        items = range(30)
        
        for item in show_progress(items, desc="Processing", unit="items"):
            # Simulate work
            time.sleep(0.2)
    
    print_success("Progress example completed!")

if __name__ == "__main__":
    main()
```

## Anti-Patterns and Best Practices

### Anti-Patterns to Avoid

#### 1. Direct Logger Creation Instead of Using Context

❌ **Anti-Pattern:**
```python
import logging

# Don't do this
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("my-app")
logger.info("Application started")
```

✅ **Best Practice:**
```python
from quack_core.cli import init_cli_env

# Do this instead
ctx = init_cli_env(app_name="my-app")
ctx.logger.info("Application started")
```

Why? The QuackCore logger ensures consistent formatting and behavior across all QuackTools, integrates with the configuration system, and handles file logging properly.

#### 2. Manual Terminal Output Formatting

❌ **Anti-Pattern:**
```python
# Don't do this
print("\033[31mError: Connection failed\033[0m")
print("\033[32mSuccess: Operation completed\033[0m")
```

✅ **Best Practice:**
```python
from quack_core.cli import print_error, print_success

# Do this instead
print_error("Connection failed")
print_success("Operation completed")
```

Why? The QuackCore formatting functions handle color support detection and consistent styling, ensuring your application works correctly in different terminal environments.

#### 3. Direct sys.exit Without Error Formatting

❌ **Anti-Pattern:**
```python
import sys

# Don't do this
def connect():
    try:
        # Connection code
        pass
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
```

✅ **Best Practice:**

```python
from quack_core.cli import handle_errors
from quack_core.core.errors import QuackError


# Do this instead
@handle_errors(error_types=Exception, title="Connection Error", exit_code=1)
def connect():
    # Connection code
    pass
```

Why? The `handle_errors` decorator provides consistent error formatting, proper logging, and a clean exit path.

#### 4. Manual Configuration Loading

❌ **Anti-Pattern:**
```python
import yaml
import os

# Don't do this
def load_my_config():
    config_path = os.environ.get("CONFIG_PATH", "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)
```

✅ **Best Practice:**
```python
from quack_core.cli import init_cli_env

# Do this instead
ctx = init_cli_env(config_path="config.yaml")
config = ctx.config
```

Why? QuackCore's configuration system handles file loading, environment variable overrides, command-line argument overrides, and normalized paths - providing a complete solution.

#### 5. Manual Progress Display

❌ **Anti-Pattern:**
```python
# Don't do this
total = 100
for i in range(total):
    progress = (i + 1) / total * 100
    print(f"\rProgress: {progress:.1f}%", end="")
    # Do work
print()  # Final newline
```

✅ **Best Practice:**
```python
from quack_core.cli import ProgressReporter

# Do this instead
reporter = ProgressReporter(total=100, desc="Processing")
reporter.start()
for i in range(100):
    # Do work
    reporter.update(i + 1)
reporter.finish()
```

Why? QuackCore's progress utilities handle terminal width, ETA calculation, and consistent formatting, providing a better user experience.

### Best Practices

#### 1. Initialize the CLI Environment Early

Always initialize the CLI environment at the beginning of your application to ensure logging, configuration, and other core services are available throughout.

```python
def main():
    # Initialize early
    ctx = init_cli_env(app_name="my-quacktool")
    
    # Use context throughout
    # ...
```

#### 2. Use Descriptive App Names

Use descriptive and unique app names when initializing the CLI environment to ensure logs and other resources are correctly identified.

```python
# Good: Descriptive and unique
ctx = init_cli_env(app_name="mycompany-data-processor")

# Bad: Generic and not unique
ctx = init_cli_env(app_name="tool")
```

#### 3. Gracefully Handle Errors

Use the error handling utilities to ensure errors are properly caught, formatted, and logged.

```python
from quack_core.cli import handle_errors

@handle_errors(error_types=(ConnectionError, TimeoutError), title="Network Error")
def fetch_data(url):
    # Network _ops
    pass
```

#### 4. Provide Feedback for Long Operations

Always provide feedback for operations that take more than a second or two.

```python
from quack_core.cli import with_spinner, ProgressReporter

@with_spinner(desc="Fetching data")
def fetch_data():
    # Long operation
    pass

# For _ops with quantifiable progress
def process_files(files):
    reporter = ProgressReporter(total=len(files), desc="Processing files")
    reporter.start()
    
    for i, file in enumerate(files):
        # Process the file
        reporter.update(i + 1, message=f"Processing {file.name}")
    
    reporter.finish(message="All files processed")
```

#### 5. Use Component-Specific Loggers

Create component-specific loggers for larger applications to make log filtering easier.

```python
def init_database_module(ctx):
    # Create a dedicated logger for the database component
    db_logger = ctx.logger.getChild("database")
    
    db_logger.info("Initializing database connection")
    # Database initialization logic
    db_logger.debug("Connection pool created with 5 connections")
```

#### 6. Follow Configuration Hierarchy

Remember the configuration precedence when debugging issues:
1. CLI arguments override everything
2. Environment variables override config file settings
3. Config file settings override defaults

This hierarchy helps understand where a particular setting is coming from.

#### 7. Keep Context Immutable

Never modify the context object directly. Use `with_extra` when you need to add data.

```python
# Good: Create a new context with additional data
def process_command(ctx, command_name):
    # Add command-specific data to context
    command_ctx = ctx.with_extra(command_name=command_name)
    
    # Use the new context
    execute_command(command_ctx)

# Bad: Don't do this
def process_command(ctx, command_name):
    # Don't modify context directly
    ctx.extra["command_name"] = command_name  # This would raise an error
```

#### 8. Handle Terminal Size Gracefully

Always handle terminal size gracefully, especially when displaying tables or other formatted output.

```python
from quack_core.cli import get_terminal_size, table

def display_results(results):
    # Get current terminal size
    columns, _ = get_terminal_size()
    
    # Create a table with appropriate width
    headers = ["ID", "Name", "Description"]
    rows = [[r.id, r.name, r.description] for r in results]
    
    # Pass max_width to ensure table fits in terminal
    result_table = table(headers, rows, max_width=columns)
    print(result_table)
```