# Project context for AI coding agents

## What this library is

`study-posting-ai-analysis` measures how much **AI-generated text assistance
survived into final human-authored content**.

Given three inputs — the suggestions an AI offered, the suggestions a user
selected, and the values the user ultimately saved — it reports, per form field,
what became of the suggestion and how much textual post-editing was required.

Built for the University of Michigan eResearch study-posting form.

The authoritative description of the analysis is
**`docs/analysis-specification.md`**. Treat it as the specification of record.
If code and that document disagree, the document governs unless the user says
otherwise.

## Scope: what this library does NOT do

This is a **pure analysis library**. It performs no input or output.

It has no knowledge of, and must never gain knowledge of:

- databases, connections, queries, or drivers;
- files, paths, CSV, or the filesystem;
- audit-table schemas, eligibility filtering, or record identity beyond an
  opaque `record_id` label;
- pandas or any DataFrame;
- logging;
- command-line arguments or configuration.

Those concerns belong to separate consuming programs. If a task appears to
require any of them, the task belongs in a different package — say so rather than
adding the capability here.

Runtime dependencies are **`sacrebleu` and `rapidfuzz`, and nothing else**.

## Public contract

```python
suggested, selected, final = parse_analysis_inputs(a, b, c)  # JSON in
results = analyze_objects(suggested, selected, final)        # dict[str, AnalysisResult]
rows = flatten_analysis_results(results, record_id="x")      # list[dict[str, object]]
```

Flattened rows contain only `None`, `bool`, `int`, `float`, or `str` — never a
nested structure. `FLATTENED_COLUMNS` defines every column and its order.

## Modules

| Module | Responsibility |
|---|---|
| `models.py` | Enums and frozen dataclasses. Derived values are properties, never stored fields. |
| `validation.py` | Runtime type checks. Accepts `object` so `isinstance` narrowing is genuine. |
| `text_normalization.py` | NFC normalization, cosmetic equivalence, `clamp01`, token counting. |
| `metrics.py` | TER, character Levenshtein, weighted soft-word. Pure calculations. |
| `field_specs.py` | `FIELD_SPECS`, contact field names, requiredness configuration. |
| `field_analysis.py` | Match classification and the four per-kind analyzers. |
| `parsing.py` | JSON input decoding. |
| `flattening.py` | Results to tabular rows. |
| `errors.py` | `InputParseError` only. |

### Hard rules

1. **No I/O anywhere.** No `sqlite3`, `oracledb`, `pandas`, `pathlib`, `open`,
   `os`, or `logging` in `src/`.
2. **Functions raise; they never log.** Error handling is the caller's decision.
3. **Results are immutable.** Frozen, slotted dataclasses.
4. **No new dependency without asking.** Two runtime dependencies is a feature.

## Domain rules you must not change without explicit instruction

### Match classification

| Outcome | Condition |
|---|---|
| `EXACT` | Selected and final Python strings are equal. |
| `COSMETIC_EQUIVALENT` | Equal after `normalize_text_for_equivalence`. |
| `EDITED` | Nonblank final text with substantive differences remaining. |
| `REMOVED` | A suggestion was selected but the optional final value is blank. |
| `UNASSISTED` | No suggestion or lookup value was selected. |

Evaluation order is **blank, then exact, then cosmetic, then edited**.

Metrics are calculated for all three nonblank outcomes, so an exact match records
a measured score rather than an assumed one.

### Metrics

| Metric | Formula | Role | Case |
|---|---|---|---|
| TER-derived | `1 - TER`, from SacreBLEU | **Primary** | insensitive |
| Character | `1 - levenshtein / final_char_count` | Secondary | sensitive |
| Soft-word | `1 - weighted_distance / final_word_count` | Robustness | sensitive |
| Characters saved | `max(0, final_chars - char_distance)` | Absolute proxy | sensitive |

The case asymmetry is deliberate. Do not "fix" it.

Every raw score may be negative and is retained alongside its `clamp01` bounded
counterpart. Never discard the raw value.

Soft-word substitution cost is the RapidFuzz **normalized** character distance.
Insertion and deletion each cost `1.0` by default. The implementation keeps two
dynamic-programming rows; the full matrix exists only in `tests/helpers/` as the
verification reference.

`_TER` is constructed once at module scope with every argument explicit. Changing
its configuration changes published results.

### Requiredness

Required: `title`, `purpose`, `description`, `contact.email`, `contact.name`.
Optional: `about`, `contact.phone`, `contact.website`.
Compensation text is required exactly when the **saved** `offersCompensation`
value is `True`. That Boolean must be `True` or `False`, never absent.

A blank required final value raises. It is not a metric of zero.

### Lookup fields

`department`, `locations`, `topics` hold sets of integer identifiers. Booleans are
rejected because `bool` subclasses `int`. Picked identifiers must have been
offered. Similarity is Jaccard between picked and saved. When nothing was picked,
the outcome is `UNASSISTED` and similarity is the **policy value `0.0`**, not a
calculated one.

Lookup rows leave the TER and policy columns as `None` in flattened output, so a
mean over text rows cannot be contaminated by a similarity value.

### Preprocessing invariants

- Metric inputs are normalized with Unicode **NFC**.
- `normalize_text_for_equivalence` uses **NFKD** plus casefolding, combining-mark
  removal, and punctuation-to-space. It is used **only** for classification and
  must never preprocess a metric input.
- Whitespace tokenization only. No stemming, lemmatization, embeddings, or
  semantic similarity.

## Interpretation discipline

These metrics measure **technical post-editing effort**. In code, docstrings,
comments, and documentation, never describe them as measuring time saved,
keystrokes avoided, cognitive effort, or user satisfaction.

Use the established vocabulary:

| Statistic | Label |
|---|---|
| Fields with an offer ÷ analyzed text fields | Suggestion offer coverage |
| Fields with a selection ÷ fields with an offer | Suggestion selection rate |
| Mean policy score among fields with an offer | Realized suggestion utility |
| Mean policy score among selected suggestions | Selected-suggestion utility |
| Mean `ter_effort_saved` among nonblank post-edits | TER-derived post-editing score |

Every mean must state its denominator. Never average lookup similarity together
with text effort-saved scores.

## Coding conventions

- Python 3.14. Full type annotations. `mypy --strict` must pass.
- Ruff formats and lints; line length 88. Do not hand-format around it.
- NumPy-style docstrings on every public module, class, and function. Module
  docstrings state the purity constraint.
- Frozen dataclasses with `slots=True` for results. Derived values are
  `@property`.
- `StrEnum` for closed vocabularies. PEP 695 `type` statements for aliases.
- Keyword-only (`*`) for flag parameters.
- Descriptive names: `number_of_final_words`, not `n`.
- Exception messages name the field, prefixed for contact and compensation.

## Validation at trust boundaries

Values arriving from decoded JSON carry no static type guarantee. Validate them
through `validation.py`, whose helpers accept `object` so that `isinstance`
narrowing is genuine rather than statically redundant.

Never replace an `isinstance` check with a truthiness test on a method result:
`None` must raise `TypeError`, not `AttributeError`, and the exception type for
each failure is asserted by tests.

Never silence a "redundant isinstance" diagnostic with `# noqa` or
`# type: ignore`. Move the check into a helper that accepts `object`.

Validate what the boundary genuinely permits, and no more. `isinstance(x, dict)`
after `json.loads` is necessary, because JSON has six value types. Re-checking
that keys are strings is not, because JSON guarantees it.

## Testing conventions

- pytest. Plain functions with `assert`. No `unittest.TestCase`.
- `pytest.raises(..., match=r"...")`. Escape regex metacharacters, including the
  dot in `contact\.email`.
- Compare enum members with `is`, not `==`.
- Mark randomized differential tests `@pytest.mark.slow`.
- Seed every generator explicitly: `random.Random(42)`.
- `pytest.approx(reference, abs=1e-12)` for float comparisons.
- `pytest-randomly` shuffles order; tests must not depend on order or shared
  state.
- Use the `valid_audit_objects` fixture and modify exactly one field to isolate
  the behavior under test.
- Synthetic text only. Never real or realistic study content.

Coverage sits near 99 percent with a 95 percent gate. The four uncovered lines
are defensive guards for states the type system prevents; leave them uncovered.

## Documentation is part of the change

Certain edits are incomplete without a matching documentation change. Before
finishing, check this table and state in your summary which documents you updated
or why none were needed.

| If you changed | Also update |
|---|---|
| A metric formula, threshold, or normalization step | `docs/analysis-specification.md` §7 or §9 |
| Requiredness of any field | `docs/analysis-specification.md` §4 |
| A `MatchType` outcome or its evaluation order | `docs/analysis-specification.md` §5, `docs/program-flow.md` §4 |
| Lookup similarity policy | `docs/analysis-specification.md` §11 |
| Compensation Boolean or text rules | `docs/analysis-specification.md` §10, `docs/program-flow.md` §6 |
| `FLATTENED_COLUMNS` | `README.md` "What it reports", `docs/program-flow.md` §8 |
| Added, removed, or renamed a module | `README.md` architecture, `docs/program-flow.md` §1 |
| The public API in `__init__.py` | `README.md` "Public API" |
| A dependency or version bound | `README.md` reproducibility table |

A pre-commit hook enforces the first five rows. If it blocks a commit, open the
named section rather than bypassing the hook.

## Workflow

Always use `make`; never invoke `pip`, and never activate the venv manually.

```bash
make setup       # bootstrap a fresh clone
make format      # Ruff format and import ordering
make lint        # Ruff lint
make typecheck   # mypy strict
make test        # pytest, clean start
make test-fast   # skip slow randomized tests
make coverage    # coverage reports into reports/
make audit       # pip-audit and bandit
make check       # everything; the gate before any commit
make clean       # remove reports and caches
```

## Things to never do

- Add I/O, pandas, logging, or a database driver to this package.
- Change a metric formula, normalization step, or threshold without updating
  `docs/analysis-specification.md`.
- Add a dependency without asking. Two runtime dependencies is deliberate.
- Loosen `mypy` strictness, or add a broad `# type: ignore`. If an ignore is
  unavoidable, make it code-specific and comment why.
- "Simplify" a validation block. Values from decoded JSON have no static type
  guarantee, and the exception type for each failure is asserted by tests.
- Use `normalize_text_for_equivalence` as preprocessing for a metric. It exists
  only for classification and would hide real edits.
- Discard a raw effort-saved score in favor of only its bounded counterpart.
- Combine lookup similarity with text effort-saved scores in one average.
- Put real or realistic study text in a test, fixture, example, or docstring.
  Invent synthetic content such as "Participants receive a $50 gift card."
- Silence a lint or type diagnostic to make an error disappear rather than
  addressing what it reports.

## When you are unsure

Ask, and state the specific ambiguity. Order of authority:

1. An explicit instruction in the current conversation.
2. `docs/analysis-specification.md`.
3. Existing behavior and its tests.
4. This file.

Prefer a small, reviewable change with a test over a large refactor. If a task
seems to require I/O, a data source, or a DataFrame, it belongs in a consuming
program rather than here — say so instead of adding the capability.
