# ===========================================================================
# Development workflow for study-posting-ai-analysis
#
# Every target runs through "uv", so nothing is installed globally and no
# virtual environment needs to be activated manually.
#
# Conventions:
#   - All application arguments are named, never positional.
#   - Generated output lives only in output/ and reports/, both removed by
#     "make clean" so each run starts from a clean state.
#
# Run "make" or "make help" to list targets.
# ===========================================================================

UV  := uv
RUN := $(UV) run

PACKAGE  := study_posting_ai_analysis
SRC_DIR  := src
TEST_DIR := tests

# --- Directories that are always regenerated -------------------------------
REPORTS_DIR ?= reports

# --- Named arguments forwarded to the application --------------------------
# Optional extra pytest arguments:
#   make test PYTEST_ARGS="-k soft_word -vv"
PYTEST_ARGS ?=

# Build the named-argument list. Empty variables contribute nothing.
RUN_ARGS := --log-level=$(LOG_LEVEL)

ifneq ($(strip $(LIMIT)),)
RUN_ARGS += --limit=$(LIMIT)
endif
ifeq ($(INCLUDE_TEXT),true)
RUN_ARGS += --include-text
endif

.DEFAULT_GOAL := help

# Every target is phony: none of them produce a file named after the target.
.PHONY: help install lock upgrade setup \
        format format-check lint lint-fix typecheck docs-check \
        audit audit-deps audit-code \
        test test-fast test-slow coverage coverage-open \
        check ci \
        clean clean-reports clean-caches clean-venv distclean \
        hooks hooks-run hooks-update hooks-clean doctor

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
help:
	@echo ""
	@echo "study-posting-ai-analysis — development targets"
	@echo ""
	@echo "  Setup"
	@echo "    setup            Bootstrap a fresh clone (idempotent)"
	@echo "    install          uv sync"
	@echo "    hooks            Install pre-commit git hooks"
	@echo "    doctor           Print versions and library summary"
	@echo ""
	@echo "  Quality"
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
	@echo "    audit-code       Insecure patterns in src/"
	@echo ""
	@echo "  Tests"
	@echo "    test             Full suite, clean start"
	@echo "    test-fast        Skip slow randomized differential tests"
	@echo "    test-slow        Run only the slow tests"
	@echo "    coverage         Tests with coverage into reports/"
	@echo "    coverage-open    Coverage, then open the HTML report"
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
	@echo "    clean-reports    Remove generated reports only"
	@echo "    clean-caches     Remove pytest, ruff, mypy, bytecode caches"
	@echo "    clean-venv       Remove the virtual environment"
	@echo "    distclean        clean + clean-venv + build artifacts"
	@echo ""
	@echo "  Options"
	@echo "    PYTEST_ARGS=\"$(PYTEST_ARGS)\""
	@echo "    REPORTS_DIR=$(REPORTS_DIR)"
	@echo ""
	@echo "  Examples"
	@echo "    make check"
	@echo "    make test PYTEST_ARGS=\"-k compensation -vv\""
	@echo ""

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
# One-command bootstrap for a fresh clone.
#
# Idempotent: safe to run repeatedly. Never overwrites .env, never changes
# pinned versions, never contacts a database.
#
#   make setup                 dependencies, hooks, .env
setup:
	@echo "==> Installing dependencies into .venv"
	$(UV) sync
	@echo ""
	@echo "==> Installing git hooks"
	$(RUN) pre-commit install --install-hooks
	@echo ""
	@echo "==> Environment summary"
	@$(MAKE) --no-print-directory doctor
	@echo ""
	@echo "Setup complete."
	@echo "  make check    Run the full quality gate"
	@echo "  make          List all targets"

install:
	$(UV) sync

lock:
	$(UV) lock

upgrade:
	$(UV) lock --upgrade
	$(UV) sync

hooks:
	$(RUN) pre-commit install --install-hooks
	@echo "Pre-commit hooks installed."

hooks-run:
	$(RUN) pre-commit run --all-files

# Update pinned hook versions in .pre-commit-config.yaml.
# It is deliberately excluded from "check" and "ci" so verification stays
# reproducible.
hooks-update:
	$(RUN) pre-commit autoupdate
	@echo ""
	@echo "Hook versions updated. Next steps:"
	@echo "  1. git diff .pre-commit-config.yaml"
	@echo "  2. Align pyproject.toml floors with any new hook versions"
	@echo "  3. make hooks-run && make check"

# Remove cached hook environments. Use when a hook behaves inconsistently
# with the command-line tool of the same name.
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
	@echo "--- Runtime libraries -----------------------------------------"
	@$(RUN) python -c "import sacrebleu, rapidfuzz; \
	print('sacrebleu', sacrebleu.__version__); \
	print('rapidfuzz', rapidfuzz.__version__)"
	@echo "--- Library ---------------------------------------------------"
	@$(RUN) python -c "import study_posting_ai_analysis as m; \
	print('version  ', m.__version__); \
	print('exports  ', len(m.__all__)); \
	print('columns  ', len(m.FLATTENED_COLUMNS))"

# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------
format:
	$(RUN) ruff format $(SRC_DIR) $(TEST_DIR)
	$(RUN) ruff check --select I --fix $(SRC_DIR) $(TEST_DIR)

format-check:
	$(RUN) ruff format --check --diff $(SRC_DIR) $(TEST_DIR)

lint:
	$(RUN) ruff check $(SRC_DIR) $(TEST_DIR)

lint-fix:
	$(RUN) ruff check --fix $(SRC_DIR) $(TEST_DIR)

typecheck:
	$(RUN) mypy

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
audit: audit-deps audit-code

# --strict fails on any dependency that cannot be audited, so a silent gap in
# coverage is reported rather than ignored.
audit-deps:
	$(UV) export --no-emit-project --no-hashes --format requirements-txt \
	  | $(RUN) pip-audit --strict --progress-spinner=off --requirement /dev/stdin

audit-code:
	$(RUN) bandit --configfile pyproject.toml --recursive $(SRC_DIR) --quiet

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
# Each test target removes caches first so results never depend on a stale
# cache or a previously collected test tree.
test: clean-caches
	$(RUN) pytest $(PYTEST_ARGS)

test-fast: clean-caches
	$(RUN) pytest -m "not slow" $(PYTEST_ARGS)

test-slow: clean-caches
	$(RUN) pytest -m slow $(PYTEST_ARGS)

coverage: clean-caches clean-reports
	@mkdir -p $(REPORTS_DIR)
	$(RUN) pytest \
	  --cov \
	  --cov-report=term-missing:skip-covered \
	  --cov-report=html \
	  --cov-report=xml \
	  --junitxml=$(REPORTS_DIR)/junit.xml \
	  $(PYTEST_ARGS)
	@echo ""
	@echo "HTML coverage report: $(REPORTS_DIR)/htmlcov/index.html"

coverage-open: coverage
	@$(RUN) python -c "import webbrowser, pathlib; \
	webbrowser.open(pathlib.Path('$(REPORTS_DIR)/htmlcov/index.html').resolve().as_uri())"

# ---------------------------------------------------------------------------
# Combined gates
# ---------------------------------------------------------------------------
check: format-check lint typecheck audit coverage
	@echo ""
	@echo "All checks passed."

ci: check

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
# All arguments are named. --reset rebuilds the local database from scratch so
# each load starts clean.
load-csv:
	$(RUN) study-posting-analysis load-csv \
	  --csv-path=$(CSV_PATH) \
	  --sqlite-path=$(SQLITE_PATH) \
	  --log-level=$(LOG_LEVEL) \
	  --reset

run: clean-output
	@mkdir -p $(OUTPUT_DIR)
	$(RUN) study-posting-analysis analyze $(RUN_ARGS)
	@echo ""
	@echo "Output written to $(OUTPUT_DIR)/"

# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------
clean: clean-reports clean-caches
	@echo "Removed generated reports and tool caches."

clean-reports:
	@rm -rf $(REPORTS_DIR)

clean-caches:
	@rm -rf .pytest_cache .ruff_cache .mypy_cache
	@rm -rf .coverage .coverage.* coverage.xml htmlcov junit.xml
	@find . -type d -name __pycache__ -not -path "./.venv/*" \
	  -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.py[co]" -not -path "./.venv/*" \
	  -delete 2>/dev/null || true

clean-venv:
	@rm -rf .venv

distclean: clean clean-venv
	@rm -rf build dist wheels
	@find . -type d -name "*.egg-info" -not -path "./.venv/*" \
	  -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "Workspace reset. Run 'make install' to rebuild."

docs-check:
	$(RUN) python scripts/check_docs_sync.py
