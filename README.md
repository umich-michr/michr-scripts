# michr-scripts

A polyglot monorepo for reusable MICHR libraries, independently runnable
programs, and operational scripts.

Python projects are managed as a
[uv workspace](https://docs.astral.sh/uv/). The repository shares one Git
history, Python lockfile, virtual environment, development workflow, and CI
configuration.

---

## Repository layout

```text
michr-scripts/
├── python/
│   ├── packages/    Reusable Python libraries
│   └── programs/    Independently runnable Python applications
├── shell/           Shell scripts and projects, organized by purpose
├── lua/             Lua scripts and projects, organized by purpose
├── tools/           Utilities that maintain this repository
├── Makefile         Repository-wide development interface
├── pyproject.toml   Python workspace and shared tool configuration
└── uv.lock          Locked dependencies for all Python workspace members
```

`uv` manages only members under `python/`. Shell and Lua projects use their own
toolchains as they are introduced. The root `Makefile` is the common developer
interface.

---

## Current Python packages

| Package | Import | Purpose |
|---|---|---|
| [`text-post-edit-metrics`](python/packages/text-post-edit-metrics/) | `text_post_edit_metrics` | Directional technical post-editing metrics for an initial text and its represented edited form |
| [`study-posting-ai-analysis`](python/packages/study-posting-ai-analysis/) | `study_posting_ai_analysis` | Study-posting field policy, requiredness, selection analysis, contact, compensation, lookup analysis, parsing, and flattening |

There are currently no runnable programs.

### Dependency direction

Dependencies point from specific behavior toward reusable behavior:

```text
text-post-edit-metrics
          ↑
study-posting-ai-analysis
          ↑
future study-posting-audit-report
```

Rules:

1. Programs may depend on packages.
2. Packages must not depend on programs.
3. More reusable packages must not depend on more specific packages.
4. Programs should not import another program's internal modules.
5. Logic shared by multiple programs should be extracted into a package.
6. Cross-language integration should use a documented command-line or data
   contract.

Inspect the current Python dependency graph with:

```bash
uv tree --package study-posting-ai-analysis
```

---

## Package contracts

### `text-post-edit-metrics`

Compares an initial text with a value represented by the caller as its edited
form:

```python
from text_post_edit_metrics import analyze_post_edit

result = analyze_post_edit(
    suggestion="Generated text",
    final="Human-edited text",
)

print(result.ter_effort_saved)
print(result.character_edit_distance)
print(result.soft_word_edit_distance)
```

It owns:

- TER and TER-derived scores;
- character-level Levenshtein metrics;
- weighted soft-word metrics;
- metric text normalization;
- descriptive length counts;
- immutable `PostEditingResult` objects.

It does not verify that the second text was actually produced by editing the
first. Its metrics describe textual transformation, not elapsed time, cognitive
effort, observed keystrokes, or user satisfaction.

See its
[package README](python/packages/text-post-edit-metrics/README.md).

### `study-posting-ai-analysis`

Analyzes AI suggestions, user selections, and final saved study-posting values:

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
rows = flatten_analysis_results(
    results,
    record_id="audit-1234",
)
```

It owns:

- study-posting field configuration;
- selection validation and outcome classification;
- requiredness rules;
- cosmetic-equivalence policy;
- contact and compensation analysis;
- lookup/Jaccard analysis;
- JSON object parsing;
- flattened study-analysis rows.

It delegates technical text calculations to `text-post-edit-metrics`.

See its:

- [package README](python/packages/study-posting-ai-analysis/README.md);
- [analysis specification](python/packages/study-posting-ai-analysis/docs/analysis-specification.md);
- [program flow](python/packages/study-posting-ai-analysis/docs/program-flow.md).

---

## Prerequisites

| Tool | Check | Installation |
|---|---|---|
| `uv` | `uv --version` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `make` | `make --version` | macOS: `xcode-select --install`; Debian/Ubuntu: `sudo apt install build-essential` |

Python does not need to be installed separately. `uv` reads `.python-version`
and installs the required interpreter.

---

## Setup

```bash
git clone https://github.com/umich-michr/michr-scripts
cd michr-scripts
make setup
```

`make setup` is idempotent. It installs all Python workspace members, installs
Git hooks, and prints an environment summary.

Verify the workspace:

```bash
make members
make doctor
make check
```

---

## Development commands

### Whole repository

| Command | Purpose |
|---|---|
| `make setup` | Bootstrap a fresh clone |
| `make install` | Synchronize all Python workspace members |
| `make members` | List discovered packages and programs |
| `make doctor` | Show interpreter, tools, and workspace members |
| `make format` | Format Python code and organize imports |
| `make lint` | Run Ruff |
| `make typecheck` | Run strict mypy checks |
| `make test` | Run every Python member's tests |
| `make coverage` | Run every Python member's coverage gate |
| `make audit` | Audit dependencies and Python source |
| `make check` | Run the complete quality gate |
| `make clean` | Remove reports and tool caches |

Run `make` without arguments to list all available targets.

### One Python member

```bash
make test PACKAGE=text-post-edit-metrics
make coverage PACKAGE=text-post-edit-metrics

make test PACKAGE=study-posting-ai-analysis
make coverage PACKAGE=study-posting-ai-analysis
```

Pass additional pytest options:

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

### Quality gate

Before committing:

```bash
make check
```

The gate includes formatting, linting, strict type checking, documentation
synchronization, dependency auditing, source security scanning, tests, and
coverage.

Pre-commit hooks may modify files and stop the commit. When that happens, review
the diff, stage the corrected files, and commit again. Do not use `--no-verify`
merely to bypass a failing check.

---

## Finding and running programs

List discovered Python workspace members:

```bash
make members
```

Python programs live under `python/programs/`. Each program must document:

- its purpose;
- installed command name;
- named CLI arguments;
- configuration;
- input and output formats;
- examples;
- exit behavior.

### Current programs

| Program | Language | Purpose | Command |
|---|---|---|---|
| _No runnable programs yet_ | — | — | — |

### Running a Python program

A Python program declares an executable command:

```toml
[project.scripts]
example-program = "example_program.cli:main"
```

Run it from the repository root:

```bash
uv run --package example-program example-program --help
```

A program uses sibling packages through workspace dependencies:

```toml
[project]
dependencies = [
    "study-posting-ai-analysis>=0.1.0",
]

[tool.uv.sources]
study-posting-ai-analysis = { workspace = true }
```

Commonly used programs may also receive explicit root Make targets after their
commands exist and can be tested.

---

## Where should new code go?

| Need | Location |
|---|---|
| Reusable Python behavior | `python/packages/<distribution-name>/` |
| Runnable Python application | `python/programs/<program-name>/` |
| Small shell script | `shell/<purpose>/<name>.sh` |
| Larger shell project | `shell/<purpose>/<name>/` |
| Small Lua script | `lua/<purpose>/<name>.lua` |
| Larger Lua project | `lua/<purpose>/<name>/` |
| Repository-maintenance utility | `tools/` |

A small shell or Lua script may remain one documented file. Promote it to a
directory when it gains tests, fixtures, configuration, documentation, or
supporting modules.

If reusable shell functions or Lua modules emerge, introduce a language-specific
`lib/` or `packages/` directory at that time. Do not create unused abstractions
in advance.

---

## Adding a Python package

Create:

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

Required steps:

1. Define the package and dependencies in its `pyproject.toml`.
2. Use a `src` layout.
3. Add `py.typed` when shipping inline type information.
4. Document the package's contract and exclusions.
5. Configure pytest and coverage in the member `pyproject.toml`.
6. Add tests.
7. Add the import name to Ruff's root `known-first-party` list.
8. Add scoped Copilot instructions when important domain rules apply.
9. Run:

```bash
uv lock
uv sync --all-packages
make check
```
10. Add the member's `src` directory to
    `.vscode/settings.json` under `python.analysis.extraPaths`.

The root workspace discovers members under:

```toml
[tool.uv.workspace]
members = [
    "python/packages/*",
    "python/programs/*",
]
```

Add an internal dependency with:

```bash
uv add \
  --package consuming-distribution \
  dependency-distribution
```

Ensure the consumer declares the workspace source:

```toml
[tool.uv.sources]
dependency-distribution = { workspace = true }
```

Never edit `uv.lock` manually.

---

## Adding a Python program

Create:

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

- command-line arguments;
- configuration and logging;
- database and filesystem access;
- CSV input and output;
- DataFrames;
- record loops and failure policy;
- report generation.

Programs should compose packages rather than copy their logic.

All nonstandard CLI options should use named arguments unless a positional
argument is an established and unambiguous convention.

---

## Shell and Lua organization

Shell and Lua projects are organized by operational purpose rather than by an
empty package/program distinction.

Possible categories include:

```text
shell/
├── sysadmin/
├── reporting/
└── data-maintenance/

lua/
├── reporting/
├── transformations/
└── integrations/
```

These categories should be created only when real projects require them.

Every runnable script or project should have nearby documentation explaining its
purpose, requirements, arguments, output, and examples.

---

## Dependency ownership

Add a dependency only to the member that directly imports it.

Examples:

- SacreBLEU and RapidFuzz belong to `text-post-edit-metrics`.
- `study-posting-ai-analysis` depends on `text-post-edit-metrics`.
- A future Oracle row-source package would own `oracledb`.
- A reporting program would own pandas only if its implementation requires it.

When a dependency can affect analytical results, bound its major version and
document the compatibility rationale.

---

## Documentation ownership

| Documentation | Location |
|---|---|
| Repository layout and shared workflow | Root `README.md` |
| Python package API | Package `README.md` |
| Python program CLI and configuration | Program `README.md` |
| Shell or Lua usage | Documentation beside the script or project |
| Study methodology and form policy | `python/packages/study-posting-ai-analysis/docs/` |
| Shared agent rules | `.github/copilot-instructions.md` |
| Member-specific agent rules | `.github/instructions/` |

A behavior or public-contract change is incomplete until its owning
documentation is updated.

---

## Security and data handling

- Never commit credentials, API keys, database wallets, or production
  connection strings.
- Never commit real audit exports or institutional data.
- Use synthetic data in tests, examples, and documentation.
- Keep generated reports out of version control.
- Avoid logging sensitive payloads or free text.
- Database and file access belong only to members whose explicit contract
  requires them.

The repository's ignore rules, hooks, audits, and CI checks are guardrails; they
do not replace review or institutional policy.

---

## CI

GitHub Actions runs workspace quality checks for pushes and pull requests.

Failures are surfaced through:

- required status checks;
- inline annotations where supported;
- test and coverage summaries;
- GitHub workflow notifications.

The stable aggregate branch-protection check is `CI success`.

---

## Current status

| Member | Coverage gate |
|---|---:|
| `text-post-edit-metrics` | 95% |
| `study-posting-ai-analysis` | 95% |

Run `make coverage` for current test counts and measured coverage.

---

## License

MIT
