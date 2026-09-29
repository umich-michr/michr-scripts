# Python workspace

Python packages and runnable programs in `michr-scripts` share one
[uv workspace](https://docs.astral.sh/uv/), lockfile, virtual environment,
development workflow, and continuous-integration configuration.

```text
python/
├── packages/    Reusable libraries
└── programs/    Runnable applications
```

Use the root `Makefile`; do not manually activate `.venv`, invoke `pip`, or edit
`uv.lock`.

## Packages

| Package | Import | Purpose |
|---|---|---|
| [`program-configuration`](packages/program-configuration/README.md) | `program_configuration` | Layered, typed, secret-aware configuration |
| [`tabular-row-sources`](packages/tabular-row-sources/README.md) | `tabular_row_sources` | Schema-aware lazy CSV and DB-API row sources |
| [`text-post-edit-metrics`](packages/text-post-edit-metrics/README.md) | `text_post_edit_metrics` | Directional technical text post-edit metrics |
| [`text-readability-metrics`](packages/text-readability-metrics/README.md) | `text_readability_metrics` | English readability metrics and counts |
| [`study-posting-ai-analysis`](packages/study-posting-ai-analysis/README.md) | `study_posting_ai_analysis` | Study-posting suggestion, selection, and final-value analysis |

Package READMEs document public APIs and link to detailed methodology, schema,
or policy references.

## Programs

| Program | Command | Purpose |
|---|---|---|
| [`study-posting-audit-report`](programs/study-posting-audit-report/README.md) | `study-posting-audit-report` | Normalize Study Posting Authoring audit rows from CSV or Oracle |
| [`study-posting-audit-exploration`](programs/study-posting-audit-exploration/README.md) | `study-posting-audit-exploration` | Validate a normalized report and publish aggregate analysis and HTML |

See the [program index](programs/README.md) for program boundaries.

## Quick start: Study Posting Audit

The root Makefile can generate a normalized audit report and its descriptive
exploration in one workflow.

### Database source

```bash
make audit-explore-database
```

Disable browser opening for remote or automated execution:

```bash
make audit-explore-database OPEN_REPORT=0
```

Database connection, SQL, schema, and prompt settings use the audit-report
program's configuration precedence. Passwords are not accepted as Make
variables or command-line arguments.

### CSV source

```bash
make audit-explore-csv \
  AUDIT_CSV_INPUT=/absolute/path/to/source-audit.csv
```

`AUDIT_CSV_INPUT` is the source audit export, not an already normalized
`records.csv`.

If `AUDIT_CSV_INPUT` is omitted, the program continues resolution through its
environment, dotenv, and interactive-prompt behavior.

Choose explicit destinations when needed:

```bash
make audit-explore-csv \
  AUDIT_CSV_INPUT=/absolute/path/to/source-audit.csv \
  AUDIT_REPORT_OUTPUT=/absolute/path/to/normalized-report \
  AUDIT_EXPLORATION_OUTPUT=/absolute/path/to/exploration \
  OPEN_REPORT=0
```

### Make defaults

| Variable | Default |
|---|---|
| `AUDIT_REPORT_OUTPUT` | `output/study-posting-ai-audit-analysis/report` |
| `AUDIT_EXPLORATION_OUTPUT` | `output/study-posting-ai-audit-analysis/exploration` |
| `AUDIT_CSV_INPUT` | Unset; resolved by the program |
| `OPEN_REPORT` | `1` |
| `FAIL_ON_QUALITY_WARNING` | `0` |

Set `FAIL_ON_QUALITY_WARNING=1` when quality warnings should produce a nonzero
workflow result.

## Direct program commands

Show audit-report help:

```bash
uv run study-posting-audit-report --help
```

Generate a normalized report from CSV:

```bash
uv run study-posting-audit-report csv \
  --input /absolute/path/to/source-audit.csv
```

Generate one from Oracle:

```bash
export STUDY_POSTING_AUDIT_DB_PASSWORD='...'

uv run study-posting-audit-report database \
  --dsn "database.example:1521/service" \
  --username reporting_user
```

Analyze an existing normalized report:

```bash
uv run study-posting-audit-exploration analyze \
  --input-report /absolute/path/to/normalized-report \
  --output /absolute/path/to/exploration
```

Validate without publishing:

```bash
uv run study-posting-audit-exploration validate \
  --input-report /absolute/path/to/normalized-report
```

See the linked program READMEs for complete options, defaults, data contracts,
security guidance, and detailed documents.

## Audit documentation path

Use this progression:

1. [Audit-report README](programs/study-posting-audit-report/README.md)
2. [Running the audit report](programs/study-posting-audit-report/docs/running.md)
3. [Feature and audit model](programs/study-posting-audit-report/docs/feature-and-audit-model.md)
4. [Normalized report contract](programs/study-posting-audit-report/docs/normalized-report.md)
5. [Exploration README](programs/study-posting-audit-exploration/README.md)
6. [Running exploration](programs/study-posting-audit-exploration/docs/running.md)
7. [Exploration analytical rules](programs/study-posting-audit-exploration/docs/analysis-rules.md)
8. [Exploration output reference](programs/study-posting-audit-exploration/docs/output-reference.md)
9. [Data lineage](programs/study-posting-audit-exploration/docs/data-lineage.md)
10. [Faculty and LLM inquiry guide](programs/study-posting-audit-exploration/docs/inquiry-guide.md)

## Dependency direction

```text
reusable package
       ↑
specific package
       ↑
runnable program
```

Rules:

1. Programs may depend on packages.
2. Packages must not depend on programs.
3. More reusable packages must not import more specific packages.
4. Shared behavior belongs in an owning package rather than being copied.
5. Add a dependency only to the member that imports it.

Add a dependency with:

```bash
uv add --package <distribution-name> <dependency>
```

Never edit `uv.lock` manually.

## Development

List workspace members:

```bash
make members
```

Run one member:

```bash
make test PACKAGE=study-posting-ai-analysis
make coverage PACKAGE=study-posting-audit-exploration
```

Pass pytest options:

```bash
make test \
  PACKAGE=study-posting-audit-report \
  PYTEST_ARGS="-k database -vv"
```

Run the full gate:

```bash
make check
```

## Adding a Python member

Packages use:

```text
python/packages/<distribution-name>/
├── pyproject.toml
├── README.md
├── src/
└── tests/
```

Programs use:

```text
python/programs/<distribution-name>/
├── pyproject.toml
├── README.md
├── src/
└── tests/
```

Each member owns its metadata, source, tests, README, detailed docs, and
coverage configuration.

When adding a member:

1. use a `src` layout;
2. document its contract and exclusions;
3. add complete type annotations and focused tests;
4. configure pytest and coverage;
5. add scoped instructions when important rules apply;
6. run `uv lock`, `uv sync --all-packages`, and `make check`.
