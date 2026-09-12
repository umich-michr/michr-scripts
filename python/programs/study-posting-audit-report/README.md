# study-posting-audit-report

Generates a normalized report from Study Posting Authoring audit rows supplied
by a CSV file or Oracle query.

The program composes:

- `program-configuration` for CLI, environment, dotenv, defaults, and prompts;
- `tabular-row-sources` for schema-aware lazy row streaming;
- `study-posting-ai-analysis` for per-record study analysis;
- `text-readability-metrics` for generic English readability metrics;
- transitively, `text-post-edit-metrics` for generic text metrics.

## Quick start

Show all commands:

```bash
uv run study-posting-audit-report --help
```

### CSV

```bash
uv run study-posting-audit-report csv \
  --input path/to/audit.csv
```

### Oracle

Prepare the local operational query:

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

The output directory must not already exist.

## Architecture

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
 records.csv + ai_assistance_metrics.csv + readability_metrics.csv
```

| Component | Responsibility |
|---|---|
| `program-configuration` | Generic precedence, dotenv loading, parsing, prompting, and secret redaction |
| `tabular-row-sources` | Stream and canonically convert CSV or DB-API rows |
| `study-posting-ai-analysis` | Apply study-specific policy to one record |
| `text-post-edit-metrics` | Calculate generic directional text metrics |
| `text-readability-metrics` | Calculate generic English readability metrics |
| This program | Select rows for analysis and publish the report |

The program does not duplicate source conversion, study policy, or metric
algorithms.

## Normalized output

A successful report contains:

```text
report/
├── records.csv
├── ai_assistance_metrics.csv
└── readability_metrics.csv
```

### `records.csv`

Contains every successfully processed source record, including:

- manual attempts;
- incomplete AI attempts;
- completed AI attempts.

Columns follow canonical schema order.

### `ai_assistance_metrics.csv`

Contains one row per analyzed study-posting field using
`study_posting_ai_analysis.FLATTENED_COLUMNS`.

Only completed AI attempts produce field metrics.

The files join through:

```text
records.<configured record ID column>
    =
ai_assistance_metrics.record_id
```
`readability_metrics.record_id` joins to the same configured source ID column.

Record IDs must be non-null and unique within a run.

### `readability_metrics.csv`

Contains one row per analyzed, nonblank text instance for:

- `title`;
- `about`;
- `purpose`;
- `description`;
- `compensation`.

For completed AI attempts, the output includes every offered suggestion and
each nonblank final value. The `selected` column identifies the first offered
suggestion matching the selected value. Compensation suggestions retain their
`genericCompensation` or `specificCompensation` kind and per-kind index.

For completed manual attempts, only nonblank final values are analyzed.
Incomplete attempts produce no readability rows.

The CSV contains metrics and labels but does not contain the source text.
Command-line runs use `text-readability-metrics` with its fixed English profile.

## Analysis selection

A row is selected for analysis when:

```text
ATTEMPT_TYPE = AI
ATTEMPT_RESULT = COMPLETE
```

Comparisons are exact and case-sensitive.

Processing order:

1. Non-AI rows are preserved without analysis.
2. AI rows whose result is not `COMPLETE` are preserved without analysis.
3. A completed AI row must have:
   - non-null `END_TIME`;
   - non-null `LLM_SUGGESTIONS`;
   - non-null `SELECTED_SUGGESTIONS`;
   - non-null `FINAL_SUBMISSION`.
4. A consistent completed AI row is analyzed.
5. Missing required data on a completed AI row raises `AuditRowError`.

Manual and incomplete rows do not require a complete set of analysis payloads.

The source query should return every row intended for `records.csv`; it should
not filter to completed AI attempts merely to control analysis.

## Input schema and SQL template

Committed program inputs:

```text
input/
├── .gitignore
├── audit-schema.json
└── audit-rows.example.sql
```

### Schema

`audit-schema.json` defines the canonical 39-column shape shared by CSV and
database sources.

Source columns:

- may appear in any order;
- must have the schema's exact case-sensitive names;
- must not be missing, unexpected, blank, or duplicated.

Canonical rows and `records.csv` use schema order.

Default processing-column names:

| Purpose | Column |
|---|---|
| Record ID | `ID` |
| Completion time | `END_TIME` |
| Attempt type | `ATTEMPT_TYPE` |
| Attempt result | `ATTEMPT_RESULT` |
| Suggestions | `LLM_SUGGESTIONS` |
| Selections | `SELECTED_SUGGESTIONS` |
| Final saved values | `FINAL_SUBMISSION` |

### SQL template

`audit-rows.example.sql` is sanitized and does not run unchanged.

Copy it to the ignored local path:

```text
input/audit-rows.sql
```

Then:

- replace `YOUR_HR_DATABASE_LINK`;
- replace account-exclusion placeholders under approved local policy;
- verify all table and view names;
- confirm the query returns no more than one row per audit ID;
- keep its projection synchronized with `audit-schema.json`;
- do not add credentials;
- omit a trailing semicolon for execution through python-oracledb.

`STACK_TRACE` is not projected. Its presence may be used inside the query to
derive `ATTEMPT_RESULT`.

Timestamp text uses microsecond precision:

```text
MM/DD/YYYY HH24:MI:SS.FF6
```

## Configuration

Both commands use:

```text
command line
→ process environment
→ dotenv
→ default
→ interactive prompt
→ missing-setting error
```

The workspace `.env` file is optional. An explicitly supplied `--env-file` must
exist.

Disable dotenv and prompts in a batch job:

```bash
uv run study-posting-audit-report csv \
  --input path/to/audit.csv \
  --no-env-file \
  --no-prompt
```

Boolean text accepts:

```text
true, false, 1, 0, yes, no, on, off
```

### Shared settings

| Setting | Environment variable | Default |
|---|---|---|
| Schema | `STUDY_POSTING_AUDIT_SCHEMA` | `input/audit-schema.json` |
| Output | `STUDY_POSTING_AUDIT_OUTPUT` | `output/study-posting-ai-audit-analysis/report/` |
| Include metric text | `STUDY_POSTING_AUDIT_INCLUDE_TEXT` | `false` |
| Dotenv file | `STUDY_POSTING_AUDIT_ENV_FILE` | workspace `.env` |
| Prompting | `STUDY_POSTING_AUDIT_PROMPT` | `true` |

`--include-text` controls only the flattened `selected_text` and `final_text`
columns in `ai_assistance_metrics.csv`. It does not remove source payloads from
`records.csv`.

## CSV command

```bash
uv run study-posting-audit-report csv \
  --input path/to/audit.csv
```

Options:

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

CSV settings:

| Setting | Environment variable | Default |
|---|---|---|
| Input | `STUDY_POSTING_AUDIT_CSV_INPUT` | Prompt if unresolved |
| Encoding | `STUDY_POSTING_AUDIT_CSV_ENCODING` | `utf-8-sig` |
| Delimiter | `STUDY_POSTING_AUDIT_CSV_DELIMITER` | `,` |
| Quote character | `STUDY_POSTING_AUDIT_CSV_QUOTECHAR` | `"` |
| Escape character | `STUDY_POSTING_AUDIT_CSV_ESCAPECHAR` | None |
| Null markers | `STUDY_POSTING_AUDIT_CSV_NULL_VALUES` | empty field and `\N` |

Repeat `--null-value` to replace the configured marker set:

```bash
uv run study-posting-audit-report csv \
  --input path/to/audit.csv \
  --null-value "" \
  --null-value '\N'
```

Environment and dotenv null markers use a JSON array:

```dotenv
STUDY_POSTING_AUDIT_CSV_NULL_VALUES=["","\\N"]
```

## Database command

```bash
uv run study-posting-audit-report database \
  --dsn "database.example:1521/service" \
  --username reporting_user
```

Options:

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

Database settings:

| Setting | Environment variable | Default |
|---|---|---|
| Driver | `STUDY_POSTING_AUDIT_DB_DRIVER` | `oracle` |
| DSN | `STUDY_POSTING_AUDIT_DB_DSN` | Prompt if unresolved |
| Username | `STUDY_POSTING_AUDIT_DB_USERNAME` | Prompt if unresolved |
| Password | `STUDY_POSTING_AUDIT_DB_PASSWORD` | Secret prompt if unresolved |
| Fetch size | `STUDY_POSTING_AUDIT_DB_FETCH_SIZE` | `500` |
| SQL file | `STUDY_POSTING_AUDIT_SQL_FILE` | local `input/audit-rows.sql` |
| SQL parameters | `STUDY_POSTING_AUDIT_SQL_PARAMS` | Empty object |

There is deliberately no `--password` option. Supply the password through the
process environment, `.env`, or a non-echoing interactive prompt.

### Oracle behavior

The registered driver is:

```text
oracle
```

Driver names are matched case-insensitively.

The adapter:

- uses `python-oracledb` thin mode;
- does not call `init_oracle_client()`;
- accepts an Easy Connect string or locally resolvable TNS alias;
- opens the connection lazily;
- delegates cursor, connection, batching, and conversion lifecycle to
  `DbApiQuerySource`.

### SQL parameters

Supply a JSON object:

```bash
uv run study-posting-audit-report database \
  --dsn "database.example:1521/service" \
  --username reporting_user \
  --sql-params-json '{"start_time":"2026-01-01","limit":100}'
```

Environment and dotenv use the same representation:

```dotenv
STUDY_POSTING_AUDIT_SQL_PARAMS={"start_time":"2026-01-01","limit":100}
```

Apply string-valued overrides:

```bash
uv run study-posting-audit-report database \
  --dsn "database.example:1521/service" \
  --username reporting_user \
  --sql-params-json '{"status":"BASE","limit":100}' \
  --sql-param status=COMPLETE \
  --sql-param end_time=2026-02-01
```

Resolution:

```text
environment or dotenv JSON
→ replaced by --sql-params-json when supplied
→ updated by repeated --sql-param NAME=VALUE
```

JSON values retain JSON types. Repeated `--sql-param` values are strings. The
first `=` separates a parameter name from its value.

The final mapping is passed separately to the DB-API cursor. SQL bind values are
never interpolated into SQL text.

## Python API

The output API accepts any configured `RowSource`:

```python
from study_posting_audit_report import generate_csv_report
from text_readability_metrics import analyze_readability

report = generate_csv_report(
    source,
    output_directory="output/report",
    readability_analyzer=analyze_readability,
)
```
The analyzer is injected at the report boundary. Omitting
`readability_analyzer` still creates `readability_metrics.csv`, but with only
its header.

Pure row processing is also available:

```python
from study_posting_audit_report import (
    AuditReportConfig,
    process_audit_rows,
    validate_source_schema,
)

config = AuditReportConfig()

validate_source_schema(
    source.schema,
    config=config,
)

with source.open_rows() as rows:
    for outcome in process_audit_rows(rows, config=config):
        consume_record(outcome.record)

        for metric_row in outcome.ai_assistance_rows:
            consume_metric(metric_row)
```

## Summary and exit behavior

`AuditReportSummary` contains:

| Field | Meaning |
|---|---|
| `source_rows` | Total source rows read |
| `analyzable_rows` | Completed AI rows selected for analysis |
| `analyzed_rows` | Selected rows successfully analyzed |
| `skipped_rows` | Manual and incomplete rows preserved without analysis |
| `failed_rows` | Reserved for a future non-fail-fast policy |
| `ai_assistance_rows` | AI-assistance field-metric rows written |
| `readability_rows` | Readability text-instance rows written |

The current implementation is fail-fast. For a published report:

```text
analyzable_rows = analyzed_rows
failed_rows = 0
source_rows = analyzed_rows + skipped_rows
```

A successful command returns status `0` and prints output paths and counts.

Expected configuration, source, analysis, row, and output failures return status
`2` with a concise message on standard error and no traceback.

On failure:

- processing stops;
- source resources close;
- the staging directory is removed;
- no output directory is published.

## Privacy and security

Report outputs may contain sensitive institutional data.

In particular, `records.csv` preserves source columns and may contain:

- AI suggestions;
- selected suggestions;
- final submissions;
- model metadata;
- feedback text.

Therefore:

- do not commit source exports or generated reports;
- keep `--include-text` disabled unless flattened text is required;
- do not log payloads or free text;
- do not expose passwords through CLI arguments;
- do not log secret-bearing connection strings;
- pass SQL bind values separately;
- run only in approved environments under applicable U-M controls.

## Development

Run from the repository root:

```bash
make test PACKAGE=study-posting-audit-report
make coverage PACKAGE=study-posting-audit-report
make check
```

See the [root README](../../../README.md) for workspace-wide guidance.

## License

MIT
