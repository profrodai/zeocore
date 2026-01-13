# Best Practices for Using the QuackCore FS Module

## Good Practices

### 1. Use the Global Service Instance

```python
from quack_core.core.fs import service as fs

# Good - uses the global service instance
result = fs._read_text("config.yaml")
```

The module provides a pre-initialized global service instance that you should use in most cases.

### 2. Always Check Result Objects

```python
# Good - checks for success before using the content
result = fs._read_text("config.yaml")
if result.success:
    config_data = result.content
    # Do something with config_data
else:
    logger.error(f"Failed to read config file: {result.error}")
```

All operations return a specialized result object with a `success` flag, not just raw content.

### 3. Use Type-Specific Operations

```python
# Good - uses type-specific method
yaml_result = fs._read_yaml("config.yaml")
if yaml_result.success:
    config = yaml_result.data  # Already parsed as a dictionary
```

The module provides specialized methods for common file formats like YAML and JSON.

### 4. Handle Paths Consistently

```python
from pathlib import Path

# Good - works with both string and Path objects
config_dir = Path("config")
fs._create_directory(config_dir)
```

All methods accept both string paths and Path objects.

### 5. Leverage Directory Operations

```python
# Good - uses find_files to search for pattern
result = fs._find_files("logs", "*.log", recursive=True)
if result.success:
    for log_file in result.files:
        process_log(log_file)
```

Use specialized methods for directory operations like listing, finding, and batch processing.

### 6. Use Atomic Operations

```python
# Good - uses atomic write for safety
fs._write_text("important_data.txt", data, atomic=True)
```

Atomic operations provide safety against partial writes during crashes.

### 7. Use Appropriate Error Handling

```python
try:
    result = fs._read_text("config.yaml")
    if not result.success:
        # Handle expected error
        logger.warning(f"Config file not found: {result.error}")
    else:
        config = result.content
except Exception as e:
    # Handle unexpected errors
    logger.error(f"Unexpected error reading config: {str(e)}")
```

Use result objects for expected errors and exceptions for unexpected ones.

## Anti-Patterns

### 1. Bypassing the FS Module

```python
# Bad - bypasses the fs module
with open("config.yaml", "r") as file:
    content = file.read()

# Good - uses the fs module
result = fs._read_text("config.yaml")
```

Don't use built-in `open()`, `os` or direct Path operations when the fs module provides the functionality.

### 2. Ignoring Result Objects

```python
# Bad - assumes success and ignores error handling
content = fs._read_text("config.yaml").content

# Good - checks the result
result = fs._read_text("config.yaml")
if result.success:
    content = result.content
else:
# Handle the error
```

Always check the `success` attribute before using the result.

### 3. Manual Path Manipulation

```python
# Bad - manually joins paths
file_path = base_dir + "/config/settings.yaml"

# Good - uses path utilities
file_path = fs._join_path(base_dir, "config", "settings.yaml")
```

Use the fs module's path utilities for path manipulation.

### 4. Recreating Functionality

```python
# Bad - recreates functionality
if not os.path.exists(dir_path):
    os.makedirs(dir_path)

# Good - uses fs module
fs._create_directory(dir_path, exist_ok=True)
```

Don't recreate functionality that already exists in the fs module.

### 5. Using Hard-Coded File Encodings

```python
# Bad - using hard-coded encoding without consideration
fs._write_text("data.txt", content)

# Good - specifies encoding when needed
fs._write_text("international_data.txt", content, encoding="utf-8")
```

Always specify encodings explicitly when working with non-ASCII text.

### 6. Mixing Different Path Styles

```python
# Bad - mixes different path styles
base_dir = "/projects/myapp"
config_file = base_dir + "/config.yaml"  # String concatenation
logs_dir = Path(base_dir) / "logs"  # Path operator

# Good - consistent path handling
base_dir = Path("/projects/myapp")
config_file = fs._join_path(base_dir, "config.yaml")
logs_dir = fs._join_path(base_dir, "logs")
```

Be consistent in how you handle paths throughout your code.

### 7. Not Creating Parent Directories

```python
# Bad - assumes directory exists
fs._write_text("logs/2023/01/01/app.log", log_content)

# Good - ensures directory exists first
fs._create_directory("logs/2023/01/01", exist_ok=True)
fs._write_text("logs/2023/01/01/app.log", log_content)
```

Always ensure parent directories exist before writing files.

## Key Takeaways

1. **Use Result Objects**: Always check the `success` attribute and handle errors appropriately.
2. **Leverage Specialized Methods**: Use type-specific methods like `read_yaml` and `write_json`.
3. **Path Consistency**: Use `fs.join_path` and other path utilities consistently.
4. **Error Handling**: Use result objects for expected errors and exceptions for unexpected ones.
5. **Directory Operations**: Create directories before writing files to them.
6. **Type Safety**: Take advantage of the strong typing and result objects.
7. **File Safety**: Use atomic operations when data integrity is important.

By following these practices, you'll make the most of the fs module's capabilities while avoiding common pitfalls.