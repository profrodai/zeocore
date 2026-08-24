# Context, configuration, and files

This lesson connects three related but separate APIs:

- `ToolContext` is the immutable dependency bundle a runner gives a tool;
- `load_config()` explicitly loads ZeoCore configuration;
- `FileSystemService` performs sandboxed file operations and returns typed
  results.

ZeoCore does not load configuration or create tool dependencies merely because
you imported it.

## `ToolContext`: dependencies belong to the runner

The canonical example constructs context like this:

```python
import logging
from tempfile import TemporaryDirectory

from zeo_core.core.fs import create_service
from zeo_core.tools import ToolContext

with TemporaryDirectory() as tmp:
    ctx = ToolContext(
        run_id="lesson-001",
        tool_name="reader",
        tool_version="1.0.0",
        logger=logging.getLogger("reader"),
        fs=create_service(base_dir=tmp),
        work_dir=tmp,
        output_dir=tmp,
        services={},
        metadata={"environment": "tutorial"},
    )
```

The required fields identify one run and provide a logger, filesystem, working
directory, and output directory. `services` holds optional integrations.
`metadata` must be JSON-safe. The context and the top level of both mappings
are immutable; tools should treat nested values as read-only too.

Inside a capability, use the public accessors:

```python
logger = ctx.require_logger()
fs = ctx.require_fs()
optional_calendar = ctx.get_service("calendar")
required_calendar = ctx.require_service("calendar")
work_dir = ctx.work_path
output_dir = ctx.output_path
```

`get_service()` returns `None` when absent. `require_service()` raises
`ValueError`, so only use it when the runner contract guarantees that service.
A tool should not silently create a missing integration.

## Load configuration explicitly

Use the public configuration entry point:

```python
from zeo_core.config import load_config

config = load_config()
print(config.general.project_name)
print(config.logging.level)
```

With no explicit path, `load_config()` searches its default locations and, if
none exists, uses built-in defaults plus environment values. It does not fail
just because no file exists.

For a specific YAML file:

```yaml
general:
  project_name: "example-app"
logging:
  level: "DEBUG"
paths:
  output_dir: "./build"
```

```python
config = load_config("zeo_config.yaml")
print(config.general.project_name)  # example-app
```

An explicit path is a promise that the file exists. A missing explicit path
raises `ZeoConfigurationError`. Run
[`examples/config_usage.py`](../../examples/config_usage.py) to see defaults,
a caught missing-path error, and a real YAML file end to end:

```bash
python3.13 examples/config_usage.py
```

Configuration is not a named `ToolContext` field. The runner decides which
derived values a capability needs and can pass JSON-safe values through
`metadata`, or provide a dedicated object in `services`. Avoid having every
tool reach for legacy global configuration state.

## Use the filesystem service

Import the public service factory, not internal `_ops` or `_internal` modules:

```python
from zeo_core.core.fs import create_service

fs = create_service(base_dir="/safe/project/root")
```

Relative paths are anchored to `base_dir`. Parent traversal is blocked, and
absolute paths outside the base directory are rejected unless the runner
deliberately enables the unsafe trust-boundary option.

Filesystem methods return typed operation results instead of raising for
ordinary failures:

```python
write = fs.write_text("output/greeting.txt", "Hello, World!")
if not write.ok:
    print(write.error_info)

read = fs.read_text("output/greeting.txt")
if read.ok:
    print(read.as_text())
else:
    print(read.error_info)
```

Before writing a nested path, create its directory and check that result:

```python
created = fs.ensure_dir("output")
if not created.ok:
    print(created.error_info)
else:
    written = fs.write_text("output/result.txt", "done")
    print(written.message)
```

Use the canonical `.ok` indicator. The filesystem result objects may include a
normalized `path`, human `message`, structured `error_info`, and
operation-specific fields such as `content` or `bytes_written`.

Inside a capability, use the injected service:

```python
def run(request: Request, ctx: ToolContext) -> CapabilityResult[Response]:
    read = ctx.require_fs().read_text(request.path)
    if not read.ok:
        return CapabilityResult.fail(
            msg=read.message or "Could not read input",
            code="ZEO_IO_READ_FAILED",
            metadata={"fs_error": read.error_info.model_dump(mode="json")}
            if read.error_info
            else {},
        )
    return CapabilityResult.ok(data=Response(text=read.as_text()))
```

The runner chooses the sandbox root and directories; the capability consumes
them. This keeps tests deterministic and host access visible.

For the smallest complete contexts, compare
[`examples/capability_authoring.py`](../../examples/capability_authoring.py)
and [`examples/minimal_tool.py`](../../examples/minimal_tool.py). Continue with
[Results and errors](results-and-errors.md) to choose the correct outward
result.
