# Project context for AI coding agents

## What this project is

A Python library and command-line program that measures how much
**AI-generated text assistance survived into final human-authored content**.

The University of Michigan eResearch study-posting form offers LLM-generated
suggestions for fields such as title, purpose, description, compensation text,
and contact details. Every attempt is written to an audit table. This project
reads those audit rows and produces per-field metrics describing how much
technical post-editing the user performed.

The canonical, authoritative description of the analysis is
**`docs/analysis-specification.md`**. Treat it as the specification of record.
If code and that document disagree, the document wins unless the user explicitly
says otherwise.

## Current scope (iteration 1)

- Read eligible audit rows from a data source, one row at a time.
- Analyze each row and produce one flat metrics row per form field.
- Export the result as CSV.

Data sources: **SQLite** (local development, loaded from a CSV export) and
**Oracle** (production, via `python-oracledb` in thin mode). Oracle batch
processing is deliberately minimal in this iteration and will be expanded next.

The code originated as a Google Colab notebook. Porting it must **not** change
any metric result.

## Architecture

Four layers. Dependencies point inward only.

- Presentation cli.py, reporting.py output <- CSV, summaries, terminal.
- Application pipeline.py <- orchestration, error capture
- Domain models, metrics, field_analysis <- pure, no I/O
- Adapter adapters/sqlite, adapters/oracle <- database access


| Module | Responsibility |
|---|---|
| `models.py` | Enums and frozen dataclasses. No logic beyond derived properties. |
| `text_normalization.py` | Unicode normalization, cosmetic equivalence, `clamp01`, token counting. |
| `metrics.py` | TER, character Levenshtein, weighted soft-word. Pure functions. |
| `field_specs.py` | `FIELD_SPECS`, contact field names, requiredness configuration. |
| `field_analysis.py` | Business rules: match classification and per-field-kind analyzers. |
| `errors.py` | Exception hierarchy rooted at `AnalysisError`. |
| `repository.py` | `AuditRecordRepository` Protocol and JSON column decoding. |
| `adapters/` | Concrete SQLite and Oracle repositories. |
| `pipeline.py` | Iterates records, calls the domain, captures per-record errors. |
| `reporting.py` | Flattening, pandas DataFrame construction, summaries, CSV export. |
| `config.py` | Settings from environment variables. No secrets in code. |
| `cli.py` | argparse entry point. |

### Hard architectural rules

1. **The domain layer imports no I/O.** `models.py`, `text_normalization.py`,
   `metrics.py`, `field_specs.py`, and `field_analysis.py` must never import
   `sqlite3`, `oracledb`, `pandas`, `os`, or anything from `adapters/`.
2. **`pandas` appears only in `reporting.py`.** Nowhere else.
3. **`oracledb` is imported lazily**, inside the Oracle adapter, so the package
   works when the optional extra is not installed.
4. **`pipeline.py` depends on the `AuditRecordRepository` Protocol**, never on a
   concrete adapter.
5. **Domain functions raise; they do not log.** Logging belongs to the
   application and presentation layers.

## Domain rules you must not change without explicit instruction

### Match classification (`MatchType`)

Applied to a text field where a suggestion was selected:

| Outcome | Condition |
|---|---|
| `EXACT` | Selected and final Python strings are equal. |
| `COSMETIC_EQUIVALENT` | Equal after `normalize_text_for_equivalence`. |
| `EDITED` | Nonblank final text with substantive differences remaining. |
| `REMOVED` | A suggestion was selected but the optional final value is blank. |
| `UNASSISTED` | No AI suggestion or lookup value was selected. |

Evaluation order is **blank check, then exact, then cosmetic, then edited**.

### Metrics

| Metric | Formula | Role |
|---|---|---|
| TER-derived | `1 - TER`, TER from SacreBLEU | **Primary**, case-insensitive |
| Character | `1 - levenshtein / final_char_count` | Secondary, case-sensitive |
| Soft-word | `1 - weighted_word_distance / final_word_count` | Robustness, case-sensitive |
| Characters saved | `max(0, final_chars - char_distance)` | Absolute proxy |

Every raw score may be negative and is retained. Bounded reporting scores are
`clamp01(raw)`. Both are stored; never discard the raw value.

Soft-word substitution cost is the RapidFuzz **normalized** character distance
between the two words. Insertion and deletion each cost `1.0` by default.

### Requiredness

Required: `title`, `purpose`, `description`, `contact.email`, `contact.name`.
Optional: `about`, `contact.phone`, `contact.website`.
Compensation text is required exactly when the **saved** `offersCompensation`
value is `True`. The saved Boolean must be `True` or `False`, never absent.

A blank required final value is a validation error, not a metric of zero.

### Lookup fields

`department`, `locations`, `topics` hold sets of integer IDs. Booleans are
rejected because `bool` subclasses `int`. Picked IDs must have been offered.
Similarity is Jaccard between picked and saved. When nothing was picked the
outcome is `UNASSISTED` and similarity is the **policy value `0.0`**, not a
calculated one.

### Preprocessing invariants

- Metric inputs are normalized with Unicode **NFC**.
- `normalize_text_for_equivalence` uses **NFKD** plus casefolding, combining-mark
  removal, and punctuation-to-space. It is used **only** for classification and
  must never preprocess a metric input.
- Whitespace tokenization only. No stemming, lemmatization, embeddings, or
  semantic similarity.

## Interpretation discipline

These metrics measure **technical post-editing effort**. In code comments,
docstrings, log messages, and documentation, never describe them as measuring
time saved, keystrokes avoided, cognitive effort, or user satisfaction.

Use the established vocabulary:

| Statistic | Label |
|---|---|
| Fields with an offer / analyzed text fields | Suggestion offer coverage |
| Fields with a selection / fields with an offer | Suggestion selection rate |
| Mean policy score among fields with an offer | Realized suggestion utility |
| Mean policy score among selected suggestions | Selected-suggestion utility |
| Mean `ter_effort_saved` among nonblank post-edits | TER-derived post-editing score |

Every reported mean must be accompanied by its denominator or sample count.
Never average lookup similarity together with text effort-saved scores.

## Coding conventions

- Python 3.14, `from __future__ import annotations` not needed.
- Full type annotations. `mypy --strict` must pass.
- Ruff formats and lints; line length 88. Do not hand-format around it.
- NumPy-style docstrings on every public function, class, and module.
- Frozen dataclasses with `slots=True` for result objects.
- `StrEnum` for closed vocabularies.
- Named keyword arguments for anything non-obvious; keyword-only (`*`) for flags.
- Descriptive names. Prefer `number_of_final_words` over `n`.
- `pathlib.Path`, never `os.path`.
- Explicit, informative exception messages naming the field and the record.
- Parameterized SQL only. Never build a query with string interpolation of
  user or configuration input except for a validated table identifier.

## Testing conventions

- pytest. New tests are plain functions with `assert`.
- Existing `unittest.TestCase` classes ported from the notebook may remain;
  do not rewrite them without being asked.
- `pytest.raises(..., match="...")` to assert on error messages.
- Mark randomized differential tests `@pytest.mark.slow`.
- Mark tests needing a live database `@pytest.mark.oracle`; they must skip
  automatically when unconfigured.
- Unit tests must never open a network or file-based database connection.
- The full-matrix reference implementation lives in `tests/helpers/` and exists
  solely to verify the memory-optimized soft-word distance.

## Workflow commands

Always use `make`; never invoke `pip`, and never activate the venv manually.

```bash
make install      # uv sync
make format       # Ruff format and import ordering
make lint         # Ruff lint
make typecheck    # mypy strict
make test         # pytest, clean start
make coverage     # pytest with coverage into reports/
make audit        # pip-audit and bandit
make check        # everything above; the gate before any commit
make clean        # remove output, reports, caches
```

Generated files live only in output/ and reports/. Both are removed bymake clean and are git-ignored.

## Things to never do

- Change a metric formula, normalization step, or threshold without anaccompanying update to docs/analysis-specification.md.
- Introduce pandas into the domain layer.
- Import oracledb at module scope outside its adapter.
- Hard-code credentials, DSNs, hostnames, or file paths. Use config.py.
- Commit real audit data. data/ is git-ignored except data/sample/.
- Put actual study text in a test fixture, an example, or a docstring. Inventsynthetic text.
- Log or print selected or final field text at INFO or above.
- Silently swallow an exception. Record it per-record in the pipeline andcontinue, or let it propagate.
- Add a dependency without asking. If one is needed, explain why and add it viauv add.
- Loosen mypy strictness or add a broad # type: ignore. Use a narrow,code-specific ignore with a comment explaining it.

## When you are unsure

Ask, and state the specific ambiguity. Preferred order of authority:

1. An explicit instruction in the current conversation.
1. docs/analysis-specification.md.
1. Existing behavior in the ported notebook code and its tests.
1. This file.

Prefer a small, reviewable change with a test over a large refactor.
