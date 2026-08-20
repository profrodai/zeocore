# ZeoCore

[![CI](https://github.com/zeroemployeeorg/zeocore/workflows/CI/badge.svg)](https://github.com/zeroemployeeorg/zeocore/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/zeocore.svg)](https://pypi.org/project/zeocore/)
[![Python versions](https://img.shields.io/pypi/pyversions/zeocore.svg)](https://pypi.org/project/zeocore/)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](https://github.com/zeroemployeeorg/zeocore)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**A typed capability-authoring framework for Python.** Write a tool once —
validated input, one method of real work, a structured result — and run it
inside any runner that respects the contract. No inheritance ceremony, no
framework lock-in, no untyped `**kwargs` soup.

```python
import logging
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


# A runner builds the context; this is what that looks like:
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
print(result.data)    # Hello, World!
print(result.status)  # CapabilityStatus.success
```

Every tool takes a typed request, runs against an immutable `ToolContext`
(logger, filesystem, config, and any services the runner wires in), and
returns a `CapabilityResult` — success or failure, always structured, always
inspectable, never a bare exception or an untyped dict. mypy checks it end to
end.

## Why a typed result instead of "just raise an exception"

Exceptions are for things the *caller* didn't expect. A `CapabilityResult` is
for things the *tool* expects and needs to report cleanly: validation
failed, a downstream API returned an error, an optional integration wasn't
configured. Callers get one shape to check (`result.status`) instead of a
`try`/`except` matrix, and a runner orchestrating many tools can log,
retry, or persist every result the same way, without special-casing which
tool happens to throw what.

If a tool *does* hit something genuinely exceptional, ZeoCore's typed error
hierarchy (`ZeoError` and its subclasses — `ZeoFileNotFoundError`,
`ZeoValidationError`, `ZeoApiError`, and more) gives you specific,
catchable exception types instead of parsing a string message. See
[`examples/error_handling.py`](examples/error_handling.py) for the full
pattern.

## Install

```bash
pip install zeocore
```

Optional integrations ship as extras, so you only install what you use:

| Extra | What it adds |
|---|---|
| `zeocore[github]` | GitHub API integration |
| `zeocore[drive]` | Google Drive |
| `zeocore[gmail]` | Gmail |
| `zeocore[google]` | Drive + Gmail auth plumbing together |
| `zeocore[notion]` | Notion |
| `zeocore[pandoc]` | Document conversion via Pandoc |
| `zeocore[llms]` | OpenAI / Anthropic / tiktoken clients |
| `zeocore[http]` | FastAPI-based HTTP adapter for exposing tools over REST |
| `zeocore[mcp]` | MCP adapter for exposing tools to Claude Code, Cursor, and other MCP-native agents |
| `zeocore[all]` | Every integration above, no `http`/`mcp`/`dev`/`lint` |

`dev` and `lint` extras exist too, for contributors — see
[CONTRIBUTING.md](CONTRIBUTING.md).

## More examples

- [`examples/toolkit_usage.py`](examples/toolkit_usage.py) — the full
  picture: lifecycle hooks, an optional integration, graceful degradation
  when a service isn't configured.
- [`examples/minimal_tool.py`](examples/minimal_tool.py) — the smallest
  possible tool: no mixins, no services, just `run()`.
- [`examples/error_handling.py`](examples/error_handling.py) — the
  `ZeoError` family, and how a tool reports a failure it expects versus one
  it doesn't.
- [`examples/config_usage.py`](examples/config_usage.py) — `load_config()`'s
  three real behaviors: default-locations lookup (never raises), an
  explicit path that doesn't exist (raises `ZeoConfigurationError`, by
  design), and an explicit path to a real file (succeeds).
- [`examples/mcp_server_usage.py`](examples/mcp_server_usage.py) — expose a
  tool as an MCP server (`zeocore[mcp]`) for Claude Code, Cursor, and other
  MCP-native agents, with zero MCP-specific code in the tool itself.

Every example is runnable as-is: `python examples/<name>.py`. None of them
are illustrative fragments — each one actually executes and prints real
output, because a code sample that's never run is a code sample that's
already stale.

## What's in the package

| Module | What it's for |
|---|---|
| `zeo_core.tools` | The framework itself — `BaseZeoTool`, `ToolContext`, and optional mixins (`IntegrationEnabledMixin`, `LifecycleMixin`, `ToolEnvInitializerMixin`). |
| `zeo_core.contracts` | The data contracts tools speak — `CapabilityResult`, artifact/manifest models, common enums and IDs. |
| `zeo_core.core` | Filesystem operations, path resolution, a typed error hierarchy, MIME detection, serialization, logging, an operation registry. |
| `zeo_core.config` | YAML/env-var configuration loading and per-tool config models. |
| `zeo_core.integrations` | Adapters for GitHub, Google Drive/Mail, LLM providers, Notion, Pandoc, and a database layer. |
| `zeo_core.modules` | Plugin discovery and explicit-loading registry. |
| `zeo_core.prompt` | Prompt template selection and enhancement utilities. |
| `zeo_core.adapters` | Optional adapters for exposing tools over a network: HTTP (FastAPI-based REST) and MCP (Model Context Protocol, for Claude Code/Cursor/other MCP-native agents). |

See [GET-STARTED.md](GET-STARTED.md) for a fuller walkthrough of each area,
including the configuration file format and error-handling patterns. See
[llms.txt](llms.txt) for a condensed summary of this package intended for
coding agents / LLM context windows.

## Quality bar

- **mypy --strict**, clean across the whole source tree.
- **2005 tests**, 90%+ coverage, enforced as a hard CI floor
  (`--cov-fail-under=90`) — a pull request that drops coverage fails the
  gate.
- **CI runs the full suite on Python 3.10, 3.11, 3.12, and 3.13** on every
  push, not just whatever version the maintainer happens to have installed.
  That matrix has already caught and fixed three genuine cross-version
  stdlib behavior differences before they shipped — see
  [CHANGELOG.md](CHANGELOG.md) for specifics.
- Production code is not allowed to detect that it's under test (a
  dedicated CI check fails the build if it finds `"pytest" in sys.modules`
  or similar) — if a test needs different behavior, it injects it, rather
  than the library quietly special-casing itself for its own test suite.

## Project status

ZeoCore just published its first release. The API is typed and tested, but
it hasn't yet had real-world usage outside the project that built it — some
rough edges are likely, and the surface may still shift before a 1.0. Issues,
questions, and API feedback are genuinely welcome; this is a good time to
influence the shape of things.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for dev environment setup, the
verification gate, and how to submit a change. This project follows the
[Contributor Covenant](CODE_OF_CONDUCT.md).

## Project links

[PyPI](https://pypi.org/project/zeocore/) ·
[Source](https://github.com/zeroemployeeorg/zeocore) ·
[Issues](https://github.com/zeroemployeeorg/zeocore/issues) ·
[Changelog](CHANGELOG.md) ·
[Get started](GET-STARTED.md) ·
[Contributing](CONTRIBUTING.md)

## License

MIT — see [LICENSE](LICENSE).
