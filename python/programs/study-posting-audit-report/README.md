# study-posting-audit-report

Generates normalized source records and field-level metrics from AI-Assisted
Study Posting Authoring audit rows.

The program composes schema-aware row sources from `tabular-row-sources` with
the study-specific analysis provided by `study-posting-ai-analysis`.

## Outputs

A successful report contains two CSV files:

```text
study-posting-report/
├── records.csv
└── field_metrics.csv
```

### `records.csv`

Contains one row per source audit record, preserving all source columns in
source-schema order.

Canonical source values are serialized consistently. By default, Python `None`
is written as `\N`. A real string equal to the configured null marker is
rejected to prevent ambiguous output.

Attempt-related columns such as `ATTEMPT_TYPE` and `ATTEMPT_RESULT` are
preserved when supplied by the source, but the report program does not require
or interpret them.

### `field_metrics.csv`

Contains one row per analyzed study-posting field, using the canonical columns
defined by:

```python
study_posting_ai_analysis.FLATTENED_COLUMNS
```

The relationship between the files is:

```text
records.<configured record ID column>
    =
field_metrics.record_id
```

Rows skipped because all three analysis payloads are null remain in
`records.csv` and produce no rows in `field_metrics.csv`.

The program requires source record IDs to be non-null and unique within one
report run.

## Payload-state policy

Whether a row is analyzed depends only on the presence of its three configured
analysis payloads:

| Suggestions | Selections | Final values | Result |
|---|---|---|---|
| Present | Present | Present | Analyze the row |
| Null | Null | Null | Skip the row |
| Mixed presence | Mixed presence | Mixed presence | Raise `AuditRowError` |

More precisely:

- all three payloads are non-`None`:
  - the row is analyzable;
  - the payloads are parsed and analyzed;
  - successful analysis produces field-metric rows;
- all three payloads are `None`:
  - the row is skipped;
  - it remains in `records.csv`;
  - it produces no field-metric rows;
- only some payloads are `None`:
  - the source row is inconsistent;
  - processing raises `AuditRowError`;
  - under the current fail-fast policy, no report is published.

Payload-state classification checks only whether values are `None`. It does not
validate payload contents. A non-null malformed payload is classified as
analyzable and then fails during parsing or study analysis.

Errors identify source row context, record identity when available, and
affected column names. They do not include source payload values.

## Attempt filtering

The report program no longer performs attempt-based eligibility filtering.

`ATTEMPT_TYPE` and `ATTEMPT_RESULT`:

- are not part of the default required-column mapping;
- are not required in the source schema;
- do not determine whether a row is analyzed;
- may still be included as provenance columns in `records.csv`;
- may still be filtered upstream by SQL, CSV preparation, or another source
  selection mechanism.

For example, a SQL query may still contain:

```sql
WHERE ATTEMPT_TYPE = 'AI'
  AND ATTEMPT_RESULT = 'COMPLETE'
```

That filtering is owned by the query or upstream source configuration, not by
this report program.

## Default source-column mapping

| Purpose | Default column |
|---|---|
| Record ID | `ID` |
| Suggestions | `LLM_SUGGESTIONS` |
| Selections | `SELECTED_SUGGESTIONS` |
| Final values | `FINAL_SUBMISSION` |

The four mapped columns must have unique, nonblank names.

The default required columns are:

```text
ID
LLM_SUGGESTIONS
SELECTED_SUGGESTIONS
FINAL_SUBMISSION
```

Additional source columns are permitted and are preserved in `records.csv`.

A custom mapping can be supplied when a source uses different names:

```python
from study_posting_audit_report import (
    AuditColumnMapping,
    AuditReportConfig,
)

config = AuditReportConfig(
    columns=AuditColumnMapping(
        record_id="AUDIT_ID",
        llm_suggestions="SUGGESTED",
        selected_suggestions="SELECTED",
        final_submission="FINAL",
    )
)
```

## Architecture

```text
CsvRowSource or DbApiQuerySource
              ↓
schema and record-ID validation
              ↓
payload-state classification
       ↙                 ↘
all null                 all present
   ↓                          ↓
 skipped            study-posting-ai-analysis
   ↓                          ↓
records.csv          records.csv + field_metrics.csv
```

Partial payload presence raises `AuditRowError`.

The program owns:

- source-column mapping;
- payload-state classification;
- source-schema validation;
- record-ID validation and duplicate detection;
- per-record processing policy;
- report summary counts;
- output serialization;
- atomic output-directory publication.

It delegates:

- row streaming and canonical conversion to `tabular-row-sources`;
- study field analysis to `study-posting-ai-analysis`;
- generic text metrics transitively to `text-post-edit-metrics`.

The analysis libraries remain independent of source schemas, databases, CSV
files, output directories, and report publication.

## Pure processing API

Source rows can be processed without writing report files:

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

A skipped row has:

```python
outcome.analyzed is False
outcome.metric_rows == ()
```

A successfully analyzed row has:

```python
outcome.analyzed is True
```

and contains one metric row per analyzed study-posting field.

Every `ProcessedAuditRow.record` is a fresh dictionary containing the complete
canonical source row.

### Explicit payload-state classification

Payload presence can also be classified directly:

```python
from study_posting_audit_report import (
    AuditReportConfig,
    PayloadState,
    classify_payload_state,
)

state = classify_payload_state(
    row,
    config=AuditReportConfig(),
    row_number=1,
    record_id=1001,
)

if state is PayloadState.ANALYZABLE:
    process_present_payloads()
elif state is PayloadState.SKIPPED:
    preserve_without_metrics()
```

`PayloadState` has two valid results:

- `PayloadState.ANALYZABLE`
- `PayloadState.SKIPPED`

Partial presence is invalid and raises `AuditRowError` rather than producing a
third state.

## Generate a report

```python
from study_posting_audit_report import generate_csv_report

report = generate_csv_report(
    source,
    output_directory="output/study-posting-report",
)

print(report.records_path)
print(report.field_metrics_path)
print(report.summary)
```

The requested output directory must not already exist.

The program writes both CSV files into a temporary sibling directory. It
publishes the completed directory only after source processing, analysis,
serialization, flushing, and file closure all succeed.

Existing output directories are never overwritten.

### Include free text

Selected and final free text are excluded from field metrics by default.

They can be included explicitly:

```python
from study_posting_audit_report import (
    AuditReportConfig,
    generate_csv_report,
)

report = generate_csv_report(
    source,
    output_directory="output/study-posting-report",
    config=AuditReportConfig(
        include_text=True,
    ),
)
```

Enabling this option may place source free text into the generated report.
Use it only when permitted by the applicable data-handling and privacy
requirements. Generated reports must not be committed to the repository.

### CSV output options

The default output settings are:

```python
from study_posting_audit_report import CsvOutputOptions

options = CsvOutputOptions(
    encoding="utf-8",
    null_value="\\N",
    lineterminator="\n",
)
```

Custom options apply to both output files:

```python
report = generate_csv_report(
    source,
    output_directory="output/study-posting-report",
    output_options=CsvOutputOptions(
        encoding="utf-8",
        null_value="NULL",
        lineterminator="\r\n",
    ),
)
```

## Report summary

A successful run returns an `AuditReportSummary` with these counts:

| Field | Meaning |
|---|---|
| `source_rows` | Total source rows read |
| `analyzable_rows` | Rows with all three payloads present |
| `analyzed_rows` | Analyzable rows successfully analyzed |
| `skipped_rows` | Rows with all three payloads null |
| `failed_rows` | Analyzable rows retained as failures under a non-fail-fast policy |
| `metric_rows` | Field-level metric rows written |

The current implementation is fail-fast, so a successfully published report
has:

```text
analyzed_rows = analyzable_rows
failed_rows = 0
source_rows = analyzed_rows + skipped_rows
```

A future non-fail-fast policy may produce nonzero `failed_rows`. That policy is
not currently implemented.

## Failure behavior

The current report-generation policy is fail-fast.

Failures include:

- a missing required source-schema column;
- an invalid or missing record ID;
- a duplicate record ID;
- partial payload presence;
- malformed analysis payloads;
- study-analysis policy violations;
- row-source failures;
- unsupported output values;
- CSV writing, flushing, or publication failures.

If any failure occurs:

- source processing stops;
- the row-source context is closed;
- the temporary staging directory is removed;
- the requested output directory is not published.

Because publication is atomic at the directory level, a failed run does not
leave a partially published `records.csv` or `field_metrics.csv`.

## Current status

Implemented:

- configurable source-column mapping;
- source-schema validation;
- record-ID extraction and duplicate detection;
- lazy payload-state classification;
- lazy study-analysis processing;
- preservation of skipped rows;
- partial-payload consistency errors;
- canonical CSV value serialization;
- atomic `records.csv` and `field_metrics.csv` publication;
- run summaries;
- expected configuration, source, row, and output exceptions.

Planned:

1. CSV-input command-line interface;
2. Oracle connection factory and database-input command-line interface;
3. optional per-record error reporting and non-fail-fast processing.

## Security and privacy

- Do not commit real audit exports or generated reports.
- Do not commit credentials, production connection strings, or secrets.
- Keep selected and final free text excluded unless it is explicitly required.
- Do not include payload contents in errors or logs.
- Use synthetic data for tests and examples.
- Handle institutional data only in approved environments and under applicable
  U-M policies and controls.

## Development

Run commands from the repository root:

```bash
make format
make lint
make typecheck
make test PACKAGE=study-posting-audit-report
make coverage PACKAGE=study-posting-audit-report
make check
```

To run one focused test file:

```bash
make test \
  PACKAGE=study-posting-audit-report \
  PYTEST_ARGS="tests/test_processing.py"
```

See the [root README](../../../README.md) for workspace-wide development
guidance.

## License

MIT
