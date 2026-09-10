# text-post-edit-metrics

Directional technical post-editing metrics for comparing an initial text with a
value represented by the caller as its edited form.

```python
from text_post_edit_metrics import analyze_post_edit

result = analyze_post_edit(
    suggestion="Support analysis of research data.",
    final="Support analysis of clinical research data.",
)

print(result.ter_effort_saved)
print(result.character_edit_distance)
print(result.soft_word_edit_distance)
```

## Contract

The comparison direction matters:

- `suggestion` is the initial, generated, or proposed text;
- `final` is represented by the caller as its edited or revised form;
- normalized denominators use final-text length.

The package does not prove that `final` was produced by editing `suggestion`.

Its metrics describe technical textual transformation. They do not directly
measure:

- elapsed time;
- cognitive effort;
- observed keystrokes;
- semantic equivalence;
- user satisfaction;
- overall usefulness.

## Responsibilities

The package owns:

- Unicode NFC normalization for metric inputs;
- Translation Edit Rate;
- TER-derived raw and bounded scores;
- character-level Levenshtein metrics;
- weighted soft-word metrics;
- estimated characters saved;
- descriptive character and token counts;
- immutable result models.

It does not own:

- application fields or requiredness;
- suggestion-selection or acceptance policy;
- product-specific classifications;
- record identifiers;
- JSON audit-object parsing;
- databases, CSV files, or filesystem access;
- reporting, logging, or CLI behavior.

Those responsibilities belong to consuming packages and programs.

## Primary API

```python
from text_post_edit_metrics import analyze_post_edit

result = analyze_post_edit(
    suggestion="We analyze research data.",
    final="We analyze clinical research data.",
)
```

`analyze_post_edit()` returns an immutable `PostEditingResult`.

An empty suggestion is valid:

```python
result = analyze_post_edit(
    suggestion="",
    final="A final response",
)
```

This represents a comparison in which the complete final text must be inserted.

The final value must:

- be a string;
- be nonempty;
- contain at least one whitespace-delimited token.

Non-string arguments raise `TypeError`. An invalid final denominator raises
`ValueError`.

## Result overview

The canonical field reference and formulas are maintained in
[`docs/methodology.md`](docs/methodology.md#9-posteditingresult).

| Field group | Purpose |
|---|---|
| `ter_rate` | Conventional TER edit rate, which may exceed `1` |
| `ter_effort_saved_raw`, `ter_effort_saved` | Raw and bounded TER-derived scores |
| `character_edit_distance` | Character-level Levenshtein distance |
| `character_effort_saved_raw`, `character_effort_saved` | Raw and bounded character scores |
| `soft_word_edit_distance` | Weighted word-level edit distance |
| `soft_word_effort_saved_raw`, `soft_word_effort_saved` | Raw and bounded soft-word scores |
| `estimated_characters_saved` | Absolute technical retained-character proxy |
| Character and word counts | Descriptive lengths and score denominators |

Raw scores may be negative when edit cost exceeds the final-length baseline.
Bounded scores remain within `[0, 1]`.

`estimated_characters_saved` is a technical proxy. It is not a measurement of
literal avoided typing or observed keystrokes.

## Standard metric behavior

The standard combined API uses:

| Metric | Case behavior | Denominator |
|---|---|---|
| TER | Case-insensitive | Final TER reference length |
| Character distance | Case-sensitive | Final character count |
| Weighted soft-word distance | Case-sensitive | Final whitespace-token count |

All metric inputs receive Unicode NFC normalization.

The weighted soft-word calculation uses:

- whitespace tokenization;
- insertion cost `1.0`;
- deletion cost `1.0`;
- normalized character Levenshtein substitution cost;
- no phrase-shift operation.

Detailed definitions, formulas, preprocessing, and interpretation limits are
authoritative in the
[methodology documentation](docs/methodology.md).

## Lower-level API

The package also exports focused calculation and normalization functions:

```python
from text_post_edit_metrics import (
    CharacterResult,
    PostEditingResult,
    SoftWordResult,
    TerResult,
    calculate_character_metrics,
    calculate_soft_word_metrics,
    calculate_ter_metrics,
    clamp01,
    count_whitespace_tokens,
    normalize_metric_text,
    normalized_word_distance,
    weighted_soft_word_distance,
)
```

Use `analyze_post_edit()` for the standard combined calculation.

Lower-level functions support specialized comparisons. For example:

```python
distance = weighted_soft_word_distance(
    suggestion="one two",
    final="one",
    insertion_cost=2.0,
    deletion_cost=3.0,
)
```

Results produced with nondefault lower-level options are outside the standard
combined configuration and should be documented by the caller.

## Documentation

| Document | Ownership |
|---|---|
| [`docs/methodology.md`](docs/methodology.md) | Comparison direction, preprocessing, formulas, result fields, and interpretation |
| [`docs/verification.md`](docs/verification.md) | Boundary tests, differential testing, seeds, coverage, and change requirements |

The detailed documents are authoritative for their subjects.

## Verification

The package verifies:

- formulas and denominator direction;
- raw and bounded scores;
- Unicode normalization;
- case behavior;
- empty and invalid inputs;
- configurable soft-word costs;
- result immutability;
- public exports;
- combined-result wiring.

The optimized soft-word implementation is compared with a readable full-matrix
reference across fixed-seed randomized and explicit boundary cases.

See
[`docs/verification.md`](docs/verification.md)
for the complete verification strategy.

## Dependencies and reproducibility

| Dependency | Purpose |
|---|---|
| Python 3.14 | Runtime |
| SacreBLEU 2.6.x | TER |
| RapidFuzz 3.14.x | Character-level distance |

Analytical dependency major versions are bounded because upgrades could change
reported values. Exact workspace versions are recorded in the root `uv.lock`.

For archived results, record:

- Python and package versions;
- Git revision;
- metric configuration;
- analysis date;
- input counts;
- any nondefault lower-level options.

## Development

Run from the repository root:

```bash
make test PACKAGE=text-post-edit-metrics
make coverage PACKAGE=text-post-edit-metrics
```

Run only randomized differential tests:

```bash
make test-slow PACKAGE=text-post-edit-metrics
```

Skip slow tests:

```bash
make test-fast PACKAGE=text-post-edit-metrics
```

Run the complete workspace gate:

```bash
make check
```

See the [root README](../../../README.md) for workspace-wide guidance.

## License

MIT
