# study-posting-audit-exploration

Validates and explores normalized output from `study-posting-audit-report`.

The program reads an existing normalized report without modifying it. It can
validate the report contract or publish derived audit and aggregate CSV files
for exploratory analysis.

## Input

The program accepts a report directory containing exactly these required source
files:

- `records.csv`
- `ai_assistance_metrics.csv`
- `readability_metrics.csv`

The input report remains read-only.

## Commands

### Validate a normalized report

~~~~bash
uv run study-posting-audit-exploration validate \
  --input-report output/study-posting-ai-audit-analysis/report
~~~~

Successful validation prints counts only. It does not print usernames, study
numbers, payloads, or free text.

### Publish the current exploration outputs

The output directory must not already exist.

~~~~bash
uv run study-posting-audit-exploration analyze \
  --input-report output/study-posting-ai-audit-analysis/report \
  --output output/study-posting-ai-audit-analysis/exploration
~~~~

Publication uses a staging directory and atomically renames the completed
directory into place. If publication fails, the staging directory is removed
and the destination is not published.

## Validation

The current validation contract checks:

- required files and exact headers;
- canonical scalar and datetime values;
- unique audit IDs;
- metric-to-attempt joins;
- one or zero completed attempts per study;
- required completed-attempt values;
- completed-attempt author and creator consistency;
- finite numeric metrics;
- readability selected-marker consistency.

Validation errors must not expose usernames, study numbers, source payloads, or
free text.

## Analytical identities

- `records.csv.ID` is the audit attempt ID.
- Metric-file `record_id` values join to the audit attempt ID.
- Derived audit files rename the attempt identifier to `audit_record_id`.
- `STUDY_NUM` groups attempts for one study.
- `AUTHOR_USER_NAME` is the attempt-author identity and is used exactly as
  stored.
- `CREATED_BY_ID` is the created study's creator ID, not the author identity for
  preceding attempts.
- A study can have no more than one `COMPLETE` attempt.
- Attempts within a study are ordered by `START_TIME`, followed by audit ID as
  the deterministic tie-breaker.

`PRIOR_CREATED_COUNT` is interpreted as the number of studies created by the
attempt author before `START_TIME`. It is available for complete and incomplete
attempts and is analyzed as
`prior_studies_created_before_attempt_start_count`.

Query-time experience values are kept distinct from attempt-start experience.
They include total studies created, other-study memberships, distinct login
days, and login-history span as of the report query.

## Current output

A successful `analyze` run publishes 13 CSV files and one JSON manifest:

~~~~text
exploration/
├── analysis_manifest.json
├── analysis-audit-records/
│   ├── study_attempt_author_history.csv
│   ├── study_attempt_history.csv
│   └── author_history.csv
├── overview/
│   ├── overview_summary.csv
│   ├── study_attempt_history_summary.csv
│   └── author_handoff_summary.csv
├── attempts/
│   ├── grouped_attempt_summary.csv
│   ├── content_source_concordance_summary.csv
│   └── content_source_concordance_matrix.csv
├── studies/
│   └── grouped_study_summary.csv
└── authors/
    ├── grouped_author_summary.csv
    ├── attempt_start_experience_summary.csv
    └── current_author_experience_summary.csv
~~~~

### Analysis audit records

These identifier-bearing files expose the derived rows used by the aggregate
analysis:

- `study_attempt_author_history.csv` has one row per attempt with study,
  authorship, role, appointment, and available experience context.
- `study_attempt_history.csv` has one row per study with its attempt pathway,
  completion state, timing, and author-handoff indicators.
- `author_history.csv` has one row per exact `AUTHOR_USER_NAME` with observed
  adoption, activity, role, and query-time experience measures.

These files contain identifiers needed for internal traceability. Handle them
as sensitive analysis data and do not publish them as faculty-facing summaries.

### Overview outputs

- `overview_summary.csv` contains top-level attempt, study, author, PI, and
  completion-pathway counts with explicit denominators.
- `study_attempt_history_summary.csv` summarizes repeated attempts and time to
  completion.
- `author_handoff_summary.csv` distinguishes same-author retries from handoffs
  to other authors.

### Attempt outputs

- `grouped_attempt_summary.csv` summarizes attempt counts and timing by
  completion group, exact result, authoring mode, source type, and content
  source.
- `content_source_concordance_summary.csv` summarizes agreement between reported
  and inferred content-source values.
- `content_source_concordance_matrix.csv` contains reported-versus-inferred
  content-source counts and percentages.

### Study output

`grouped_study_summary.csv` summarizes distinct-study populations, completion
history, timing, participant type, department, appointments, source type, and
content source.

Appointment group counts are non-mutually-exclusive. A study or author may be
represented in more than one appointment group.

### Author outputs

- `grouped_author_summary.csv` reports distinct-author counts by completion,
  authoring mode, effective role, and appointment group.
- `attempt_start_experience_summary.csv` reports distributions of prior studies
  created before each attempt's `START_TIME`, grouped by author adoption,
  completion, and authoring mode.
- `current_author_experience_summary.csv` reports author-grain distributions for
  experience and activity values measured as of the report query.

Aggregate author files do not contain usernames or audit IDs. Identifier-bearing
author details remain in `analysis-audit-records/author_history.csv`.

### Manifest

`analysis_manifest.json` records:

- the analysis program version;
- generation time;
- source report path and filenames;
- source row counts;
- published analysis row counts;
- output file count;
- configured edit-intensity scheme;
- readability tolerance;
- warning count.

The manifest contains no source payload text.

## Missing values and stable output

CSV files use:

- UTF-8 encoding;
- LF line endings;
- stable declared column order;
- `\N` for missing values.

Published aggregate percentages use explicit denominators. Empty denominators
produce missing percentages rather than misleading zero percentages.

## Privacy and interpretation

The aggregate outputs are intended for exploratory analysis. Counts,
percentages, timing distributions, experience measures, and readability
indicators must not be interpreted as causal findings or evaluations of an
individual author.

Do not place real audit records, source payload text, credentials, connection
values, or operational SQL in tests, documentation, commits, or issue reports.
Use synthetic data for development.

## Boundary

This program owns exploratory derivation, aggregation, validation, and
publication.

It does not recreate:

- source extraction;
- study-field analysis;
- post-edit metric calculation;
- readability metric calculation;
- database or Oracle connectivity.

The normalized report remains the source contract.

## Development

Run focused checks from the repository root:

~~~~bash
make format
make lint
make typecheck
make test PACKAGE=study-posting-audit-exploration
make coverage PACKAGE=study-posting-audit-exploration
git diff --check
~~~~

Before committing a completed increment, run the full repository gates:

~~~~bash
make docs-check
make check
make hooks-run
~~~~

## License

MIT
