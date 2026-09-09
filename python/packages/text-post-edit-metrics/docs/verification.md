# Text Post-Edit Metrics: Verification

**Status:** Canonical software-verification description for
`text-post-edit-metrics`.

This document describes how the package verifies its formulas, preprocessing,
boundary behavior, optimized soft-word implementation, and public API.

For metric definitions and interpretation, see
[`methodology.md`](methodology.md).

---

## 1. Purpose

The verification suite provides evidence that `text-post-edit-metrics`
implements its documented calculations consistently.

It tests:

- TER-derived metrics;
- character-level Levenshtein metrics;
- weighted soft-word metrics;
- Unicode normalization;
- case behavior;
- directional denominators;
- raw and bounded scores;
- result construction;
- public API exports;
- validation and error behavior;
- equivalence between optimized and reference soft-word implementations.

Passing tests demonstrate agreement between code and the documented
methodology.

They do not prove that the metrics measure:

- human cognitive effort;
- elapsed editing time;
- observed keystrokes;
- semantic equivalence;
- user satisfaction;
- practical usefulness.

Those claims require separate empirical validation.

---

## 2. Test ownership

The package owns tests for all generic text-comparison behavior:

```text
python/packages/text-post-edit-metrics/tests/
├── helpers/
│   └── reference_impl.py
├── test_analyze_post_edit.py
├── test_metrics_character.py
├── test_metrics_differential.py
├── test_metrics_soft_word.py
├── test_metrics_ter.py
├── test_models.py
├── test_normalization.py
└── test_package.py
```

Consuming packages should not duplicate this complete low-level suite.

A consumer should instead test:

- its decision to call `analyze_post_edit()`;
- correct argument direction;
- correct attachment or transformation of `PostEditingResult`;
- its own domain-specific classifications and policy.

---

## 3. Identity behavior

For identical suggestion and final text, tests require:

```text
ter_rate = 0
ter_effort_saved_raw = 1
ter_effort_saved = 1

character_edit_distance = 0
character_effort_saved_raw = 1
character_effort_saved = 1

soft_word_edit_distance = 0
soft_word_effort_saved_raw = 1
soft_word_effort_saved = 1
```

The estimated-characters-saved proxy equals final character count when no
character edits are required.

These tests verify the expected identity boundary for every metric family.

---

## 4. Direction and denominator verification

The comparison is directional:

```text
suggestion → final
```

Tests verify that:

- character effort saved uses final character count;
- soft-word effort saved uses final token count;
- TER uses final reference length;
- insertion and deletion costs apply in the documented direction;
- unequal suggestion and final lengths do not silently omit words.

Direction is tested with examples where reversing insertion and deletion would
produce different results.

---

## 5. Empty and invalid values

### Empty suggestion

An empty suggestion is valid.

Tests verify that transforming an empty suggestion into a nonempty final text
requires:

- insertion of every final character at character level;
- insertion of every final token at soft-word level;
- zero bounded effort-saved scores under those measures.

### Empty final text

A final text with zero characters is invalid for normalized character metrics
because the denominator would be zero.

A final text with zero whitespace-delimited tokens is invalid for TER and
soft-word normalized metrics.

Tests verify that:

- an empty final string is rejected;
- a whitespace-only final string is rejected by the combined API;
- errors use the documented exception types and messages.

### Invalid types

The combined API accepts strings only.

Tests verify that non-string suggestion or final values raise `TypeError`
instead of failing later with an unrelated attribute or library error.

---

## 6. Raw and bounded scores

Each normalized metric stores:

- a raw score;
- a bounded score within `[0, 1]`.

Tests verify:

```text
bounded = min(1, max(0, raw))
```

They include cases where editing cost exceeds final length, requiring:

```text
raw < 0
bounded = 0
```

This confirms that negative raw values remain available for diagnostics while
bounded values remain suitable for reporting.

---

## 7. TER verification

TER tests verify:

- identical text produces TER `0`;
- effort saved equals `1 - TER`;
- one inserted token produces the expected final-reference-normalized rate;
- raw scores may be negative;
- bounded scores remain within `[0, 1]`;
- TER rejects a final value with no tokens;
- TER is case-insensitive under the configured API;
- canonically equivalent Unicode text compares consistently after NFC
  normalization.

The fixed SacreBLEU configuration is:

```text
normalized     = False
no_punct       = False
asian_support  = False
case_sensitive = False
```

Any change to these options requires updated expected values, documentation, and
compatibility review.

---

## 8. Character metric verification

Character tests verify:

- identical strings have distance `0`;
- a single substitution has distance `1`;
- an empty suggestion requires insertion of every final character;
- final character count is the denominator;
- raw scores may be negative;
- bounded scores remain within `[0, 1]`;
- case-sensitive and case-insensitive modes behave differently;
- canonically equivalent Unicode text has zero distance after NFC
  normalization;
- an empty final string is rejected.

The combined `analyze_post_edit()` API uses case-sensitive character metrics.

---

## 9. Weighted soft-word verification

### 9.1 Identity and boundaries

Tests verify:

- identical text has distance `0`;
- an empty suggestion incurs one insertion cost per final token;
- an empty final value incurs one deletion cost per suggestion token at the
  low-level distance function;
- normalized soft-word scoring rejects a zero-token final denominator.

### 9.2 Unequal-length alignments

Tests include transformations such as:

```text
very quickly → fast
fast → very quickly
```

These cases verify that every source and target token contributes to the
distance and that unequal-length sequences do not omit an operation.

### 9.3 Fractional substitutions

Tests verify that:

- small orthographic changes receive fractional substitution costs;
- unrelated replacements cost more than small spelling or suffix changes;
- the substitution cost equals RapidFuzz normalized character distance;
- final token count is the normalized-score denominator.

### 9.4 Insertion and deletion direction

Tests use unequal custom costs:

```text
insertion_cost = 2
deletion_cost = 3
```

They verify:

```text
"" → "word" costs 2
"word" → "" costs 3
```

They also verify insertion and deletion within nonempty sequences.

Using unequal costs detects accidental reversal that equal default costs would
hide.

### 9.5 Invalid costs

Tests reject:

- negative insertion cost;
- negative deletion cost;
- positive infinity;
- negative infinity;
- NaN.

Operation costs must be finite and nonnegative.

### 9.6 Tokenization and case

Tests verify:

- repeated whitespace does not alter tokenization;
- punctuation remains attached to tokens;
- hyphenated forms remain one token;
- case is preserved by default;
- case-insensitive behavior is available through the low-level API;
- NFC-equivalent text receives zero distance.

The combined API uses case-sensitive soft-word metrics.

---

## 10. Unicode normalization verification

Tests construct composed and decomposed forms programmatically using
`unicodedata.normalize()`.

This avoids dependence on editor behavior, because an editor may normalize a
source file when saving it.

Tests verify:

- NFC and NFD source forms differ before normalization;
- NFC normalization makes canonically equivalent text equal;
- capitalization is preserved by default;
- optional case folding behaves as documented;
- punctuation and whitespace are preserved by metric normalization.

Metric normalization must not perform product-specific cosmetic transformations.

---

## 11. Combined-result verification

Tests for `analyze_post_edit()` verify that:

- every combined field matches its corresponding low-level calculation;
- TER, character, and soft-word values are not cross-wired;
- character and token counts use NFC-normalized text;
- estimated characters saved uses final character count and character distance;
- estimated characters saved is bounded below at zero;
- an empty suggestion remains valid;
- the standard case behavior differs intentionally across metric families.

These tests protect the wiring between low-level functions and
`PostEditingResult`.

---

## 12. Result-model verification

Result-model tests verify that:

- TER, character, and soft-word results preserve raw and bounded values;
- `PostEditingResult` exposes every documented metric family;
- result objects are immutable;
- package-level public exports point to the expected result classes.

Immutability prevents a completed analysis result from being modified after
construction.

---

## 13. Public API verification

Package tests verify that:

- the package is not an implicit namespace package;
- `__version__` is exposed;
- the `py.typed` marker is shipped;
- result models are exported;
- normalization helpers are exported;
- metric functions are exported;
- `analyze_post_edit()` is exported.

This protects the package import contract independently of internal module
organization.

---

## 14. Differential testing

### 14.1 Purpose

The production soft-word implementation retains only two dynamic-programming
rows to reduce memory use.

A separate reference implementation stores the complete matrix and prioritizes
readability over memory efficiency.

Differential testing compares both implementations on identical inputs.

### 14.2 Procedure

For each generated pair:

1. Generate suggestion and final token sequences.
2. Calculate distance with the optimized two-row implementation.
3. Calculate distance with the full-matrix reference implementation.
4. Compare results using absolute tolerance `1e-12`.

### 14.3 Standard-cost cases

The suite evaluates 1,000 pseudorandom pairs using:

```text
insertion_cost = 1
deletion_cost = 1
random seed = 42
```

Generated sequences include:

- empty inputs;
- unequal lengths;
- repeated tokens;
- insertions;
- deletions;
- exact matches;
- fractional substitutions.

### 14.4 Unequal-cost cases

The suite evaluates 500 pseudorandom pairs using:

```text
insertion_cost = 1.25
deletion_cost = 1.75
random seed = 123
```

Unequal costs expose directional mistakes that equal costs could conceal.

### 14.5 Explicit boundary cases

Additional deterministic cases cover:

- both inputs empty;
- empty suggestion;
- empty final;
- repeated source tokens;
- repeated target tokens;
- repeated fractional substitutions.

### 14.6 Interpretation

Agreement between the optimized and reference implementations demonstrates
implementation consistency for the tested recurrence.

It does not independently validate:

- the chosen operation costs;
- the use of orthographic substitution cost;
- the measure as a model of human effort;
- semantic validity.

Both implementations intentionally use the same recurrence and substitution-cost
function.

---

## 15. Test determinism

The suite uses fixed pseudorandom seeds.

`pytest-randomly` may reorder tests, so tests must not depend on:

- execution order;
- mutable global state;
- files left by another test;
- cache contents created by another test.

The metric implementation may use internal memoization, but tests must remain
correct regardless of cache state.

---

## 16. Coverage

The package enforces statement and branch coverage through its member
`pyproject.toml`.

Run:

```bash
make coverage PACKAGE=text-post-edit-metrics
```

The coverage report is written under:

```text
python/packages/text-post-edit-metrics/reports/
```

The configured gate is 95%.

Coverage is a guardrail, not proof of correctness. Tests should prioritize
meaningful formulas, boundaries, and invariants rather than constructing
artificial states solely to execute defensive lines.

---

## 17. Running verification

From the repository root:

```bash
make test PACKAGE=text-post-edit-metrics
make coverage PACKAGE=text-post-edit-metrics
```

Skip slow randomized tests:

```bash
make test-fast PACKAGE=text-post-edit-metrics
```

Run only tests marked slow:

```bash
make test-slow PACKAGE=text-post-edit-metrics
```

Run the complete repository gate:

```bash
make check
```

---

## 18. Change requirements

A change to any of the following requires updated tests and methodology
documentation:

- TER configuration;
- comparison direction;
- denominator choice;
- Unicode normalization;
- case behavior;
- tokenization;
- insertion or deletion defaults;
- substitution cost;
- dynamic-programming recurrence;
- raw or bounded formulas;
- `PostEditingResult` fields;
- public exports.

A change described as a refactor must preserve all existing expected values.

If analytical output changes intentionally, the change must state:

1. what values can change;
2. why the new behavior is preferred;
3. which tests and documentation were updated;
4. whether consuming packages require compatibility changes.
