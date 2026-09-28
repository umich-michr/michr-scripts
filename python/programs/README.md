# Python programs

Runnable Python applications live under `python/programs/`. Programs may
compose packages from `python/packages/` and own their command-line interface,
configuration, orchestration, logging, and external I/O.

## Programs

| Program | Purpose | Primary input | Primary output |
|---|---|---|---|
| [`study-posting-audit-report`](study-posting-audit-report/) | Normalize Study Posting Authoring audit rows | Source audit CSV or Oracle query | Four-file normalized report |
| [`study-posting-audit-exploration`](study-posting-audit-exploration/) | Validate and summarize a normalized report | Normalized report directory | 36-file exploration and self-contained HTML |

## Fastest end-to-end workflows

From the repository root:

```bash
make audit-explore-database OPEN_REPORT=0
```

Or from a source audit CSV:

```bash
make audit-explore-csv \
  AUDIT_CSV_INPUT=/absolute/path/to/source-audit.csv \
  OPEN_REPORT=0
```

Default destinations are:

```text
output/study-posting-ai-audit-analysis/report
output/study-posting-ai-audit-analysis/exploration
```

Override them with `AUDIT_REPORT_OUTPUT` and `AUDIT_EXPLORATION_OUTPUT`.

## Run programs directly

Generate a normalized report from CSV:

```bash
uv run study-posting-audit-report csv \
  --input /absolute/path/to/source-audit.csv
```

Generate one from a database:

```bash
uv run study-posting-audit-report database \
  --dsn "database.example:1521/service" \
  --username reporting_user
```

Analyze an existing normalized report:

```bash
uv run study-posting-audit-exploration analyze \
  --input-report /absolute/path/to/normalized-report \
  --output /absolute/path/to/exploration
```

See each program README for required settings, defaults, data contracts,
security guidance, and direct subcommands.

## Program boundaries

Programs may depend on reusable packages. Packages must not depend on programs.
Shared behavior belongs in a package rather than being copied between programs.

`tools/` is reserved for repository-maintenance utilities. User-facing and
operational applications belong here.
