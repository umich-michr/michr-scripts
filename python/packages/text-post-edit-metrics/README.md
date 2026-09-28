# text-post-edit-metrics

Directional technical text-comparison metrics for an initial text and a value
represented by the caller as its edited form.

```python
from text_post_edit_metrics import analyze_post_edit

result = analyze_post_edit(
    suggestion="Support analysis of research data.",
    final="Support analysis of clinical research data.",
)
```

The comparison direction is:

```text
suggestion → final
```

Final-text length supplies normalized denominators. The package does not prove
that the final value was actually produced by editing the suggestion.

## Standard result

`analyze_post_edit()` returns an immutable `PostEditingResult` containing:

- Translation Edit Rate and raw/bounded TER-derived scores;
- character Levenshtein distance and raw/bounded scores;
- weighted soft-word distance and raw/bounded scores;
- estimated characters saved;
- character and whitespace-token counts.

Raw scores may be negative when edit cost exceeds the final-length baseline.
Bounded scores remain in `[0, 1]`.

## Standard configuration

| Metric | Case behavior | Denominator |
|---|---|---|
| TER | Case-insensitive | Final TER reference length |
| Character distance | Case-sensitive | Final character count |
| Weighted soft-word distance | Case-sensitive | Final whitespace-token count |

All metric inputs use Unicode NFC normalization.

The weighted soft-word measure uses whitespace tokenization, insertion and
deletion cost `1.0`, normalized character-distance substitutions, and no
phrase-shift operation.

## Validation

- Suggestion and final values must be strings.
- An empty suggestion is valid.
- Final text must be nonblank and contain at least one token.
- Invalid types raise `TypeError`.
- Invalid final denominators raise `ValueError`.

## Interpretation

The metrics describe technical textual transformation. They do not directly
measure:

- elapsed time;
- cognitive effort;
- observed keystrokes;
- semantic equivalence;
- satisfaction;
- overall usefulness.

`estimated_characters_saved` is a technical proxy, not observed avoided typing.

## Public API

Use `analyze_post_edit()` for the standard combined calculation.

Lower-level exports support TER, character, soft-word, normalization, token
counting, configurable operation costs, and result classes. Nondefault
lower-level configurations should be documented by the caller.

## Documentation

| Document | Purpose |
|---|---|
| [`docs/methodology.md`](docs/methodology.md) | Authoritative formulas, preprocessing, result fields, and interpretation |
| [`docs/verification.md`](docs/verification.md) | Boundary, differential, coverage, and change-control verification |

## Reproducibility

The package depends on SacreBLEU and RapidFuzz. Compatible major versions are
bounded; exact versions are in the root `uv.lock`.

For archived results, record the Git revision, Python/package versions, metric
configuration, analysis date, and input counts.

## Development

```bash
make test PACKAGE=text-post-edit-metrics
make coverage PACKAGE=text-post-edit-metrics
make check
```

## License

MIT
