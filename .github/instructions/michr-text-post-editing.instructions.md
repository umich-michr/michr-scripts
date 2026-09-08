---
applyTo: "packages/michr-text-post-editing/**"
---

# michr-text-post-editing instructions

## Package contract

This package performs a directional technical comparison:

```python
PostEditingResult = analyze_post_edit(
    suggestion=generated_or_original_text,
    final=human_edited_reference_text,
)
```

The argument direction must never be reversed. Every normalized denominator uses
the final text length.

## Scope

This package owns only:

- Unicode NFC metric normalization;
- TER and TER-derived scores;
- character-level Levenshtein metrics;
- weighted soft-word metrics;
- the estimated-characters-saved proxy;
- descriptive text-length counts;
- generic immutable result models.

It must not contain:

- study-posting fields or requiredness;
- selection or acceptance policy;
- cosmetic-equivalence policy;
- contact, compensation, or lookup behavior;
- JSON audit-object parsing;
- database, CSV, filesystem, pandas, logging, or CLI code.

## Metric invariants

### TER

SacreBLEU TER configuration is fixed:

```python
TER(
    normalized=False,
    no_punct=False,
    asian_support=False,
    case_sensitive=False,
)
```

Changing any argument changes reported results and requires explicit
documentation and compatibility tests.

```text
ter_effort_saved_raw = 1 - ter_rate
ter_effort_saved = clamp01(ter_effort_saved_raw)
```

TER may exceed `1`; the raw score may be negative.

### Character metric

```text
character_effort_saved_raw =
    1 - character_edit_distance / final_character_count
```

The standard combined API is case-sensitive for this metric.

### Weighted soft-word metric

- whitespace tokenization;
- insertion cost `1.0`;
- deletion cost `1.0`;
- substitution cost is RapidFuzz normalized character distance;
- no phrase-shift operation;
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

Never describe this as observed keystrokes or literal avoided typing.

## Validation

- Empty suggestion: valid.
- Empty final text: invalid.
- Whitespace-only final text: invalid.
- Non-string arguments: `TypeError`.
- Zero final denominator: `ValueError`.

Runtime validators accept `object` so `isinstance` checks are meaningful to
Pylance and mypy.

## Result model

`PostEditingResult` contains only metric values and text counts. Do not add:

- field name;
- record identifier;
- source name;
- selection status;
- policy classification.

Those belong to the consuming package.

## Interpretation

These values describe technical textual transformation. They do not directly
measure:

- elapsed time;
- cognitive effort;
- observed keystrokes;
- semantic equivalence;
- user satisfaction.

## Verification

Any implementation change must preserve or deliberately update:

- direct unit tests;
- boundary tests;
- case and Unicode tests;
- raw and bounded formulas;
- 1,500 seeded differential cases;
- public API tests;
- package README.

Run:

```bash
make test PACKAGE=michr-text-post-editing
make coverage PACKAGE=michr-text-post-editing
make check
```
