# ZeoCore

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

**ZeoCore** is a capability-authoring framework for Python. It gives you a small,
typed base (`BaseZeoTool`, `ToolContext`, `CapabilityResult`) for writing tools
that validate input, do their work, and return a structured, machine-readable
result — plus filesystem, configuration, and integration primitives to support
them.

It is not a CLI, not a task runner, and not an application framework. It is the
kernel other things get built on top of: a tool you write against ZeoCore's
contracts can run inside any runner that respects them.

## Install

```bash
pip install zeocore
```

Optional integrations are available as extras:

```bash
pip install "zeocore[google]"   # Google Drive + Gmail auth plumbing
pip install "zeocore[drive]"    # Google Drive only
pip install "zeocore[gmail]"    # Gmail only
pip install "zeocore[notion]"   # Notion
pip install "zeocore[pandoc]"   # Document conversion via pandoc
pip install "zeocore[llms]"     # OpenAI / Anthropic / tiktoken clients
pip install "zeocore[github]"   # GitHub integration
pip install "zeocore[http]"     # FastAPI-based HTTP adapter
pip install "zeocore[all]"      # Everything above except http/dev/lint
```

`dev` and `lint` extras exist too, for contributors — see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Quick start

```python
from pydantic import BaseModel
from zeo_core.contracts import CapabilityResult
from zeo_core.tools import BaseZeoTool, ToolContext


class GreetRequest(BaseModel):
    name: str


class GreetTool(BaseZeoTool):
    name = "greet"
    version = "1.0.0"

    def run(self, request: GreetRequest, ctx: ToolContext) -> CapabilityResult[str]:
        return CapabilityResult.ok(data=f"Hello, {request.name}!")


# A runner builds the context and drives the tool; this is what that looks like:
import logging

ctx = ToolContext(
    run_id="demo-run-001",
    tool_name="greet",
    tool_version="1.0.0",
    logger=logging.getLogger("greet"),
    fs=None,
    work_dir="/tmp",
    output_dir="/tmp",
)

result = GreetTool().run(GreetRequest(name="World"), ctx)
print(result.data)  # "Hello, World!"
```

For a fuller walkthrough — lifecycle hooks, optional integrations, graceful
degradation when a service isn't configured — see
[`examples/toolkit_usage.py`](examples/toolkit_usage.py), or the smaller,
focused examples in [`examples/`](examples/):

- [`minimal_tool.py`](examples/minimal_tool.py) — the smallest possible tool,
  no mixins, no services.
- [`error_handling.py`](examples/error_handling.py) — structured error
  handling with the `ZeoError` family.

Each example is runnable as-is: `python examples/<name>.py`.

## What's in the package

- `zeo_core.tools` — the capability-authoring framework itself: `BaseZeoTool`,
  `ToolContext`, and optional mixins (`IntegrationEnabledMixin`,
  `LifecycleMixin`, `ToolEnvInitializerMixin`).
- `zeo_core.contracts` — the data contracts tools speak: `CapabilityResult`,
  artifact/manifest models, common enums and IDs.
- `zeo_core.core` — filesystem operations (`core.fs`), path resolution
  (`core.paths`), a typed error hierarchy (`core.errors`), MIME detection,
  serialization helpers, logging, and a small operation registry.
- `zeo_core.config` — YAML/env-var configuration loading and per-tool config
  models.
- `zeo_core.integrations` — adapters for GitHub, Google Drive/Mail, LLM
  providers (OpenAI/Anthropic), Notion, Pandoc, and a database layer.
- `zeo_core.modules` — plugin discovery and explicit-loading registry.
- `zeo_core.prompt` — prompt template selection and enhancement utilities.
- `zeo_core.adapters` — an optional HTTP adapter (FastAPI-based) for exposing
  tools over a REST API.

See [GET-STARTED.md](GET-STARTED.md) for a more detailed walkthrough of each
area, including configuration file format and error handling patterns.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to set up a dev environment,
run the test/lint/type-check gate, and submit a change. This project follows
the [Contributor Covenant](CODE_OF_CONDUCT.md).

## License

MIT — see [LICENSE](LICENSE).
