---
applyTo: "tests/**/*.py"
---

# Test instructions

## Style

New tests are plain functions. Name them after the behavior asserted, not the
function called.

```python
def test_cosmetic_equivalence_does_not_suppress_character_edit_distance():
    match, metrics = compare_selected_text(
        field="title",
        selected="Résumé: Data Analysis",
        final="resume data analysis",
        allow_empty_final=False,
    )

    assert match is MatchType.COSMETIC_EQUIVALENT
    assert metrics is not None
    assert metrics.character_edit_distance > 0
```

Compare enum members with is, not ==.

## Assertions on errors

Always constrain the message:


```python
with pytest.raises(ValueError, match="final saved text must not be blank"):
    ...
```

## Parameterization

Use `pytest.mark.parametrize` with `ids` so a failure names the case:

```python
@pytest.mark.parametrize(
    ("suggestion", "final", "expected"),
    [
        ("data", "data", 0),
        ("data", "date", 1),
        ("", "data", 4),
    ],
    ids=["identical", "one-substitution", "empty-suggestion"],
)
def test_character_distance(suggestion, final, expected):
    result = calculate_character_metrics(suggestion, final)
    assert result.distance == expected
```

## Markers

- @pytest.mark.slow — randomized differential tests. Excluded bymake test-fast.
- @pytest.mark.oracle — needs a live database. Must skip automatically:pytest.mark.skipif(not oracle_configured(), reason="...").
- @pytest.mark.integration — exercises more than one layer.

## Fixtures

Shared fixtures live in tests/conftest.py. Provide a valid_audit_objectsfixture returning the baseline suggested/selected/final triple, so a test canmodify exactly one field to isolate the behavior under test. This mirrors themake_valid_objects helper from the original notebook suite.
Use tmp_path for any file or SQLite database. Never write into the repositorytree, and never rely on a database created by another test.

## Determinism

Seed every random generator explicitly: random.Random(42). pytest-randomlyshuffles test order, so tests must not depend on execution order or on stateleft by another test.

## Floating point

Use pytest.approx. Match the reference implementation to 12 decimal places:

```python
assert optimized == pytest.approx(reference, abs=1e-12)
```

## Data

Never use real study text. Invent synthetic content such as"Participants receive a $50 gift card." Fixture CSV files belong indata/sample/ and must contain only synthetic rows.

## Coverage expectations

metrics.py, text_normalization.py, and field_analysis.py should approachfull statement and branch coverage, including every validation error path. EachMatchType outcome needs at least one direct test.
