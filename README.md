# study-posting-ai-analysis

Measures how much **AI-generated text assistance survived into final
human-authored content** in the University of Michigan eResearch study-posting
form.

The form offers LLM-generated suggestions for fields such as title, purpose,
description, compensation text, and contact details. Every authoring attempt is
written to an audit table. This project reads those audit rows and produces
per-field metrics describing how much technical post-editing the user performed.

> **Interpretation note.** These metrics quantify *technical post-editing
> effort*. They do not measure time saved, keystrokes avoided, cognitive effort,
> or user satisfaction. See [Interpretation limits](docs/analysis-specification.md#16-interpretation-limits).
>

---

## Prerequisites

Two tools must exist before `make` can bootstrap anything else.

| Tool | Check | Install |
|---|---|---|
| **uv** | `uv --version` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **make** | `make --version` | macOS: `xcode-select --install` · Debian/Ubuntu: `sudo apt install build-essential` |

Python itself is **not** a prerequisite. `uv` reads `.python-version` and
downloads the required interpreter automatically.

---

## Quick start

```bash
git clone <repository-url>
cd study-posting-ai-analysis
make setup
```

`make setup` is idempotent — run it again any time something looks wrong.

Verify the workspace:

```bash
make doctor    # interpreter, tooling, and library versions
make check     # format, lint, types, security audit, tests, coverage
```

List every available command:

```bash
make
```

---

## Common commands

| Command | Purpose |
|---|---|
| `make setup` | Bootstrap a fresh clone: dependencies, git hooks, `.env` |
| `make check` | Full quality gate. **Run before every commit.** |
| `make test` | Run the test suite from a clean state |
| `make test-fast` | Skip slow randomized differential tests |
| `make coverage` | Tests plus coverage reports in `reports/` |
| `make coverage-open` | Coverage, then open the HTML report |
| `make format` | Format code and organize imports |
| `make lint` / `make typecheck` | Ruff lint · mypy strict |
| `make audit` | Dependency and source security scan |
| `make clean` | Remove generated output, reports, and caches |
| `make doctor` | Print environment summary |

Run a subset of tests:

```bash
make test PYTEST_ARGS="-k compensation -vv"
```

All application arguments are **named**, never positional:

```bash
make load-csv CSV_PATH=data/sample/audit_records_sample.csv
make run LIMIT=100 LOG_LEVEL=DEBUG
```

---

## Running the analysis

### Local development, from a CSV export

```bash
# 1. Load a CSV export into a local SQLite database
make load-csv CSV_PATH=data/my_export.csv

# 2. Analyze eligible records and write CSV output
make run
```

Output lands in `output/`. Only rows with `ATTEMPT_TYPE = 'AI'` and
`ATTEMPT_RESULT = 'COMPLETE'` are analyzed.

### Against Oracle

```bash
make install-oracle          # install the optional driver
cp .env.example .env         # then fill in DSN, user, password
make run-oracle LIMIT=10
```

The driver runs in **thin mode**, so no Oracle Instant Client installation is
required. Credentials are read from `.env`, which is git-ignored.

---

## Architecture

Four layers. Dependencies point inward only.

```
Presentation    cli.py, reporting.py      CSV, summaries, terminal output
Application     pipeline.py               orchestration, per-record errors
Domain          models, metrics,          pure analysis, no I/O
                field_analysis
Adapter         adapters/sqlite, oracle   database access
```

```
src/study_posting_ai_analysis/
├── models.py             Enums and frozen result dataclasses
├── text_normalization.py Unicode normalization, cosmetic equivalence
├── metrics.py            TER, character, and soft-word calculations
├── field_specs.py        Field configuration and requiredness rules
├── field_analysis.py     Match classification and per-field analyzers
├── errors.py             AnalysisError hierarchy
├── repository.py         AuditRecordRepository Protocol
├── adapters/             SQLite and Oracle implementations
├── pipeline.py           Record iteration and error capture
├── reporting.py          Flattening, DataFrame, CSV export
├── config.py             Settings from environment variables
└── cli.py                argparse entry point
```

Three rules hold the design together:

1. **The domain layer performs no I/O.** No `sqlite3`, `oracledb`, `pandas`, or
   filesystem access.
2. **`pandas` appears only in `reporting.py`.**
3. **`pipeline.py` depends on a Protocol**, never on a concrete adapter — which
   is what allows Oracle to be added without touching analysis code.

See [`docs/program-flow.md`](docs/program-flow.md) for the detailed flow diagram.

---

## What the analysis produces

One row per form field per audit record, containing:

| Group | Columns |
|---|---|
| Classification | `match_type`: `EXACT`, `COSMETIC_EQUIVALENT`, `EDITED`, `REMOVED`, `UNASSISTED` |
| Primary metric | `ter_rate`, `ter_effort_saved_raw`, `ter_effort_saved` |
| Robustness | `character_effort_saved`, `soft_word_effort_saved` |
| Absolute proxy | `estimated_characters_saved` |
| Policy score | `policy_adjusted_effort_saved` |
| Lookup fields | `lookup_similarity` (Jaccard), plus kept/dropped/added ID sets |
| Compensation | `flag_suggested`, `flag_saved`, `flag_accepted`, `flag_changed` |

The primary reported measure is **`ter_effort_saved`** — `1 - TER`, bounded to
`[0, 1]`. Raw unbounded values are always retained alongside it.

Free text is excluded from exports by default. Pass `--include-text` only when
handling the output appropriately.

---

## Documentation

| Document | Contents |
|---|---|
| [`docs/analysis-specification.md`](docs/analysis-specification.md) | **The specification of record.** Metric definitions, formulas, requiredness rules, outcome vocabulary, reporting terminology, interpretation limits, references. |
| [`docs/program-flow.md`](docs/program-flow.md) | Control-flow and architecture diagrams. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Development workflow, conventions, AI-agent guidance. |
| [`.github/copilot-instructions.md`](.github/copilot-instructions.md) | Context automatically supplied to Copilot Chat. |

If code and the specification disagree, **the specification wins** — or the
specification must be updated in the same change.

---

## Handling data responsibly

- **Never commit real audit exports.** `data/` is git-ignored except
  `data/sample/`, which holds synthetic rows only.
- **Never commit credentials.** `.env`, Oracle wallets, and `tnsnames.ora` are
  ignored, and a pre-commit hook blocks them.
- **Do not use real study text** in tests, fixtures, examples, or docstrings.
- Field text is not logged above `DEBUG`.

---

## Reproducibility

Pinned in `.python-version` and `uv.lock`:

| Component | Version |
|---|---|
| Python | 3.14 |
| SacreBLEU | 2.6.x — TER implementation |
| RapidFuzz | 3.14.x — character-level Levenshtein |
| pandas | 2.2.x — reporting layer only |

Major versions are bounded deliberately: a major release of a metric library
could change reported scores. Upgrades are a reviewed, separately committed act
(`make upgrade`).

`uv.lock` is committed so every clone and CI run resolves identical versions.

---

## License

MIT
