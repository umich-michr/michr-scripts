# MICHR scripts workspace context

## Repository purpose

`michr-scripts` is one Git repository containing reusable Python libraries and
independently runnable Python programs.

The repository uses a **uv workspace**:

```text
michr-scripts/
├── packages/    Importable libraries
└── programs/    Independently runnable applications
```

A library is imported by other members. A program declares a command-line entry
point and composes one or more libraries.

## Current workspace members

### `packages/michr-text-post-editing`

Pure, reusable technical post-editing metrics.

Contract:

```python
result = analyze_post_edit(
    suggestion="generated text",
    final="human-edited text",
)
```

Owns TER, character Levenshtein metrics, weighted soft-word metrics, metric text
normalization, and `PostEditingResult`.

### `packages/study-posting-ai-analysis`

Pure study-posting business analysis.

Contract:

```python
results = analyze_objects(
    suggested_object,
    selected_object,
    final_object,
)
```

Owns form-field policy, selection validation, outcome classification,
requiredness, contact, compensation, lookup analysis, JSON parsing, and
flattening.

Depends on `michr-text-post-editing` for technical text comparisons.

### Future members

Planned reusable components include:

- a row-stream package with interchangeable database and CSV sources;
- a study-posting audit-report program that composes row streaming and study
  analysis.

Do not add those concerns to either existing analysis library.

## Dependency direction

Dependencies point from more specific members toward more reusable members:

```text
michr-text-post-editing
          ↑
study-posting-ai-analysis
          ↑
future study-posting-audit-report
```

Rules:

1. A lower-level package must never import a higher-level package.
2. Programs may compose packages; packages must not import programs.
3. A package must not gain application concerns merely because one consumer
   needs them.
4. Shared behavior belongs in a package only when at least one coherent,
   reusable contract can be stated for it.

## Package and program boundaries

### Packages

Packages belong under `packages/<distribution-name>/`.

Each package owns:

- its `pyproject.toml`;
- its `README.md`;
- its `src/` package;
- its tests;
- package-specific technical documentation;
- its pytest and coverage configuration.

Packages should expose a small public API through `__init__.py`.

### Programs

Programs belong under `programs/<program-name>/`.

Each program owns:

- its `pyproject.toml`;
- its CLI entry point;
- configuration and logging;
- orchestration;
- external I/O;
- program-specific tests and documentation.

Programs may use database drivers, CSV, pandas, logging, and configuration when
their responsibilities require them.

## Shared tooling

The workspace root owns:

- `.python-version`;
- `uv.lock`;
- the shared virtual environment;
- Ruff configuration;
- mypy strict configuration;
- Bandit configuration;
- pre-commit;
- CI;
- VS Code settings;
- the root `Makefile`.

Use `make`; do not invoke `pip` or activate the virtual environment manually.

```bash
make setup
make format
make lint
make typecheck
make test
make coverage
make audit
make check
```

Target one member with:

```bash
make test PACKAGE=michr-text-post-editing
make coverage PACKAGE=study-posting-ai-analysis
```

`make check` is the required local and CI gate.

## Python conventions

- Python 3.14.
- Full type annotations; root `mypy --strict` configuration must pass.
- Ruff owns formatting, imports, and linting.
- NumPy-style docstrings for public modules, classes, and functions.
- PEP 695 `type` statements for aliases.
- Frozen, slotted dataclasses for immutable result objects.
- Keyword-only arguments for optional flags and configuration.
- Descriptive names rather than abbreviations.
- Narrow validation at trust boundaries.
- Do not silence diagnostics merely to make a gate pass.

## Tests

- pytest with plain functions and `assert`.
- Use `pytest.raises(..., match=r"...")` for failure behavior.
- Compare enum members with `is`.
- Use `pytest.approx` for floating-point results.
- Seed randomized tests explicitly.
- Mark expensive randomized tests `@pytest.mark.slow`.
- Tests must be independent of order and state.
- Test data must be synthetic.

Run tests from the owning workspace member. Each member owns its coverage gate.

## Dependencies

Do not add a dependency without explaining:

1. what contract requires it;
2. why the standard library or an existing dependency is insufficient;
3. which workspace member owns it;
4. whether it affects reported analytical results.

Use:

```bash
uv add --package <member> <dependency>
```

Commit both the member `pyproject.toml` and root `uv.lock`.

Never edit `uv.lock` manually.

## Documentation obligations

Documentation belongs with the code it governs:

- package behavior → package README or package docs;
- program behavior → program README or program docs;
- workspace organization → root README;
- shared development workflow → root contributing guidance.

Before completing a change, state which documents were updated or why no
documentation change was necessary.

Changes to formulas, normalization, requiredness, classifications, public API,
flattened columns, CLI arguments, or package boundaries require documentation in
the same change.

## Agent behavior

Before editing:

1. identify the owning workspace member;
2. read its `pyproject.toml` and README;
3. read the scoped instruction file matching that member;
4. inspect existing tests for the behavior;
5. avoid crossing package boundaries without an explicit architectural reason.

After editing:

1. run the narrow member tests;
2. run `make lint`;
3. run `make typecheck`;
4. run `make check`;
5. review the complete Git diff;
6. report documentation changes.

Do not suggest reloading VS Code as generic troubleshooting. Use concrete command
output, file inspection, and tool diagnostics first.

## Never do these things

- Put database, filesystem, CSV, DataFrame, logging, or CLI behavior into a pure
  analysis package.
- Duplicate behavior already owned by another workspace package.
- Import a more specific package from a more reusable package.
- Change analytical formulas or policy while describing the change as a
  refactor.
- Add broad lint or type suppressions.
- Add real institutional data to tests, examples, logs, or documentation.
- Commit credentials, environment files, database wallets, or generated reports.
