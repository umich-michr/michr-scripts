# ===========================================================================
# michr-scripts — development workflow
#
# One repository, several packages and programs. Every target runs through
# "uv", so nothing is installed globally and no virtual environment needs to
# be activated manually.
#
# Ruff, mypy, and bandit run once across the whole workspace.
# Tests run per package, because each owns its own suite and coverage gate.
#
# Run "make" or "make help" to list targets.
# ===========================================================================

UV  := uv
RUN := $(UV) run

# --- Python workspace members ----------------------------------------------
# A directory is a workspace member only when it contains pyproject.toml.
# This avoids treating documentation files such as python/programs/README.md
# as runnable programs.
PACKAGES := $(sort $(patsubst %/,%,$(dir \
	$(wildcard python/packages/*/pyproject.toml))))

PROGRAMS := $(sort $(patsubst %/,%,$(dir \
	$(wildcard python/programs/*/pyproject.toml))))

MEMBERS := $(PACKAGES) $(PROGRAMS)

# --- Paths that Ruff and mypy examine --------------------------------------
SRC_DIRS := \
	$(wildcard python/packages/*/src) \
	$(wildcard python/programs/*/src) \
	tools

TEST_DIRS := \
	$(wildcard python/packages/*/tests) \
	$(wildcard python/programs/*/tests)

EXAMPLE_DIRS := \
	$(wildcard python/packages/*/examples) \
	$(wildcard python/programs/*/examples)

LINT_DIRS := $(SRC_DIRS) $(TEST_DIRS) $(EXAMPLE_DIRS)

REPORTS_DIR ?= reports

# --- Optional pytest arguments ---------------------------------------------
#   make test PYTEST_ARGS="-k soft_word -vv"
PYTEST_ARGS ?=

# --- Target a single member ------------------------------------------------
#   make test PACKAGE=study-posting-ai-analysis
PACKAGE ?=

ifeq ($(strip $(PACKAGE)),)
TEST_TARGETS := $(MEMBERS)
else
TEST_TARGETS := $(filter %/$(PACKAGE),$(MEMBERS))
endif

.DEFAULT_GOAL := help

.PHONY: help setup install install-all lock upgrade \
        format format-check lint lint-fix typecheck docs-check \
        audit audit-deps audit-code \
        test test-fast test-slow coverage coverage-open \
        check ci members validate-package \
        clean clean-reports clean-output clean-caches clean-venv distclean \
        hooks hooks-run hooks-update hooks-clean doctor


# Run a command in each workspace member.
#
# Expanded by Make rather than the shell, so there is no loop syntax, no
# quoting hazard, and no failure when the member list is empty. The && chain
# propagates a nonzero exit status.
define for_each_member
$(foreach member,$(MEMBERS),echo "" && echo "==> $(member)" && ( cd $(member) && $(1) ) &&) true
endef

# Same, restricted to the member named by PACKAGE when it is set.
define for_each_target
$(foreach member,$(TEST_TARGETS),echo "" && echo "==> $(member)" && ( cd $(member) && $(1) ) &&) true
endef


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
help:
	@echo ""
	@echo "michr-scripts — development targets"
	@echo ""
	@echo "  Setup"
	@echo "    setup            Bootstrap a fresh clone (idempotent)"
	@echo "    install          uv sync --all-packages"
	@echo "    hooks            Install pre-commit git hooks"
	@echo "    doctor           Print versions and workspace summary"
	@echo "    members          List workspace packages and programs"
	@echo ""
	@echo "  Quality (whole workspace)"
	@echo "    format           Format code and organize imports"
	@echo "    format-check     Verify formatting without editing"
	@echo "    lint             Ruff lint"
	@echo "    lint-fix         Ruff lint with safe automatic fixes"
	@echo "    typecheck        mypy strict"
	@echo "    docs-check       Verify docs accompany rule changes"
	@echo ""
	@echo "  Security"
	@echo "    audit            Dependency and source security audit"
	@echo "    audit-deps       Known vulnerabilities in the lockfile"
	@echo "    audit-code       Insecure patterns in source"
	@echo ""
	@echo "  Tests (per member)"
	@echo "    test             Full suite, clean start"
	@echo "    test-fast        Skip slow randomized tests"
	@echo "    test-slow        Run only the slow tests"
	@echo "    coverage         Tests with coverage into each member's reports/"
	@echo "    coverage-open    Coverage, then open the HTML reports"
	@echo ""
	@echo "  Gates"
	@echo "    check            Everything above; run before committing"
	@echo "    ci               Same as check, for pipelines"
	@echo ""
	@echo "  Maintenance"
	@echo "    lock             Refresh uv.lock"
	@echo "    upgrade          Bump dependency versions (review the diff)"
	@echo "    hooks-update     Bump hook versions (review the diff)"
	@echo "    hooks-clean      Remove cached hook environments"
	@echo ""
	@echo "  Cleaning"
	@echo "    clean            Remove reports and tool caches"
	@echo "    clean-output     Remove application output under output/"
	@echo "    clean-reports    Remove generated reports only"
	@echo "    clean-caches     Remove pytest, ruff, mypy, bytecode caches"
	@echo "    clean-venv       Remove the virtual environment"
	@echo "    distclean        clean + clean-venv + build artifacts"
	@echo ""
	@echo "  Options"
	@echo "    PACKAGE=$(PACKAGE)   (empty means every member)"
	@echo "    PYTEST_ARGS=\"$(PYTEST_ARGS)\""
	@echo ""
	@echo "  Examples"
	@echo "    make check"
	@echo "    make test PACKAGE=study-posting-ai-analysis"
	@echo "    make test PYTEST_ARGS=\"-k compensation -vv\""
	@echo ""

members:
	@echo "Python packages:"
	@$(if $(strip $(PACKAGES)),\
	  $(foreach member,$(PACKAGES),echo "  $(member)";),\
	  echo "  (none)")
	@echo "Python programs:"
	@$(if $(strip $(PROGRAMS)),\
	  $(foreach member,$(PROGRAMS),echo "  $(member)";),\
	  echo "  (none)")

validate-package:
ifneq ($(strip $(PACKAGE)),)
	@test -n "$(strip $(TEST_TARGETS))" || { \
	  echo "ERROR: unknown Python workspace member: $(PACKAGE)"; \
	  echo "Run 'make members' to list available members."; \
	  exit 2; \
	}
endif


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
# Idempotent: safe to run repeatedly. Never changes pinned versions.
setup:
	@echo "==> Installing all workspace members into .venv"
	$(UV) sync --all-packages
	@echo ""
	@echo "==> Installing git hooks"
	$(RUN) pre-commit install --install-hooks
	@echo ""
	@echo "==> Workspace summary"
	@$(MAKE) --no-print-directory doctor
	@echo ""
	@echo "Setup complete."
	@echo "  make check    Run the full quality gate"
	@echo "  make          List all targets"

install install-all:
	$(UV) sync --all-packages

lock:
	$(UV) lock

upgrade:
	$(UV) lock --upgrade
	$(UV) sync --all-packages

hooks:
	$(RUN) pre-commit install --install-hooks
	@echo "Pre-commit hooks installed."

hooks-run:
	$(RUN) pre-commit run --all-files

# Deliberately excluded from "check" and "ci" so verification stays
# reproducible: this edits .pre-commit-config.yaml.
hooks-update:
	$(RUN) pre-commit autoupdate
	@echo ""
	@echo "Hook versions updated. Next steps:"
	@echo "  1. git diff .pre-commit-config.yaml"
	@echo "  2. Align pyproject.toml floors with any new hook versions"
	@echo "  3. make hooks-run && make check"

hooks-clean:
	$(RUN) pre-commit clean
	$(RUN) pre-commit gc

doctor:
	@echo "--- Interpreter -----------------------------------------------"
	@$(RUN) python -V
	@echo "--- Tooling ---------------------------------------------------"
	@$(RUN) ruff --version
	@$(RUN) mypy --version
	@$(RUN) pytest --version
	@echo "--- Workspace members -----------------------------------------"
	@$(MAKE) --no-print-directory members
	@echo "--- Analytical packages ---------------------------------------"
	@$(RUN) python -c "import text_post_edit_metrics as m; \
	print('text-post-edit-metrics', m.__version__)" \
	  2>/dev/null || echo "text-post-edit-metrics  not importable"
	@$(RUN) python -c "import study_posting_ai_analysis as m; \
	print('study-posting-ai-analysis', m.__version__, \
	'-', len(m.__all__), 'exports,', len(m.FLATTENED_COLUMNS), 'columns')" \
	  2>/dev/null || echo "study-posting-ai-analysis  not importable"

# ---------------------------------------------------------------------------
# Quality: one pass across the whole workspace
# ---------------------------------------------------------------------------
format:
	$(RUN) ruff format $(LINT_DIRS)
	$(RUN) ruff check --select I --fix $(LINT_DIRS)

format-check:
	$(RUN) ruff format --check --diff $(LINT_DIRS)

lint:
	$(RUN) ruff check $(LINT_DIRS)

lint-fix:
	$(RUN) ruff check --fix $(LINT_DIRS)

typecheck:
	@$(call for_each_member,MYPYPATH=src $(RUN) mypy --config-file $(CURDIR)/pyproject.toml src tests)
	@echo ""
	@echo "==> tools"
	@$(RUN) mypy --config-file $(CURDIR)/pyproject.toml tools

docs-check:
	$(RUN) python tools/check_docs_sync.py

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
audit: audit-deps audit-code

# Auditing the exported lockfile checks exactly the pinned set, and avoids
# looking up workspace members on PyPI.
audit-deps:
	$(UV) export --all-packages --no-emit-workspace --no-hashes \
	  --format requirements-txt \
	  | $(RUN) pip-audit --strict --progress-spinner=off \
	    --ignore-vuln PYSEC-2026-3740 \
	    --requirement /dev/stdin

audit-code:
	$(RUN) bandit --configfile pyproject.toml --recursive \
	  $(SRC_DIRS) --quiet

# ---------------------------------------------------------------------------
# Tests: each member runs its own suite from its own directory
# ---------------------------------------------------------------------------
test: validate-package clean-caches
	@$(call for_each_target,$(RUN) pytest $(PYTEST_ARGS))

test-fast: validate-package clean-caches
	@$(call for_each_target,$(RUN) pytest -m "not slow" $(PYTEST_ARGS))

test-slow: validate-package clean-caches
	@$(call for_each_target,$(RUN) pytest -m slow $(PYTEST_ARGS))

coverage: validate-package clean-caches clean-reports
	@$(call for_each_target,mkdir -p $(REPORTS_DIR) && $(RUN) pytest --cov --cov-report=term-missing:skip-covered --cov-report=html --cov-report=xml --junitxml=$(REPORTS_DIR)/junit.xml $(PYTEST_ARGS))
	@echo ""
	@echo "HTML coverage reports:"
	@$(foreach member,$(TEST_TARGETS),echo "  $(member)/$(REPORTS_DIR)/htmlcov/index.html";)

coverage-open: coverage
	@$(foreach member,$(TEST_TARGETS),$(RUN) python -c "import pathlib, webbrowser; webbrowser.open(pathlib.Path('$(member)/$(REPORTS_DIR)/htmlcov/index.html').resolve().as_uri())";)

# ---------------------------------------------------------------------------
# Combined gates
# ---------------------------------------------------------------------------
check: format-check lint typecheck docs-check audit coverage
	@echo ""
	@echo "All checks passed."

ci: check

# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------
clean: clean-reports clean-caches
	@echo "Removed generated reports and tool caches."

clean-reports:
	@rm -rf $(REPORTS_DIR)
	@rm -rf python/packages/*/$(REPORTS_DIR) python/programs/*/$(REPORTS_DIR)

clean-output:
	@if [ -e "$(CURDIR)/output" ]; then \
	  echo "Removing application output directory: $(CURDIR)/output"; \
	  rm -rf "$(CURDIR)/output"; \
	  echo "Removed application output directory: $(CURDIR)/output"; \
	else \
	  echo "No application output directory exists: $(CURDIR)/output"; \
	fi

clean-caches:
	@rm -rf .pytest_cache .ruff_cache .mypy_cache
	@rm -rf .coverage .coverage.* coverage.xml htmlcov junit.xml
	@rm -rf python/packages/*/.pytest_cache python/packages/*/.ruff_cache python/packages/*/.mypy_cache
	@rm -rf python/packages/*/.coverage python/packages/*/.coverage.*
	@rm -rf python/programs/*/.pytest_cache python/programs/*/.ruff_cache python/programs/*/.mypy_cache
	@rm -rf python/programs/*/.coverage python/programs/*/.coverage.*
	@find . -type d -name __pycache__ -not -path "./.venv/*" \
	  -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.py[co]" -not -path "./.venv/*" \
	  -delete 2>/dev/null || true

clean-venv:
	@rm -rf .venv

distclean: clean clean-venv
	@rm -rf build dist wheels
	@rm -rf python/packages/*/build python/packages/*/dist python/programs/*/build python/programs/*/dist
	@find . -type d -name "*.egg-info" -not -path "./.venv/*" \
	  -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "Workspace reset. Run 'make setup' to rebuild."
