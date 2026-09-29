# michr-scripts workspace instructions

## Repository purpose

`michr-scripts` is a polyglot monorepo for reusable libraries, runnable
applications, and operational scripts.

```text
python/packages/    Reusable Python libraries
python/programs/    Runnable Python applications
shell/              Shell scripts and projects
lua/                Lua scripts and projects
tools/              Repository-maintenance utilities
```

`uv` manages Python workspace members. Use the root `Makefile` as the shared
developer interface.

## Ownership and dependency direction

Before editing:

1. identify the owning package, program, language project, or repository tool;
2. read its README, detailed docs, `pyproject.toml`, and scoped instructions;
3. inspect focused tests;
4. preserve dependency direction.

```text
reusable package
       ↑
specific package
       ↑
runnable program
```

Rules:

- programs may depend on packages;
- packages must not depend on programs;
- more reusable packages must not import more specific packages;
- shared behavior belongs in an owning package rather than being duplicated;
- cross-language integration uses documented executable and data contracts;
- `tools/` is not a home for user-facing or operational programs.

## Documentation navigation

Use one authoritative home per subject.

| Subject | Document |
|---|---|
| Repository setup and shared gates | Root `README.md` |
| Python workspace, commands, packages, and programs | `python/README.md` |
| Program-only catalog | `python/programs/README.md` |
| Feature and audit model | `study-posting-audit-report/docs/feature-and-audit-model.md` |
| Audit-report CLI/defaults | `study-posting-audit-report/docs/running.md` |
| Normalized report contract | `study-posting-audit-report/docs/normalized-report.md` |
| Exploration CLI | `study-posting-audit-exploration/docs/running.md` |
| Exploration analytical rules | `study-posting-audit-exploration/docs/analysis-rules.md` |
| Exploration output inventory | `study-posting-audit-exploration/docs/output-reference.md` |
| Data lineage | `study-posting-audit-exploration/docs/data-lineage.md` |
| Faculty/LLM navigation | `study-posting-audit-exploration/docs/inquiry-guide.md` |
| Study-field policy | `study-posting-ai-analysis/docs/analysis-specification.md` |
| Generic edit formulas | `text-post-edit-metrics/docs/methodology.md` |
| Tabular schema | `tabular-row-sources/docs/schema-format.md` |

Update the owning document when behavior, formulas, classifications, schemas,
public APIs, CLI contracts, configuration defaults, business rules,
eligibility or denominator rules, missing-value policy, user-visible behavior,
or output inventories change. Link rather than duplicating details.

Review documentation by the contract being changed, not merely by the source
file path:

1. identify the public, business, analytical, data, or command contract affected;
2. use the table above, the owning member README, its linked detailed docs,
   scoped instructions, and focused tests to locate the authoritative document;
3. update only the authoritative documents whose facts or guidance changed;
4. leave unrelated documentation untouched;
5. document stable domain knowledge, goals, rules, formulas, data contracts,
   interpretation limits, and supported entry points rather than narrating
   implementation details that readers can obtain from source code;
6. keep implementation detail only when it is necessary to explain a durable
   business rule, calculation, data boundary, or user-visible contract.

Do not make documentation changes solely because a nearby implementation file
changed, and do not reintroduce a hard-coded source-to-document pairing
registry without explicit authorization.

## Shared workflow

Use `make`. Do not use `pip`, manually activate `.venv`, or edit `uv.lock`.

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
make test PACKAGE=<member-name>
make coverage PACKAGE=<member-name>
```

`make check` is the required local and CI gate.

## Security and data handling

- Never commit credentials, production connection strings, operational SQL,
  source exports, generated reports, or institutional data.
- Use synthetic data in tests, examples, and documentation.
- Avoid logging sensitive payloads or free text.
- Keep database and filesystem access in members whose contracts require it.
- Pass SQL bind values separately from SQL text.

## Faculty and LLM answers

When answering a report question:

1. identify the analytical unit and eligible population;
2. state numerator, denominator, and missing-value treatment;
3. trace source column through normalized, derived, aggregate, and HTML layers;
4. cite the owning documentation, implementation, and focused tests;
5. distinguish descriptive output from causal or scientific claims;
6. use synthetic examples;
7. state uncertainty rather than guessing.

Start with the exploration inquiry guide and data-lineage document. Generated
`definitions/metric_definitions.csv` and `analysis_manifest.json` are the
run-specific references.

## Completion checklist

After editing:

1. run focused tests;
2. run `make lint` and `make typecheck`;
3. run `make check`;
4. inspect the complete Git diff;
5. update owning documentation when required.
