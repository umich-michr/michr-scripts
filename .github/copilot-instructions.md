# michr-scripts workspace instructions

## Repository purpose

`michr-scripts` is a polyglot monorepo for reusable libraries, runnable
applications, and operational scripts.

```text
michr-scripts/
├── python/
│   ├── packages/    Reusable Python libraries
│   └── programs/    Runnable Python applications
├── shell/           Shell scripts and projects
├── lua/             Lua scripts and projects
└── tools/           Repository-maintenance utilities
```

`uv` manages only Python workspace members. The root `Makefile` is the common
developer interface across the repository.

`tools/` is not a location for user-facing or operational programs.

## Current Python packages

### `text-post-edit-metrics`

Generic directional text post-editing metrics:

```python
result = analyze_post_edit(
    suggestion=initial_text,
    final=represented_edited_text,
)
```

Owns TER, character Levenshtein metrics, weighted soft-word metrics, metric
normalization, and `PostEditingResult`.

### `study-posting-ai-analysis`

Study-posting policy analysis:

```python
results = analyze_objects(suggested, selected, final)
```

Owns field configuration, requiredness, suggestion selection, outcome
classification, contact, compensation, lookup analysis, parsing, and flattening.

Depends on `text-post-edit-metrics` for technical text comparisons.

## Dependency direction

```text
text-post-edit-metrics
          ↑
study-posting-ai-analysis
          ↑
runnable reporting programs
```

Rules:

1. Programs may depend on packages.
2. Packages must not depend on programs.
3. Reusable packages must not depend on more specific packages.
4. Do not duplicate behavior owned by another member.
5. Shared program logic belongs in a reusable package.
6. Cross-language integration uses documented executable and data contracts.

## Ownership

Before editing:

1. identify the owning package, program, language project, or repository tool;
2. read its README and `pyproject.toml` when present;
3. read the matching scoped instruction file;
4. inspect existing tests;
5. preserve dependency direction.

Python members own their package metadata, source, tests, README, and coverage
configuration.

Programs own their CLI, configuration, logging, orchestration, and external I/O.

Package-specific analytical rules belong in scoped instructions and package
documentation, not in this file.

## Shared workflow

Use `make`; do not use `pip`, manually activate `.venv`, or edit `uv.lock`.

```bash
make setup
make members
make lint
make typecheck
make test
make coverage
make audit
make check
```

Target one Python member:

```bash
make test PACKAGE=text-post-edit-metrics
make coverage PACKAGE=study-posting-ai-analysis
```

`make check` is the required local and CI gate.

## Adding dependencies

Add a dependency only to the member that imports it:

```bash
uv add --package <distribution-name> <dependency>
```

Before adding one, explain:

- which contract requires it;
- why existing dependencies or the standard library are insufficient;
- which member owns it;
- whether it can change analytical results.

Commit the member `pyproject.toml` and root `uv.lock`.

## Documentation ownership

Documentation lives with the behavior it governs:

- repository organization and shared workflow → root README;
- package API and behavior → package README or package docs;
- program CLI and configuration → program README;
- shell or Lua usage → documentation beside the script or project;
- shared agent guidance → this file;
- package-specific rules → scoped instruction files.

Changes to formulas, normalization, classifications, requiredness, public APIs,
flattened columns, package boundaries, or CLI contracts require documentation in
the same change.

## Security and data handling

- Never commit credentials, wallets, production connection strings, exports, or
  institutional data.
- Use synthetic data in tests, examples, and documentation.
- Avoid logging sensitive payloads or free text.
- Keep generated reports out of version control.
- Database and filesystem access belong only to members whose documented
  contracts require them.

## Agent completion checklist

After editing:

1. run focused tests for the owning member;
2. run `make lint` and `make typecheck`;
3. run `make check`;
4. inspect the complete Git diff;
5. report documentation changes or explain why none were needed.

Do not recommend reloading VS Code as generic troubleshooting. Prefer concrete
file inspection, command output, and tool diagnostics.
