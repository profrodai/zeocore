# Terminal colors
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
WHITE  := $(shell tput -Txterm setaf 7)
RESET  := $(shell tput -Txterm sgr0)
BLUE   := $(shell tput -Txterm setaf 4)

# Project settings
PYTHON_VERSION := 3.13
VENV_NAME := .venv
PROJECT_NAME := quack-core
REPO_ROOT := $(shell pwd)
PYTHON := $(REPO_ROOT)/$(VENV_NAME)/bin/python
# Prefer venv python if present, otherwise fall back to system python3/python, otherwise blank
PYTHON_BIN := $(shell \
  if [ -x "$(PYTHON)" ]; then echo "$(PYTHON)"; \
  elif command -v python3 >/dev/null 2>&1; then echo python3; \
  elif command -v python >/dev/null 2>&1; then echo python; \
  else echo ""; fi)


# Test settings
TEST_PATH := tests/
PYTEST_ARGS ?= -v
COVERAGE_THRESHOLD := 90

RUN_ARGS ?= --help

# Aggregate settings - use first argument or current directory
AGGREGATE_TARGET = $(if $(filter-out aggregate,$(MAKECMDGOALS)),$(filter-out aggregate,$(MAKECMDGOALS)),.)

help: ## Show this help message
	@echo ''
	@echo '${YELLOW}Development Guide${RESET}'
	@echo ''
	@echo '${YELLOW}Installation Options:${RESET}'
	@echo '  Quackcore:    ${GREEN}make install-quackcore${RESET}   - Install quack-core'
	@echo '  All:        ${GREEN}make install-all${RESET}        - Install both packages'
	@echo '  Development:${GREEN}make install-dev${RESET}        - Development tools'
	@echo ''
	@echo '${YELLOW}Development Workflow:${RESET}'
	@echo '  1. Setup:     ${GREEN}make setup${RESET}              - Full development environment'
	@echo '  2. Activate:  ${GREEN}source .venv/bin/activate${RESET} - Activate environment'
	@echo '  3. Check:     ${GREEN}make check-env${RESET}          - Verify installation'
	@echo ''
	@echo '${YELLOW}Quick Setup:${RESET}'
	@echo '  All-in-one:  ${GREEN}make quick-setup${RESET}         - Fast complete setup'
	@echo ''
	@echo '${YELLOW}File Operations:${RESET}'
	@echo '  Aggregate:   ${GREEN}make aggregate <directory>${RESET}  - Aggregate files from directory'
	@echo '               ${GREEN}make aggregate${RESET}             - Aggregate files from current directory'
	@echo ''
	@echo '${YELLOW}Available Targets:${RESET}'
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_.-]+:.*## / {printf "  ${YELLOW}%-15s${GREEN}%s${RESET}\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ''

# Development environment targets
.PHONY: env
env: ## Create virtual environment using uv
	@echo "${BLUE}Creating virtual environment...${RESET}"
	uv venv --python $(PYTHON_VERSION)
	@echo "${GREEN}Virtual environment created. Activate it with:${RESET}"
	@echo "source $(VENV_NAME)/bin/activate"

.PHONY: install-quackcore
install-quackcore: ## Install quackcore package
	@echo "${BLUE}Installing quack-core package...${RESET}"
	@# Ensure we're using the virtual environment
	@if [ ! -f "$(PYTHON)" ]; then \
	   echo "${YELLOW}Virtual environment not found. Creating it first...${RESET}"; \
	   make env; \
	fi
	@# Install the package in editable mode using global uv but targeting the venv
	cd quack-core && uv pip install -e . --python $(REPO_ROOT)/$(VENV_NAME)/bin/python
	@echo "${GREEN}quack-core installed successfully${RESET}"
	@# Verify installation with proper PYTHONPATH
	@echo "${BLUE}Verifying installation...${RESET}"
	@PYTHONPATH="$(REPO_ROOT)/quack-core/src:$(PYTHONPATH)" $(PYTHON) -c "import quack_core; print(f'✓ quack-core installed at: {quack_core.__file__}')" || \
	(echo "${YELLOW}Warning: Import verification failed. This might be expected if package structure needs adjustment.${RESET}" && \
	 echo "${BLUE}Checking package installation status...${RESET}" && \
	 $(PYTHON) -m pip list | grep quack-core)

.PHONY: install-all
install-all: install-quackcore ## Install all packages with their optional dependencies
	@echo "${BLUE}Installing optional dependencies for all packages...${RESET}"
	cd quack-core && uv pip install -e ".[gmail,notion,google,drive,pandoc,llms,github,http]" --python $(REPO_ROOT)/$(VENV_NAME)/bin/python
	@echo "${GREEN}All packages and dependencies installed successfully${RESET}"

.PHONY: install-dev
install-dev: ## Install development dependencies for all packages
	@echo "${BLUE}Installing development tools...${RESET}"
	@# Ensure we have the virtual environment
	@if [ ! -f "$(PYTHON)" ]; then \
	   echo "${YELLOW}Virtual environment not found. Creating it first...${RESET}"; \
	   make env; \
	fi
	cd quack-core && uv pip install -e ".[dev]" --python $(REPO_ROOT)/$(VENV_NAME)/bin/python
	@# Install root development dependencies
	uv pip install -e ".[dev]" --python $(REPO_ROOT)/$(VENV_NAME)/bin/python
	@echo "${GREEN}Development dependencies installed successfully${RESET}"

.PHONY: setup
setup: ## Create environment and install full development dependencies
	@echo "${BLUE}Creating complete development environment...${RESET}"
	@echo "${YELLOW}Note: This will create a virtual environment but won't activate it automatically.${RESET}"
	@echo "${YELLOW}After completion, run: source .venv/bin/activate${RESET}"
	@echo ""
	make env
	@echo "${BLUE}Installing all packages and dependencies...${RESET}"
	make install-all
	make install-dev
	@echo ""
	@echo "${GREEN}Setup complete! Development environment ready.${RESET}"
	@echo "${YELLOW}To activate the environment, run:${RESET}"
	@echo "  ${GREEN}source .venv/bin/activate${RESET}"

.PHONY: setup-and-activate
setup-and-activate: ## Create environment, install dependencies, and generate activation helper
	@echo "${BLUE}Creating complete development environment...${RESET}"
	make env
	make install-all
	make install-dev
	@echo '#!/bin/bash' > activate_env.sh
	@echo 'source .venv/bin/activate' >> activate_env.sh
	@echo 'echo "QuackVerse development environment activated!"' >> activate_env.sh
	@echo 'echo "Python: $(which python)"' >> activate_env.sh
	@chmod +x activate_env.sh
	@echo ""
	@echo "${GREEN}Setup complete! Development environment ready.${RESET}"
	@echo "${YELLOW}To activate the environment, run:${RESET}"
	@echo "  ${GREEN}source activate_env.sh${RESET}"
	@echo ""
	@echo "${YELLOW}Or manually activate with:${RESET}"
	@echo "  ${GREEN}source .venv/bin/activate${RESET}"

.PHONY: check-env
check-env: ## Check if virtual environment is active and working
	@echo "${BLUE}Checking environment...${RESET}"
	@if [ ! -f "$(PYTHON)" ]; then \
	   echo "${YELLOW}Virtual environment not found at $(PYTHON)${RESET}"; \
	   echo "Run 'make env' first"; \
	   exit 1; \
	fi
	@echo "Python: $(PYTHON)"
	@$(PYTHON) --version
	@$(PYTHON) -c "import sys; print(f'Python executable: {sys.executable}')"
	@$(PYTHON) -m pip list | head -5
	@echo "${GREEN}Environment check complete${RESET}"

.PHONY: update
update: ## Update all dependencies
	@echo "${BLUE}Updating dependencies...${RESET}"
	make install-dev

.PHONY: aggregate
aggregate: ## Aggregate text files from a directory (usage: make aggregate <directory>)
	@echo "${BLUE}Aggregating files from: ${AGGREGATE_TARGET}${RESET}"
	@$(PYTHON_BIN) scripts/aggregate.py "$(AGGREGATE_TARGET)"
	@echo "${GREEN}✓ File aggregation completed${RESET}"

# Dummy target for directory arguments to aggregate
%:
	@:

.PHONY: test
test: ## Run tests with coverage
	@echo "${BLUE}Running tests with coverage...${RESET}"
	cd quack-core && \
	PYTHONPATH="$(REPO_ROOT)/quack-core/src:$(REPO_ROOT)/quack-core/tests:$(PYTHONPATH)" \
	$(REPO_ROOT)/$(VENV_NAME)/bin/python -m pytest tests -v --cov=src --cov-report=term-missing && \
	$(REPO_ROOT)/$(VENV_NAME)/bin/python -m pytest tests -v --cov=src --cov-report=term-missing

.PHONY: test-quackcore
test-quackcore: ## Run only quackcore tests
	@echo "${BLUE}Running quack-core tests...${RESET}"
	cd quack-core && \
	PYTHONPATH="$(REPO_ROOT)/quack-core/src:$(REPO_ROOT)/quack-core/tests:$(PYTHONPATH)" \
	$(REPO_ROOT)/$(VENV_NAME)/bin/python -m pytest tests -v --cov=src --cov-report=term-missing

.PHONY: test-integration
test-integration: ## Run only integration tests
	@echo "${BLUE}Running integration tests...${RESET}"
	PYTHONPATH="$(REPO_ROOT)/quack-core/src:$(PYTHONPATH)" \
	$(REPO_ROOT)/$(VENV_NAME)/bin/python -m pytest tests/integration $(PYTEST_ARGS) \
	   --cov=quack-core/src --cov-report=term-missing

.PHONY: test-module
test-module: ## Run only integration tests with coverage
	@echo "${BLUE}Running specific integration tests...${RESET}"
	$(PYTHON) -m pytest tests/test_integrations/pandoc $(PYTEST_ARGS) --cov=quack-core/src --cov-report=term-missing

.PHONY: format
format: ## Format code with Ruff and isort
	@echo "${BLUE}Formatting code...${RESET}"
	$(PYTHON) -m ruff check quack-core/src/ quack-core/tests/ examples/ --fix
	$(PYTHON) -m ruff format .
	$(PYTHON) -m isort .

.PHONY: lint
lint: ## Run linters
	@echo "${BLUE}Running linters...${RESET}"
	$(PYTHON) -m ruff check quack-core/src/ quack-core/tests/ examples/
	$(PYTHON) -m ruff format --check quack-core/src/ quack-core/tests/ examples/
	$(PYTHON) -m mypy quack-core/src/ quack-core/tests/ examples/

.PHONY: clean
clean: ## Clean build artifacts and cache
	@echo "${BLUE}Cleaning build artifacts and cache...${RESET}"
	rm -rf build/ dist/ *.egg-info .coverage .mypy_cache .pytest_cache .ruff_cache $(VENV_NAME)
	rm -rf setup.sh
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	# Clean subpackages
	cd quack-core && rm -rf build/ dist/ *.egg-info
	@echo "${GREEN}Cleaned all build artifacts and cache.${RESET}"

.PHONY: build
build: clean format lint test ## Build all packages for distribution
	@echo "${BLUE}Building packages for distribution...${RESET}"
	cd quack-core && uv build
	@echo "${GREEN}Packages built successfully. Distribution files in respective dist/ directories.${RESET}"

.PHONY: publish
publish: build ## Publish packages to PyPI
	@echo "${BLUE}Publishing packages to PyPI...${RESET}"
	@echo "${YELLOW}This will publish the following packages:${RESET}"
	@echo "  - quack_core"
	@echo "${YELLOW}Are you sure you want to continue? (y/n)${RESET}"
	@read -p " " yn; \
	if [ "$$yn" = "y" ]; then \
	   cd quack-core && uv publish --repository pypi; \
	   echo "${GREEN}All packages published successfully!${RESET}"; \
	else \
	   echo "${YELLOW}Publishing cancelled.${RESET}"; \
	fi

.PHONY: pre-commit
pre-commit: format lint test ## Run all checks before committing
	@echo "${GREEN}✓ All checks passed${RESET}"

.PHONY: structure
structure: ## Show project structure (filtered + summary)
	@echo "${YELLOW}Project Summary:${RESET}"
	@echo "  Python: $$( [ -n "$(PYTHON_BIN)" ] && $(PYTHON_BIN) -V 2>/dev/null || echo 'n/a')"
	@echo "  Git branch: $$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'n/a')"
	@echo "  Files: $$(find . -type f -not -path './.git/*' -not -path './.venv/*' -not -path './_transient-files/*' -not -path './.idea/*' -not -path './.hypothesis/*' | wc -l | tr -d ' ')"
	@echo "  Dirs:  $$(find . -type d -not -path './.git/*' -not -path './.venv/*' -not -path './_transient-files/*' -not -path './.idea/*' -not -path './.hypothesis/*' | wc -l | tr -d ' ')"
	@echo ""
	@$(MAKE) --no-print-directory structure-insights
	@echo ""
	@$(MAKE) --no-print-directory structure-tree

.PHONY: structure-tree
structure-tree:
	@echo "${YELLOW}Current Project Structure:${RESET}"
	@echo "${BLUE}"
	@IGNORE='\.git|\.venv|__pycache__|\.DS_Store|_transient-files|\.idea|\.hypothesis|\.pytest_cache|\.ruff_cache|\.mypy_cache|\.coverage|htmlcov|build|dist|.*\.egg-info'; \
	if command -v tree > /dev/null; then \
	   tree -a -I "$$IGNORE"; \
	else \
	   find . \
	      -not -path './.git/*' \
	      -not -path './.venv/*' \
	      -not -path './__pycache__/*' \
	      -not -path './_transient-files/*' \
	      -not -path './.idea/*' \
	      -not -path './.hypothesis/*' \
	      -not -name '.DS_Store' \
	      -not -path './.pytest_cache/*' \
	      -not -path './.ruff_cache/*' \
	      -not -path './.mypy_cache/*' \
	      -not -path './htmlcov/*' \
	      -not -path './build/*' \
	      -not -path './dist/*' \
	      -not -path './*.egg-info/*' \
	      | sort; \
	fi
	@echo "${RESET}"

.PHONY: structure-brief
structure-brief: ## High-signal structure view (2 levels)
	@echo "${YELLOW}High-signal Structure (2 levels):${RESET}"
	@echo "${BLUE}"
	@IGNORE='\.git|\.venv|__pycache__|\.DS_Store|_transient-files|\.idea|\.hypothesis|\.pytest_cache|\.ruff_cache|\.mypy_cache|\.coverage|htmlcov|build|dist|.*\.egg-info'; \
	tree -a -L 3 -I "$$IGNORE" .
	@echo "${RESET}"

.PHONY: structure-insights
structure-insights: ## Repo hotspots (largest dirs / file counts)
	@echo "${YELLOW}Hotspots (by file count):${RESET}"
	@find . -type f \
	   -not -path './.git/*' -not -path './.venv/*' \
	   -not -path './_transient-files/*' -not -path './.idea/*' -not -path './.hypothesis/*' \
	   | sed 's|^\./||' \
	   | awk -F/ '{print $$1}' \
	   | sort | uniq -c | sort -nr | head -n 12 \
	   | awk '{printf "  %-6s %s\n", $$1, $$2}'
	@echo ""
	@echo "${YELLOW}Largest subtrees (depth 2):${RESET}"
	@find . -type f \
	   -not -path './.git/*' -not -path './.venv/*' \
	   -not -path './_transient-files/*' -not -path './.idea/*' -not -path './.hypothesis/*' \
	   | sed 's|^\./||' \
	   | awk -F/ 'NF>=2 {print $$1"/"$$2}' \
	   | sort | uniq -c | sort -nr | head -n 12 \
	   | awk '{printf "  %-6s %s\n", $$1, $$2}'


.PHONY: prune-branches
prune-branches: ## Remove local branches that are no longer tracked on the remote
	@echo "${BLUE}Pruning local branches that are no longer tracked on the remote...${RESET}"
	@$(PYTHON_BIN) scripts/prune_branches.py
	@echo "${GREEN}Stale branches have been removed.${RESET}"

ANNOTATE_SCOPE ?= .
ANNOTATE_EXT ?= .py,.yaml,.yml,.toml,.env
ANNOTATE_MAX_NEIGHBORS ?= 6

.PHONY: annotate
annotate: ## Add/update QV-LLM header blocks across common repo files
	@$(PYTHON) scripts/annotate_headers.py \
	   --scope "$(ANNOTATE_SCOPE)" \
	   --extensions "$(ANNOTATE_EXT)" \
	   --max-neighbors "$(ANNOTATE_MAX_NEIGHBORS)" \
	   --remove-legacy-path-line

.PHONY: add-paths
add-paths: ## Python-only QV-LLM headers
	@$(PYTHON) scripts/annotate_headers.py --scope "$(or $(SCOPE),.)" --extensions ".py"


# --- Flatten defaults (override on CLI) ---
FLATTEN_OUT ?= _transient-files/flatten
FLATTEN_EXT ?= .py,.yaml,.yml,.toml,.env,.example,.md
FLATTEN_SKIP ?= .git,.venv,__pycache__,.mypy_cache,.pytest_cache,.ruff_cache,build,dist,.egg-info,node_modules

# Default to repo root; override with: make flatten SCOPE=quack-core/src/quack_core/lib/fs
FLATTEN_SCOPE ?= .

# Cap output to keep it shareable; override with: make flatten MAX_BYTES=8000000
MAX_BYTES ?= 4000000
MAX_FILES ?=

.PHONY: flatten-scope
flatten-scope: ## Flatten a specific directory: make flatten-scope SCOPE=quack-core/src/quack_core/lib/fs
	@test -n "$(SCOPE)" || (echo "Usage: make flatten-scope SCOPE=path/to/dir" && exit 1)
	@$(PYTHON) scripts/flatten.py \
	   --mode scope \
	   --scope "$(SCOPE)" \
	   --out-dir "$(FLATTEN_OUT)" \
	   --extensions "$(FLATTEN_EXT)" \
	   --skip-dirs "$(FLATTEN_SKIP)" \
	   --exclude "flat.txt" \
	   --exclude "_transient-files/**" \
	   --max-bytes 4000000

.PHONY: flatten-tree
flatten-tree: ## Flatten one file per subdir: make flatten-tree SCOPE=quack-core/src/quack_core/lib/fs
	@test -n "$(SCOPE)" || (echo "Usage: make flatten-tree SCOPE=path/to/dir" && exit 1)
	@$(PYTHON) scripts/flatten.py \
	   --mode tree \
	   --scope "$(SCOPE)" \
	   --out-dir "$(FLATTEN_OUT)" \
	   --extensions "$(FLATTEN_EXT)" \
	   --skip-dirs "$(FLATTEN_SKIP)" \
	   --exclude "flat.txt" \
	   --exclude "_transient-files/**" \
	   --max-bytes 2500000

.PHONY: flatten-clean
flatten-clean: ## Remove transient flatten outputs
	@rm -rf "$(FLATTEN_OUT)"

.PHONY: flatten
flatten: ## Flatten files using scripts/flatten.py (defaults to repo root). Override: make flatten SCOPE=path
	@echo "${BLUE}Flattening '$(FLATTEN_SCOPE)' into $(FLATTEN_OUT) (max $(MAX_BYTES) bytes)...${RESET}"
	@mkdir -p "$(FLATTEN_OUT)"
	@$(PYTHON) scripts/flatten.py \
	   --mode scope \
	   --scope "$(FLATTEN_SCOPE)" \
	   --out-dir "$(FLATTEN_OUT)" \
	   --extensions "$(FLATTEN_EXT)" \
	   --skip-dirs "$(FLATTEN_SKIP)" \
	   --exclude "flat.txt" \
	   --exclude "_transient-files/**" \
	   $(if $(MAX_FILES),--max-files $(MAX_FILES),) \
	   $(if $(MAX_BYTES),--max-bytes $(MAX_BYTES),)
	@echo "${GREEN}✓ Done. See: $(FLATTEN_OUT)/manifest.md${RESET}"


.PHONY: api-run
api-run: ## Run HTTP adapter server
	@echo "${BLUE}Starting QuackCore HTTP adapter...${RESET}"
	cd quack-core && \
	PYTHONPATH="$(REPO_ROOT)/quack-core/src:$(PYTHONPATH)" \
	$(REPO_ROOT)/$(VENV_NAME)/bin/uvicorn quack_core.adapters.http.app:create_app --factory --host 0.0.0.0 --port 8080

.PHONY: api-run-reload
api-run-reload: ## Run HTTP adapter server with auto-reload
	@echo "${BLUE}Starting QuackCore HTTP adapter with reload...${RESET}"
	cd quack-core && \
	PYTHONPATH="$(REPO_ROOT)/quack-core/src:$(PYTHONPATH)" \
	$(REPO_ROOT)/$(VENV_NAME)/bin/uvicorn quack_core.adapters.http.app:create_app --factory --reload --host 0.0.0.0 --port 8080

.PHONY: api-test
api-test: ## Run HTTP adapter tests
	@echo "${BLUE}Running HTTP adapter tests...${RESET}"
	cd quack-core && \
	PYTHONPATH="$(REPO_ROOT)/quack-core/src:$(REPO_ROOT)/quack-core/tests/test_http:$(PYTHONPATH)" \
	$(REPO_ROOT)/$(VENV_NAME)/bin/python -m pytest tests/test_http -v --cov=src/quack-core/adapters/http --cov-report=term-missing

.PHONY: api-test-verbose
api-test-verbose: ## Run HTTP adapter tests with verbose output
	@echo "${BLUE}Running HTTP adapter tests (verbose)...${RESET}"
	cd quack-core && \
	PYTHONPATH="$(REPO_ROOT)/quack-core/src:$(REPO_ROOT)/quack-core/tests/test_http:$(PYTHONPATH)" \
	$(REPO_ROOT)/$(VENV_NAME)/bin/python -m pytest tests/test_http -v --cov=src/quack-core/adapters/http --cov-report=term-missing

.PHONY: api-cov
api-cov: ## Run HTTP adapter tests with coverage
	@echo "${BLUE}Running HTTP adapter tests with coverage...${RESET}"
	cd quack-core && \
	PYTHONPATH="$(REPO_ROOT)/quack-core/src:$(REPO_ROOT)/quack-core/tests/test_http:$(PYTHONPATH)" \
	$(REPO_ROOT)/$(VENV_NAME)/bin/python -m pytest tests/test_http -v --cov=src/quack-core/adapters/http --cov-report=html --cov-report=term-missing

.DEFAULT_GOAL := help