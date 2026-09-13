import math

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationValidationError,
    describe_numeric,
)


def test_describe_numeric_returns_explicit_distribution() -> None:
    values = pd.Series([1, 2, 3, 4, None], dtype="Float64")

    result = describe_numeric(
        values,
        metric_name="synthetic_measure",
    )

    assert result.nonmissing_count == 4
    assert result.missing_count == 1
    assert result.minimum == pytest.approx(1.0)
    assert result.percentile_25 == pytest.approx(1.75)
    assert result.median == pytest.approx(2.5)
    assert result.average == pytest.approx(2.5)
    assert result.standard_deviation == pytest.approx(1.2909944487358056)
    assert result.percentile_75 == pytest.approx(3.25)
    assert result.percentile_90 == pytest.approx(3.7)
    assert result.maximum == pytest.approx(4.0)


def test_describe_numeric_counts_nonnumeric_values_as_missing() -> None:
    values = pd.Series(["1", "not numeric", None], dtype="string")

    result = describe_numeric(
        values,
        metric_name="synthetic_measure",
    )

    assert result.nonmissing_count == 1
    assert result.missing_count == 2
    assert result.minimum == pytest.approx(1.0)
    assert result.standard_deviation is None


def test_describe_numeric_returns_empty_statistics() -> None:
    values = pd.Series([None, None], dtype="Float64")

    result = describe_numeric(
        values,
        metric_name="synthetic_measure",
    )

    assert result.nonmissing_count == 0
    assert result.missing_count == 2
    assert result.minimum is None
    assert result.percentile_25 is None
    assert result.median is None
    assert result.average is None
    assert result.standard_deviation is None
    assert result.percentile_75 is None
    assert result.percentile_90 is None
    assert result.maximum is None


@pytest.mark.parametrize("value", [math.inf, -math.inf])
def test_describe_numeric_rejects_nonfinite_values(value: float) -> None:
    values = pd.Series([1.0, value], dtype="Float64")

    with pytest.raises(
        ExplorationValidationError,
        match="contains non-finite values",
    ):
        describe_numeric(
            values,
            metric_name="synthetic_measure",
        )
