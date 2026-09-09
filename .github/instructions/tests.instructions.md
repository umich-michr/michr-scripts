---
applyTo: "**/tests/**/*.py"
---

# Shared test instructions

These rules apply across Python workspace members. Package-specific instructions
may add domain requirements.

## Style

Use pytest, plain functions, complete annotations, and bare assertions:

```python
def test_identical_text_has_zero_distance() -> None:
    result = calculate_character_metrics("data", "data")

    assert result.distance == 0
```

Compare enum members with `is`.

## Exceptions

Assert both type and message:

```python
with pytest.raises(ValueError, match=r"final text must not be blank"):
    ...
```

`match=` is a regular expression. Escape metacharacters such as the dot in
`contact\.email`, or use `re.escape()` for dynamic literal messages.

## Parameterization

Use descriptive IDs and annotate all parameters:

```python
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", True),
        ("text", False),
    ],
    ids=["empty", "nonempty"],
)
def test_is_blank(value: str, expected: bool) -> None:
    assert is_blank(value) is expected
```

## Floating-point results

Use `pytest.approx`:

```python
assert result.effort_saved == pytest.approx(0.8)
```

For differential calculations near zero, specify an absolute tolerance:

```python
assert optimized == pytest.approx(reference, abs=1e-12)
```

## Determinism

- Seed random generators explicitly.
- Mark expensive randomized tests `@pytest.mark.slow`.
- Do not depend on test order or shared mutable state.
- Assume `pytest-randomly` may reorder tests.

## Files and external services

- Unit tests must not contact live services.
- Use `tmp_path` for filesystem tests.
- Use fakes or stubs for database unit tests.
- Live integration tests require a member-defined marker and must skip when
  configuration is unavailable.
- The default workspace test run must not require credentials.
- Never write generated test output into the repository tree.

Do not impose database-specific markers on unrelated members.

## Fixtures and data

- Shared fixtures belong in the owning member's `tests/conftest.py`.
- Use synthetic data only.
- Never include real study text, production identifiers, credentials, or
  database exports.
- Modify only fixture fields relevant to the tested behavior.

## Test behavior in its owning member

Examples:

- text metrics and normalization belong to `text-post-edit-metrics`;
- study field policy, contact, compensation, lookup, parsing, and flattening
  belong to `study-posting-ai-analysis`;
- future row-source packages own database and CSV streaming tests;
- programs own orchestration and output tests.

Do not duplicate a dependency's full low-level test suite in a consumer. Add
small integration tests proving that the consumer uses the dependency correctly.

## Running tests

One member:

```bash
make test PACKAGE=<member-name>
make coverage PACKAGE=<member-name>
```

Whole workspace:

```bash
make check
```

Test meaningful boundary and validation behavior. Do not construct artificial
states solely to execute defensive guards that current types or configuration
make unreachable.
