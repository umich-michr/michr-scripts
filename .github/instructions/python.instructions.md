---
applyTo: "src/**/*.py"
---

# Source code instructions

## Module template

Every module opens with a NumPy-style docstring stating its layer and its
dependency constraints.

```python
"""Weighted text post-editing metrics.

Domain layer. Pure functions only: no database, filesystem, pandas, or
logging dependencies. All inputs are NFC-normalized before measurement.

See docs/analysis-specification.md section 7 for the formulas.
"""

## Dataclass conventions

Result objects are immutable and slotted:

```python
@dataclass(frozen=True, slots=True)
class TerResult:
    """TER and its effort-saved transformation.

    Attributes
    ----------
    ter_rate
        TER expressed as a proportion. May exceed 1.
    effort_saved_raw
        1 - TER. May be negative.
    effort_saved
        effort_saved_raw bounded to [0, 1] for reporting.
    """

    ter_rate: float
    effort_saved_raw: float
    effort_saved: float
```

Derived values are `@property`, never stored fields, so they cannot drift out ofsync. `flag_accepted`, `flag_changed`, `kept, dropped`, `added`, and `policy_adjusted_effort_saved` are all properties.

## Validation style

Validate at the boundary of a public function, before any calculation. Raisewith the field name and, where available, the record identifier.

```python
if not isinstance(field_name, str) or not field_name.strip():
    raise ValueError("field_name must be a non-empty string")
```

bool must be rejected explicitly where an int is expected, because bool subclasses int:

```python
if not isinstance(value, int) or isinstance(value, bool):
    raise TypeError(f"{field}: must contain integer IDs only")
```

Optional Booleans use type(value) is not bool for the same reason.

## Metric implementation rules

- Normalize with `unicode_nfc_normalize_text` before measuring.
- Reject a zero-length or zero-word final text: the denominator would be zero.
- Return both the raw and the clamped score.
- `_TER` is constructed once at module scope with every argument explicit, forreproducibility. Do not change its configuration.
- `normalized_word_distance` is `@lru_cache`-decorated. Keep it a module-level function taking two str arguments so caching remains effective.
- The soft-word implementation keeps two dynamic-programming rows. Do not replace it with a full matrix; the full matrix exists in tests/helpers/ asthe verification reference.

## Exceptions

This library raises only `TypeError`, `ValueError`, and `InputParseError`, which
subclasses `ValueError`. Callers therefore need no special handling to use it
idiomatically.

Do not introduce an exception hierarchy. Record-level, repository, and
configuration error types belong to consuming programs.

Messages name the field, prefixed where applicable:

```python
raise ValueError(f"{field_name}: final saved text must not be blank")
```

Never catch a bare `Exception`. Never log; raising is how this library reports a
problem.

Include the audit record ID and field name in the message whenever available. Never catch a bare `Exception` in the domain layer.

## Logging

The domain layer does not log. In the application and presentation layers use amodule-level logger and lazy `%s` formatting:

```python
logger = logging.getLogger(__name__)
logger.warning("Record %s failed: %s", record.audit_id, error)
```

Never log selected or final field text above `DEBUG`.

## Purity

Every module in `src/` is pure. None may import `sqlite3`, `oracledb`, `pandas`,
`pathlib`, `os`, `logging`, or call `open`.

Module docstrings state this constraint explicitly, so a reader or agent opening
the file sees it before writing anything:

```python
"""Weighted text post-editing metrics.

Pure functions only: no database, filesystem, pandas, or logging dependencies.
All inputs are NFC-normalized before measurement.

See docs/analysis-specification.md section 7 for the formulas.
"""
```

If a task appears to require I/O, it belongs in a consuming program. Say so.

## Type annotation notes

- Prefer frozenset[int] over set[int] in result objects.
- TypeAlias for repeated shapes, for example
- Suggestions: TypeAlias = dict[str, list[str]].
- Use Protocol for the repository interface, not an abstract base class.
- Return X | None explicitly rather than Optional[X].
Guard imports used only for typing with if TYPE_CHECKING:.
