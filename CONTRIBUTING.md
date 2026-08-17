# Contributing to ZeoCore

Thanks for considering a contribution. This document covers how to set up a
dev environment, what the verification gate expects, and how to add tests.

## Development setup

This repo uses [`uv`](https://github.com/astral-sh/uv) for environment and
dependency management, wired up through `make`:

```bash
git clone https://github.com/zeroemployeeorg/zeocore.git
cd zeocore
make setup
```

`make setup` creates a `.venv` (Python 3.13 by default -- see `PYTHON_VERSION`
in the Makefile; the package itself supports 3.10+), installs `zeocore` in
editable mode with all optional integrations, and installs the `dev` and
`lint` extras. Activate it with:

```bash
source .venv/bin/activate
```

Run `make help` at any point to see every available target.

## Before you open a PR: the gate

This repo has one gate that matters: `make verify`. Run it before every
commit you intend to submit:

```bash
make verify
```

It runs, in order: `format-check` -> `ruff` lint -> `mypy` (strict) ->
`arch-check` (import-linter directional contracts) -> `hygiene-check` (fails
if production code detects it's under test) -> `hygiene-secrets` ->
`plugin-boundary` -> the test suite with coverage (floor: 90%).

For a slower, more thorough version that reinstalls from a clean environment
first (catches issues that stale caches or a broken package layout would
hide), use:

```bash
make verify-full
```

A PR that doesn't pass `make verify` won't merge cleanly -- run it locally
first, not just in CI.

### Individual checks

If you want faster inner-loop feedback while iterating:

```bash
make format        # auto-fix formatting with ruff + isort (mutates files)
make lint           # ruff check + format --check
make typecheck       # mypy --strict
make test-fast       # pytest without coverage
make test-module M=test_fs   # run one module's tests with coverage
```

## Code style

- **Linting**: [ruff](https://docs.astral.sh/ruff/), configured in
  `pyproject.toml`'s `[tool.ruff]` / `[tool.ruff.lint]`. Enabled rule sets
  include pycodestyle (E/W), pyflakes (F), isort (I), flake8-comprehensions
  (C), flake8-bugbear (B), pyupgrade (UP), pep8-naming (N),
  flake8-annotations (ANN), flake8-bandit (S), and flake8-builtins (A).
  Line length is 88, double-quote strings.
- **Type checking**: [mypy](https://mypy-lang.org/) in strict mode
  (`disallow_untyped_defs`, `disallow_incomplete_defs`,
  `warn_return_any`, etc -- see `[tool.mypy]` in `pyproject.toml`). New or
  changed code must be fully typed; mypy only checks what's annotated, so
  untyped code isn't actually gated.
- **Import architecture**: `import-linter` enforces the directional
  contracts declared in `.importlinter` (checked by `make arch-check`).
- **No test-detection in production code**: production code (`src/zeo_core`)
  must never branch on whether it's running under test (no
  `inspect.stack()`, no `"pytest" in sys.modules`, etc). `make hygiene-check`
  fails the build if it finds this pattern. If a test needs different
  behavior, inject it (a parameter, a fixture, a fake) rather than having
  production code sniff its caller.

## Adding tests

- Tests live under `tests/`, mirroring `src/zeo_core/`'s module layout --
  see `tests/README.md` for the full structure and the fixtures available
  in `tests/conftest.py`.
- Test both success and failure paths, not just the happy path.
- Prefer the dedicated mock classes already present in each test package
  over ad hoc `MagicMock` wiring, for consistency with existing tests.
- The coverage floor is 90% (`--cov-fail-under=90` in `make test`); a PR
  that drops coverage below that will fail the gate.
- `hypothesis` is available for property-based testing where it adds real
  value (see the `dev` extra in `pyproject.toml`).

## Submitting a change

1. Fork the repository and create a branch for your change.
2. Make your change, with tests.
3. Run `make verify` locally and confirm it passes clean.
4. Open a pull request describing what changed and why.

## Reporting issues

Please open a GitHub issue with a clear description, steps to reproduce (for
bugs), and your Python/zeocore version.
