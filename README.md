# michr-scripts

A Python monorepo containing reusable MICHR libraries and independently runnable
programs.

The repository is managed as a [uv workspace](https://docs.astral.sh/uv/).
Every member has its own package metadata, source code, tests, documentation,
and dependency declaration, while the workspace shares:

- one Git repository;
- one `uv.lock`;
- one `.venv`;
- one Python version;
- one Make-based development workflow;
- shared linting, type checking, security, editor, and CI configuration.

---

## Repository organization

```text
michr-scripts/
├── python/packages/    Reusable importable Python libraries
├── python/programs/    Independently runnable Python applications
├── scripts/     Repository-maintenance utilities
├── pyproject.toml
├── uv.lock
└── Makefile
```

### Packages

A package exposes reusable Python behavior through imports. It does not declare
a command-line entry point unless it is intentionally both a library and an
application.

Current packages:

| Member | Import name | Purpose |
|---|---|---|
| [`text-post-edit-metrics`](python/packages/text-post-edit-metrics/) | `text_post_edit_metrics` | Generic technical post-editing metrics for comparing generated text with final human-edited text |
| [`study-posting-ai-analysis`](python/packages/study-posting-ai-analysis/) | `study_posting_ai_analysis` | Study-posting field policy, selection analysis, requiredness, contact, compensation, lookup analysis, parsing, and flattening |

### Programs

A program is independently runnable and may compose one or more packages. It
owns its CLI, configuration, logging, orchestration, and external I/O.

No programs have been added yet.

Planned programs and reusable components include:

- a reusable row-stream package with interchangeable database and CSV sources;
- a study-posting audit-report program that combines row streaming with
  `study-posting-ai-analysis`;
- additional reporting or administrative programs as needs evolve.

Planned members are not part of the current public API until implemented and
tested.

---

## Dependency direction

Dependencies point from specific behavior toward reusable behavior:

```text
text-post-edit-metrics
          ↑
study-posting-ai-analysis
          ↑
future study-posting-audit-report program
```

Rules:

1. A reusable package must not import a more specific package.
2. A package must never import a program.
3. Programs may compose packages.
4. Shared behavior belongs in a package only when it has a coherent reusable
   contract.
5. Application concerns must not be added to a pure library merely because one
   consumer needs them.

The current dependency graph is:

```bash
uv tree --package study-posting-ai-analysis
```

Expected shape:

```text
study-posting-ai-analysis
└── text-post-edit-metrics
    ├── rapidfuzz
    └── sacrebleu
```

---

## Current package contracts

### `text-post-edit-metrics`

Two texts in, one immutable technical post-editing result out:

```python
from text_post_edit_metrics import analyze_post_edit

result = analyze_post_edit(
    suggestion="Generated text",
    final="Human-edited text",
)

result.ter_effort_saved
result.character_edit_distance
result.soft_word_edit_distance
```

It owns:

- TER;
- character-level Levenshtein metrics;
- weighted soft-word metrics;
- metric text normalization;
- descriptive text-length counts;
- `PostEditingResult`.

It performs no database, CSV, filesystem, DataFrame, logging, or CLI work.

See its [README](python/packages/text-post-edit-metrics/README.md).

### `study-posting-ai-analysis`

Three study-posting objects in, one structured result per field out:

```python
from study_posting_ai_analysis import (
    analyze_objects,
    flatten_analysis_results,
    parse_analysis_inputs,
)

suggested, selected, final = parse_analysis_inputs(
    suggested_payload,
    selected_payload,
    final_payload,
)

results = analyze_objects(suggested, selected, final)
rows = flatten_analysis_results(results, record_id="audit-1234")
```

It owns:

- field configuration;
- selection validation;
- exact, cosmetic-equivalent, edited, removed, and unassisted outcomes;
- requiredness;
- contact and compensation policy;
- lookup/Jaccard analysis;
- JSON parsing;
- flattened study-analysis rows.

It delegates technical text metrics to `text-post-edit-metrics`.

It performs no database, CSV, filesystem, DataFrame, logging, or CLI work.

See its:

- [README](python/packages/study-posting-ai-analysis/README.md);
- [analysis specification](python/packages/study-posting-ai-analysis/docs/analysis-specification.md);
- [program flow](python/packages/study-posting-ai-analysis/docs/program-flow.md).

---

## Prerequisites

Two tools are required before the workspace can bootstrap itself:

| Tool | Check | Installation |
|---|---|---|
| `uv` | `uv --version` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `make` | `make --version` | macOS: `xcode-select --install`; Debian/Ubuntu: `sudo apt install build-essential` |

Python does not need to be installed separately. `uv` reads `.python-version`
and installs the required interpreter.

---

## Initial setup

```bash
git clone <repository-url>
cd michr-scripts
make setup
```

`make setup` is idempotent. It:

1. installs all workspace members into `.venv`;
2. installs pre-commit hooks;
3. prints an environment and workspace summary.

Verify the workspace:

```bash
make doctor
make members
make check
```

---

## Common commands

### Whole workspace

| Command | Purpose |
|---|---|
| `make setup` | Bootstrap a fresh clone |
| `make install` | Synchronize all workspace members |
| `make members` | List packages and programs |
| `make doctor` | Print interpreter, tool, and workspace information |
| `make format` | Format all workspace Python code |
| `make lint` | Run Ruff across the workspace |
| `make typecheck` | Run strict mypy checks per member |
| `make test` | Run every member's test suite |
| `make coverage` | Run every member's coverage gate |
| `make audit` | Audit dependencies and source code |
| `make check` | Run the complete quality gate |
| `make clean` | Remove reports and tool caches |

Run `make` with no arguments to list every available target.

### One workspace member

```bash
make test PACKAGE=text-post-edit-metrics
make coverage PACKAGE=text-post-edit-metrics

make test PACKAGE=study-posting-ai-analysis
make coverage PACKAGE=study-posting-ai-analysis
```

Pass additional pytest arguments:

```bash
make test \
  PACKAGE=study-posting-ai-analysis \
  PYTEST_ARGS="-k compensation -vv"
```

Run only or exclude tests marked `slow`:

```bash
make test-slow PACKAGE=text-post-edit-metrics
make test-fast PACKAGE=text-post-edit-metrics
```

---

## Quality gate

Before committing:

```bash
make check
```

The gate includes:

1. formatting verification;
2. Ruff linting;
3. strict mypy type checking;
4. documentation synchronization checks;
5. dependency vulnerability auditing;
6. Bandit source-code security scanning;
7. each member's pytest suite;
8. each member's coverage threshold.

Pre-commit hooks run a faster subset automatically. If a hook modifies a file,
review the diff, stage the correction, and commit again.

Never use `--no-verify` merely to bypass a failing check.

---

## Adding a reusable package

Create packages under:

```text
python/packages/<distribution-name>/
```

Recommended layout:

```text
python/packages/example-package/
├── pyproject.toml
├── README.md
├── src/
│   └── example_package/
│       ├── __init__.py
│       └── py.typed
└── tests/
    └── test_package.py
```

### Required steps

1. Create the member directory and `pyproject.toml`.
2. Add a `src`-layout import package.
3. Add `py.typed` when publishing inline types.
4. Add a member README describing its contract and exclusions.
5. Add pytest and coverage configuration to the member `pyproject.toml`.
6. Add tests.
7. Add the import name to Ruff's root `known-first-party` list.
8. Add scoped Copilot instructions when the member has important architectural
   or domain rules.
9. Run:

```bash
uv lock
uv sync --all-packages
make check
```

The root workspace declaration currently discovers:

```toml
[tool.uv.workspace]
members = ["python/packages/*", "python/programs/*"]
```

Therefore, adding a valid member under `python/packages/` normally requires no explicit
workspace-list edit.

### Adding an internal dependency

From the workspace root:

```bash
uv add \
  --package consuming-distribution \
  dependency-distribution
```

For a workspace dependency, ensure the consuming member declares:

```toml
[tool.uv.sources]
dependency-distribution = { workspace = true }
```

The dependency direction must remain from specific members toward reusable
members.

---

## Adding a runnable program

Create programs under:

```text
python/programs/<program-name>/
```

Recommended layout:

```text
python/programs/example-program/
├── pyproject.toml
├── README.md
├── src/
│   └── example_program/
│       ├── __init__.py
│       ├── cli.py
│       └── __main__.py
└── tests/
```

Programs may own:

- CLI arguments;
- environment or file configuration;
- logging;
- database access;
- CSV input and output;
- DataFrames;
- record loops;
- retry and failure policy;
- report generation.

Declare a named command in the program's `pyproject.toml`:

```toml
[project.scripts]
example-program = "example_program.cli:main"
```

All CLI arguments should be named rather than positional unless a positional
argument is a well-established and unambiguous command convention.

A program should remain independently runnable:

```bash
uv run example-program --help
```

It should compose packages rather than copy their logic.

---

## Dependency ownership

Add a dependency only to the member that directly imports it.

Examples:

- SacreBLEU and RapidFuzz belong to `text-post-edit-metrics`.
- `study-posting-ai-analysis` depends only on
  `text-post-edit-metrics`.
- A future Oracle row-source package would own `oracledb`.
- A reporting program would own pandas only if its reporting implementation
  requires pandas.

Use:

```bash
uv add --package <member> <dependency>
```

Never edit `uv.lock` manually.

When a dependency can affect analytical results, bound its major version and
document the compatibility rationale.

---

## Documentation ownership

Documentation lives with the code it governs:

| Documentation | Location |
|---|---|
| Workspace structure and common workflow | Root `README.md` |
| Reusable package API | Package `README.md` |
| Program CLI and configuration | Program `README.md` |
| Study methodology and form policy | `python/packages/study-posting-ai-analysis/docs/` |
| Shared agent rules | `.github/copilot-instructions.md` |
| Member-specific agent rules | `.github/instructions/` |

A behavior change is incomplete until its owning documentation is updated.

---

## Security and data handling

- Never commit credentials, API keys, database wallets, or production
  connection strings.
- Never commit real audit exports or institutional data.
- Use synthetic data in tests, examples, and documentation.
- Keep generated reports out of version control.
- Avoid logging sensitive row payloads or free text.
- Database and file access belong only to members whose explicit contract
  requires them.

The root `.gitignore`, pre-commit hooks, dependency audit, and Bandit scan provide
guardrails, but they do not replace review.

---

## CI

GitHub Actions runs the workspace quality gate for pushes and pull requests.

Failures are surfaced through:

- failed required status checks;
- inline annotations where supported;
- test and coverage summaries;
- GitHub workflow notifications.

The required aggregate check is intended to remain stable as new workspace
members are added.

---

## Current status

| Member | Tests | Coverage gate |
|---|---:|---:|
| `text-post-edit-metrics` | Metric, normalization, model, and differential tests | 95% |
| `study-posting-ai-analysis` | Field policy, parsing, flattening, and integration tests | 95% |

Use `make coverage` for current counts and measured coverage.

---

## License

MIT
