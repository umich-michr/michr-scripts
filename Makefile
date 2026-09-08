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
OUTPUT_DIR  ?= output
REPORTS_DIR ?= reports

# --- Named arguments forwarded to the application --------------------------
# Override on the command line, for example:
#   make run SOURCE=oracle LIMIT=50 LOG_LEVEL=DEBUG
SOURCE       ?= sqlite
SQLITE_PATH  ?= data/local_audit_records.db
CSV_PATH     ?= data/sample/audit_records_sample.csv
LIMIT        ?=
LOG_LEVEL    ?= INFO
INCLUDE_TEXT ?= false

# Optional extra pytest arguments:
#   make test PYTEST_ARGS="-k soft_word -vv"
PYTEST_ARGS ?=

# Build the named-argument list. Empty variables contribute nothing.
RUN_ARGS := --source=$(SOURCE) --output-dir=$(OUTPUT_DIR) --log-level=$(LOG_LEVEL)
# Set ORACLE=true to include the Oracle driver extra.
#   make setup ORACLE=true
ORACLE ?= false

ifeq ($(ORACLE),true)
SYNC_FLAGS := --extra oracle
else
SYNC_FLAGS :=
endif
ifeq ($(SOURCE),sqlite)
RUN_ARGS += --sqlite-path=$(SQLITE_PATH)
endif
ifneq ($(strip $(LIMIT)),)
RUN_ARGS += --limit=$(LIMIT)
endif
ifeq ($(INCLUDE_TEXT),true)
RUN_ARGS += --include-text
endif

.DEFAULT_GOAL := help

# Every target is phony: none of them produce a file named after the target.
.PHONY: help setup install install-oracle lock upgrade \
	    docs-check format format-check lint lint-fix typecheck \
	    audit audit-deps audit-code \
	    test test-fast test-slow coverage coverage-open \
	    check ci \
	    load-csv run run-oracle \
	    clean clean-output clean-caches clean-venv distclean \
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
	@echo "                     ORACLE=true to include the Oracle driver"
	@echo "    install          Create .venv and install all dependencies"
	@echo "    install-oracle   Also install the Oracle driver extra"
	@echo "    hooks            Install pre-commit git hooks"
	@echo "    hooks-update     Update pinned hook versions (review the diff)"
	@echo "    hooks-clean      Remove cached hook environments"
	@echo "    doctor           Print tool versions and environment summary"
	@echo ""
	@echo "  Quality"
	@echo "    docs-check       Verify documentation accompanies rule changes"
	@echo "    format           Format code with Ruff"
	@echo "    format-check     Verify formatting without editing files"
	@echo "    lint             Lint with Ruff"
	@echo "    lint-fix         Lint and apply safe automatic fixes"
	@echo "    typecheck        Static type check with mypy (strict)"
	@echo ""
	@echo "  Security"
	@echo "    audit            Dependency and source-code security audit"
	@echo "    audit-deps       Known vulnerabilities in locked dependencies"
	@echo "    audit-code       Insecure patterns in our own source"
	@echo ""
	@echo "  Tests"
	@echo "    test             Run the full suite (clean start)"
	@echo "    test-fast        Skip slow randomized differential tests"
	@echo "    test-slow        Run only the slow tests"
	@echo "    coverage         Run tests with coverage; write reports/"
	@echo "    coverage-open    Open the HTML coverage report"
	@echo ""
	@echo "  Gates"
	@echo "    check            format-check + lint + typecheck + audit + coverage"
	@echo "    ci               Same as check, for automated pipelines"
	@echo ""
	@echo "  Application"
	@echo "    load-csv         Load a CSV export into the local SQLite database"
	@echo "    run              Analyze eligible records and write CSV output"
	@echo "    run-oracle       Same, reading from Oracle"
	@echo ""
	@echo "  Cleaning"
	@echo "    clean            Remove output, reports, and tool caches"
	@echo "    clean-output     Remove generated output and reports only"
	@echo "    clean-caches     Remove pytest, ruff, mypy, and bytecode caches"
	@echo "    clean-venv       Remove the virtual environment"
	@echo "    distclean        clean + clean-venv + remove build artifacts"
	@echo ""
	@echo "  Named arguments (override on the command line)"
	@echo "    SOURCE=$(SOURCE)  SQLITE_PATH=$(SQLITE_PATH)"
	@echo "    CSV_PATH=$(CSV_PATH)"
	@echo "    LIMIT=$(LIMIT)  LOG_LEVEL=$(LOG_LEVEL)  INCLUDE_TEXT=$(INCLUDE_TEXT)"
	@echo "    OUTPUT_DIR=$(OUTPUT_DIR)  REPORTS_DIR=$(REPORTS_DIR)"
	@echo "    PYTEST_ARGS=\"$(PYTEST_ARGS)\""
	@echo ""
	@echo "  Examples"
	@echo "    make check"
	@echo "    make test PYTEST_ARGS=\"-k compensation -vv\""
	@echo "    make load-csv CSV_PATH=data/export.csv"
	@echo "    make run LIMIT=100 LOG_LEVEL=DEBUG"
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
#   make setup ORACLE=true     also install the Oracle driver extra
setup:
	@echo "==> Installing dependencies into .venv"
	$(UV) sync $(SYNC_FLAGS)
	@echo ""
	@echo "==> Installing git hooks"
	$(RUN) pre-commit install --install-hooks
	@echo ""
	@echo "==> Environment file"
	@if [ -f .env ]; then \
	  echo "    .env already exists; left unchanged"; \
	else \
	  cp .env.example .env; \
	  echo "    Created .env from .env.example"; \
	fi
	@echo ""
	@echo "==> Environment summary"
	@$(MAKE) --no-print-directory doctor
	@echo ""
	@echo "Setup complete."
	@echo "  make check    Run the full quality gate"
	@echo "  make          List all targets"

install:
	$(UV) sync $(SYNC_FLAGS)

install-oracle:
	@$(MAKE) install ORACLE=true

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
	@$(RUN) python -c "import sacrebleu, rapidfuzz, pandas, sqlite3; \
	print('sacrebleu ', sacrebleu.__version__); \
	print('rapidfuzz ', rapidfuzz.__version__); \
	print('pandas    ', pandas.__version__); \
	print('sqlite    ', sqlite3.sqlite_version)"
	@echo "--- Oracle driver ---------------------------------------------"
	@$(RUN) python -c "import oracledb; print('oracledb  ', oracledb.__version__)" \
	  2>/dev/null || echo "oracledb   not installed (run: make install-oracle)"

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

coverage: clean-caches clean-output
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

run-oracle:
	@$(MAKE) run SOURCE=oracle

# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------
clean: clean-output clean-caches
	@echo "Removed generated output and tool caches."

clean-output:
	@rm -rf $(OUTPUT_DIR) $(REPORTS_DIR)

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
