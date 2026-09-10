# michr-scripts

A polyglot monorepo for reusable MICHR libraries, independently runnable
programs, and operational scripts.

Python projects are managed as a
[uv workspace](https://docs.astral.sh/uv/). The repository shares one Git
history, lockfile, virtual environment, development workflow, and CI
configuration.

## Repository layout

```text
michr-scripts/
├── python/
│   ├── packages/    Reusable Python libraries
│   └── programs/    Independently runnable applications
├── shell/           Shell scripts and projects organized by purpose
├── lua/             Lua scripts and projects organized by purpose
├── tools/           Repository-maintenance utilities
├── Makefile         Repository-wide development interface
├── pyproject.toml   Workspace and shared tool configuration
└── uv.lock          Locked Python dependencies
```

`uv` manages members under `python/`. The root `Makefile` is the normal
development interface.

## Python workspace members

### Packages

| Package | Import | Responsibility |
|---|---|---|
| [`program-configuration`](python/packages/program-configuration/) | `program_configuration` | Layered, typed, secret-aware configuration resolution |
| [`tabular-row-sources`](python/packages/tabular-row-sources/) | `tabular_row_sources` | Schema-aware lazy CSV and DB-API row sources |
| [`text-post-edit-metrics`](python/packages/text-post-edit-metrics/) | `text_post_edit_metrics` | Generic directional text post-edit metrics |
| [`study-posting-ai-analysis`](python/packages/study-posting-ai-analysis/) | `study_posting_ai_analysis` | Study-posting field policy, parsing, analysis, and flattening |

### Programs

| Program | Command | Responsibility |
|---|---|---|
| [`study-posting-audit-report`](python/programs/study-posting-audit-report/) | `study-posting-audit-report` | Generate normalized audit records and completed-AI field metrics from CSV or Oracle |

## Architecture

The audit-report program composes reusable packages:

```text
study-posting-audit-report
├── program-configuration
├── tabular-row-sources
└── study-posting-ai-analysis
    └── text-post-edit-metrics
```

The end-to-end flow is:

```text
CSV file or Oracle query
            ↓
    tabular-row-sources
            ↓ canonical rows
study-posting-audit-report
            ↓
study-posting-ai-analysis
            ↓
 text-post-edit-metrics
            ↓
 records.csv + field_metrics.csv
```

Dependency rules:

1. Programs may depend on packages.
2. Packages must not depend on programs.
3. More reusable packages must not import more specific packages.
4. Programs must not import another program's internal modules.
5. Shared behavior belongs in a package rather than being copied.
6. Cross-language integration uses documented executable and data contracts.
7. Add a dependency only to the member that directly imports it.

Inspect the dependency graph with:

```bash
uv tree --package study-posting-audit-report
```

## Package contracts

### `program-configuration`

Resolves program settings using:

```text
explicit value
→ process environment
→ dotenv
→ default
→ interactive prompt
→ missing-setting error
```

It owns generic precedence, parsing, provenance, dotenv loading, prompting, and
secret redaction. Programs retain ownership of their setting names, CLI syntax,
defaults, and application policy.

See its
[package README](python/packages/program-configuration/README.md).

### `tabular-row-sources`

Streams canonical rows from CSV files and DB-API queries through a common
interface:

```python
with source.open_rows() as rows:
    for row in rows:
        process(row)
```

CSV and database sources use the same `RowSchema` and conversion layer. Source
columns may arrive in any order, but names must match the schema exactly.
Yielded rows follow canonical schema order.

See:

- the [package README](python/packages/tabular-row-sources/README.md);
- the [schema format](python/packages/tabular-row-sources/docs/schema-format.md).

### `text-post-edit-metrics`

Compares an initial suggestion with text represented by the caller as its edited
form:

```python
from text_post_edit_metrics import analyze_post_edit

result = analyze_post_edit(
    suggestion="Generated text",
    final="Human-edited text",
)
```

It owns generic TER-derived, character, and soft-word metrics. It does not own
study fields, product policy, source records, or reporting.

See:

- the [package README](python/packages/text-post-edit-metrics/README.md);
- the [methodology](python/packages/text-post-edit-metrics/docs/methodology.md);
- the [verification strategy](python/packages/text-post-edit-metrics/docs/verification.md).

### `study-posting-ai-analysis`

Analyzes one record's suggested, selected, and final study-posting objects:

```python
from study_posting_ai_analysis import (
    analyze_objects,
    flatten_analysis_results,
    parse_analysis_inputs,
)

suggested, selected, final = parse_analysis_inputs(
    suggested_payload,
    selected_payload,
    final_payload,
)
results = analyze_objects(suggested, selected, final)
rows = flatten_analysis_results(
    results,
    record_id="synthetic-record",
)
```

It owns study-specific field policy and delegates generic text calculations to
`text-post-edit-metrics`.

See:

- the [package README](python/packages/study-posting-ai-analysis/README.md);
- the [analysis specification](python/packages/study-posting-ai-analysis/docs/analysis-specification.md);
- the [program flow](python/packages/study-posting-ai-analysis/docs/program-flow.md).

## Setup

### Prerequisites

| Tool | Check |
|---|---|
| `uv` | `uv --version` |
| `make` | `make --version` |

Python does not need to be installed separately. `uv` reads `.python-version`
and installs the required interpreter.

### Bootstrap a clone

```bash
git clone https://github.com/umich-michr/michr-scripts
cd michr-scripts
make setup
```

`make setup` synchronizes all workspace members, installs Git hooks, and prints
an environment summary.

Verify the workspace:

```bash
make members
make doctor
make check
```

Do not manually activate `.venv`, invoke `pip`, or edit `uv.lock`.

## Development commands

### Whole workspace

| Command | Purpose |
|---|---|
| `make setup` | Bootstrap a fresh clone |
| `make install` | Synchronize all Python members |
| `make members` | List workspace members |
| `make doctor` | Show interpreter and tool information |
| `make format` | Format code and organize imports |
| `make format-check` | Check formatting without modification |
| `make lint` | Run Ruff |
| `make typecheck` | Run strict mypy |
| `make test` | Run every member's tests |
| `make coverage` | Run every member's coverage gate |
| `make docs-check` | Check staged documentation synchronization |
| `make audit` | Audit dependencies and source |
| `make check` | Run the complete quality gate |
| `make hooks-run` | Run pre-commit hooks against all files |
| `make clean` | Remove generated reports and caches |

Run `make` without arguments for the complete target list.

### One member

```bash
make test PACKAGE=program-configuration
make coverage PACKAGE=tabular-row-sources
make test PACKAGE=study-posting-ai-analysis
make coverage PACKAGE=study-posting-audit-report
```

Pass pytest arguments with:

```bash
make test \
  PACKAGE=study-posting-audit-report \
  PYTEST_ARGS="-k database -vv"
```

An unknown `PACKAGE=` value fails rather than silently running no tests.

### Before committing

```bash
make check
make hooks-run
git diff --check
git status --short
```

Pre-commit hooks may modify files and stop the commit. Review and stage those
changes, then rerun the hooks. Do not bypass a failing hook merely to complete a
commit.

## Running the audit-report program

Show available source modes:

```bash
uv run study-posting-audit-report --help
```

CSV input:

```bash
uv run study-posting-audit-report csv \
  --input path/to/audit.csv
```

Oracle input:

```bash
uv run study-posting-audit-report database \
  --dsn "database.example:1521/service" \
  --username reporting_user
```

The program writes normalized:

```text
records.csv
field_metrics.csv
```

See the
[program README](python/programs/study-posting-audit-report/README.md)
for configuration, input templates, SQL parameters, output behavior, and
security guidance.

## Adding a Python member

Python packages use:

```text
python/packages/<distribution-name>/
├── pyproject.toml
├── README.md
├── src/
│   └── <import_name>/
│       ├── __init__.py
│       └── py.typed
└── tests/
```

Runnable programs use:

```text
python/programs/<distribution-name>/
├── pyproject.toml
├── README.md
├── src/
│   └── <import_name>/
│       ├── __init__.py
│       ├── cli.py
│       └── __main__.py
└── tests/
```

For either kind of member:

1. use a `src` layout;
2. document its contract and exclusions;
3. configure pytest and coverage in its `pyproject.toml`;
4. add full type annotations and focused tests;
5. add the import name to Ruff's `known-first-party` list;
6. add its source path to `.vscode/settings.json`;
7. add scoped instructions when important rules apply;
8. run `uv lock`, `uv sync --all-packages`, and `make check`.

The workspace discovers:

```toml
[tool.uv.workspace]
members = ["python/packages/*", "python/programs/*"]
```

Add an internal dependency with:

```bash
uv add \
  --package consuming-distribution \
  dependency-distribution
```

Declare internal workspace resolution:

```toml
[tool.uv.sources]
dependency-distribution = { workspace = true }
```

## Shell, Lua, and repository tools

Use:

```text
shell/<purpose>/
lua/<purpose>/
```

A small script may remain one file. Promote it to a directory when it gains
tests, fixtures, configuration, or supporting files.

`tools/` is reserved for utilities that maintain this repository. User-facing
or operational programs belong under the language-specific program area.

## Documentation ownership

| Documentation | Owner |
|---|---|
| Repository layout and shared workflow | Root `README.md` |
| Public package API | Package `README.md` |
| Program CLI and configuration | Program `README.md` |
| Generic metric formulas | `text-post-edit-metrics/docs/methodology.md` |
| Generic metric verification | `text-post-edit-metrics/docs/verification.md` |
| Study policy | `study-posting-ai-analysis/docs/analysis-specification.md` |
| Study control flow | `study-posting-ai-analysis/docs/program-flow.md` |
| Tabular schema and conversion | `tabular-row-sources/docs/schema-format.md` |
| Shared agent rules | `.github/copilot-instructions.md` |
| Member-specific rules | `.github/instructions/` |

A behavior or public-contract change is incomplete until its owning
documentation is updated.

## Security and data handling

- Never commit credentials, API keys, wallets, production connection strings,
  or local operational SQL.
- Never commit real audit exports or institutional data.
- Use synthetic values in tests, examples, and documentation.
- Keep generated reports out of version control.
- Avoid logging payloads, free text, credentials, or secret-bearing DSNs.
- Pass SQL bind values separately from SQL text.
- Database and filesystem access belongs only to members whose contract
  requires it.
- Repository checks are guardrails; they do not replace institutional policy or
  review.

## CI

GitHub Actions runs formatting, linting, strict typing, documentation checks,
security audits, tests, and coverage gates.

The stable aggregate branch-protection check is:

```text
CI success
```

## Current status

All current Python members require at least 95% measured coverage.

Run:

```bash
make members
make coverage
```

for authoritative member, test, and coverage information.

## License

MIT
