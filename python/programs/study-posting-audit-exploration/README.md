# study-posting-audit-exploration

Validates a normalized Study Posting Audit report and atomically publishes
identifier-free aggregates, restricted internal traceability files, metric
definitions, a manifest, and a self-contained faculty-facing HTML report.

The program reads its input report without modifying it.

## Quick start

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

Summarize published quality checks:

```bash
uv run study-posting-audit-exploration summarize-quality \
  --exploration /absolute/path/to/exploration
```

For end-to-end generation from a database or source audit CSV, use:

```bash
make audit-explore-database OPEN_REPORT=0
```

```bash
make audit-explore-csv \
  AUDIT_CSV_INPUT=/absolute/path/to/source-audit.csv \
  OPEN_REPORT=0
```

## Input

The normalized report must contain:

```text
records.csv
ai_assistance_metrics.csv
readability_metrics.csv
report_metadata.json
```

The input remains read-only. See the
[normalized-report contract](../study-posting-audit-report/docs/normalized-report.md).

## Output

A successful run publishes exactly 36 files, including:

- `report.html`;
- `analysis_manifest.json`;
- 31 CSV files;
- restricted analysis-audit records;
- identifier-free aggregate tables;
- metric definitions;
- candidate research questions.

See the [output reference](docs/output-reference.md) for the inventory and each
file's analytical grain.

## Documentation

| Document | Purpose |
|---|---|
| [`docs/running.md`](docs/running.md) | Commands, defaults, publication behavior, and exit statuses |
| [`docs/analysis-rules.md`](docs/analysis-rules.md) | Analytical units, eligibility, business rules, missing values, and interpretation |
| [`docs/output-reference.md`](docs/output-reference.md) | Exact 36-file inventory and output responsibilities |
| [`docs/data-lineage.md`](docs/data-lineage.md) | Source-column to normalized, derived, aggregate, and HTML lineage |
| [`docs/inquiry-guide.md`](docs/inquiry-guide.md) | Navigation for faculty, analysts, developers, and LLM assistants |
| Generated `definitions/metric_definitions.csv` | Aggregate-column definitions |
| Generated `analysis_manifest.json` | Source/output counts and reproducibility settings |

## Privacy boundary

Faculty-facing charts use aggregate tables only.

The final feedback table is the narrow authorized exception and displays only
audit record ID with `USER_FEEDBACK_COMMENTS`.

Files under `analysis-audit-records/` contain identifiers for authorized
internal traceability. Do not treat them as faculty-facing output.

Do not publish usernames, study numbers, source payloads, selected text, final
text, credentials, or operational SQL.

## Interpretation boundary

The exploration is descriptive.

It does not establish:

- causal effects of AI or manual authoring;
- author productivity, engagement quality, motivation, or tenure;
- writing quality or accessibility;
- why a suggestion was selected or edited;
- abandonment or final outcomes from no completion observed;
- scientific validity merely because software tests pass.

Every percentage requires an explicit eligible population and denominator.

## Development

From the repository root:

```bash
make test PACKAGE=study-posting-audit-exploration
make coverage PACKAGE=study-posting-audit-exploration
make check
```

## License

MIT
