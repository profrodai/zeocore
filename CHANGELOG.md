# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### BREAKING

- **Python floor raised from `>=3.10` to `>=3.13`.** Python 3.10 is inside
  its own final support window (security-only since October 2023, full
  end-of-life October 2026); 3.13 is also the version the `ffmpeg` extra
  (below) needed to resolve at all (`ffmpeg-zeo` requires Python >=3.12).
  If you're pinned to an older interpreter, stay on a pre-`0.2.0` release
  of this package; otherwise upgrade before installing. CI's version
  matrix was trimmed from `["3.10", "3.11", "3.12", "3.13"]` to
  `["3.13"]` to match — the dropped legs could not pass regardless of
  this change (3.10/3.11 fail `ffmpeg-zeo`'s own floor; keeping them past
  the bump would test versions the package no longer claims to support).

### Added

- **MCP server adapter** (`zeo_core.adapters.mcp`, `zeocore[mcp]`
  extra): expose zeocore tools to Claude Code, Cursor, and other
  MCP-native coding agents. Any `BaseZeoTool` becomes MCP-callable with
  **zero MCP-specific code** from the tool author — `register_tool()`
  mechanically derives the MCP tool definition from the tool's own
  `run(request, ctx)` type hint and registers it into the same
  `OperationRegistry` `zeo_core.adapters.http` already reads, so one
  registration reaches both adapters. See
  [`examples/mcp_server_usage.py`](examples/mcp_server_usage.py) and
  GET-STARTED.md's "Exposing Tools as an MCP Server" section.
- **Notion integration** (`zeo_core.integrations.notion`, `zeocore[notion]`
  extra): full read (`get_page`, `list_page_blocks`, `search`,
  `get_database`, `query_database`) and write (`create_page`,
  `create_database_entry`, `update_page`, `append_blocks`) surface,
  bearer-integration-token auth (Notion's own model, not OAuth). Handles
  the `notion-client` SDK's 2025-09-03 database→data-source model change
  transparently — callers still pass a `database_id`. See
  [`examples/notion_usage.py`](examples/notion_usage.py).
- **Jupytext integration** (`zeo_core.integrations.jupytext`,
  `zeocore[jupytext]` extra): `script_to_notebook()` (percent-format
  `.py` → `.ipynb`, matching how `quackslides` uses jupytext today) and
  `notebook_to_script()` (its natural inverse). See
  [`examples/jupytext_usage.py`](examples/jupytext_usage.py).
- **FFmpeg integration** (`zeo_core.integrations.ffmpeg`,
  `zeocore[ffmpeg]` extra): wraps the org's own `ffmpeg-zeo` PyPI package
  (not the raw `ffmpeg` binary directly). `probe()`, `convert()`,
  `transcode_h264()`, `extract_audio()`, `thumbnail()`. See
  [`examples/ffmpeg_usage.py`](examples/ffmpeg_usage.py).
- `LLMOptions.cache_system_prompt`: marks the system prompt cacheable via
  Anthropic's `cache_control: ephemeral` breakpoints. Provider-agnostic
  field on the shared `LLMProviderProtocol`; a no-op on providers without
  caching support (OpenAI, Ollama).
- `llms.txt`: a condensed package summary for coding agents / LLM context
  windows.

### Fixed

- Anthropic client's default model updated (both `clients/anthropic.py`
  and `config.py`'s `AnthropicConfig.default_model`) — the previous
  default, `claude-3-opus-20240229`, was retired 2026-01-05.
- Real Anthropic-shaped tool-use request passthrough:
  `LLMOptions.tools` is converted to Anthropic's flat
  `{name, description, input_schema}` shape and reaches the real request.
  **Known gap, not yet closed**: response-side tool-call extraction is
  incomplete — `chat()` only reads `response.content[0].text`, so a
  `tool_use` response block is not parsed into structured output today.
  See GET-STARTED.md's LLM providers section for the full detail.
- `zeo_core.integrations.google` now re-exports `GoogleDriveService` and
  `GoogleMailService` at the shallow path (previously only reachable at
  `.google.drive`/`.google.mail`).
- `CapabilityResult` re-exported from the top-level `zeo_core` package
  (previously only reachable via `zeo_core.contracts`).
- GET-STARTED.md's configuration quick-start corrected (an unmarked
  placeholder path was being presented as a runnable example); a real,
  runnable [`examples/config_usage.py`](examples/config_usage.py) added.
- `Makefile`'s `install-all` target was missing the `mcp`/`mcp-dev`
  extras, silently skipping the MCP adapter's own dependencies on a
  plain `make install-all` — fixed.
- An order-dependent test failure
  (`test_configure_logger_attaches_real_file_handler`, passed in
  isolation, failed under full-suite ordering) was root-caused to a
  `functools.lru_cache`-backed filesystem-service singleton leaking a
  stale working directory across tests, and fixed by scoping
  `cache_clear()` around the affected test.

### Research (no code shipped)

- Database integration (BigQuery, Supabase, SQLite) was evaluated and
  **not built** this round: BigQuery dropped (zero consumers anywhere in
  the org); Supabase held (its only real consumer, `profrod-site`, is
  TypeScript and architecturally unreachable from this Python package);
  SQLite judged buildable but not urgent (`quackresearch` already
  self-serves with hand-rolled `sqlite3`). The `zeo_core.integrations.database`
  package directories exist as empty stubs — not yet implemented.

### Changed

- `CapabilityResult.machine_message` and `CapabilityError.code` now accept
  `ZEO_<AREA>_<DETAIL>` (new preferred prefix, matching the `zeo_core`
  package name) and `ZC_<AREA>_<DETAIL>` (short-form alias), in addition to
  the legacy `QC_<AREA>_<DETAIL>` inherited from the pre-extraction
  `quack_core` package. Previously only `QC_` was accepted, which
  contradicted this file's own 0.1.0 "full mechanical rename" claim below
  (see that entry's amendment) and had no documented reason for surviving
  the rename. This is a backward-compatible widening, not a breaking
  change: all 0.1.0 code using `QC_*` codes continues to validate
  unchanged. All of this package's own internal call sites
  (`tools/mixins/env_init.py`, `contracts/capabilities/demo/_impl.py`,
  `examples/toolkit_usage.py`, `contracts/EXAMPLES.md`) were migrated to
  `ZEO_*` to lead by example.

## [0.1.0] - 2026-08-17

Initial extraction from the quackverse monorepo as a standalone,
MIT-licensed package.

### Added

- `zeo_core.tools`: a capability-authoring framework (`BaseZeoTool`,
  `ToolContext`, `ZeoToolProtocol`) with optional mixins
  (`IntegrationEnabledMixin`, `LifecycleMixin`, `ToolEnvInitializerMixin`)
  for writing doctrine-compliant tools.
- `zeo_core.contracts`: typed data contracts (`CapabilityResult`, artifact
  and manifest models, common enums and IDs).
- `zeo_core.core`: filesystem operations (`core.fs`), path resolution
  (`core.paths`), a typed error hierarchy (`core.errors`), MIME detection,
  serialization helpers, logging, and an operation registry.
- `zeo_core.config`: YAML/environment-variable configuration loading and
  per-tool configuration models.
- `zeo_core.integrations`: adapters for GitHub, Google Drive, Gmail, LLM
  providers (OpenAI, Anthropic), Notion, and Pandoc.
- `zeo_core.modules`: plugin discovery and explicit-loading registry.
- `zeo_core.prompt`: prompt template selection and enhancement utilities.
- `zeo_core.adapters`: an optional FastAPI-based HTTP adapter for exposing
  tools over a REST API.
- `examples/`: runnable, verified example scripts (`toolkit_usage.py`,
  `minimal_tool.py`, `error_handling.py`).
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1).

### Changed

- Full mechanical rename from the monorepo's `quack_core` package to
  `zeo_core` (PyPI distribution name: `zeocore`), including class names
  (`Quack*` -> `Zeo*`), environment variable prefixes, and config file
  keys. **Amendment (see Unreleased):** this rename did not originally
  extend to the `QC_*` machine-message/error-code prefix enforced by
  `CapabilityResult`/`CapabilityError`'s validators, which kept rejecting
  anything but `QC_` -- contradicting "full" above. Fixed by widening
  those validators to also accept `ZEO_`/`ZC_`, rather than retroactively
  editing this historical entry.
- Fixed a broken version-sourcing path and a production test-detection bug
  found during the extraction (see git history for detail).

### Fixed

- CI now runs the full test suite on every supported Python version
  (3.10-3.13) on real GitHub Actions infrastructure. That surfaced three
  real, previously-invisible cross-version bugs (this package's own
  pre-release local development only ever ran on 3.13), all fixed and
  independently verified across every supported version before release:
  - A `pathlib.Path.__init__`/`__new__` split changed in CPython 3.12;
    an autouse test fixture that monkeypatched `Path.__init__` only was
    crashing the entire test suite on 3.10/3.11 with an `INTERNALERROR`.
    Fixed by coercing on both `__new__` and `__init__`, matching whichever
    one actually does the real work on a given Python version.
  - `unittest.mock`'s dotted-string `@patch(...)` target resolution
    changed in 3.11 (`pkgutil.resolve_name` instead of an eager
    `getattr`-walk). Three call sites depended on the newer resolution
    semantics to reach their intended target; on 3.10 they silently
    patched the wrong object, cascading into shared-state pollution across
    unrelated test files.
  - `typing.Protocol.__instancecheck__`'s structural-membership check
    changed in 3.12 (from plain `hasattr` to `inspect.getattr_static`,
    which does not trigger `MagicMock`'s attribute auto-fabrication).
    Five tests asserting that a bare, unconfigured `MagicMock()` does
    *not* satisfy a runtime-checkable protocol passed on 3.12/3.13 but
    failed on 3.10/3.11. Fixed by constructing the mocks with an explicit
    `spec=`, which is version-stable and expresses the real test intent.

### Removed

- The `BaseZeoToolPlugin` back-compat alias -- unused outside this repo's
  own test suite, and this package has never had a public release, so no
  back-compat was owed for it.

[0.1.0]: https://github.com/zeroemployeeorg/zeocore/releases/tag/v0.1.0
