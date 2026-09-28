# michr-scripts

`michr-scripts` is a polyglot monorepo for reusable libraries, runnable
applications, and operational scripts maintained by the Michigan Institute for
Clinical & Health Research (MICHR).

Python projects share one
[uv workspace](https://docs.astral.sh/uv/), lockfile, virtual environment,
development workflow, and continuous-integration configuration.

## Repository layout

```text
michr-scripts/
├── python/
│   ├── packages/    Reusable Python libraries
│   └── programs/    Runnable Python applications
├── shell/           Shell scripts and projects
├── lua/             Lua scripts and projects
├── tools/           Repository-maintenance utilities
├── Makefile         Shared development and workflow commands
├── pyproject.toml   Workspace and tool configuration
└── uv.lock          Locked Python dependencies
```

Behavior-specific documentation belongs with the package, program, or script
that owns it. This README covers only repository-wide setup, navigation, and
common commands.

## Setup

Prerequisites:

- [`uv`](https://docs.astral.sh/uv/)
- `make`

Bootstrap a clone:

```bash
git clone https://github.com/umich-michr/michr-scripts
cd michr-scripts
make setup
```

`make setup` installs all Python workspace members and Git hooks. Python does
not need to be installed separately; `uv` uses the version in
`.python-version`.

Useful checks:

```bash
make members
make doctor
make check
```

Do not manually activate `.venv`, use `pip`, or edit `uv.lock`.

## Quick start: Study Posting Audit

The root Makefile can generate a normalized audit report and its descriptive
exploration in one workflow.

### Database source

```bash
make audit-explore-database
```

Disable automatic browser opening:

```bash
make audit-explore-database OPEN_REPORT=0
```

Database settings resolve through the audit-report program's command-line,
process-environment, dotenv, default, and prompt precedence. Passwords are not
accepted as Make variables or command-line arguments.

### CSV source

```bash
make audit-explore-csv \
  AUDIT_CSV_INPUT=/absolute/path/to/source-audit.csv
```

`AUDIT_CSV_INPUT` is the source audit export, not an already normalized
`records.csv`. If omitted, the audit-report program continues resolution
through environment, dotenv, then an interactive prompt.

Choose explicit destinations when needed:

```bash
make audit-explore-csv \
  AUDIT_CSV_INPUT=/absolute/path/to/source-audit.csv \
  AUDIT_REPORT_OUTPUT=/absolute/path/to/normalized-report \
  AUDIT_EXPLORATION_OUTPUT=/absolute/path/to/exploration \
  OPEN_REPORT=0
```

Defaults:

| Variable | Default |
|---|---|
| `AUDIT_REPORT_OUTPUT` | `output/study-posting-ai-audit-analysis/report` |
| `AUDIT_EXPLORATION_OUTPUT` | `output/study-posting-ai-audit-analysis/exploration` |
| `AUDIT_CSV_INPUT` | Unset; resolved by the program |
| `OPEN_REPORT` | `1` |
| `FAIL_ON_QUALITY_WARNING` | `0` |

Set `FAIL_ON_QUALITY_WARNING=1` when warnings should produce a nonzero workflow
result.

If a normalized report already exists, run exploration directly:

```bash
uv run study-posting-audit-exploration analyze \
  --input-report /absolute/path/to/normalized-report \
  --output /absolute/path/to/exploration
```

See the program documentation for data contracts, business rules, privacy
boundaries, and all options.

## Python workspace

### Programs

| Program | Purpose |
|---|---|
| [`study-posting-audit-report`](python/programs/study-posting-audit-report/) | Normalize Study Posting Authoring audit rows from CSV or Oracle |
| [`study-posting-audit-exploration`](python/programs/study-posting-audit-exploration/) | Validate a normalized report and publish aggregate analysis and HTML |

See the [program catalog](python/programs/README.md) for direct commands and
input/output summaries.

### Packages

| Package | Purpose |
|---|---|
| [`program-configuration`](python/packages/program-configuration/) | Layered, typed, secret-aware configuration |
| [`tabular-row-sources`](python/packages/tabular-row-sources/) | Schema-aware lazy CSV and database row sources |
| [`text-post-edit-metrics`](python/packages/text-post-edit-metrics/) | Directional technical text post-edit metrics |
| [`text-readability-metrics`](python/packages/text-readability-metrics/) | English readability metrics and counts |
| [`study-posting-ai-analysis`](python/packages/study-posting-ai-analysis/) | Study-posting suggestion, selection, and final-value analysis |

Each package README documents its public API and links to detailed methodology
or schema documentation.

## Development commands

Run `make` or `make help` for the complete target list.

| Command | Purpose |
|---|---|
| `make setup` | Bootstrap the workspace |
| `make members` | List Python workspace members |
| `make format` | Format Python code |
| `make format-check` | Verify formatting |
| `make lint` | Run Ruff |
| `make typecheck` | Run strict mypy |
| `make test` | Run all member tests |
| `make coverage` | Run all coverage gates |
| `make docs-check` | Verify documentation synchronization |
| `make audit` | Audit dependencies and source |
| `make check` | Run the complete local and CI gate |
| `make hooks-run` | Run all pre-commit hooks |

Target one member:

```bash
make test PACKAGE=study-posting-ai-analysis
make coverage PACKAGE=study-posting-audit-exploration
```

Pass pytest options with:

```bash
make test \
  PACKAGE=study-posting-audit-report \
  PYTEST_ARGS="-k database -vv"
```

Before committing:

```bash
make check
make hooks-run
git diff --check
git status --short
```

## Documentation map

Documentation lives with the behavior it governs.

| Subject | Location |
|---|---|
| Repository setup and shared workflow | This README |
| Program catalog | [`python/programs/README.md`](python/programs/README.md) |
| Program CLI and configuration | Each program README and `docs/` directory |
| Package API | Each package README |
| AI-assisted Study Posting feature and audit capture | [`feature-and-audit-model.md`](python/programs/study-posting-audit-report/docs/feature-and-audit-model.md) |
| Normalized audit-report contract | [`normalized-report.md`](python/programs/study-posting-audit-report/docs/normalized-report.md) |
| Exploration data lineage | [`data-lineage.md`](python/programs/study-posting-audit-exploration/docs/data-lineage.md) |
| Faculty and LLM inquiry navigation | [`inquiry-guide.md`](python/programs/study-posting-audit-exploration/docs/inquiry-guide.md) |
| Study-field analysis policy | [`analysis-specification.md`](python/packages/study-posting-ai-analysis/docs/analysis-specification.md) |
| Generic post-edit formulas | [`methodology.md`](python/packages/text-post-edit-metrics/docs/methodology.md) |
| Tabular schema format | [`schema-format.md`](python/packages/tabular-row-sources/docs/schema-format.md) |

Do not duplicate detailed program or analytical rules in the repository README.
Link to the owning document instead.

## Security and data handling

- Never commit credentials, production connection details, source exports, or
  institutional data.
- Use synthetic values in tests, examples, and documentation.
- Keep generated reports out of version control.
- Avoid logging payloads, free text, credentials, or secret-bearing connection
  strings.
- Run operational programs only in approved environments under applicable U-M
  controls.
- Repository checks are guardrails and do not replace institutional policy.

## License

MIT
