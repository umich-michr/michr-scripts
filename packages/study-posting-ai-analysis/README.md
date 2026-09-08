# study-posting-ai-analysis

Measures how much **AI-generated text assistance survived into final
human-authored content**.

Given three inputs — the suggestions an AI offered, the suggestions a user
selected, and the values the user ultimately saved — this library reports, per
form field, what became of the suggestion and how much textual post-editing was
required.

Built for the University of Michigan eResearch study-posting form, where an LLM
suggests values for fields such as title, purpose, description, compensation
text, and contact details.

> **Interpretation note.** These metrics quantify *technical post-editing
> effort*. They do not measure time saved, keystrokes avoided, cognitive effort,
> or user satisfaction. See
> [interpretation limits](docs/analysis-specification.md#16-interpretation-limits).

---

## Scope

This library performs **no input or output**. It has no knowledge of databases,
files, audit-table schemas, or command lines. Three dictionaries in, analysis
results out.

Reading rows from a data source, looping over them, aggregating results, and
writing reports are the responsibility of the programs that consume it.

Runtime dependencies: `sacrebleu` and `rapidfuzz`. Nothing else.

---

## Usage

```python
from study_posting_ai_analysis import (
    analyze_objects,
    flatten_analysis_results,
    parse_analysis_inputs,
)

# Decode JSON payloads from wherever they came from: a database column, a CSV
# cell, an HTTP request. Already-decoded dictionaries pass straight through.
suggested, selected, final = parse_analysis_inputs(
    suggestions_json,
    selections_json,
    final_json,
)

# One structured result per analyzed form field.
results = analyze_objects(suggested, selected, final)

results["title"].match  # MatchType.EDITED
results["title"].ter_effort_saved  # 0.83
results["title"].policy_adjusted_effort_saved  # 0.83
results["topics"].similarity  # 0.33 (Jaccard)

# One flat dictionary per field, ready for CSV, a DataFrame, or a table insert.
rows = flatten_analysis_results(results, record_id="audit-1234")
```

Writing the rows out is the consumer's job:

```python
import csv

from study_posting_ai_analysis import FLATTENED_COLUMNS

with open("analysis.csv", "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=FLATTENED_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
```

---

## What it reports

### Outcome classification

Every field receives a `MatchType`:

| Outcome | Meaning |
|---|---|
| `EXACT` | The suggestion and the saved value are identical |
| `COSMETIC_EQUIVALENT` | They differ only in case, diacritics, punctuation, or whitespace |
| `EDITED` | A suggestion was applied and substantive differences remain |
| `REMOVED` | A suggestion was selected, then the optional field was cleared |
| `UNASSISTED` | No suggestion was selected |

### Metrics

| Measure | Formula | Role |
|---|---|---|
| TER-derived | `1 − TER` | **Primary**, case-insensitive |
| Character | `1 − levenshtein / final_chars` | Secondary robustness |
| Soft-word | `1 − weighted_distance / final_words` | Robustness |
| Characters saved | `max(0, final_chars − distance)` | Absolute proxy |

Raw scores may be negative and are always retained alongside their bounded
`[0, 1]` counterparts, so a suggestion that cost more to fix than to rewrite
remains identifiable.

Lookup fields report **Jaccard similarity** between picked and saved identifier
sets. Compensation reports the Boolean flag outcome **separately** from its text
outcome. Neither may be averaged together with text effort-saved scores.

### Flattened output

`FLATTENED_COLUMNS` defines 38 columns present on every row: identification,
suggestion counts, the classification, all metric variants, compensation flag
outcomes, and lookup identifier sets. Values are only `None`, `bool`, `int`,
`float`, or `str` — no nested structures.

Free text is excluded unless `include_text=True` is passed.

---

## Public API

| Function | Purpose |
|---|---|
| `analyze_objects(suggested, selected, final)` | Analyze every configured field |
| `parse_analysis_inputs(...)` | Decode three JSON payloads |
| `parse_json_object(value, name=...)` | Decode one JSON payload |
| `flatten_analysis_results(results, ...)` | Convert results to flat rows |

Individual analyzers — `analyze_text_field`, `analyze_contact`,
`analyze_compensation`, `analyze_lookup_values`, `compare_selected_text`,
`analyze_selected_suggestion` — and the metric functions are also exported for
callers analyzing one field at a time.

Configuration is exposed as `FIELD_SPECS`, `CONTACT_FIELDS`,
`REQUIRED_CONTACT_FIELDS`, and `COMPENSATION_KINDS`.

Invalid input raises `TypeError` or `ValueError`. Malformed JSON raises
`InputParseError`, which subclasses `ValueError`.

---

## Development

### Prerequisites

| Tool | Check | Install |
|---|---|---|
| **uv** | `uv --version` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **make** | `make --version` | macOS: `xcode-select --install` |

Python is not a prerequisite; `uv` reads `.python-version` and downloads the
interpreter.

### Setup

```bash
git clone <repository-url>
cd study-posting-ai-analysis
make setup      # idempotent; re-run any time
make check      # the full gate
```

### Commands

| Command | Purpose |
|---|---|
| `make setup` | Bootstrap a fresh clone |
| `make check` | Format, lint, types, security audit, coverage. **Run before committing.** |
| `make test` | Test suite, clean start |
| `make test-fast` | Skip slow randomized differential tests |
| `make coverage-open` | Coverage, then open the HTML report |
| `make format` | Format and organize imports |
| `make lint` / `make typecheck` | Ruff · mypy strict |
| `make audit` | Dependency and source security scan |
| `make clean` | Remove reports and caches |
| `make doctor` | Environment summary |

Run a subset:

```bash
make test PYTEST_ARGS="-k compensation -vv"
```

Run `make` alone to list every target.

---

## Architecture

Nine modules, no I/O anywhere.

```
src/study_posting_ai_analysis/
├── models.py             Enums and frozen result dataclasses
├── validation.py         Runtime type checks at trust boundaries
├── text_normalization.py NFC normalization, cosmetic equivalence
├── metrics.py            TER, character, and soft-word calculations
├── field_specs.py        Field configuration and requiredness
├── field_analysis.py     Match classification and per-field analyzers
├── parsing.py            JSON input decoding
├── flattening.py         Results to tabular rows
└── errors.py             InputParseError
```

Three constraints hold:

1. **No I/O.** No `sqlite3`, `oracledb`, `pandas`, filesystem, or `logging`.
2. **Functions raise; they do not log.** Error handling belongs to the caller.
3. **Results are immutable.** Frozen, slotted dataclasses with derived
   properties rather than stored duplicates.

See [`docs/program-flow.md`](docs/program-flow.md) for the flow diagrams.

---

## Documentation

| Document | Contents |
|---|---|
| [`docs/analysis-specification.md`](docs/analysis-specification.md) | **The specification of record.** Formulas, requiredness rules, outcome vocabulary, reporting terminology, interpretation limits, references. |
| [`docs/program-flow.md`](docs/program-flow.md) | Control-flow diagrams. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Workflow, conventions, the metric-change protocol, AI-agent guidance. |
| [`.github/copilot-instructions.md`](.github/copilot-instructions.md) | Context supplied automatically to Copilot Chat. |

If code and the specification disagree, **the specification governs** — or it
must be amended in the same change. A pre-commit hook enforces this for the
modules that determine reported numbers.

---

## Reporting guidance for consumers

Each statistic below has a different denominator and answers a different
question. Report them separately, and always state the denominator.

| Statistic | Denominator | Label |
|---|---|---|
| Fields with an offer ÷ analyzed text fields | all text fields | Suggestion offer coverage |
| Fields with a selection ÷ fields with an offer | offered fields | Suggestion selection rate |
| Mean policy score among offered fields | offered fields | Realized suggestion utility |
| Mean policy score among selected suggestions | selected fields | Selected-suggestion utility |
| Mean `ter_effort_saved` among nonblank post-edits | measurable post-edits | TER-derived post-editing score |

Two rules that matter:

- Never report an all-text-fields average simply as "effort saved" without
  stating its denominator.
- Never average lookup similarity together with text effort-saved scores; they
  measure different constructs.

Lookup rows deliberately leave the TER and policy columns as `None` so that a
mean over text rows cannot be contaminated by a similarity value.

---

## Handling data responsibly

- Free text is excluded from flattened rows unless `include_text=True` is passed
  deliberately.
- This library never logs. A consumer that logs field text should do so only at
  `DEBUG`.
- Test fixtures contain synthetic text only. Real study content must never
  appear in a test, example, or docstring.

---

## Reproducibility

| Component | Version |
|---|---|
| Python | 3.14 |
| SacreBLEU | 2.6.x — TER implementation |
| RapidFuzz | 3.14.x — character-level Levenshtein |

Major versions are bounded deliberately: a major release of either library could
change reported scores. `uv.lock` is committed so every clone and CI run
resolves identical versions.

For a publication or archived analysis, record the Python and package versions,
the analysis date, the library version, random seeds, record counts, inclusion
rules, and every aggregate denominator. See
[specification section 17](docs/analysis-specification.md#17-reproducibility).

---

## License

MIT
