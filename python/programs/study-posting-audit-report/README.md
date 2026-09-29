# study-posting-audit-report

Generates a normalized report from Study Posting Authoring audit rows supplied
by a CSV file or Oracle query.

The program preserves every successfully processed source row, applies field
analysis only where eligible, calculates readability for eligible nonblank
text, and atomically publishes a four-file normalized report.

## Quick start

From a source CSV:

```bash
uv run study-posting-audit-report csv \
  --input /absolute/path/to/source-audit.csv
```

From Oracle, first copy the sanitized example query to the program's
ignored default SQL path:

```bash
cp \
  python/programs/study-posting-audit-report/input/audit-rows.example.sql \
  python/programs/study-posting-audit-report/input/audit-rows.sql
```

Adapt that local copy for the approved reporting environment. With
`input/audit-rows.sql` in place, `--sql-file` is not required:

```bash
export STUDY_POSTING_AUDIT_DB_PASSWORD='...'

uv run study-posting-audit-report database \
  --dsn "database.example:1521/service" \
  --username reporting_user
```

See the [database-source guide](docs/running.md#database-source) for SQL
template requirements, configuration precedence, and path overrides.

The destination must not already exist. By default it is:

```text
output/study-posting-ai-audit-analysis/report
```

For the simplest end-to-end report and exploration workflows, use the root
Make targets:

```bash
make audit-explore-database OPEN_REPORT=0
```

```bash
make audit-explore-csv \
  AUDIT_CSV_INPUT=/absolute/path/to/source-audit.csv \
  OPEN_REPORT=0
```

## Documentation

| Document | Purpose |
|---|---|
| [`docs/running.md`](docs/running.md) | Commands, options, configuration precedence, defaults, and exit behavior |
| [`docs/feature-and-audit-model.md`](docs/feature-and-audit-model.md) | User flow, feature behavior, domain concepts, and captured audit data |
| [`docs/normalized-report.md`](docs/normalized-report.md) | Four-file output contract, joins, eligibility, and privacy |
| [`../study-posting-audit-exploration/docs/data-lineage.md`](../study-posting-audit-exploration/docs/data-lineage.md) | Source-column and downstream lineage |
| [`../../packages/study-posting-ai-analysis/docs/analysis-specification.md`](../../packages/study-posting-ai-analysis/docs/analysis-specification.md) | Study-field analysis policy |

## Responsibilities

This program owns:

- CSV and database source selection;
- program-specific configuration and CLI behavior;
- canonical source-column mapping;
- record identity and duplicate detection;
- completed-AI analysis eligibility;
- readability-instance selection;
- fail-fast row processing;
- atomic normalized-report publication.

It delegates:

- configuration precedence to `program-configuration`;
- CSV and DB-API conversion to `tabular-row-sources`;
- study-field policy to `study-posting-ai-analysis`;
- text metrics to `text-post-edit-metrics`;
- readability formulas to `text-readability-metrics`.

## Output

A successful run publishes:

```text
report/
├── records.csv
├── ai_assistance_metrics.csv
├── readability_metrics.csv
└── report_metadata.json
```

See [`docs/normalized-report.md`](docs/normalized-report.md) for exact grains,
joins, eligibility, and metadata semantics.

## Security

The normalized report may contain sensitive institutional data, including
source payloads and free text in `records.csv`.

- Run only in an approved environment.
- Do not commit source exports or generated reports.
- Keep flattened selected/final text disabled unless explicitly required.
- Do not log payloads, free text, credentials, or secret-bearing connection
  strings.
- Supply database passwords through environment, dotenv, or a non-echoing
  prompt; there is no password command-line option.
- Pass SQL bind values separately from SQL text.

## Development

From the repository root:

```bash
make test PACKAGE=study-posting-audit-report
make coverage PACKAGE=study-posting-audit-report
make check
```

## License

MIT
