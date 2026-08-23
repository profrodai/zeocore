# ZeoCore

[![CI](https://github.com/zeroemployeeorg/zeocore/workflows/CI/badge.svg)](https://github.com/zeroemployeeorg/zeocore/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/zeocore.svg)](https://pypi.org/project/zeocore/)
[![Python versions](https://img.shields.io/pypi/pyversions/zeocore.svg)](https://pypi.org/project/zeocore/)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](https://github.com/zeroemployeeorg/zeocore)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**A typed capability-authoring framework for Python.** Declare a capability
once — namespaced identity, Pydantic request/response, declared effects,
structured result — and invoke it from a runner, an HTTP API, MCP, or an
LLM tool list. SPDX: `MIT`.

```python
import logging
from tempfile import TemporaryDirectory

from pydantic import BaseModel

from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.core.fs import get_service as get_fs_service
from zeo_core.tools import ToolContext, bound_capability_of, capability, invoke_sync


class GreetRequest(BaseModel):
    name: str


class GreetResponse(BaseModel):
    message: str


@capability(
    id="demo.greet@1.0.0",
    description="Greet a person by name.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            request={"name": "World"},
            response={"message": "Hello, World!"},
        ),
    ),
)
def greet(request: GreetRequest, ctx: ToolContext) -> CapabilityResult[GreetResponse]:
    ctx.require_logger().info("greeting %s", request.name)
    return CapabilityResult.ok(data=GreetResponse(message=f"Hello, {request.name}!"))


with TemporaryDirectory() as tmp:
    ctx = ToolContext(
        run_id="demo-run-001",
        tool_name="greet",
        tool_version="1.0.0",
        logger=logging.getLogger("greet"),
        fs=get_fs_service(),
        work_dir=tmp,
        output_dir=tmp,
    )
    result = invoke_sync(bound_capability_of(greet), GreetRequest(name="World"), ctx)
    print(result.data.message)  # Hello, World!
```

Class-based tools still work: subclass `BaseZeoTool`, implement
`run(request, ctx) -> CapabilityResult`, and optionally adapt with
`tool_to_capability`. See [`examples/minimal_tool.py`](examples/minimal_tool.py)
and [`examples/tool_to_capability.py`](examples/tool_to_capability.py).

Every capability takes a typed request, runs against an immutable
`ToolContext` (logger, filesystem, config, and any services the runner
wires in), and returns a `CapabilityResult` — success, skip, or error,
always structured. mypy checks it end to end.

## Why a typed result instead of "just raise an exception"

Exceptions are for things the *caller* didn't expect. A `CapabilityResult`
is for things the *tool* expects and needs to report cleanly: validation
failed, a downstream API returned an error, an optional integration wasn't
configured. Callers get one shape to check (`result.status`, plus
fine-grained `result.outcome`) instead of a `try`/`except` matrix, and a
runner orchestrating many tools can log, retry, or persist every result the
same way.

If a tool *does* hit something genuinely exceptional, ZeoCore's typed error
hierarchy (`ZeoError` and its subclasses) gives you catchable types instead
of parsing a string. See [`examples/error_handling.py`](examples/error_handling.py).

## Install

**Requires Python 3.13 or newer.** The floor moved from `>=3.10` to
`>=3.13` in an earlier cycle. If you're pinned to an older Python, stay on
a pre-floor-bump release.

```bash
pip install zeocore
# or
uv pip install zeocore
```

Optional integrations ship as extras, so you only install what you use:

| Extra | What it adds |
|---|---|
| `zeocore[github]` | GitHub API integration |
| `zeocore[drive]` | Google Drive |
| `zeocore[gmail]` | Gmail |
| `zeocore[calendar]` | Google Calendar (read + write) |
| `zeocore[google]` | Drive + Gmail auth plumbing together |
| `zeocore[notion]` | Notion (read + write) |
| `zeocore[pandoc]` | Document conversion via Pandoc |
| `zeocore[llms]` | OpenAI / Anthropic / tiktoken clients — chat, tool-calling, prompt caching |
| `zeocore[jupytext]` | Script ↔ Jupyter notebook conversion |
| `zeocore[ffmpeg]` | Media probing/transcoding via the org's `ffmpeg-zeo` package |
| `zeocore[http]` | FastAPI-based HTTP adapter for exposing tools over REST |
| `zeocore[mcp]` | MCP adapter for exposing tools to Claude Code, Cursor, and other MCP-native agents |
| `zeocore[all]` | Every integration above, no `http`/`mcp`/`dev`/`lint` |

`dev` and `lint` extras exist too, for contributors — see
[CONTRIBUTING.md](CONTRIBUTING.md) (`make setup`, then `make verify`).
`mcp`/`mcp-dev` are real, separate extras — `zeocore[all]` does **not**
pull in the MCP adapter; install `zeocore[mcp]` explicitly (e.g.
`zeocore[all,mcp]`).

## More examples

- [`examples/capability_authoring.py`](examples/capability_authoring.py) —
  canonical `@capability` authoring, registry, and `invoke_sync`.
- [`examples/capability_guards.py`](examples/capability_guards.py) —
  `RequestGuard` rejecting a request before the handler runs.
- [`examples/tool_to_capability.py`](examples/tool_to_capability.py) —
  adapt a `BaseZeoTool` class into a `BoundCapability`.
- [`examples/llm_tools_usage.py`](examples/llm_tools_usage.py) —
  project a `CapabilityManifest` to an OpenAI function tool (or refuse).
- [`examples/minimal_tool.py`](examples/minimal_tool.py) — the smallest
  class tool: no mixins, no services, just `run()`.
- [`examples/toolkit_usage.py`](examples/toolkit_usage.py) — lifecycle
  hooks, an optional integration, graceful skip when a service isn't wired.
- [`examples/error_handling.py`](examples/error_handling.py) — the
  `ZeoError` family.
- [`examples/config_usage.py`](examples/config_usage.py) —
  `load_config()`'s three real behaviors.
- [`examples/http_adapter_usage.py`](examples/http_adapter_usage.py) —
  bind a capability into `OperationRegistry` and exercise the FastAPI app
  (`zeocore[http]`).
- [`examples/mcp_server_usage.py`](examples/mcp_server_usage.py) — expose
  a tool as an MCP server (`zeocore[mcp]`).
- [`examples/explicit_plugin_loading_example.py`](examples/explicit_plugin_loading_example.py) —
  discover and load plugins without import-time side effects.
- [`examples/notion_usage.py`](examples/notion_usage.py) — Notion
  read/write, skipped when `NOTION_TOKEN` isn't set.
- [`examples/calendar_usage.py`](examples/calendar_usage.py) — Google
  Calendar read/write, skipped when OAuth isn't configured.
- [`examples/jupytext_usage.py`](examples/jupytext_usage.py) — script ↔
  notebook round-trip.
- [`examples/ffmpeg_usage.py`](examples/ffmpeg_usage.py) — probe,
  transcode, and thumbnail a synthetic test video.

Every example is runnable as-is: `python examples/<name>.py`. None of them
are illustrative fragments.

Examples that need a credential (`NOTION_TOKEN`, `GITHUB_TOKEN`, an LLM API
key, …) read it from the process environment. Copy [`.env.example`](.env.example)
to `.env`, fill in real values, and load it however your shell/tooling
prefers (e.g. `uv run --env-file .env ...`) — see GET-STARTED.md's "Secrets
and `.env`" section.

## What's in the package

| Module | What it's for |
|---|---|
| `zeo_core.tools` | Authoring — `@capability`, `CapabilityRegistry`, `invoke_sync` / `invoke_async`, `BaseZeoTool`, `ToolContext`, `tool_to_capability`, optional mixins. |
| `zeo_core.contracts` | Data contracts — `CapabilityId`, `CapabilityDefinition`, `CapabilityManifest`, `CapabilityResult`, `CapabilityOutcome`, guards, invocation records. See [contracts/README.md](src/zeo_core/contracts/README.md). |
| `zeo_core.adapters` | Optional adapters: HTTP, MCP, and `llm_tools` (OpenAI-compatible function projection from one `CapabilityManifest`). |
| `zeo_core.core` | Filesystem operations, path resolution, a typed error hierarchy, MIME detection, serialization, logging, an operation registry. |
| `zeo_core.config` | YAML/env-var configuration loading and per-tool config models. |
| `zeo_core.integrations` | Adapters for GitHub, Google Drive/Mail/Calendar, LLM providers, Notion, Pandoc, jupytext, and ffmpeg. Database integrations were evaluated and **not built** — see [CHANGELOG.md](CHANGELOG.md). |
| `zeo_core.modules` | Plugin discovery and explicit-loading registry. |
| `zeo_core.prompt` | Prompt template selection and enhancement utilities. |
| `zeo_core.contract_pack` | Versioned consumption contract pack for ecosystem runners (no `sovereign_agent` import). |

See [GET-STARTED.md](GET-STARTED.md) for a module-by-module walkthrough,
including the [Capabilities](GET-STARTED.md#capabilities) section.
[docs/](docs/README.md) indexes tutorials (MCP, Notion, Calendar,
[capability authoring](docs/tutorials/capability-authoring.md)) separately
from maintainer reports.
[llms.txt](llms.txt) is a condensed summary for coding agents.

## Quality bar

- **mypy --strict**, clean across the whole source tree.
- **2494 tests**, 90%+ coverage, enforced as a hard CI floor
  (`--cov-fail-under=90`) — a pull request that drops coverage fails the
  gate.
- **CI runs the full suite on Python 3.13** (zeocore's minimum-supported
  interpreter) on every push.
- Production code is not allowed to detect that it's under test (a
  dedicated CI check fails the build if it finds `"pytest" in sys.modules`
  or similar).

## Project status

ZeoCore **0.5.0** is a beta library: the API is typed and tested, and this
release is the canonical capability-authoring surface for the Zero Employee
ecosystem. The surface may still shift before 1.0. Issues, questions, and
API feedback are welcome.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for dev environment setup, the
verification gate (`make verify`), and how to submit a change. This project
follows the [Contributor Covenant](CODE_OF_CONDUCT.md).

## Project links

[PyPI](https://pypi.org/project/zeocore/) ·
[Source](https://github.com/zeroemployeeorg/zeocore) ·
[Issues](https://github.com/zeroemployeeorg/zeocore/issues) ·
[Changelog](CHANGELOG.md) ·
[Get started](GET-STARTED.md) ·
[Contributing](CONTRIBUTING.md) ·
[Security](SECURITY.md)

## License

MIT — see [LICENSE](LICENSE).
