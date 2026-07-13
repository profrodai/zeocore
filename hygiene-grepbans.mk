# hygiene-grepbans.mk — Tier-1 grep-ban gate targets (Track C).
# Included by the root Makefile. Clones the hygiene-check offenders shape.
# Scope = PKG_SRC (production only); -I skips binaries, --exclude-dir=__pycache__
# skips compiled artifacts (they embed /Users/ build paths and false-match).

.PHONY: hygiene-secrets
hygiene-secrets: ## Ban hardcoded key literals (sk-...) and absolute /Users/ paths in production
	@echo "$(BLUE)Checking for hardcoded secrets / absolute paths...$(RESET)"
	@offenders=$$(grep -rEnI --include='*.py' --exclude-dir=__pycache__ 'sk-[A-Za-z0-9]{16,}|/Users/' $(PKG_SRC) 2>/dev/null || true); \
	if [ -n "$$offenders" ]; then \
	echo "$(RED)FAIL: hardcoded secret or absolute path in production:$(RESET)"; \
	echo "$$offenders" | sed 's/^/    /'; \
	echo "$(YELLOW)  Move secrets to env; make paths relative/configurable.$(RESET)"; \
	exit 1; \
	fi
	@echo "$(GREEN)OK: no hardcoded secrets or absolute paths$(RESET)"

.PHONY: plugin-boundary
plugin-boundary: ## Ban plugin.py importing tools/capabilities (Plugin is a leaf)
	@echo "$(BLUE)Checking plugin.py boundary...$(RESET)"
	@offenders=$$(grep -rEnI 'quack_core\.tools|quack_core\.contracts\.capabilities' $$(find $(PKG_SRC) -name plugin.py) 2>/dev/null || true); \
	if [ -n "$$offenders" ]; then \
	echo "$(RED)FAIL: plugin.py must not import tools/capabilities:$(RESET)"; \
	echo "$$offenders" | sed 's/^/    /'; \
	exit 1; \
	fi
	@echo "$(GREEN)OK: plugin boundary clean$(RESET)"
