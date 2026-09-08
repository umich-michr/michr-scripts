---
applyTo: "**/tests/**/*.py"
---

# Shared test instructions

These conventions apply to tests in every workspace member. Package-scoped
instructions may add domain-specific requirements.

## Style

Use pytest with plain functions and bare `assert`.

```python
def test_identical_text_has_zero_distance() -> None:
    result = calculate_character_metrics("data", "data")

    assert result.distance == 0
```

Use explicit return annotations on test functions:

```python
def test_example() -> None: ...
```

Compare enum members with `is`, not `==`.

## Exceptions

Constrain both type and message:

```python
with pytest.raises(ValueError, match=r"final text must not be blank"):
    ...
```

`match=` is a regular expression. Escape metacharacters such as the dot in
`contact\.email`, or use `re.escape()` for dynamic literal messages.

## Parameterization

Use `pytest.mark.parametrize` with descriptive IDs:

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

Annotate every parametrized argument.

## Floating-point results

Use `pytest.approx`:

```python
assert result.effort_saved == pytest.approx(0.8)
```

For differential algorithms near zero, use an explicit absolute tolerance:

```python
assert optimized == pytest.approx(reference, abs=1e-12)
```

## Randomness and test order

- Seed every generator explicitly, such as `random.Random(42)`.
- Mark expensive randomized tests with `@pytest.mark.slow`.
- Tests must not depend on execution order.
- Tests must not share mutable state.
- `pytest-randomly` may reorder tests.

## Files and external resources

- Unit tests must not access a live network service.
- Use `tmp_path` for filesystem tests.
- Use fake or stub connections for database unit tests.
- Live integration tests must use a marker defined by the owning member and
  skip automatically when their required configuration is unavailable.
- Never require credentials for the default workspace test run.
- Never write generated files into the repository tree.

Do not impose an Oracle-specific marker on every package. A future package that
owns Oracle integration may define its own marker in that member's
`pyproject.toml`.

## Fixtures and data

- Shared fixtures belong in the owning member's `tests/conftest.py`.
- Test data must be synthetic.
- Never use real study content, production identifiers, credentials, or database
  extracts.
- Modify only the fixture fields relevant to the behavior being tested.

## Package boundaries

Test behavior in the package that owns it.

Examples:

- TER, character distance, soft-word distance, and metric normalization belong
  to `michr-text-post-editing`.
- Study field requiredness, classification, compensation, contact, lookup, and
  flattening belong to `study-posting-ai-analysis`.
- A future row-stream package owns database and CSV streaming tests.
- A future reporting program owns orchestration and output tests.

Do not duplicate a complete low-level test suite in a consuming package. Add a
small integration test proving that the consumer uses the dependency correctly.

## Coverage

Each workspace member owns its own pytest and coverage configuration.

Run one member:

```bash
make test PACKAGE=<member-name>
make coverage PACKAGE=<member-name>
```

Run the workspace gate:

```bash
make check
```

Coverage should include meaningful validation and branch behavior. Do not create
artificial states solely to execute defensive guards that the type system or
configuration makes unreachable.
