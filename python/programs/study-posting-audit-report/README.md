# study-posting-audit-report

Generates a normalized two-file report from Study Posting Authoring audit rows.

The program composes:

- `tabular-row-sources` for schema-aware CSV and DB-API row streaming;
- `study-posting-ai-analysis` for per-record study-posting analysis;
- transitively, `text-post-edit-metrics` for generic text post-edit metrics.

A command-line client for selecting CSV or Oracle input is planned but is not
yet implemented. The current public API accepts an already configured
`RowSource`.

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

## Planned CLI

The planned client will support:

```text
study-posting-audit-report csv ...
study-posting-audit-report database ...
```

It will accept:

- a CSV path or Oracle SQL input;
- a schema path;
- an output path;
- database connection settings;
- SQL bind parameters.

Configuration resolution will use a shared reusable package with this
precedence:

```text
command line
→ process environment
→ .env
→ default
→ interactive prompt
```

That CLI and configuration package are not yet implemented.

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
