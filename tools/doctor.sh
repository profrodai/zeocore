#!/usr/bin/env bash
# tools/doctor.sh — "is this machine ready to develop/release zeocore?"
#
# Invoked by `make doctor`. NEVER exits at the first problem: every check
# runs regardless of earlier failures (a KEEP_GOING pattern by construction,
# not a flag), a running FAIL count is kept, and the script's own exit code
# is that count -- zero only if everything passed. Each finding prints the
# CHECK and the FIX side by side, written for someone who has never
# debugged a Python environment before.
#
# Usage: tools/doctor.sh <repo_root> <venv_python_path> <venv_dir_name>
set -uo pipefail

REPO_ROOT="${1:?doctor.sh: missing repo_root argument}"
VENV_PYTHON="${2:?doctor.sh: missing venv_python_path argument}"
VENV_NAME="${3:?doctor.sh: missing venv_dir_name argument}"

cd "$REPO_ROOT" || { echo "doctor: cannot cd to $REPO_ROOT"; exit 1; }

GREEN=$(tput -Txterm setaf 2 2>/dev/null || true)
YELLOW=$(tput -Txterm setaf 3 2>/dev/null || true)
RED=$(tput -Txterm setaf 1 2>/dev/null || true)
BLUE=$(tput -Txterm setaf 4 2>/dev/null || true)
RESET=$(tput -Txterm sgr0 2>/dev/null || true)

FAILS=0
CHECKS=0

# pass <name>                      -- prints a green line, no fix needed
# fail <name> <check-desc> <fix>   -- prints a red line + the fix, bumps FAILS
pass() {
    CHECKS=$((CHECKS + 1))
    echo "  ${GREEN}✓${RESET} $1"
}

fail() {
    CHECKS=$((CHECKS + 1))
    FAILS=$((FAILS + 1))
    local name="$1" check="$2" fix="$3"
    echo "  ${RED}✗ ${name}${RESET}"
    echo "      ${YELLOW}checked:${RESET} ${check}"
    echo "      ${YELLOW}fix:${RESET}     ${fix}"
}

warn() {
    CHECKS=$((CHECKS + 1))
    local name="$1" check="$2" note="$3"
    echo "  ${YELLOW}! ${name}${RESET}"
    echo "      ${YELLOW}checked:${RESET} ${check}"
    echo "      ${YELLOW}note:${RESET}    ${note}"
}

echo "${BLUE}zeocore doctor — checking this machine is ready to work on zeocore${RESET}"
echo ""

# ------------------------------------------------------------------
# 1. Python floor. Read the SAME source of truth pyproject.toml uses
#    (requires-python), never a hardcoded number here that could itself
#    go stale.
# ------------------------------------------------------------------
FLOOR=$(grep -E '^requires-python' pyproject.toml | sed -E 's/.*>=\s*"?([0-9]+\.[0-9]+)"?.*/\1/' | head -1)
if [ -z "$FLOOR" ]; then
    warn "Python floor" "grep requires-python in pyproject.toml" \
         "pyproject.toml has no parseable 'requires-python = \">=X.Y\"' line -- cannot check your interpreter against it."
else
    echo "  ${BLUE}Required Python version: ${FLOOR}+ (from pyproject.toml)${RESET}"
    if command -v python3 >/dev/null 2>&1; then
        SYS_PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
        if [ -n "$SYS_PY_VER" ]; then
            MEETS_FLOOR=$(python3 -c "
floor = tuple(int(x) for x in '${FLOOR}'.split('.'))
have = tuple(int(x) for x in '${SYS_PY_VER}'.split('.'))
print('yes' if have >= floor else 'no')
" 2>/dev/null)
            if [ "$MEETS_FLOOR" = "yes" ]; then
                pass "system python3 is ${SYS_PY_VER}, meets the ${FLOOR}+ floor"
            else
                fail "python version too old" \
                     "python3 --version -> ${SYS_PY_VER}, floor is ${FLOOR}+" \
                     "Install Python ${FLOOR} or newer, then re-run 'make env'. QUICKSTART.md Step 2 walks through this on macOS/Linux/Windows."
            fi
        else
            warn "python3 version" "python3 -c 'import sys; ...' produced no output" \
                 "python3 may be broken on PATH. Try 'python3 --version' directly."
        fi
    else
        fail "python3 not found on PATH" "command -v python3" \
             "Install Python ${FLOOR}+ (see QUICKSTART.md Step 2), or install it via 'uv python install ${FLOOR}'."
    fi
fi
echo ""

# ------------------------------------------------------------------
# 2. uv present (this repo's env/dependency manager).
# ------------------------------------------------------------------
if command -v uv >/dev/null 2>&1; then
    UV_VER=$(uv --version 2>/dev/null)
    pass "uv is installed (${UV_VER})"
else
    fail "uv not found on PATH" "command -v uv" \
         "Install uv: 'curl -LsSf https://astral.sh/uv/install.sh | sh' (macOS/Linux) — see https://github.com/astral-sh/uv for other platforms, then restart your shell."
fi
echo ""

# ------------------------------------------------------------------
# 3. Virtual environment present.
# ------------------------------------------------------------------
if [ -x "$VENV_PYTHON" ]; then
    pass "virtual environment found at ${VENV_NAME}/"
else
    fail "no virtual environment" "test -x ${VENV_PYTHON}" \
         "Run 'make env' to create it, or 'make setup' to create it and install everything."
fi
echo ""

# ------------------------------------------------------------------
# 4. zeocore importable from the venv (core install, no extras).
# ------------------------------------------------------------------
if [ -x "$VENV_PYTHON" ]; then
    if "$VENV_PYTHON" -c "import zeo_core" >/dev/null 2>&1; then
        pass "zeo_core imports cleanly from ${VENV_NAME}/"
    else
        fail "zeo_core is not installed / does not import" \
             "${VENV_PYTHON} -c 'import zeo_core'" \
             "Run 'make install' (or 'make setup' for the full dev environment)."
    fi
else
    warn "zeo_core import" "skipped — no venv yet" "Run 'make env' first, then re-run 'make doctor'."
fi
echo ""

# ------------------------------------------------------------------
# 5. Dev + lint extras installed (needed for `make verify`).
# ------------------------------------------------------------------
if [ -x "$VENV_PYTHON" ]; then
    if "$VENV_PYTHON" -c "import pytest, ruff" >/dev/null 2>&1; then
        pass "dev tools installed (pytest, ruff importable)"
    else
        fail "dev tools missing" "${VENV_PYTHON} -c 'import pytest, ruff'" \
             "Run 'make install-dev' to install the [dev] extra."
    fi
    if "$VENV_PYTHON" -c "import mypy" >/dev/null 2>&1; then
        pass "mypy installed"
    else
        fail "mypy missing" "${VENV_PYTHON} -c 'import mypy'" \
             "Run 'make install-dev' to install the [dev] extra (includes mypy)."
    fi
    if "$VENV_PYTHON" -c "import importlinter" >/dev/null 2>&1; then
        pass "import-linter installed (architecture gate)"
    else
        fail "import-linter missing" "${VENV_PYTHON} -c 'import importlinter'" \
             "Run 'make install-lint' to install the [lint] extra."
    fi
else
    warn "dev/lint tooling" "skipped — no venv yet" "Run 'make env' first, then re-run 'make doctor'."
fi
echo ""

# ------------------------------------------------------------------
# 6. Optional integration extras: report which are installed, which are
#    not. Absence is NOT a failure -- these are opt-in -- but a beginner
#    following GET-STARTED.md for, say, Google Docs needs to know their
#    extra isn't in yet before they hit a confusing ImportError three
#    steps later.
# ------------------------------------------------------------------
echo "  ${BLUE}Optional integration extras (absence is fine — only matters if you plan to use one):${RESET}"
if [ -x "$VENV_PYTHON" ]; then
    check_extra() {
        local extra_name="$1" import_name="$2"
        if "$VENV_PYTHON" -c "import ${import_name}" >/dev/null 2>&1; then
            echo "    ${GREEN}✓${RESET} ${extra_name}"
        else
            echo "    ${YELLOW}·${RESET} ${extra_name} not installed (run: make install-all, or 'uv pip install -e \".[${extra_name}]\"')"
        fi
    }
    check_extra "gmail"    "googleapiclient"
    check_extra "notion"   "notion_client"
    check_extra "pandoc"   "pypandoc"
    check_extra "llms"     "tiktoken"
    check_extra "bluesky"  "platformdirs"
    check_extra "jupytext" "jupytext"
else
    echo "    ${YELLOW}skipped — no venv yet${RESET}"
fi
echo ""

# ------------------------------------------------------------------
# 7. Credentials directory (platformdirs-computed, RULING-407/408). Not
#    required to develop zeocore itself -- only for exercising a live
#    integration -- so absence is a note, not a failure.
# ------------------------------------------------------------------
if [ -x "$VENV_PYTHON" ]; then
    CRED_DIR=$("$VENV_PYTHON" -c "
import platformdirs
print(platformdirs.user_config_dir('zeocore'))
" 2>/dev/null)
    if [ -n "$CRED_DIR" ]; then
        if [ -d "$CRED_DIR" ]; then
            pass "credentials directory exists (${CRED_DIR})"
        else
            warn "credentials directory not yet created" "test -d '${CRED_DIR}'" \
                 "Not required until you authorize a live integration (Google, Bluesky, ...) — it is created automatically the first time you do. See GET-STARTED.md's token-acquisition guide."
        fi
    else
        warn "credentials directory" "platformdirs not importable yet" \
             "Install an integration extra that needs it (e.g. 'make install-all'), then re-run 'make doctor'."
    fi
else
    warn "credentials directory" "skipped — no venv yet" "Run 'make env' first, then re-run 'make doctor'."
fi
echo ""

# ------------------------------------------------------------------
# 8. .env present (secrets), from .env.example. Optional -- only needed
#    once you have a real secret to store.
# ------------------------------------------------------------------
if [ -f ".env" ]; then
    pass ".env file present (secrets loaded via zeo_core.config.load_dotenv_file())"
elif [ -f ".env.example" ]; then
    warn ".env not created yet" "test -f .env" \
         "Not required until an integration needs a secret. Copy it when you do: 'cp .env.example .env', then fill in real values (never commit .env — it is gitignored)."
else
    warn ".env.example missing" "test -f .env.example" \
         "This is unusual for this repo — if you deleted it, restore it from git: 'git checkout .env.example'."
fi
echo ""

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo "${BLUE}────────────────────────────────────────────${RESET}"
if [ "$FAILS" -eq 0 ]; then
    echo "${GREEN}✓ All ${CHECKS} checks passed. This machine is ready.${RESET}"
else
    echo "${RED}✗ ${FAILS} of ${CHECKS} checks failed.${RESET} Fix each ${RED}✗${RESET} above, then run 'make doctor' again."
fi

exit "$FAILS"
