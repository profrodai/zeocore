# ZeoCore

[![CI](https://github.com/zeroemployeeorg/zeocore/workflows/CI/badge.svg)](https://github.com/zeroemployeeorg/zeocore/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/zeocore.svg)](https://pypi.org/project/zeocore/)
[![Python versions](https://img.shields.io/pypi/pyversions/zeocore.svg)](https://pypi.org/project/zeocore/)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](https://github.com/zeroemployeeorg/zeocore)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**ZeoCore is a Python framework for writing capabilities: small, typed,
named units of work that anything can call.**

You write a function once — giving it an identity, a typed request and
response, a declaration of its side effects, and a structured result — and
that same function can then be run by a script, served over HTTP, exposed to
an MCP-native coding agent like Claude Code or Cursor, or handed to an LLM as
a callable tool. You don't rewrite it for each destination.

**New here? Start with the [Quickstart](QUICKSTART.md).** It takes you from
an empty folder to a running capability in about ten minutes, and assumes no
prior knowledge of ZeoCore.

## Who this is for

- **Students and newcomers** learning how to structure real Python tools —
  typed inputs, explicit error handling, no hidden global state.
- **Developers** building automation, content pipelines, or integrations who
  don't want to re-solve configuration, filesystem, and error handling in
  every project.
- **Teams** in the Zero Employee ecosystem who need one authoring surface
  that runners, HTTP services, and agents can all consume.

You should be comfortable writing Python functions and classes. You do *not*
need prior experience with Pydantic, MCP, or agent frameworks.

## Requirements

**Python 3.14 or newer.** That's the only hard requirement. (The floor moved
to `>=3.14` in 0.6.0, matching sovereign-agent; if you're pinned to an older
interpreter, stay on 0.5.0, which requires `>=3.13`.)

Not sure what you have? Run `python3 --version` on macOS/Linux or
`py --version` on Windows. The [Quickstart](QUICKSTART.md#step-1-check-your-python-version)
walks through installing 3.14 if you need it.

## Install

```bash
pip install zeocore
# or, with uv
uv pip install zeocore
```

The package is `zeocore`; the module you import is `zeo_core`.

## Your first capability

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
    print(result.status.value, "|", result.data.message)
```

Expected output:

```
success | Hello, World!
```

Line-by-line explanation of that script lives in
[QUICKSTART.md](QUICKSTART.md#what-each-part-of-that-file-does).

## The mental model

Four ideas carry the whole framework.

**1. A capability is identified, not just named.** Identity is
`namespace.name@semver` (`demo.greet@1.0.0`), so versions can coexist and
callers can pin one.

**2. The request and response are Pydantic models.** JSON Schema is generated
from those models, which is how HTTP, MCP, and LLM adapters can call your
capability without you hand-writing schema for each.

**3. Everything from the outside world arrives via `ToolContext`.** Logger,
filesystem, config, and any services the caller wired in — your capability
asks the context instead of reaching for ambient global state. Absence of a
declared service fails closed.

**4. Expected failures are returned, not raised.** A `CapabilityResult` is
success, skip, or error, always structured. Exceptions are for what the
*caller* didn't expect; a `CapabilityResult` is for what the *tool* expects
and needs to report cleanly — validation failed, a downstream API errored, an
optional integration wasn't configured. Callers get one shape to check
(`result.status`, plus fine-grained `result.outcome`) instead of a
`try`/`except` matrix, so a runner orchestrating many tools can log, retry,
or persist every result the same way. For genuinely exceptional cases,
ZeoCore's typed `ZeoError` hierarchy gives you catchable types instead of
string parsing — see [`examples/error_handling.py`](examples/error_handling.py).

Class-based tools are still supported: subclass `BaseZeoTool`, implement
`run(request, ctx) -> CapabilityResult`, and adapt with `tool_to_capability`.
See [`examples/minimal_tool.py`](examples/minimal_tool.py) and
[`examples/tool_to_capability.py`](examples/tool_to_capability.py).

mypy checks all of it end to end.

## Learn ZeoCore

| Start here | What it gives you |
|---|---|
| [QUICKSTART.md](QUICKSTART.md) | Install Python 3.14, make a venv, write and run your first capability. No prior knowledge assumed. |
| [docs/README.md](docs/README.md) | The learning hub: tutorials, a guided path through the examples, and reference material. |
| [docs/tutorials/capability-authoring.md](docs/tutorials/capability-authoring.md) | The canonical authoring tutorial — registry, guards, manifests, adapter binding. |
| [GET-STARTED.md](GET-STARTED.md) | The full manual: configuration, paths, filesystem, plugins, every integration, adapters, troubleshooting. |
| [docs/reference/api.md](docs/reference/api.md) | The public API surface, symbol by symbol, and which import paths are supported. |
| [llms.txt](llms.txt) | A condensed import map for coding agents. |

## Examples

Every example under [`examples/`](examples/) is a real, runnable script —
none are illustrative fragments. Run any of them with
`python examples/<name>.py`.

- [`capability_authoring.py`](examples/capability_authoring.py) — canonical
  `@capability` authoring, registry, and `invoke_sync`.
- [`minimal_tool.py`](examples/minimal_tool.py) — the smallest class tool: no
  mixins, no services, just `run()`.
- [`capability_guards.py`](examples/capability_guards.py) — a `RequestGuard`
  rejecting a request before the handler runs.
- [`error_handling.py`](examples/error_handling.py) — the `ZeoError` family.
- [`config_usage.py`](examples/config_usage.py) — `load_config()`'s three
  real behaviors.

The [docs hub](docs/README.md#runnable-examples) indexes all fifteen,
grouped by topic.

Examples that need a credential (`NOTION_TOKEN`, `GITHUB_TOKEN`, an LLM API
key, …) read it from the process environment. Copy
[`.env.example`](.env.example) to `.env`, fill in real values, and load it
however your shell or tooling prefers (e.g. `uv run --env-file .env ...`) —
see [GET-STARTED.md's "Secrets and `.env`"](GET-STARTED.md#secrets-and-env)
section.

## Optional integrations

Integrations ship as extras, so you install only what you use:

| Extra | What it adds |
|---|---|
| `zeocore[github]` | GitHub API integration |
| `zeocore[drive]` | Google Drive |
| `zeocore[gmail]` | Gmail |
| `zeocore[calendar]` | Google Calendar (read + write) |
| `zeocore[google]` | Drive + Gmail + **Docs** auth plumbing together |
| `zeocore[bluesky]` | Bluesky posting via an app password — no OAuth, no developer app |
| `zeocore[notion]` | Notion (read + write) |
| `zeocore[pandoc]` | Document conversion via Pandoc |
| `zeocore[llms]` | OpenAI / Anthropic / tiktoken clients — chat, tool-calling, prompt caching |
| `zeocore[jupytext]` | Script ↔ Jupyter notebook conversion |
| `zeocore[ffmpeg]` | Media probing/transcoding via the org's `ffmpeg-zeo` package |
| `zeocore[http]` | FastAPI-based HTTP adapter for exposing tools over REST |
| `zeocore[mcp]` | MCP adapter for exposing tools to Claude Code, Cursor, and other MCP-native agents |
| `zeocore[all]` | Every integration above, no `http`/`mcp`/`dev`/`lint` |

`mcp` and `mcp-dev` are real, separate extras — `zeocore[all]` does **not**
pull in the MCP adapter. Install it explicitly (e.g. `zeocore[all,mcp]`).
The `dev` and `lint` extras are for contributors; see
[CONTRIBUTING.md](CONTRIBUTING.md).

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

[GET-STARTED.md](GET-STARTED.md#core-modules-overview) walks through these
module by module.

## Quality bar

- **mypy --strict**, clean across the whole source tree.
- **2494 tests**, 90%+ coverage, enforced as a hard CI floor
  (`--cov-fail-under=90`) — a pull request that drops coverage fails the gate.
- **CI runs the full suite on Python 3.13** (the minimum supported
  interpreter) on every push.
- Production code is not allowed to detect that it's under test (a dedicated
  CI check fails the build if it finds `"pytest" in sys.modules` or similar).

## Project status

ZeoCore **0.5.0** is a beta library: the API is typed and tested, and this
release is the canonical capability-authoring surface for the Zero Employee
ecosystem. The surface may still shift before 1.0. Issues, questions, and API
feedback are welcome.

## Contributing

New contributors start at [CONTRIBUTING.md](CONTRIBUTING.md), which covers
dev environment setup (`make setup`), the verification gate (`make verify`),
and how to submit a change. This project follows the
[Contributor Covenant](CODE_OF_CONDUCT.md). Security reports go through
[SECURITY.md](SECURITY.md).

## Project links

[PyPI](https://pypi.org/project/zeocore/) ·
[Source](https://github.com/zeroemployeeorg/zeocore) ·
[Issues](https://github.com/zeroemployeeorg/zeocore/issues) ·
[Quickstart](QUICKSTART.md) ·
[Docs](docs/README.md) ·
[Manual](GET-STARTED.md) ·
[Changelog](CHANGELOG.md) ·
[Contributing](CONTRIBUTING.md) ·
[Security](SECURITY.md)

## License

MIT — see [LICENSE](LICENSE). SPDX: `MIT`.
