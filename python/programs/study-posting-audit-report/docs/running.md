# Running study-posting-audit-report

This document is the command and configuration reference for
`study-posting-audit-report`.

## Configuration precedence

Settings resolve in this order:

```text
command line
→ process environment
→ dotenv
→ default
→ interactive prompt
→ missing-setting error
```

The workspace `.env` file is optional. An explicitly supplied `--env-file`
must exist.

Disable dotenv and prompts in automation:

```bash
uv run study-posting-audit-report csv \
  --input /absolute/path/to/source-audit.csv \
  --no-env-file \
  --no-prompt
```

Boolean text accepts `true`, `false`, `1`, `0`, `yes`, `no`, `on`, and `off`.

## Shared options and defaults

| Setting | CLI | Environment | Default |
|---|---|---|---|
| Schema | `--schema` | `STUDY_POSTING_AUDIT_SCHEMA` | Program `input/audit-schema.json` |
| Output | `--output` | `STUDY_POSTING_AUDIT_OUTPUT` | `output/study-posting-ai-audit-analysis/report` |
| Include flattened text | `--include-text` / `--no-include-text` | `STUDY_POSTING_AUDIT_INCLUDE_TEXT` | `false` |
| Dotenv file | `--env-file` / `--no-env-file` | `STUDY_POSTING_AUDIT_ENV_FILE` | Workspace `.env` |
| Prompting | `--prompt` / `--no-prompt` | `STUDY_POSTING_AUDIT_PROMPT` | `true` |

`--include-text` controls selected and final text columns in
`ai_assistance_metrics.csv`; it does not remove source payloads from
`records.csv`.

## CSV source

```bash
uv run study-posting-audit-report csv \
  --input /absolute/path/to/source-audit.csv
```

CSV options:

```text
--input PATH
--schema PATH
--output PATH
--include-text / --no-include-text
--encoding NAME
--delimiter CHARACTER
--quotechar CHARACTER
--escapechar CHARACTER
--null-value TEXT
--env-file PATH / --no-env-file
--prompt / --no-prompt
```

| Setting | Environment | Default |
|---|---|---|
| Input | `STUDY_POSTING_AUDIT_CSV_INPUT` | Prompt if unresolved |
| Encoding | `STUDY_POSTING_AUDIT_CSV_ENCODING` | `utf-8-sig` |
| Delimiter | `STUDY_POSTING_AUDIT_CSV_DELIMITER` | `,` |
| Quote character | `STUDY_POSTING_AUDIT_CSV_QUOTECHAR` | `"` |
| Escape character | `STUDY_POSTING_AUDIT_CSV_ESCAPECHAR` | None |
| Null markers | `STUDY_POSTING_AUDIT_CSV_NULL_VALUES` | Empty field and `\N` |

Repeat `--null-value` to replace the configured marker set:

```bash
uv run study-posting-audit-report csv \
  --input /absolute/path/to/source-audit.csv \
  --null-value "" \
  --null-value '\N'
```

Environment and dotenv null markers use a JSON array:

```dotenv
STUDY_POSTING_AUDIT_CSV_NULL_VALUES=["","\\N"]
```

## Database source

Prepare the ignored local SQL file:

```bash
cp \
  python/programs/study-posting-audit-report/input/audit-rows.example.sql \
  python/programs/study-posting-audit-report/input/audit-rows.sql
```

Then run:

```bash
export STUDY_POSTING_AUDIT_DB_PASSWORD='...'

uv run study-posting-audit-report database \
  --dsn "database.example:1521/service" \
  --username reporting_user
```

Database options:

```text
--driver NAME
--dsn VALUE
--username VALUE
--sql-file PATH
--schema PATH
--output PATH
--fetch-size INTEGER
--sql-params-json JSON
--sql-param NAME=VALUE
--include-text / --no-include-text
--env-file PATH / --no-env-file
--prompt / --no-prompt
```

| Setting | Environment | Default |
|---|---|---|
| Driver | `STUDY_POSTING_AUDIT_DB_DRIVER` | `oracle` |
| DSN | `STUDY_POSTING_AUDIT_DB_DSN` | Prompt if unresolved |
| Username | `STUDY_POSTING_AUDIT_DB_USERNAME` | Prompt if unresolved |
| Password | `STUDY_POSTING_AUDIT_DB_PASSWORD` | Secret prompt if unresolved |
| Fetch size | `STUDY_POSTING_AUDIT_DB_FETCH_SIZE` | `500` |
| SQL file | `STUDY_POSTING_AUDIT_SQL_FILE` | Program `input/audit-rows.sql` |
| SQL parameters | `STUDY_POSTING_AUDIT_SQL_PARAMS` | `{}` |

There is no `--password` option. The Oracle adapter uses python-oracledb thin
mode.

Supply bind parameters as JSON:

```bash
uv run study-posting-audit-report database \
  --dsn "database.example:1521/service" \
  --username reporting_user \
  --sql-params-json '{"start_time":"2026-01-01","limit":100}'
```

Apply string-valued overrides with repeated `--sql-param`:

```bash
uv run study-posting-audit-report database \
  --dsn "database.example:1521/service" \
  --username reporting_user \
  --sql-param status=COMPLETE
```

Bind values are passed separately to the database driver and are never
interpolated into SQL text.

## Root Make workflows

Database:

```bash
make audit-explore-database
```

CSV:

```bash
make audit-explore-csv \
  AUDIT_CSV_INPUT=/absolute/path/to/source-audit.csv
```

Make variables:

| Variable | Default |
|---|---|
| `AUDIT_REPORT_OUTPUT` | `output/study-posting-ai-audit-analysis/report` |
| `AUDIT_EXPLORATION_OUTPUT` | `output/study-posting-ai-audit-analysis/exploration` |
| `AUDIT_CSV_INPUT` | Unset |
| `OPEN_REPORT` | `1` |
| `FAIL_ON_QUALITY_WARNING` | `0` |

The helper removes and regenerates only the two validated destinations beneath
the repository `output/` directory. It rejects broad, overlapping, or
source-containing paths.

## SQL template

The committed `input/audit-rows.example.sql` is sanitized and does not run
unchanged.

Copy it to ignored `input/audit-rows.sql`, then:

- replace local database-link and exclusion placeholders;
- verify table and view names;
- confirm no more than one row per audit ID;
- keep its projection synchronized with `input/audit-schema.json`;
- omit a trailing semicolon for python-oracledb;
- never add credentials.

## Exit behavior

A successful command returns status `0` and prints output paths and counts.

Expected configuration, source, analysis, row, and publication failures return
status `2` with a concise message and no traceback.

Processing is fail-fast. On failure, source resources close, staging output is
removed, and no destination is published.
