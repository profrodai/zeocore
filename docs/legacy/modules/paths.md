# QuackCore Paths Module

The `quack_core.core.paths` module provides utilities for path resolution, project structure detection, and context inference in QuackCore projects. It builds upon the lower-level file system operations in `quack_core.core.fs` to provide project-aware path operations.

## Overview

The paths module provides a high-level API for:

- Finding project roots and source directories
- Resolving paths relative to project context
- Detecting project structure and content organization
- Converting between file paths and module names
- Working with content-specific directories

Unlike the `quack_core.core.fs` module, which provides low-level file system operations, the `paths` module understands QuackCore project structures and conventions.

## PathService

The main entry point for the paths module is the `PathService` class, which provides a comprehensive API for path operations. A global instance is available as `quack_core.core.paths.paths`.

```python
from quack_core.core.paths import service as paths

# Get the project root
result = paths.get_project_root()
if result.success:
    print(f"Project root: {result.path}")
else:
    print(f"Error: {result.error}")
```

### Result Types

Path operations return strongly-typed result objects:

- **`PathResult`**: Contains path resolution results with `success`, `path`, and `error` fields
- **`ContextResult`**: Contains context detection results with `success`, `context`, and `error` fields

These result types follow a consistent pattern, allowing you to check for success before accessing the result:

```python
from quack_core.core.paths import service as paths

result = paths.get_module_path("myproject.utils.helper")
if result.success:
    print(f"Module path: {result.path}")
else:
    print(f"Error: {result.error}")
```

## Basic Path Operations

### Finding Project Root

```python
from quack_core.core.paths import service as paths

result = paths.get_project_root()
if result.success:
    project_root = result.path
```

### Resolving Project Paths

```python
from quack_core.core.paths import service as paths

result = paths.resolve_project_path("src/module.py")
if result.success:
    absolute_path = result.path
```

### Getting Relative Paths

```python
from quack_core.core.paths import service as paths

result = paths.get_relative_path("/home/user/project/src/module.py")
if result.success:
    relative_path = result.path  # "src/module.py"
```

## Working with Project Structure

### Getting Known Directories

```python
from quack_core.core.paths import service as paths

# Get a specific known directory
result = paths.get_known_directory("src")
if result.success:
    src_dir = result.path

# List all known directories
known_dirs = paths.list_known_directories()
```

### Working with Content

```python
from quack_core.core.paths import service as paths

# Get a content directory
result = paths.get_content_dir("tutorials", "tests")
if result.success:
    tutorial_dir = result.path

# Infer current content
content_info = paths.infer_current_content()
if "type" in content_info:
    content_type = content_info["type"]
    content_name = content_info.get("name")
```

### Finding Special Directories

```python
from quack_core.core.paths import service as paths

# Find source directory
result = paths.find_source_directory()
if result.success:
    src_dir = result.path

# Find or create output directory
result = paths.find_output_directory(create=True)
if result.success:
    output_dir = result.path
```

## Module and Path Conversion

### Path to Module

```python
from quack_core.core.paths import service as paths

result = paths.resolve_content_module("/home/user/project/src/tutorials/tests/intro.py")
if result.success:
    module_name = result.path  # "tutorials.tests.intro"
```

### Module to Path

```python
from quack_core.core.paths import service as paths

result = paths.get_module_path("tutorials.tests.intro")
if result.success:
    file_path = result.path  # "/home/user/project/src/tutorials/tests/intro.py"
```

## Path Checking

### Inside Project Check

```python
from quack_core.core.paths import service as paths

if paths.is_inside_project("/home/user/project/src/module.py"):
    print("Path is inside the project")
```

### Path Exists in Known Directory

```python
from quack_core.core.paths import service as paths

if paths.path_exists_in_known_dir("assets", "images/logo.png"):
    print("Asset exists")
```

## Project Context

For more advanced use cases, you can access the full project context:

```python
from quack_core.core.paths import service as paths

result = paths.detect_project_context()
if result.success:
    context = result.context

    # Access project information
    project_root = context.root_dir
    project_name = context.name

    # Access directories
    for name, dir_info in context.directories.items():
        print(f"{name}: {dir_info.path}")

    # Check directory types
    source_dirs = [d for d in context.directories.values() if d.is_source]
    data_dirs = [d for d in context.directories.values() if d.is_data]
```

## Content Context

For content-specific projects, you can access the content context:

```python
from quack_core.core.paths import service as paths

result = paths.detect_content_context()
if result.success:
    context = result.context

    # Access content information
    content_type = context.content_type
    content_name = context.content_name
    content_dir = context.content_dir

    # Access special directories
    assets_dir = context._get_assets_dir()
    temp_dir = context._get_temp_dir()
```

## Integration with Other Modules

The paths module is designed to be used by other QuackCore modules that need project-aware path resolution. For example, a content generation module might use the paths module to locate the appropriate output directory for generated content.

```python
from quack_core.core.paths import service as paths


def generate_content(content_name, content_type="tutorials"):
    # Find the content directory
    result = paths.get_content_dir(content_type, content_name)
    if not result.success:
        raise ValueError(f"Could not find content directory: {result.error}")

    content_dir = result.path

    # Generate content in the content directory
    # ...
```

## Best Practices

1. **Always check result success**: Path operations return result objects with a `success` flag. Always check this flag before accessing the result.

2. **Handle missing directories gracefully**: Use the `create=True` parameter for methods like `find_output_directory` to create directories if they don't exist.

3. **Use the path service for semantic operations**: Use the path service for operations that require project context, and use `quack_core.core.fs` for low-level file operations.

4. **Cache project context**: For performance-critical code, consider caching the project context instead of detecting it repeatedly.

```python
from quack_core.core.paths import service as paths

# Cache the project context
context_result = paths.detect_project_context()
if context_result.success:
    context = context_result.context

    # Use the cached context for multiple _ops
    src_dir = context._get_source_dir()
    data_dir = context._get_data_dir()
    config_dir = context._get_config_dir()
```