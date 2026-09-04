# Contributing

## Before you start

```bash
make setup      # idempotent; safe to re-run any time
make check      # confirm a clean baseline before changing anything
```

Read [`docs/analysis-specification.md`](docs/analysis-specification.md) first.
It is the specification of record. If code and that document disagree, the
document wins — or the document must be updated in the same change.

---

## The change cycle

```bash
git switch -c feat/short-description

# ... edit ...

make format      # Ruff format and import ordering
make test        # fast feedback while iterating
make check       # full gate: format, lint, types, audit, coverage

git add -A
git commit       # pre-commit hooks run automatically
git push -u origin HEAD
```

`make check` is the same gate CI runs. If it passes locally, CI should pass.

---

## Commit messages

Conventional Commits, enforced by a `commit-msg` hook:

```
type(scope): imperative summary under 72 characters
```

Allowed types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`,
`ci`, `chore`, `revert`.

```
feat(metrics): add soft-word robustness score
fix(field-analysis): reject blank required contact email
docs(spec): clarify lookup similarity policy value
test(compensation): cover flag change with removed text
```

A rejected message is explained by the hook. Amend and retry:

```bash
git commit --amend
```

---

## Hooks modify files, then fail the commit

When `ruff-format` reformats a staged file, pre-commit aborts and leaves the
corrected file in your working tree. This is normal:

```bash
git add -A
git commit    # re-run; now passes
```

Bypassing hooks with `--no-verify` is strongly discouraged. CI runs the same
checks and will fail instead.

---

## Architectural rules

Dependencies point inward only.

| Layer | Modules | May import |
|---|---|---|
| Presentation | `cli.py`, `reporting.py` | anything |
| Application | `pipeline.py` | domain, `repository` Protocol |
| Domain | `models`, `text_normalization`, `metrics`, `field_specs`, `field_analysis` | **stdlib, sacrebleu, rapidfuzz only** |
| Adapter | `adapters/*` | domain, database drivers |

Four rules that must not be broken:

1. **The domain layer performs no I/O.** No `sqlite3`, `oracledb`, `pandas`,
   `logging`, or filesystem access.
2. **`pandas` appears only in `reporting.py`.**
3. **`oracledb` is imported lazily**, inside the Oracle adapter, so the package
   works without the optional extra installed.
4. **`pipeline.py` depends on the `AuditRecordRepository` Protocol**, never on a
   concrete adapter.

Domain functions raise; they do not log. Logging belongs to the application and
presentation layers.

---

## Changing a metric

Metric changes alter published results. Treat them as a protocol amendment.

1. Update [`docs/analysis-specification.md`](docs/analysis-specification.md)
   first, stating the old behavior, the new behavior, and the rationale.
2. Change the implementation.
3. Add or amend a test asserting the new behavior explicitly.
4. Note the change in the commit body, not only the summary.

Do **not** change any of the following without an explicit decision recorded in
the specification:

- The `_TER` configuration (`normalized`, `no_punct`, `asian_support`,
  `case_sensitive`).
- Unicode normalization form: **NFC** for metric inputs, **NFKD** for cosmetic
  equivalence classification only.
- Soft-word insertion and deletion costs, or the use of RapidFuzz normalized
  distance as the substitution cost.
- Requiredness rules, or the evaluation order
  *blank → exact → cosmetic → edited*.
- The policy that unpicked lookup sets receive similarity `0.0` as a policy
  value rather than a calculated one.

`normalize_text_for_equivalence` must never preprocess a metric input. It exists
solely for classification; using it upstream of a metric would hide real edits.

---

## Code conventions

Ruff and mypy enforce most of this; `make check` is the arbiter.

- Full type annotations. `mypy --strict` must pass with no new ignores. If an
  ignore is unavoidable, make it code-specific and comment why:
  `# type: ignore[arg-type]  # sacrebleu lacks stubs for this overload`
- NumPy-style docstrings on every public module, class, and function. Module
  docstrings state the layer and its dependency constraints.
- Frozen dataclasses with `slots=True` for result objects. Derived values are
  `@property`, never stored fields.
- `StrEnum` for closed vocabularies.
- Keyword-only (`*`) for flag parameters.
- Descriptive names: `number_of_final_words`, not `n`.
- `pathlib.Path`, never `os.path`.
- Exception messages name the field and, where available, the record ID.
- Parameterized SQL only. A table identifier from configuration must be
  validated against a strict pattern before interpolation, with a comment
  explaining the validation.

---

## Testing

New tests are plain functions with `assert`. `unittest.TestCase` classes ported
from the original notebook may remain; do not rewrite them unasked.

```bash
make test                                  # full suite, clean start
make test-fast                             # skip slow randomized tests
make test PYTEST_ARGS="-k soft_word -vv"   # subset
make coverage-open                         # HTML report in a browser
```

Requirements:

- Constrain error assertions: `pytest.raises(ValueError, match="...")`.
- Compare enum members with `is`, not `==`.
- Mark randomized differential tests `@pytest.mark.slow`.
- Mark tests needing a live database `@pytest.mark.oracle`; they must skip
  automatically when unconfigured.
- Unit tests never open a network or file-based database connection.
- Seed every random generator explicitly: `random.Random(42)`.
- Use `pytest.approx(reference, abs=1e-12)` for float comparisons.
- Use `tmp_path` for any file. Never write into the repository tree.

`pytest-randomly` shuffles test order, so tests must not depend on execution
order or on state left behind by another test. Reproduce a specific ordering
with the seed printed in the pytest header, or disable it with
`-p no:randomly`.

Coverage must not fall below the `fail_under` gate in `pyproject.toml`.
`metrics.py`, `text_normalization.py`, and `field_analysis.py` should approach
full statement and branch coverage, including every validation error path. Each
`MatchType` outcome needs at least one direct test.

---

## Working with the Copilot agent

Project context is supplied automatically from
[`.github/copilot-instructions.md`](.github/copilot-instructions.md) and the
scoped files in `.github/instructions/`. Keep them accurate — a stale
instruction file produces confidently wrong code.

What works well:

- Ask for one function or one test file at a time, then run `make check`.
- Reference the specification section by name in your prompt, for example
  "per section 7.3 of the analysis specification".
- Use the **Coverage Gutters: Watch** command after `make coverage` to see which
  branches agent-written code has not exercised.
- Review generated code against the architectural rules above. Agents readily
  reach for `pandas` or a direct database call inside the domain layer.

What to check every time:

- No new dependency was added silently. Dependencies are a discussed decision
  added with `uv add`.
- No metric formula, normalization step, or threshold changed incidentally.
- No `# type: ignore` or lint suppression was added to make an error disappear.
- No real or realistic study text appears in a test or docstring. Use synthetic
  content such as "Participants receive a $50 gift card."
- No exception is silently swallowed. A per-record failure is recorded by the
  pipeline and processing continues; anything else propagates.

Never let an agent edit `.env`, `uv.lock`, or `data/` contents.

---

## Adding a dependency

```bash
uv add <package>              # runtime
uv add --dev <package>        # development only
uv add --optional oracle <package>
```

Commit both `pyproject.toml` and `uv.lock`. Bound the major version if the
package could affect a reported metric. Explain the need in the pull request.

---

## Updating tooling

Version bumps are a separate, deliberate commit:

```bash
make upgrade         # refresh uv.lock and .venv
make hooks-update    # refresh .pre-commit-config.yaml pins
make doctor          # note the versions now installed
```

Reconcile the two: if Ruff moved from `0.16.6` to `0.17.2`, update the floor in
`pyproject.toml` **and** the `rev:` in `.pre-commit-config.yaml`. If they drift
apart, editor diagnostics and `make lint` will disagree.

```bash
make hooks-clean && make hooks-run && make check
git commit -am "build: update development tooling versions"
```

---

## Handling data responsibly

- Never commit real audit exports. `data/` is git-ignored except
  `data/sample/`, which contains synthetic rows only.
- Never commit credentials. `.env`, Oracle wallets, and `tnsnames.ora` are
  ignored, and a pre-commit hook blocks them by filename.
- Field text is not logged above `DEBUG`, and is excluded from CSV exports
  unless `--include-text` is passed deliberately.

---

## Pull requests

- One logical change per pull request.
- `make check` passes locally.
- Tests accompany any behavior change.
- The specification is updated alongside any metric or rule change.
- The description states what changed, why, and whether any reported metric
  could differ as a result.

The required status check is **CI success**. Failures appear as inline
annotations on the changed lines, with a coverage table and test summary on the
run page.
