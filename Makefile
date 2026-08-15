# ============================================================
# QuackVerse — quack-core Makefile
# ============================================================
# Python monorepo. The one gate that matters is `make verify-full`:
#   format-check -> ruff -> mypy (strict) -> hygiene-check -> pytest+coverage
# run against a clean editable install with fresh caches.
#
# Doctrine this gate enforces (see WORK-POLICY handout):
#   - mypy is the closest thing Python has to `tsc`. It only checks what
#     is annotated, so NEW/CHANGED code must be fully typed or it is not
#     actually gated.
#   - The test run is the verdict. Green mypy is necessary, not sufficient.
#   - Production code must NEVER detect that it is under test
#     (no inspect.stack(), no "pytest" in sys.modules in shipped paths).
#     hygiene-check fails the build if it finds this.
# ============================================================

# Terminal colors
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
WHITE  := $(shell tput -Txterm setaf 7)
RESET  := $(shell tput -Txterm sgr0)
BLUE   := $(shell tput -Txterm setaf 4)
RED    := $(shell tput -Txterm setaf 1)

SHELL := /bin/bash

# Project settings
PYTHON_VERSION := 3.13
VENV_NAME := .venv
PROJECT_NAME := quack-core
REPO_ROOT := $(shell pwd)
PYTHON := $(REPO_ROOT)/$(VENV_NAME)/bin/python
SRC := quack-core/src
PKG_SRC := quack-core/src/quack_core
TESTS := quack-core/tests

# Prefer venv python if present, otherwise fall back to system python3/python
PYTHON_BIN := $(shell \
  if [ -x "$(PYTHON)" ]; then echo "$(PYTHON)"; \
  elif command -v python3 >/dev/null 2>&1; then echo python3; \
  elif command -v python >/dev/null 2>&1; then echo python; \
  else echo ""; fi)

# Test settings
PYTEST_ARGS ?= -v
COVERAGE_THRESHOLD := 90

RUN_ARGS ?= --help

AGGREGATE_TARGET = $(if $(filter-out aggregate,$(MAKECMDGOALS)),$(filter-out aggregate,$(MAKECMDGOALS)),.)

.DEFAULT_GOAL := help

help: ## Show this help message
	@echo ''
	@echo '${YELLOW}QuackVerse / quack-core — Development Guide${RESET}'
	@echo ''
	@echo '${YELLOW}Setup:${RESET}'
	@echo '  ${GREEN}make setup${RESET}            - Full dev environment (env + install + dev tools)'
	@echo '  ${GREEN}make check-env${RESET}        - Verify installation'
	@echo ''
	@echo '${YELLOW}THE GATE (run before every commit):${RESET}'
	@echo '  ${GREEN}make verify${RESET}           - format-check + ruff + mypy + hygiene + tests (fast gate)'
	@echo '  ${GREEN}make verify-full${RESET}      - clean install + the full gate (slow, complete, trustworthy)'
	@echo ''
	@echo '${YELLOW}Individual checks:${RESET}'
	@echo '  ${GREEN}make format${RESET}           - Auto-fix formatting (ruff + isort) — mutates files'
	@echo '  ${GREEN}make format-check${RESET}     - Check formatting only — never mutates'
	@echo '  ${GREEN}make lint${RESET}             - ruff check + ruff format --check'
	@echo '  ${GREEN}make typecheck${RESET}        - mypy (strict)'
	@echo '  ${GREEN}make hygiene-check${RESET}    - fail if production code detects tests'
	@echo '  ${GREEN}make test${RESET}             - pytest with coverage (runs ONCE)'
	@echo ''
	@echo '${YELLOW}Inspection:${RESET}'
	@echo '  ${GREEN}make structure${RESET}        - Project structure + hotspots'
	@echo '  ${GREEN}make aggregate <dir>${RESET}  - Aggregate files from a directory'
	@echo '  ${GREEN}make flatten SCOPE=...${RESET} - Flatten a subtree for LLM context'
	@echo ''
	@echo '${YELLOW}All targets:${RESET}'
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_.-]+:.*## / {printf "  ${YELLOW}%-18s${GREEN}%s${RESET}\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ''

# ============================================================
# Environment
# ============================================================
.PHONY: env
env: ## Create virtual environment using uv
	@echo "${BLUE}Creating virtual environment...${RESET}"
	uv venv --python $(PYTHON_VERSION)
	@echo "${GREEN}Virtual environment created. Activate: source $(VENV_NAME)/bin/activate${RESET}"

.PHONY: install-quackcore
install-quackcore: ## Install quack-core (editable)
	@echo "${BLUE}Installing quack-core...${RESET}"
	@if [ ! -f "$(PYTHON)" ]; then \
	   echo "${YELLOW}Virtual environment not found. Creating it first...${RESET}"; \
	   $(MAKE) --no-print-directory env; \
	fi
	cd quack-core && uv pip install -e . --python $(PYTHON)
	@echo "${GREEN}quack-core installed${RESET}"
	@echo "${BLUE}Verifying import (no sys.path hacks allowed)...${RESET}"
	@$(PYTHON) -c "import quack_core; print(f'OK: quack_core at {quack_core.__file__}')" || \
	  (echo "${RED}Import failed — package is not cleanly installable. This is a doctrine failure, not a warning.${RESET}" && exit 1)

.PHONY: install-all
install-all: install-quackcore ## Install quack-core with all optional integrations
	@echo "${BLUE}Installing optional integration dependencies...${RESET}"
	cd quack-core && uv pip install -e ".[gmail,notion,google,drive,pandoc,llms,github,http]" --python $(PYTHON)
	@echo "${GREEN}All integration dependencies installed${RESET}"

.PHONY: install-dev
install-dev: ## Install development dependencies
	@echo "${BLUE}Installing development tools...${RESET}"
	@if [ ! -f "$(PYTHON)" ]; then $(MAKE) --no-print-directory env; fi
	cd quack-core && uv pip install -e ".[dev]" --python $(PYTHON)
	uv pip install -e ".[dev]" --python $(PYTHON)
	@echo "${GREEN}Development dependencies installed${RESET}"

.PHONY: install-lint
install-lint: ## Install Tier-1 architecture linters (.[lint] extra — import-linter)
	@echo "${BLUE}Installing architecture linters (.[lint])...${RESET}"
	@if [ ! -f "$(PYTHON)" ]; then $(MAKE) --no-print-directory env; fi
	cd quack-core && uv pip install -e ".[lint]" --python $(PYTHON)
	@echo "${GREEN}Architecture linters installed${RESET}"

.PHONY: setup
setup: ## Create environment and install full development dependencies
	@echo "${BLUE}Creating complete development environment...${RESET}"
	$(MAKE) --no-print-directory env
	$(MAKE) --no-print-directory install-all
	$(MAKE) --no-print-directory install-dev
	@echo ""
	@echo "${GREEN}Setup complete. Activate: source .venv/bin/activate${RESET}"

.PHONY: check-env
check-env: ## Check that the virtual environment is active and working
	@echo "${BLUE}Checking environment...${RESET}"
	@if [ ! -f "$(PYTHON)" ]; then \
	   echo "${RED}Virtual environment not found at $(PYTHON). Run 'make setup'.${RESET}"; exit 1; \
	fi
	@$(PYTHON) --version
	@$(PYTHON) -c "import sys; print(f'Python executable: {sys.executable}')"
	@$(PYTHON) -c "import quack_core; print(f'quack_core: {quack_core.__file__}')" 2>/dev/null || \
	  echo "${YELLOW}quack_core not importable yet — run 'make install-quackcore'${RESET}"
	@echo "${GREEN}Environment check complete${RESET}"

# ============================================================
# THE GATE — verify / verify-full
# ============================================================
# verify       = the fast doctrine gate (no reinstall). Run before every commit.
# verify-full  = the complete gate: clean caches + fresh editable install first,
#                so it cannot pass on stale bytecode or a broken package layout.
#                This is the TS `verify-full` equivalent, adapted to Python.

.PHONY: verify
verify: ## The doctrine gate: format-check + ruff + mypy + hygiene + tests
	@echo "${BLUE}Running doctrine gate...${RESET}"
	@echo ""
	@echo "${BLUE}[1/8] format-check${RESET}"
	@$(MAKE) --no-print-directory format-check
	@echo ""
	@echo "${BLUE}[2/8] ruff lint${RESET}"
	@$(MAKE) --no-print-directory lint
	@echo ""
	@echo "${BLUE}[3/8] mypy (strict)${RESET}"
	@$(MAKE) --no-print-directory typecheck
	@echo ""
	@echo "${BLUE}[4/8] arch-check (import-linter directional contracts)${RESET}"
	@$(MAKE) --no-print-directory arch-check
	@echo ""
	@echo "${BLUE}[5/8] hygiene-check (no test-detection in production code)${RESET}"
	@$(MAKE) --no-print-directory hygiene-check
	@echo ""
	@echo "${BLUE}[6/8] hygiene-secrets${RESET}"
	@$(MAKE) --no-print-directory hygiene-secrets
	@echo ""
	@echo "${BLUE}[7/8] plugin-boundary${RESET}"
	@$(MAKE) --no-print-directory plugin-boundary
	@echo ""
	@echo "${BLUE}[8/8] tests + coverage${RESET}"
	@$(MAKE) --no-print-directory test
	@echo ""
	@echo "${GREEN}✓ verify complete: doctrine gate passes${RESET}"

.PHONY: verify-full
verify-full: ## verify, preceded by clean caches + fresh editable install (slow, complete)
	@echo "${BLUE}Running FULL verification (fresh install, no stale state)...${RESET}"
	@$(MAKE) --no-print-directory clean-caches
	@$(MAKE) --no-print-directory install-all
	@$(MAKE) --no-print-directory install-dev
	@$(MAKE) --no-print-directory install-lint
	@$(MAKE) --no-print-directory verify
	@echo ""
	@echo "${GREEN}✓ verify-full complete: system is healthy on a clean install${RESET}"

# --- Individual gate steps ---------------------------------

.PHONY: format
format: ## Format code with Ruff + isort (MUTATES files — not part of the gate)
	@echo "${BLUE}Formatting code...${RESET}"
	$(PYTHON) -m ruff check $(SRC) $(TESTS) examples/ --fix
	$(PYTHON) -m ruff format $(SRC) $(TESTS) examples/
	$(PYTHON) -m isort $(SRC) $(TESTS) examples/

.PHONY: format-check
format-check: ## Check formatting only (never mutates — gate-safe)
	@echo "${BLUE}Checking formatting...${RESET}"
	$(PYTHON) -m ruff format --check $(SRC) $(TESTS) examples/

.PHONY: lint
lint: ## Run ruff lint + format-check
	@echo "${BLUE}Running ruff...${RESET}"
	$(PYTHON) -m ruff check $(SRC) $(TESTS) examples/

.PHONY: typecheck
typecheck: ## Run mypy in strict mode (the closest thing to tsc)
	@echo "${BLUE}Running mypy (strict)...${RESET}"
	# RULING-111 s1: quack-core is a HYPHENATED directory, not a legal Python package
	# name, so a plain path-mode mypy target beneath it (tests/, examples/) walks up and
	# aborts "quack-core is not a valid Python package name". Option A (-p quack_core,
	# src-only) was the ruled INTERIM fix, narrowing the gate and filing tests/examples
	# coverage as a debt. Ruling authorized exactly ONE recon block to test Option D
	# (explicit_package_bases + mypy_path including quack-core) as a config-only way to
	# keep full scope. D's falsifier (a walk-up "not a valid Python package name" abort
	# on quack-core/tests or examples/) did NOT fire -- see quackverse-repo-hygiene chain,
	# rev 34/n:35, for the verbatim recon output. Per s1 ("if it resolves, D supersedes A
	# before A is even committed"), D is what ships: full three-target scope restored,
	# config only, no restructure, no deletion.
	MYPYPATH="$(REPO_ROOT)/quack-core" $(PYTHON) -m mypy --explicit-package-bases $(SRC) $(TESTS) examples/

.PHONY: hygiene-check
hygiene-check: ## Fail if production code detects that it is under test (RULING-111 s2/s2a: widened)
	@echo "${BLUE}Checking for test-detection in production code...${RESET}"
	@offenders=$$(grep -rEn 'inspect\.stack\(\)|["'"'"']pytest["'"'"'] +in +sys\.modules|_is_test_environment|f_locals|_mock_name|__name__ *== *["'"'"']MagicMock["'"'"']' $(PKG_SRC) 2>/dev/null || true); \
	if [ -n "$$offenders" ]; then \
	  echo "${RED}✗ Production code must not detect tests (green instrument, wrong render):${RESET}"; \
	  echo "$$offenders" | sed 's/^/    /'; \
	  echo "${YELLOW}  Move the behavior into the test, or inject it. See WORK-POLICY handout.${RESET}"; \
	  exit 1; \
	fi
	@echo "${GREEN}✓ hygiene OK — no mechanism-based or mock-duck-typed test-detection in production paths${RESET}"
	@echo "${YELLOW}  BLIND SPOT (RULING-111 s2a-2, by design, not a gap in this gate): arbitrary${RESET}"
	@echo "${YELLOW}  VALUE-BASED fakery (e.g. \`if path == \"test.md\": return fake_result\`) is NOT${RESET}"
	@echo "${YELLOW}  mechanically detectable -- a pattern broad enough to catch every literal fires${RESET}"
	@echo "${YELLOW}  on legitimate value handling too. This gate catches MECHANISM (stack/frame${RESET}"
	@echo "${YELLOW}  introspection, sys.modules test-env checks) and MOCK DUCK-TYPING (_mock_name,${RESET}"
	@echo "${YELLOW}  MagicMock type checks). Value-based fakery needs human review. GREEN HERE means${RESET}"
	@echo "${YELLOW}  clean of what this instrument can see, not clean absolutely.${RESET}"

.PHONY: test
test: ## Run tests with coverage (ONCE — fixed from the old doubled run)
	@echo "${BLUE}Running tests with coverage...${RESET}"
	cd quack-core && \
	PYTHONPATH="$(REPO_ROOT)/$(SRC):$(REPO_ROOT)/$(TESTS):$(PYTHONPATH)" \
	$(PYTHON) -m pytest tests $(PYTEST_ARGS) \
	  --cov=quack_core --cov-report=term-missing \
	  --cov-fail-under=$(COVERAGE_THRESHOLD)

.PHONY: test-fast
test-fast: ## Run tests without coverage (quick inner-loop feedback)
	@echo "${BLUE}Running tests (no coverage)...${RESET}"
	cd quack-core && \
	PYTHONPATH="$(REPO_ROOT)/$(SRC):$(REPO_ROOT)/$(TESTS):$(PYTHONPATH)" \
	$(PYTHON) -m pytest tests $(PYTEST_ARGS)

.PHONY: test-module
test-module: ## Run one module's tests: make test-module M=test_integrations/pandoc
	@test -n "$(M)" || (echo "Usage: make test-module M=test_integrations/pandoc" && exit 1)
	cd quack-core && \
	PYTHONPATH="$(REPO_ROOT)/$(SRC):$(REPO_ROOT)/$(TESTS):$(PYTHONPATH)" \
	$(PYTHON) -m pytest tests/$(M) $(PYTEST_ARGS) --cov=quack_core --cov-report=term-missing

# ============================================================
# HTTP adapter
# ============================================================
.PHONY: api-run
api-run: ## Run HTTP adapter server
	@echo "${BLUE}Starting quack_core HTTP adapter...${RESET}"
	cd quack-core && \
	PYTHONPATH="$(REPO_ROOT)/$(SRC):$(PYTHONPATH)" \
	$(REPO_ROOT)/$(VENV_NAME)/bin/uvicorn quack_core.adapters.http.app:create_app --factory --host 0.0.0.0 --port 8080

.PHONY: api-run-reload
api-run-reload: ## Run HTTP adapter with auto-reload
	cd quack-core && \
	PYTHONPATH="$(REPO_ROOT)/$(SRC):$(PYTHONPATH)" \
	$(REPO_ROOT)/$(VENV_NAME)/bin/uvicorn quack_core.adapters.http.app:create_app --factory --reload --host 0.0.0.0 --port 8080

.PHONY: api-test
api-test: ## Run HTTP adapter tests (cov path FIXED: quack_core.adapters.http)
	@echo "${BLUE}Running HTTP adapter tests...${RESET}"
	cd quack-core && \
	PYTHONPATH="$(REPO_ROOT)/$(SRC):$(REPO_ROOT)/$(TESTS)/test_http:$(PYTHONPATH)" \
	$(PYTHON) -m pytest tests/test_http $(PYTEST_ARGS) \
	  --cov=quack_core.adapters.http --cov-report=term-missing

# ============================================================
# Clean
# ============================================================
.PHONY: clean-caches
clean-caches: ## Remove test/type/lint caches and compiled bytecode (fast, safe)
	@echo "${BLUE}Clearing caches...${RESET}"
	@rm -rf .coverage .mypy_cache .pytest_cache .ruff_cache
	@cd quack-core && rm -rf .coverage .mypy_cache .pytest_cache .ruff_cache 2>/dev/null || true
	@find . -type d -name "__pycache__" -not -path "./$(VENV_NAME)/*" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -not -path "./$(VENV_NAME)/*" -delete 2>/dev/null || true
	@echo "${GREEN}✓ caches cleared${RESET}"

.PHONY: clean
clean: clean-caches ## Remove build artifacts + caches (keeps venv)
	@echo "${BLUE}Cleaning build artifacts...${RESET}"
	@rm -rf build/ dist/ *.egg-info
	@cd quack-core && rm -rf build/ dist/ *.egg-info 2>/dev/null || true
	@echo "${GREEN}✓ cleaned${RESET}"

.PHONY: clean-all
clean-all: clean ## Remove everything including the virtual environment
	@echo "${BLUE}Removing virtual environment...${RESET}"
	@rm -rf $(VENV_NAME)
	@echo "${GREEN}✓ cleaned all (venv removed — run 'make setup' to rebuild)${RESET}"

# ============================================================
# Inspection / navigation
# ============================================================
.PHONY: aggregate
aggregate: ## Aggregate text files from a directory (usage: make aggregate <dir>)
	@echo "${BLUE}Aggregating files from: ${AGGREGATE_TARGET}${RESET}"
	@$(PYTHON_BIN) scripts/aggregate.py "$(AGGREGATE_TARGET)"

# Dummy target so bare directory args to `aggregate` don't error
%:
	@:

.PHONY: structure
structure: ## Show project structure + hotspots
	@echo "${YELLOW}Project Summary:${RESET}"
	@echo "  Python: $$( [ -n "$(PYTHON_BIN)" ] && $(PYTHON_BIN) -V 2>/dev/null || echo 'n/a')"
	@echo "  Git branch: $$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'n/a')"
	@echo "  Files: $$(find . -type f -not -path './.git/*' -not -path './.venv/*' -not -path './_transient-files/*' -not -path './.idea/*' -not -path './.hypothesis/*' | wc -l | tr -d ' ')"
	@echo ""
	@$(MAKE) --no-print-directory structure-insights

.PHONY: structure-insights
structure-insights: ## Repo hotspots (largest dirs / file counts)
	@echo "${YELLOW}Hotspots (by file count):${RESET}"
	@find . -type f \
	   -not -path './.git/*' -not -path './.venv/*' \
	   -not -path './_transient-files/*' -not -path './.idea/*' -not -path './.hypothesis/*' \
	   | sed 's|^\./||' | awk -F/ '{print $$1}' \
	   | sort | uniq -c | sort -nr | head -n 12 \
	   | awk '{printf "  %-6s %s\n", $$1, $$2}'

.PHONY: structure-tree
structure-tree: ## Directory tree (filtered)
	@IGNORE='\.git|\.venv|__pycache__|\.DS_Store|_transient-files|\.idea|\.hypothesis|\.pytest_cache|\.ruff_cache|\.mypy_cache|build|dist|.*\.egg-info'; \
	if command -v tree > /dev/null; then tree -a -I "$$IGNORE"; \
	else find . -not -path './.git/*' -not -path './.venv/*' -not -path './__pycache__/*' | sort; fi

.PHONY: prune-branches
prune-branches: ## Remove local branches no longer tracked on the remote
	@$(PYTHON_BIN) scripts/prune_branches.py

# ============================================================
# Flatten — LLM context bundles
# ============================================================
FLATTEN_OUT ?= _transient-files/flatten
FLATTEN_EXT ?= .py,.yaml,.yml,.toml,.env,.example,.md
FLATTEN_SKIP ?= .git,.venv,__pycache__,.mypy_cache,.pytest_cache,.ruff_cache,build,dist,.egg-info,node_modules
FLATTEN_SCOPE ?= .
MAX_BYTES ?= 4000000
MAX_FILES ?=

.PHONY: flatten
flatten: ## Flatten files for LLM context (defaults to repo root; override SCOPE=path)
	@echo "${BLUE}Flattening '$(or $(SCOPE),$(FLATTEN_SCOPE))' into $(FLATTEN_OUT)...${RESET}"
	@mkdir -p "$(FLATTEN_OUT)"
	@$(PYTHON) scripts/flatten.py \
	   --mode scope --scope "$(or $(SCOPE),$(FLATTEN_SCOPE))" \
	   --out-dir "$(FLATTEN_OUT)" --extensions "$(FLATTEN_EXT)" --skip-dirs "$(FLATTEN_SKIP)" \
	   --exclude "_transient-files/**" \
	   $(if $(MAX_FILES),--max-files $(MAX_FILES),) $(if $(MAX_BYTES),--max-bytes $(MAX_BYTES),)
	@echo "${GREEN}✓ See: $(FLATTEN_OUT)/manifest.md${RESET}"

.PHONY: flatten-clean
flatten-clean: ## Remove flatten outputs
	@rm -rf "$(FLATTEN_OUT)"

# ============================================================
# QV-LLM headers
# ============================================================
ANNOTATE_SCOPE ?= .
ANNOTATE_EXT ?= .py,.yaml,.yml,.toml,.env
ANNOTATE_MAX_NEIGHBORS ?= 6

.PHONY: annotate
annotate: ## Add/update full QV-LLM header blocks (path/module/role/neighbors/exports/git)
	@$(PYTHON) scripts/annotate_headers.py \
	   --scope "$(ANNOTATE_SCOPE)" --extensions "$(ANNOTATE_EXT)" \
	   --max-neighbors "$(ANNOTATE_MAX_NEIGHBORS)" --remove-legacy-path-line \
	   --mode full

.PHONY: annotate-strip
annotate-strip: ## Reduce existing QV-LLM blocks to path-only (min tokens, still re-annotatable)
	@$(PYTHON) scripts/annotate_headers.py \
	   --scope "$(ANNOTATE_SCOPE)" --extensions "$(ANNOTATE_EXT)" \
	   --mode strip

.PHONY: annotate-remove
annotate-remove: ## Delete QV-LLM header blocks entirely, no trace left
	@$(PYTHON) scripts/annotate_headers.py \
	   --scope "$(ANNOTATE_SCOPE)" --extensions "$(ANNOTATE_EXT)" \
	   --mode remove

.PHONY: arch-check
arch-check: ## Enforce directional import contracts (.importlinter via import-linter)
	@echo "${BLUE}Checking import architecture (.importlinter)...${RESET}"
	@$(VENV_NAME)/bin/lint-imports || ($(PYTHON) -m importlinter lint)
	@echo "${GREEN}✓ arch OK — directional import contracts kept${RESET}"

# Tier-1 grep-ban gate targets (Track C)
include hygiene-grepbans.mk
