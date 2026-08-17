# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
  keys.
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
