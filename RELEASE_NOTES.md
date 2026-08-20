# zeocore 0.2.0

First feature release since the initial extraction (0.1.0). This release makes zeocore
substantially easier for AI coding agents (Claude Code, Cursor) to build against, adds three
real integrations, brings the Anthropic client current, and fixes a real cross-suite test bug.

## ⚠️ Breaking change

**Python floor raised from `>=3.10` to `>=3.13`.** Python 3.10 has been security-only since
October 2023 and reaches full end-of-life in October 2026; 3.13 is also the floor the new
`ffmpeg` extra needs (`ffmpeg-zeo` requires Python >=3.12). If you're pinned below 3.13, stay
on a `0.1.x` release of this package until you can upgrade your interpreter.

## What's new

**MCP server** (`zeocore[mcp]`) — expose zeocore tools directly to Claude Code, Cursor, and
other MCP-native coding agents. Any tool built on `BaseZeoTool` becomes MCP-callable with zero
MCP-specific code: `register_tool()` derives the MCP tool definition mechanically from the
tool's own type hints and registers it into the same `OperationRegistry` the HTTP adapter
already reads — one registration reaches both adapters. See `examples/mcp_server_usage.py` and
the new tutorial at `docs/tutorials/mcp-server-with-claude-code.md`.

**Notion integration** (`zeocore[notion]`) — full read and write: search, get/query pages and
databases, create/update pages, append blocks. Bearer-token auth (Notion's own model). See
`examples/notion_usage.py` and `docs/tutorials/notion-integration.md`.

**Jupytext integration** (`zeocore[jupytext]`) — script ↔ notebook conversion
(`script_to_notebook()`, `notebook_to_script()`). See `examples/jupytext_usage.py`.

**FFmpeg integration** (`zeocore[ffmpeg]`) — wraps the org's own `ffmpeg-zeo` package (not the
raw binary): probe, convert, transcode to H.264, extract audio, generate thumbnails. See
`examples/ffmpeg_usage.py`.

**LLM prompt caching** — `LLMOptions.cache_system_prompt` marks the system prompt cacheable via
Anthropic's `cache_control: ephemeral` breakpoints. Provider-agnostic; a no-op on providers
without caching support.

## Fixed

- Anthropic client's default model updated (the previous default was retired 2026-01-05).
  Tool-use *requests* now pass through correctly to Anthropic's API shape.
  **Known gap, not yet closed in this release**: tool-use *responses* are not yet parsed back
  into structured output — see GET-STARTED.md's LLM providers section.
- `zeo_core.integrations.google` now re-exports `GoogleDriveService`/`GoogleMailService` at the
  shallow path.
- `CapabilityResult` re-exported from the top-level `zeo_core` package.
- GET-STARTED.md's configuration quick-start corrected to a real, runnable example.
- `make install-all` was silently skipping the MCP adapter's own dependencies — fixed.
- A cross-suite test failure (`test_configure_logger_attaches_real_file_handler`) was
  root-caused to a filesystem-service singleton leaking a stale working directory across tests,
  and fixed.

## Evaluated, not shipped

Database integration (BigQuery, Supabase, SQLite) was researched this cycle and deliberately
**not built**: BigQuery has zero consumers anywhere in the org; Supabase's only real consumer is
a TypeScript app architecturally unreachable from this Python package; SQLite is buildable but
not urgent. See `CHANGELOG.md`'s "Research (no code shipped)" entry for the full reasoning.

## Upgrading

```bash
pip install --upgrade zeocore
```

If you were relying on Python 3.10–3.12, hold at `zeocore<0.2` until you can move to 3.13.

Full diff: https://github.com/zeroemployeeorg/zeocore/compare/v0.1.0...v0.2.0
