---
applyTo: "**/*.py"
---

# Shared Python instructions

These conventions apply across the `michr-scripts` uv workspace. Package-specific
and program-specific instruction files may impose additional constraints.

## Determine ownership first

Before editing a Python file, identify its workspace member:

- `packages/<name>/` contains an importable library;
- `programs/<name>/` contains an independently runnable application;
- `scripts/` contains repository-maintenance utilities.

Read that member's `pyproject.toml`, README, and scoped instruction file before
making changes.

Do not assume every workspace member has the same purity or dependency rules.

## Shared conventions

- Python 3.14.
- Full type annotations.
- Root `mypy --strict` configuration must pass.
- Ruff owns formatting, import ordering, and linting.
- Line length is 88.
- NumPy-style docstrings for public modules, classes, and functions.
- Use PEP 695 `type` statements for type aliases.
- Prefer frozen, slotted dataclasses for immutable value objects.
- Prefer `StrEnum` for closed string vocabularies.
- Use keyword-only parameters for flags and optional behavior.
- Prefer descriptive names over abbreviations.
- Use `pathlib.Path` rather than `os.path` when filesystem work is appropriate.
- Raise precise exceptions with actionable messages.
- Do not add broad lint or type suppressions.

## Dependency boundaries

Dependencies point from specific members toward reusable members:

```text
reusable package
       ↑
specific package
       ↑
runnable program
```

Rules:

1. A package must never import a program.
2. A more reusable package must not import a more specific package.
3. Do not duplicate behavior already owned by another workspace member.
4. Add a dependency only to the member that needs it.
5. Explain why the standard library and existing dependencies are insufficient.

Use:

```bash
uv add --package <distribution-name> <dependency>
```

Never edit `uv.lock` manually.

## I/O and logging depend on the member

Do not apply one universal purity rule.

- Pure analysis packages may prohibit database, filesystem, pandas, logging, and
  CLI behavior. Follow their scoped instructions.
- Row-source packages may perform database, CSV, and filesystem I/O as part of
  their explicit contract.
- Programs may use configuration, logging, databases, CSV, pandas, and CLI
  entry points when required by their responsibilities.

Do not add I/O to a pure package merely because one consumer needs it. Put the
behavior in the correct package or program.

## Validation at trust boundaries

Values from JSON, CSV, databases, environment variables, and command-line
arguments have no static type guarantee.

Validate them before use. If static analysis reports that an inline
`isinstance()` check is redundant because a parameter is already annotated,
move runtime validation into a helper accepting `object`; do not replace the
check with unsafe truthiness logic.

Container validation should:

1. narrow the outer container;
2. validate each element;
3. construct a correctly typed result.

Do not return `list[Unknown]` or `dict[Unknown, Unknown]` as a typed container.

## Exceptions

Use exception types appropriate to the owning member:

- reusable package input errors generally derive from `TypeError` or
  `ValueError`;
- programs may define configuration, source, or record-processing exceptions;
- never silently swallow an exception;
- never catch bare `Exception` unless the application boundary deliberately
  records unexpected failures and then re-raises or exits.

Pure libraries raise and do not log. Programs may log, but must avoid sensitive
payloads.

## SQL and database code

These rules apply only in members whose explicit contract includes database
access:

- parameterized SQL values only;
- never interpolate credentials or user input into SQL;
- validate identifiers before interpolating table or column names;
- stream rows rather than calling `fetchall()` for unbounded queries;
- close cursors and connections deterministically;
- do not log credentials, connection strings containing secrets, or row
  payloads;
- database drivers belong only to the package or program that owns database
  access.

## Filesystem and CSV code

These rules apply only where file I/O belongs:

- accept `Path` or `str | Path` at public boundaries;
- open text files with an explicit encoding;
- use `newline=""` with the standard-library CSV module;
- stream rows rather than reading an unbounded file into memory;
- avoid writing generated output into source directories;
- use temporary paths in tests.

## Security and privacy

- Never hard-code credentials, tokens, DSNs, or institutional hostnames.
- Never commit real audit exports or production payloads.
- Never place real study text in tests, examples, snapshots, or logs.
- Use synthetic fixtures.
- Do not log selected or final free text unless explicitly required and handled
  under an approved data policy.

## Change discipline

Before completing a change:

1. run the narrow tests for the owning member;
2. run `make lint`;
3. run `make typecheck`;
4. run `make check`;
5. inspect `git diff`;
6. update documentation if the public contract or behavior changed.

Do not describe a behavior-changing analytical modification as a refactor.
