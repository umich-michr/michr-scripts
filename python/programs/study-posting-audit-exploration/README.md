# study-posting-audit-exploration

Validates and explores normalized output from `study-posting-audit-report`.

## Input

The program accepts a report directory containing exactly the required source files:

- `records.csv`
- `ai_assistance_metrics.csv`
- `readability_metrics.csv`

The input report remains read-only.

## Initial Command

```bash
uv run study-posting-audit-exploration validate \
  --input-report output/study-posting-ai-audit-analysis/report
```

# First Implementation Milestone

The first implementation milestone validates:

- Required files and exact headers
- Canonical scalar and datetime values
- Unique audit IDs
- Metric-to-attempt joins
- One or zero completed attempts per study
- Required completed-attempt values
- Completed-attempt author and creator consistency
- Finite numeric metrics
- Readability selected-marker consistency

It prints counts only. It does not print usernames, study numbers, payloads, or free text.

## Analytical Identities

- `records.csv.ID` is the audit attempt ID.
- Metric-file `record_id` values join to the audit attempt ID.
- `STUDY_NUM` groups attempts for one study.
- `AUTHOR_USER_NAME` is the attempt-author identity and is used exactly as stored.
- `CREATED_BY_ID` is the created study's creator ID, not the author identity for preceding attempts.
- A study can have no more than one `COMPLETE` attempt.

## Boundary

This program owns exploratory derivation, aggregation, and publication.

It does not recreate:

- Source extraction
- Study-field analysis
- Post-edit metrics
- Readability calculations

## Development

Run from the repository root:

```bash
make test PACKAGE=study-posting-audit-exploration
make coverage PACKAGE=study-posting-audit-exploration
```

# License

MIT
