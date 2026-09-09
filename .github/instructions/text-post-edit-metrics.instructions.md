---
applyTo: "python/packages/text-post-edit-metrics/**"
---

# text-post-edit-metrics instructions

## Contract and scope

This pure package performs a directional text comparison:

```python
result = analyze_post_edit(
    suggestion=initial_text,
    final=represented_edited_text,
)
```

The package measures the pair under a post-editing interpretation. It does not
verify that `final` was actually produced by editing `suggestion`.

It owns:

- Unicode NFC metric normalization;
- TER and TER-derived scores;
- character-level Levenshtein metrics;
- weighted soft-word metrics;
- estimated characters saved;
- descriptive text counts;
- immutable generic result models.

It must not contain form fields, selection policy, record identifiers,
study-posting rules, JSON audit parsing, database or file I/O, pandas, logging,
or CLI behavior.

## Direction and result model

Never reverse the arguments. All normalized denominators use final-text length.

`PostEditingResult` contains only metric values and text counts. Do not add:

- field or record identity;
- source information;
- selection status;
- product-policy classification.

Those belong to consumers.

## Metric invariants

### TER

The SacreBLEU configuration is fixed:

```python
TER(
    normalized=False,
    no_punct=False,
    asian_support=False,
    case_sensitive=False,
)
```

```text
ter_effort_saved_raw = 1 - ter_rate
ter_effort_saved = clamp01(ter_effort_saved_raw)
```

TER may exceed `1`; retain negative raw scores.

### Character metric

```text
character_effort_saved_raw =
    1 - character_edit_distance / final_character_count
```

The combined API is case-sensitive for this metric.

### Weighted soft-word metric

- whitespace tokenization;
- insertion cost `1.0`;
- deletion cost `1.0`;
- substitution cost is RapidFuzz normalized character distance;
- no phrase shifts;
- two-row Wagner–Fischer implementation.

```text
soft_word_effort_saved_raw =
    1 - soft_word_edit_distance / final_word_count
```

The full-matrix implementation belongs only in `tests/helpers/`.

### Absolute proxy

```text
estimated_characters_saved =
    max(0, final_character_count - character_edit_distance)
```

Do not describe this as observed keystrokes or literal avoided typing.

## Validation and interpretation

- Empty suggestion: valid.
- Empty or whitespace-only final text: invalid.
- Non-string arguments: `TypeError`.
- Zero final denominator: `ValueError`.

These metrics describe technical textual transformation. They do not directly
measure time, cognition, observed keystrokes, semantic equivalence, or user
satisfaction.

## Change control

Changes to formulas, preprocessing, case behavior, TER configuration, operation
costs, denominators, or result fields can change reported values. Such changes
require:

- updated package documentation;
- direct boundary and formula tests;
- compatibility review with consuming packages;
- seeded differential tests where applicable.

The optimized soft-word implementation must continue to agree with the
full-matrix reference across the established 1,500 seeded random cases.

Run:

```bash
make test PACKAGE=text-post-edit-metrics
make coverage PACKAGE=text-post-edit-metrics
make check
```
