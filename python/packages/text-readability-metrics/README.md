# text-readability-metrics

Generic readability analysis for nonblank English text.

## Contract

Use the public API:

```python
from text_readability_metrics import analyze_readability

result = analyze_readability("Synthetic text used for readability analysis.")
```

`analyze_readability()` returns an immutable `ReadabilityResult`.

## Metrics

The result contains:

- flesch_kincaid_grade;
- automated_readability_index;
- coleman_liau_index;
- gunning_fog;
- dale_chall_readability_score;
- estimated_reading_time_seconds;
- sentence_count;
- word_count;
- syllable_count;
- letter_count;
- polysyllable_count.

The implementation uses textstat with the fixed en_US language profile. `estimated_reading_time_seconds` is expressed in seconds.
Readability scores may legitimately be negative for short or unusual text. Every score must be finite. Estimated reading time must be finite and nonnegative. Counts must be nonnegative integers.

## Input validation

Input must be a nonblank string. Empty and whitespace-only strings raise `InvalidReadabilityTextError`.
Malformed or non-finite backend results raise `InvalidReadabilityResultError`. Both exceptions derive from `ReadabilityError`.

## Interpretation

Readability formulas estimate characteristics associated with sentence length, word length, syllables, and familiar-word lists. They do not determine whethertext is correct, useful, inclusive, understandable to a particular audience, oraccessible.

Scores can vary across implementations and versions because tokenization,sentence segmentation, syllable estimation, and word-list behavior vary. The package constrains `textstat` to a compatible version range, and the workspace lockfile records the exact resolved version.

## Boundary

This package owns:

- generic readability calculation;
- the fixed English profile;
- immutable result modeling;
- input and result validation.

It performs no:

- study-specific field extraction;
- suggestion-selection matching;
- database access;
- CSV or filesystem output;
- report publication;
- command-line processing.

## Development

Run from the repository root:
```shell
make test PACKAGE=text-readability-metrics
make coverage PACKAGE=text-readability-metrics
```

## License

MIT
