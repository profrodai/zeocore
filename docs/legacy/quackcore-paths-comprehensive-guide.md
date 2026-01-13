# QuackCore Paths Module Documentation

## Introduction

The `quack_core.core.paths` module provides sophisticated project structure detection and path resolution utilities for QuackCore projects. While `quack_core.core.fs` focuses on file operations, `quack_core.core.paths` understands the semantic meaning of paths within a project context, making it easier to work with project files regardless of where your code is running from.

This documentation will guide you through the concepts, features, and best practices for effectively leveraging the power of `quack_core.core.paths` in your QuackTools.

## Table of Contents

- [Getting Started](#getting-started)
- [Core Concepts](#core-concepts)
  - [Project Context](#project-context)
  - [Content Context](#content-context)
  - [Project Directories](#project-directories)
- [Basic Usage](#basic-usage)
  - [Finding Project Roots](#finding-project-roots)
  - [Resolving Project Paths](#resolving-project-paths)
  - [Working with Project Context](#working-with-project-context)
- [Advanced Features](#advanced-features)
  - [Content Context Detection](#content-context-detection)
  - [Directory Type Detection](#directory-type-detection)
  - [Module Inference](#module-inference)
- [Integration with QuackCore](#integration-with-quackcore)
  - [Using with quack_core.core.fs](#using-with-quackcore-fs)
  - [Plugin System](#plugin-system)
- [Best Practices](#best-practices)
- [Common Patterns](#common-patterns)
- [API Reference](#api-reference)

## Getting Started

### Installation

QuackCore Paths is part of the QuackCore package. If you've installed QuackCore, you already have access to the Paths module.

### Basic Usage

The quickest way to start using the `quack_core.core.paths` module is through the global resolver instance:

```python
from quack_core.core.paths import resolver

# Find project root
project_root = resolver._get_project_root()
print(f"Project root is at: {project_root}")

# Resolve a path relative to project root
config_path = resolver._resolve_project_path("config/settings.yaml")
print(f"Config path: {config_path}")

# Get project context with directory information
context = resolver._detect_project_context()
print(f"Project name: {context.name}")
print(f"Source directory: {context._get_source_dir()}")
```

## Core Concepts

### Project Context

A `ProjectContext` represents the structure of a project, containing information about the project's directories, configuration files, and other key elements. It provides methods to access various types of directories within the project.

Key attributes and methods:

- `root_dir`: The root directory of the project
- `directories`: Dictionary of project directories by name
- `config_file`: Path to the project configuration file (if detected)
- `name`: Name of the project
- `get_source_dir()`: Get the primary source code directory
- `get_output_dir()`: Get the primary output directory
- `get_data_dir()`: Get the primary data directory

### Content Context

`ContentContext` extends the `ProjectContext` with additional information specific to content creation projects (like tutorials, videos, etc.). It adds context for the specific type of content, name, and location.

Additional attributes and methods:

- `content_type`: Type of content (e.g., 'tutorial', 'video')
- `content_name`: Name of the content item
- `content_dir`: Path to the content directory
- `get_assets_dir()`: Get the assets directory
- `get_temp_dir()`: Get the temporary directory

### Project Directories

The `ProjectDirectory` class represents a specific directory within a project and includes metadata about the directory's purpose and location:

- `name`: Name of the directory
- `path`: Absolute path to the directory
- `rel_path`: Path relative to the project root
- Type flags: `is_source`, `is_output`, `is_data`, `is_config`, `is_test`, `is_asset`, `is_temp`

## Basic Usage

### Finding Project Roots

The `quack_core.core.paths` module provides robust utilities for finding the root directory of a project:

```python
from quack_core.core.paths import resolver, find_project_root

# Using the global resolver
project_root = resolver._get_project_root()

# Using the standalone function
project_root = find_project_root()

# Specifying a starting directory
project_root = find_project_root("/path/to/start/search")

# Customizing marker files and directories
project_root = find_project_root(
  marker_files=["pyproject.toml", "setup.py"],
  marker_dirs=["src", "tests"]
)
```

The module identifies project roots by looking for common marker files (like `pyproject.toml`, `.git`) and directory patterns. It's smart enough to handle nested project structures and will find the most appropriate root directory.

### Resolving Project Paths

Resolving paths relative to the project root is one of the key features of `quack_core.core.paths`:

```python
from quack_core.core.paths import resolver, resolve_project_path

# Resolve a relative path from the project root
config_path = resolver._resolve_project_path("config/settings.yaml")

# Using the standalone function
config_path = resolve_project_path("config/settings.yaml")

# Specifying a custom project root
config_path = resolve_project_path(
  "config/settings.yaml",
  project_root="/custom/project/root"
)

# Absolute paths are returned unchanged
abs_path = resolver._resolve_project_path("/absolute/path/to/file.txt")
```

This makes it easy to work with project files regardless of the current working directory, eliminating the need for complex path manipulation in your code.

### Working with Project Context

The `ProjectContext` provides a rich set of information about a project's structure:

```python
from quack_core.core.paths import resolver

# Detect project context
context = resolver._detect_project_context()

# Get key directories
src_dir = context._get_source_dir()
output_dir = context._get_output_dir()
data_dir = context._get_data_dir()
config_dir = context._get_config_dir()

# Get arbitrary directories by name
tests_dir = context._get_directory("tests")
docs_dir = context._get_directory("docs")

# Check project configuration file
if context.config_file:
  print(f"Project configuration found at: {context.config_file}")

# Enumerate all project directories
for name, dir_info in context.directories.items():
  print(f"{name}: {dir_info.path}")
  if dir_info.is_source:
    print("  (source directory)")
  if dir_info.is_output:
    print("  (output directory)")
```

This context awareness makes it easy to build tools that operate on different parts of a project without hardcoding paths.

## Advanced Features

### Content Context Detection

For content creation projects (like tutorials, documentation sites, etc.), `quack_core.core.paths` provides additional context detection:

```python
from quack_core.core.paths import resolver

# Detect content context
content_context = resolver._detect_content_context()

# Check if content type is identified
if content_context.content_type:
  print(f"Content type: {content_context.content_type}")
  print(f"Content name: {content_context.content_name}")

  # Access content-specific directories
  assets_dir = content_context._get_assets_dir()
  if assets_dir:
    print(f"Assets directory: {assets_dir}")

# Explicitly specify content type
tutorial_context = resolver._detect_content_context(content_type="tutorial")
```

Content context is particularly useful for tools that generate or process specific types of content within a larger project.

### Directory Type Detection

The module automatically identifies common directory types within projects:

```python
from quack_core.core.paths import resolver

context = resolver._detect_project_context()

# Find all test directories
test_dirs = [
  dir_info.path
  for dir_info in context.directories.values()
  if dir_info.is_test
]

# Find all asset directories
asset_dirs = [
  dir_info.path
  for dir_info in context.directories.values()
  if dir_info.is_asset
]


# Check if a directory is a source directory
def is_source_directory(directory_path):
  for dir_info in context.directories.values():
    if str(dir_info.path) == str(directory_path) and dir_info.is_source:
      return True
  return False
```

This feature lets you identify the purpose of directories without relying on naming conventions.

### Module Inference

The module can infer Python module names from file paths:

```python
from quack_core.core.paths import infer_module_from_path

# Infer module name from file path
file_path = "/path/to/project/src/quack-core/paths/api.py"
module_name = infer_module_from_path(file_path)
print(f"Module name: {module_name}")  # Output: quack_core.core.paths.api
```

This is especially useful for tooling that needs to import or reference modules dynamically.

## Integration with QuackCore

### Using with quack_core.core.fs

The `quack_core.core.paths` module works seamlessly with `quack_core.core.fs` for advanced file operations:

```python
from quack_core.core.paths import resolver
from quack_core.core.fs import service as fs

# Find project and resolve path
project_context = resolver._detect_project_context()
config_path = resolver._resolve_project_path("config/settings.yaml")

# Check if config exists and read it
info_result = fs._get_file_info(config_path)
if info_result.success and info_result.exists:
  # Read configuration
  yaml_result = fs._read_yaml(config_path)
  if yaml_result.success:
    config = yaml_result.data
    print(f"Loaded configuration: {config}")
else:
  # Create default config
  source_dir = project_context._get_source_dir()
  if source_dir:
    # Create default config based on project structure
    default_config = {
      "project_name": project_context.name,
      "source_dir": str(source_dir),
      "output_dir": str(project_context._get_output_dir() or "output")
    }
    # Ensure config directory exists
    fs._create_directory(config_path.parent, exist_ok=True)
    # Write config
    fs._write_yaml(config_path, default_config)
    print(f"Created default configuration at: {config_path}")
```

### Plugin System

The `quack_core.core.paths` module provides a plugin interface for integration with the QuackCore ecosystem:

```python
from quack_core.core.paths import create_plugin
from quack_core.plugin_manager import PluginManager

# Create paths plugin
paths_plugin = create_plugin()

# Register with plugin manager
plugin_manager = PluginManager()
plugin_manager.register_plugin(paths_plugin)

# Now other components can use the paths functionality
plugin = plugin_manager.get_plugin("paths")
project_root = plugin._find_project_root()
```

## Best Practices

### 1. Use Context Over Direct Paths

```python
# Not recommended: Hard-coding relative paths
config_path = Path("config/settings.yaml")

# Better: Use project context
from quack_core.core.paths import resolver

project_context = resolver._detect_project_context()
config_dir = project_context._get_config_dir() or project_context.root_dir / "config"
config_path = config_dir / "settings.yaml"
```

### 2. Cache Project Context for Performance

```python
# Instead of detecting context for each operation
def process_file(file_path):
  context = resolver._detect_project_context()
  # Process with context...


# Better: Detect once and reuse
def process_files(file_paths):
  context = resolver._detect_project_context()
  for file_path in file_paths:
# Process with shared context...
```

### 3. Handle Project Detection Failures Gracefully

```python
from quack_core.core.errors import QuackFileNotFoundError
from quack_core.core.paths import resolver

try:
  project_context = resolver._detect_project_context()
  # Use project context...
except QuackFileNotFoundError:
  # Fallback to current directory
  from pathlib import Path

  current_dir = Path.cwd()
  print(f"No project structure detected, using current directory: {current_dir}")
  # Continue with reduced functionality...
```

### 4. Combine with fs Module for Complete Path Management

```python
from quack_core.core.paths import resolver
from quack_core.core.fs import service as fs

# Find source directory
project_context = resolver._detect_project_context()
src_dir = project_context._get_source_dir()

if src_dir:
  # List Python files
  result = fs._find_files(src_dir, "*.py", recursive=True)
  if result.success:
    for py_file in result.files:
  # Process Python files...
```

### 5. Use Content Context for Content-Specific Tools

```python
from quack_core.core.paths import resolver

# Detect if we're in a content directory
content_context = resolver._detect_content_context()

if content_context.content_type == "tutorial":
  # Apply tutorial-specific processing
  print(f"Processing tutorial: {content_context.content_name}")
  # ...
elif content_context.content_type == "video":
  # Apply video-specific processing
  print(f"Processing video content: {content_context.content_name}")
  # ...
else:
  print("Not in a recognized content directory")
```

## Common Patterns

### Finding Configuration Files

```python
from quack_core.core.paths import resolver
from quack_core.core.fs import service as fs
from pathlib import Path
import os


def find_config_file(config_name="config", file_types=None):
  """Find a configuration file in standard locations."""
  if file_types is None:
    file_types = [".yaml", ".yml", ".json", ".toml"]

  # Check environment variable first
  env_var = f"QUACK_{config_name.upper()}_CONFIG"
  if env_var in os.environ:
    config_path = fs._expand_user_vars(os.environ[env_var])
    info = fs._get_file_info(config_path)
    if info.success and info.exists:
      return Path(config_path)

  # Try to find project root
  try:
    project_context = resolver._detect_project_context()

    # Try config directory first
    config_dir = project_context._get_config_dir()
    if config_dir:
      for ext in file_types:
        config_path = config_dir / f"{config_name}{ext}"
        info = fs._get_file_info(config_path)
        if info.success and info.exists:
          return config_path

    # Check project root
    for ext in file_types:
      config_path = project_context.root_dir / f"{config_name}{ext}"
      info = fs._get_file_info(config_path)
      if info.success and info.exists:
        return config_path

    # Check for config directory in project root
    for ext in file_types:
      config_path = project_context.root_dir / "config" / f"{config_name}{ext}"
      info = fs._get_file_info(config_path)
      if info.success and info.exists:
        return config_path

  except Exception:
    pass  # Fall through to user directory

  # Try user config directory
  home_dir = Path.home()
  config_home = home_dir / ".config" / "quack"
  for ext in file_types:
    config_path = config_home / f"{config_name}{ext}"
    info = fs._get_file_info(config_path)
    if info.success and info.exists:
      return config_path

  # Not found
  return None
```

### Creating Project Structure

```python
from quack_core.core.paths import resolver
from quack_core.core.fs import service as fs
from pathlib import Path


def initialize_project(name, template="basic"):
  """Initialize a new project with standard structure."""
  # Create project directory
  project_dir = Path(name)
  fs._create_directory(project_dir, exist_ok=True)

  # Create standard directories
  directories = {
    "src": {"is_source": True},
    "tests": {"is_test": True},
    "docs": {},
    "config": {"is_config": True},
    "data": {"is_data": True},
    "output": {"is_output": True}
  }

  # Create project context
  context = resolver._detect_project_context(project_dir)

  # Create each directory and register in context
  for name, attrs in directories.items():
    dir_path = project_dir / name
    fs._create_directory(dir_path, exist_ok=True)
    context._add_directory(name, dir_path, **attrs)

  # Create a basic config file
  config = {
    "project": {
      "name": name,
      "version": "0.1.0"
    },
    "paths": {
      "source": "src",
      "tests": "tests",
      "output": "output"
    }
  }

  config_file = project_dir / "config" / "project.yaml"
  fs._write_yaml(config_file, config)

  # Create a README
  readme = f"# {name}\n\nA new QuackTool project."
  fs._write_text(project_dir / "GET-STARTED.md", readme)

  return context
```

### Working with Linked Projects

```python
from quack_core.core.paths import resolver
from quack_core.core.fs import service as fs
from pathlib import Path


def link_projects(main_project, dependency_projects):
  """Link dependency projects to a main project."""
  # Find the main project
  main_context = resolver._detect_project_context(main_project)

  # Ensure dev directory exists
  dev_dir = main_context.root_dir / "dev"
  fs._create_directory(dev_dir, exist_ok=True)

  # Link each dependency
  for dep_path in dependency_projects:
    dep_context = resolver._detect_project_context(dep_path)
    dep_name = dep_context.name

    # Create symbolic link
    link_path = dev_dir / dep_name
    if not link_path.exists():
      # Get source directory from dependency
      dep_src = dep_context._get_source_dir()
      if dep_src:
        # Create symbolic link to dependency source
        Path(link_path).symlink_to(dep_src, target_is_directory=True)
        print(f"Linked {dep_name} -> {dep_src}")
      else:
        print(f"Could not find source directory in {dep_name}")
```

## API Reference

### Core Classes

#### PathResolver

```python
class PathResolver:
    def __init__(self, log_level: int = LOG_LEVELS[LogLevel.INFO]) -> None: ...
    
    def get_project_root(
        self,
        start_dir: str | Path | None = None,
        marker_files: list[str] | None = None,
        marker_dirs: list[str] | None = None,
    ) -> Path: ...
    
    def find_source_directory(
        self,
        start_dir: str | Path | None = None,
    ) -> Path: ...
    
    def find_output_directory(
        self,
        start_dir: str | Path | None = None,
        create: bool = False,
    ) -> Path: ...
    
    def resolve_project_path(
        self,
        path: str | Path,
        project_root: str | Path | None = None,
    ) -> Path: ...
    
    def detect_project_context(
        self,
        start_dir: str | Path | None = None,
    ) -> ProjectContext: ...
    
    def detect_content_context(
        self,
        start_dir: str | Path | None = None,
        content_type: str | None = None,
    ) -> ContentContext: ...
    
    def infer_current_content(
        self,
        start_dir: str | Path | None = None,
    ) -> dict[str, str]: ...
```

#### ProjectContext

```python
class ProjectContext(BaseModel):
    root_dir: Path
    directories: dict[str, ProjectDirectory]
    config_file: Path | None
    name: str | None
    
    def get_source_dir(self) -> Path | None: ...
    def get_output_dir(self) -> Path | None: ...
    def get_data_dir(self) -> Path | None: ...
    def get_config_dir(self) -> Path | None: ...
    def get_directory(self, name: str) -> Path | None: ...
    
    def add_directory(
        self,
        name: str,
        path: Path,
        is_source: bool = False,
        is_output: bool = False,
        is_data: bool = False,
        is_config: bool = False,
        is_test: bool = False,
        is_asset: bool = False,
        is_temp: bool = False,
    ) -> None: ...
```

#### ContentContext

```python
class ContentContext(ProjectContext):
    content_type: str | None
    content_name: str | None
    content_dir: Path | None
    
    def get_assets_dir(self) -> Path | None: ...
    def get_temp_dir(self) -> Path | None: ...
```

#### ProjectDirectory

```python
class ProjectDirectory(BaseModel):
    name: str
    path: Path
    rel_path: Path | None
    is_source: bool
    is_output: bool
    is_data: bool
    is_config: bool
    is_test: bool
    is_asset: bool
    is_temp: bool
```

### Utility Functions

```python
def find_project_root(
    start_dir: str | Path | None = None,
    marker_files: list[str] | None = None,
    marker_dirs: list[str] | None = None,
    max_levels: int = 5,
) -> Path: ...

def find_nearest_directory(
    name: str,
    start_dir: str | Path | None = None,
    max_levels: int = 5,
) -> Path: ...

def resolve_relative_to_project(
    path: str | Path,
    project_root: str | Path | None = None,
) -> Path: ...

def normalize_path(path: str | Path) -> Path: ...

def join_path(*parts: str | Path) -> Path: ...

def split_path(path: str | Path) -> list[str]: ...

def get_extension(path: str | Path) -> str: ...

def infer_module_from_path(
    path: str | Path,
    project_root: str | Path | None = None,
) -> str: ...

def resolve_project_path(
    path: str | Path,
    project_root: str | Path | None = None,
) -> Path: ...

def get_project_root(
    start_dir: str | Path | None = None,
    marker_files: list[str] | None = None,
    marker_dirs: list[str] | None = None,
) -> Path: ...
```

### Global Instance

```python
resolver: PathResolver
```

## Conclusion

The `quack_core.core.paths` module provides a robust foundation for working with project structures in the QuackVerse ecosystem. By understanding the semantic meaning of directories and providing context-aware path resolution, it simplifies many common tasks in project-based tools.

When combined with `quack_core.core.fs` for file operations, you have a complete solution for all path and filesystem needs in your QuackTools. The module's ability to detect project structure automatically makes it particularly valuable for creating tools that "just work" without complex configuration.

By following the patterns and best practices outlined in this documentation, you'll be able to build QuackTools that seamlessly integrate with projects of all types and structures.