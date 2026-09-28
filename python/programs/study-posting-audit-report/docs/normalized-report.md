# Normalized Study Posting Audit report

A successful `study-posting-audit-report` run atomically publishes four files.

```text
report/
├── records.csv
├── ai_assistance_metrics.csv
├── readability_metrics.csv
└── report_metadata.json
```

The destination must not already exist. Publication uses a staging directory;
a failed run removes staging output and does not publish a partial report.

## `records.csv`

Grain: one successfully processed source attempt.

The file preserves manual, incomplete AI, and completed AI attempts in canonical
schema order.

Key:

```text
configured record ID column
```

The default is `ID`, which must be nonmissing and unique.

The file may contain sensitive identifiers, payloads, metadata, and free text.
It is not a faculty-facing aggregate.

## `ai_assistance_metrics.csv`

Grain: one analyzed field from a completed AI attempt.

Join:

```text
ai_assistance_metrics.record_id = records.ID
```

Rows follow `study_posting_ai_analysis.FLATTENED_COLUMNS`.

Only completed AI attempts produce these rows. Selected and final text are
excluded by default. Enabling `--include-text` affects this flattened file only;
it does not remove payloads from `records.csv`.

## `readability_metrics.csv`

Grain: one eligible, nonblank text instance.

Join:

```text
readability_metrics.record_id = records.ID
```

Completed AI attempts contribute offered suggestions and final values.
Completed manual attempts contribute final values. Incomplete attempts
contribute no readability rows.

The file contains metric values and labels, not source text. Blank text is
omitted, so absence of a row does not prove that a field was absent from the
source.

## `report_metadata.json`

Grain: one normalized-report run.

Schema version is currently `1`.

Fields:

| Field | Meaning |
|---|---|
| `schema_version` | Metadata schema version |
| `report_generated_at_utc` | UTC instant captured once for report generation |
| `source_snapshot_as_of_utc` | Report-run cutoff for new reports |
| `source_snapshot_provenance` | `REPORT_RUN_CUTOFF` for new reports |

New reports reuse one captured UTC instant for report generation and source
cutoff. The cutoff is not inferred from attempt, completion, creation, login,
filesystem, or downstream publication timestamps.

## Analysis eligibility

A row is selected for field analysis when:

```text
ATTEMPT_TYPE = AI
ATTEMPT_RESULT = COMPLETE
```

The comparison is exact and case-sensitive.

An eligible row must also have:

- nonmissing `END_TIME`;
- `LLM_SUGGESTIONS`;
- `SELECTED_SUGGESTIONS`;
- `FINAL_SUBMISSION`.

Missing required values raise `AuditRowError`.

Manual and incomplete attempts remain in `records.csv` without field metrics.

## Summary invariants

The program is fail-fast.

For a successful report:

```text
analyzable_rows = analyzed_rows
failed_rows = 0
source_rows = analyzed_rows + skipped_rows
```

`skipped_rows` are manual or incomplete attempts preserved without study-field
analysis.

## Serialization

CSV output uses:

- UTF-8;
- canonical declared column order;
- the configured missing-value representation;
- atomic publication through staging.

The source schema is
`input/audit-schema.json`. The exact source-column dictionary and downstream
lineage are maintained in the exploration
[data-lineage guide](../../study-posting-audit-exploration/docs/data-lineage.md).

## Privacy

Treat the normalized report as sensitive institutional data.

- Do not commit it.
- Do not attach it to issues or public discussions.
- Do not log payloads, free text, or identifiers.
- Keep flattened text disabled unless required.
- Store and process it only in approved environments.

Faculty-facing output is produced later by the exploration program from
aggregate tables, except for its narrowly authorized feedback display.
