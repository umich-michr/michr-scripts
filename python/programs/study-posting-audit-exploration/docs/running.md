# Running study-posting-audit-exploration

## Validate

```bash
uv run study-posting-audit-exploration validate \
  --input-report /absolute/path/to/normalized-report
```

Validation reads the four normalized input files and prints aggregate counts
only. It does not print usernames, study numbers, payloads, or free text.

## Analyze

```bash
uv run study-posting-audit-exploration analyze \
  --input-report /absolute/path/to/normalized-report \
  --output /absolute/path/to/exploration
```

The destination must not already exist.

Publication uses a staging directory and atomically renames the completed
directory. A failed run removes staging output and does not publish a partial
destination.

A successful run writes exactly 36 files. See
[`output-reference.md`](output-reference.md).

## Summarize quality

```bash
uv run study-posting-audit-exploration summarize-quality \
  --exploration /absolute/path/to/exploration
```

This command reads only:

- `quality/data_quality_summary.csv`;
- `analysis_manifest.json`.

It prints an identifier-free summary of validation guarantees, warnings,
affected counts, denominators, percentages, and analysis consequences.

Warnings do not fail by default. For warning-sensitive automation:

```bash
uv run study-posting-audit-exploration summarize-quality \
  --exploration /absolute/path/to/exploration \
  --fail-on-warning
```

Exit statuses:

| Status | Meaning |
|---:|---|
| `0` | Success |
| `2` | Invalid input or inconsistent exploration |
| `3` | Summary printed and at least one warning affected attempts |

## End-to-end Make workflows

From a database:

```bash
make audit-explore-database
```

From a source audit CSV:

```bash
make audit-explore-csv \
  AUDIT_CSV_INPUT=/absolute/path/to/source-audit.csv
```

Defaults:

| Variable | Default |
|---|---|
| `AUDIT_REPORT_OUTPUT` | `output/study-posting-ai-audit-analysis/report` |
| `AUDIT_EXPLORATION_OUTPUT` | `output/study-posting-ai-audit-analysis/exploration` |
| `AUDIT_CSV_INPUT` | Unset |
| `OPEN_REPORT` | `1` |
| `FAIL_ON_QUALITY_WARNING` | `0` |

Example for unattended CSV execution:

```bash
make audit-explore-csv \
  AUDIT_CSV_INPUT=/absolute/path/to/source-audit.csv \
  AUDIT_REPORT_OUTPUT=/absolute/path/to/normalized-report \
  AUDIT_EXPLORATION_OUTPUT=/absolute/path/to/exploration \
  OPEN_REPORT=0 \
  FAIL_ON_QUALITY_WARNING=1
```

The root helper validates cleanup paths and regenerates only the two requested
destinations. It rejects broad, overlapping, or source-containing paths.

## Input metadata

`report_metadata.json` uses schema version `1`.

New reports use:

```text
source_snapshot_provenance = REPORT_RUN_CUTOFF
```

The report process captures one UTC instant and reuses it for report generation
and source cutoff.

Normalized attempt timestamps are naive `America/Detroit` local time.
Exploration localizes them strictly before UTC cutoff comparison. Ambiguous or
nonexistent daylight-saving transition times fail validation.

The cutoff supports descriptive observation-window durations. It does not
create a minimum follow-up threshold or an abandonment classification.

## Browser behavior

The exploration CLI writes the report; the root Make workflow optionally opens
it.

Set:

```bash
OPEN_REPORT=0
```

for remote or automated execution.

Failure to open a browser does not invalidate successfully generated output.
