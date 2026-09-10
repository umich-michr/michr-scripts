# study-posting-audit-report

Generates a normalized two-file report from Study Posting Authoring audit rows.

The program composes:

- `tabular-row-sources` for schema-aware CSV and DB-API row streaming;
- `study-posting-ai-analysis` for per-record study-posting analysis;
- transitively, `text-post-edit-metrics` for generic text post-edit metrics.

The command-line client reads either CSV input or an Oracle query result. The
public Python API also accepts any configured `RowSource`.

## Architecture

```text
CSV file or DB-API query
          ↓
tabular-row-sources
          ↓ canonical Row values
study-posting-audit-report
          ↓
study-posting-ai-analysis
          ↓
text-post-edit-metrics
```

Responsibilities remain separate:

| Component | Responsibility |
|---|---|
| `tabular-row-sources` | Stream and canonically convert CSV or query rows |
| `study-posting-ai-analysis` | Apply study-specific analysis to one audit record |
| `text-post-edit-metrics` | Calculate generic directional text metrics |
| This program | Select rows for analysis and publish the normalized report |

The program does not duplicate source conversion, study policy, or text-metric
algorithms.

## Output

A successful report contains:

```text
report/
├── records.csv
└── field_metrics.csv
```

### `records.csv`

Contains every successfully processed source record, including:

- manual attempts;
- incomplete AI attempts;
- completed AI attempts.

Columns follow canonical schema order. Additional source columns are preserved
when they are part of the supplied schema.

### `field_metrics.csv`

Contains one row per analyzed study-posting field, using:

```python
study_posting_ai_analysis.FLATTENED_COLUMNS
```

Only completed AI attempts produce field metrics.

The files join through:

```text
records.<configured record ID column>
    =
field_metrics.record_id
```

Record IDs must be non-null and unique within a report run.

## Analysis selection

A row is selected for analysis when:

```text
ATTEMPT_TYPE = AI
ATTEMPT_RESULT = COMPLETE
```

The values are compared exactly and case-sensitively.

Rows are handled in this order:

1. A non-AI row is preserved without analysis.
2. An AI row whose result is not `COMPLETE` is preserved without analysis.
3. A completed AI row must have:
   - a non-null `END_TIME`;
   - non-null `LLM_SUGGESTIONS`;
   - non-null `SELECTED_SUGGESTIONS`;
   - non-null `FINAL_SUBMISSION`.
4. A consistent completed AI row is parsed and analyzed.
5. A completed AI row missing required analysis data raises `AuditRowError`.

Manual and incomplete rows are not required to have a consistent set of
analysis payloads. This allows completed manual rows to retain
`FINAL_SUBMISSION` without AI suggestion or selection payloads.

The source query should return all records intended for `records.csv`; it should
not filter to completed AI attempts merely to control analysis.

## Default source-column mapping

| Purpose | Default column |
|---|---|
| Record ID | `ID` |
| Attempt completion time | `END_TIME` |
| Attempt type | `ATTEMPT_TYPE` |
| Attempt result | `ATTEMPT_RESULT` |
| Suggestions | `LLM_SUGGESTIONS` |
| Selections | `SELECTED_SUGGESTIONS` |
| Final saved values | `FINAL_SUBMISSION` |

All configured names must be nonblank and unique.

A custom mapping can be supplied:

```python
from study_posting_audit_report import (
    AuditColumnMapping,
    AuditReportConfig,
)

config = AuditReportConfig(
    columns=AuditColumnMapping(
        record_id="AUDIT_ID",
        end_time="FINISHED_AT",
        attempt_type="TYPE",
        attempt_result="RESULT",
        llm_suggestions="SUGGESTED",
        selected_suggestions="SELECTED",
        final_submission="FINAL",
    )
)
```

## Input templates

The program directory contains:

```text
input/
├── .gitignore
├── audit-schema.json
└── audit-rows.example.sql
```

### `audit-schema.json`

Defines the canonical 39-column row shape shared by CSV and database input.

Source columns may appear in any order, but their case-sensitive names must
match the schema exactly. Canonical rows and `records.csv` use schema order.

### `audit-rows.example.sql`

A sanitized example of the operational Oracle query.

It must be copied locally to:

```text
input/audit-rows.sql
```

before database execution. The local file is ignored by Git because it may
contain environment-specific database links and approved account exclusions.

The example SQL:

- contains no credentials;
- uses placeholders for the HR database link;
- uses placeholders for locally excluded test, service, or system accounts;
- excludes stack-trace text from the final projection;
- retains stack-trace presence only to derive `ATTEMPT_RESULT`;
- formats timestamps with six fractional digits.

The default database CLI will use `input/audit-rows.sql` after that CLI is
implemented.

## CSV command

Run from the repository root:

```bash
uv run study-posting-audit-report csv \
  --input path/to/audit.csv
```

The command uses these workspace defaults:

| Setting | Default |
|---|---|
| Schema | `python/programs/study-posting-audit-report/input/audit-schema.json` |
| Output directory | `output/study-posting-ai-audit-analysis/report/` |
| Dotenv file | `.env` |
| Include selected/final metric text | `false` |
| CSV encoding | `utf-8-sig` |
| Delimiter | `,` |
| Quote character | `"` |
| Escape character | none |
| Null markers | empty field and `\N` |

The output directory must not already exist.

### Configuration precedence

CSV command settings use:

```text
command line
→ process environment
→ .env
→ default
→ interactive prompt
```

The default `.env` file is optional. An explicitly requested `--env-file` must
exist.

Disable dotenv loading and prompting for a batch invocation:

```bash
uv run study-posting-audit-report csv \
  --input path/to/audit.csv \
  --no-env-file \
  --no-prompt
```

### CSV options

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

Repeat `--null-value` to define multiple null markers:

```bash
uv run study-posting-audit-report csv \
  --input path/to/audit.csv \
  --null-value "" \
  --null-value '\N'
```

Explicit CLI null markers replace environment, dotenv, and default markers.

`--include-text` controls only the flattened `selected_text` and `final_text`
columns in `field_metrics.csv`. It does not remove source payload columns from
`records.csv`.

### Environment variables

| Setting | Environment variable |
|---|---|
| CSV input | `STUDY_POSTING_AUDIT_CSV_INPUT` |
| Schema | `STUDY_POSTING_AUDIT_SCHEMA` |
| Output directory | `STUDY_POSTING_AUDIT_OUTPUT` |
| Include metric text | `STUDY_POSTING_AUDIT_INCLUDE_TEXT` |
| CSV encoding | `STUDY_POSTING_AUDIT_CSV_ENCODING` |
| Delimiter | `STUDY_POSTING_AUDIT_CSV_DELIMITER` |
| Quote character | `STUDY_POSTING_AUDIT_CSV_QUOTECHAR` |
| Escape character | `STUDY_POSTING_AUDIT_CSV_ESCAPECHAR` |
| Null markers | `STUDY_POSTING_AUDIT_CSV_NULL_VALUES` |
| Dotenv path | `STUDY_POSTING_AUDIT_ENV_FILE` |
| Prompting | `STUDY_POSTING_AUDIT_PROMPT` |

Environment and dotenv null markers use a JSON array:

```dotenv
STUDY_POSTING_AUDIT_CSV_NULL_VALUES=["","\\N"]
```

Boolean values accept:

```text
true, false, 1, 0, yes, no, on, off
```

### Exit behavior

A successful command returns exit status `0` and prints the output paths and
summary counts.

Expected configuration, source, row-processing, analysis, and report-output
failures return status `2` with a concise message on standard error. Expected
failures do not print a traceback.

## Pure processing API

Rows can be processed without writing files:

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
    for outcome in process_audit_rows(
        rows,
        config=config,
    ):
        consume_record(outcome.record)

        for metric_row in outcome.metric_rows:
            consume_metric(metric_row)
```

Skipped manual and incomplete rows have:

```python
outcome.analyzed is False
outcome.metric_rows == ()
```

Successfully analyzed completed AI rows have:

```python
outcome.analyzed is True
```

and contain one metric row per analyzed study-posting field.

## Generate a report

```python
from study_posting_audit_report import generate_csv_report

report = generate_csv_report(
    source,
    output_directory="output/study-posting-ai-audit-analysis/report",
)

print(report.records_path)
print(report.field_metrics_path)
print(report.summary)
```

The output directory must not already exist.

Both files are written into a temporary sibling directory. The completed
directory is published only after source processing, analysis, serialization,
flushing, and file closure all succeed.

Existing output directories are never overwritten.

## Free text

Selected and final free text are excluded from field metrics by default.

To include them explicitly:

```python
from study_posting_audit_report import (
    AuditReportConfig,
    generate_csv_report,
)

report = generate_csv_report(
    source,
    output_directory="output/study-posting-ai-audit-analysis/report",
    config=AuditReportConfig(
        include_text=True,
    ),
)
```

Enabling this option may place source free text in the generated report. Use it
only under applicable privacy and data-handling requirements.

## CSV output options

Default output settings are:

```python
from study_posting_audit_report import CsvOutputOptions

options = CsvOutputOptions(
    encoding="utf-8",
    null_value="\\N",
    lineterminator="\n",
)
```

A real string equal to the configured null marker is rejected to avoid
ambiguous output.

## Summary counts

`AuditReportSummary` contains:

| Field | Meaning |
|---|---|
| `source_rows` | Total source rows read |
| `analyzable_rows` | Completed AI rows selected for analysis |
| `analyzed_rows` | Selected rows successfully analyzed |
| `skipped_rows` | Manual and incomplete rows preserved without analysis |
| `failed_rows` | Selected rows retained as failures under a future non-fail-fast policy |
| `metric_rows` | Field-level metric rows written |

The current implementation is fail-fast. A successfully published report has:

```text
analyzable_rows = analyzed_rows
failed_rows = 0
source_rows = analyzed_rows + skipped_rows
```

## Failure behavior

Expected failures include:

- missing required schema columns;
- invalid or duplicate record IDs;
- a completed AI row without `END_TIME`;
- a completed AI row missing an analysis payload;
- malformed analysis payloads;
- study-analysis policy violations;
- source failures;
- unsupported output values;
- publication failures.

On failure:

- processing stops;
- source resources are closed;
- the staging directory is removed;
- no output directory is published.

Errors must not contain analysis payloads, free text, credentials, passwords, or
secret-bearing connection strings.

## Oracle connection adapter

The program includes an Oracle connection adapter built on `python-oracledb`.

The adapter:

- uses python-oracledb thin mode;
- does not call `init_oracle_client()`;
- accepts an Easy Connect string or a locally resolvable TNS alias;
- validates the DSN, username, and password;
- creates connections lazily through a zero-argument factory;
- leaves connection and cursor ownership to `DbApiQuerySource`.

Example Python composition:

```python
from study_posting_audit_report.connections import OracleDriver
from tabular_row_sources import (
    DbApiQuerySource,
    load_schema_json,
    read_sql_file,
)

driver = OracleDriver()
connect = driver.create_connect(
    dsn=database_dsn,
    username=database_username,
    password=database_password,
)

source = DbApiQuerySource(
    connect=connect,
    sql=read_sql_file(sql_path),
    schema=load_schema_json(schema_path),
    parameters=sql_parameters,
    fetch_size=500,
)
```

SQL and bind parameters remain separate. `DbApiQuerySource` passes them
separately to the database cursor and does not interpolate values into SQL.

Connection creation belongs to this program. Generic query streaming and
canonical row conversion remain in `tabular-row-sources`.

The driver registry currently supports:

```text
oracle
```

The registry provides an extension point for future database adapters without
changing report processing or row streaming.

## Database command

Run an Oracle query and generate the normalized report:

```bash
uv run study-posting-audit-report database \
  --dsn "database.example:1521/service" \
  --username reporting_user
```

The command uses these defaults:

| Setting | Default |
|---|---|
| Driver | `oracle` |
| SQL file | `python/programs/study-posting-audit-report/input/audit-rows.sql` |
| Schema | `python/programs/study-posting-audit-report/input/audit-schema.json` |
| Output directory | `output/study-posting-ai-audit-analysis/report/` |
| Dotenv file | `.env` |
| Fetch size | `500` |
| SQL parameters | Empty mapping |
| Include selected/final metric text | `false` |

The local operational SQL file is ignored by Git. Create it by copying and
adapting the sanitized example:

```bash
cp \
  python/programs/study-posting-audit-report/input/audit-rows.example.sql \
  python/programs/study-posting-audit-report/input/audit-rows.sql
```

Review the copied query before use:

- replace the database-link placeholder;
- replace account-exclusion placeholders according to approved local policy;
- confirm the final projection matches `audit-schema.json`;
- confirm the query returns at most one row per audit record ID;
- do not add credentials to the SQL file.

### Oracle connection

The initial database command uses `python-oracledb` in thin mode.

The DSN may be:

- an Easy Connect string; or
- a TNS alias resolvable by the local Oracle configuration.

The command does not call `init_oracle_client()`.

The initial authentication mode is username and password. There is deliberately
no `--password` command-line option because command-line values can be exposed
through shell history or process inspection.

Resolve the password through:

```text
STUDY_POSTING_AUDIT_DB_PASSWORD
```

in the process environment or `.env`. If it remains unresolved and prompting
is enabled in an interactive terminal, the command requests it through a
non-echoing secret prompt.

### Database options

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

The currently registered database driver is:

```text
oracle
```

Driver names are matched case-insensitively.

### Database environment variables

| Setting | Environment variable |
|---|---|
| Driver | `STUDY_POSTING_AUDIT_DB_DRIVER` |
| DSN | `STUDY_POSTING_AUDIT_DB_DSN` |
| Username | `STUDY_POSTING_AUDIT_DB_USERNAME` |
| Password | `STUDY_POSTING_AUDIT_DB_PASSWORD` |
| Fetch size | `STUDY_POSTING_AUDIT_DB_FETCH_SIZE` |
| SQL file | `STUDY_POSTING_AUDIT_SQL_FILE` |
| SQL parameters | `STUDY_POSTING_AUDIT_SQL_PARAMS` |
| Schema | `STUDY_POSTING_AUDIT_SCHEMA` |
| Output directory | `STUDY_POSTING_AUDIT_OUTPUT` |
| Include metric text | `STUDY_POSTING_AUDIT_INCLUDE_TEXT` |
| Dotenv path | `STUDY_POSTING_AUDIT_ENV_FILE` |
| Prompting | `STUDY_POSTING_AUDIT_PROMPT` |

### Parameterized SQL

SQL bind parameters remain separate from SQL text.

Provide a JSON object:

```bash
uv run study-posting-audit-report database \
  --dsn "database.example:1521/service" \
  --username reporting_user \
  --sql-params-json '{"start_time":"2026-01-01","limit":100}'
```

Environment and dotenv configuration use the same JSON-object representation:

```dotenv
STUDY_POSTING_AUDIT_SQL_PARAMS={"start_time":"2026-01-01","limit":100}
```

Apply string-valued command-line overrides with repeated options:

```bash
uv run study-posting-audit-report database \
  --dsn "database.example:1521/service" \
  --username reporting_user \
  --sql-params-json '{"status":"BASE","limit":100}' \
  --sql-param status=COMPLETE \
  --sql-param end_time=2026-02-01
```

Resolution for SQL parameters is:

```text
environment or dotenv JSON object
→ replaced by --sql-params-json when supplied
→ updated by repeated --sql-param NAME=VALUE options
```

JSON values retain their JSON types. Values supplied through `--sql-param` are
strings. The first `=` separates the parameter name from its value, so a value
may itself contain `=`.

The final mapping is passed separately to the DB-API cursor. The program never
interpolates bind values into SQL text.

### Database execution flow

```text
database command
      ↓
layered configuration
      ↓
Oracle driver registry and deferred connection factory
      ↓
DbApiQuerySource
      ↓
study-posting audit processing
      ↓
records.csv + field_metrics.csv
```

Connections and cursors are opened lazily and closed by `DbApiQuerySource` after
normal completion, early termination, or failure.

## Development

Run from the repository root:

```bash
make test PACKAGE=study-posting-audit-report
make coverage PACKAGE=study-posting-audit-report
make check
```

See the [root README](../../../README.md) for workspace guidance.

## License

MIT
