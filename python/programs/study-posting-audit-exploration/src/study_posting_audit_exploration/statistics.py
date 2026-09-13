"""Reusable descriptive statistics for exploratory summaries."""

import math
from typing import Literal

import pandas as pd

from study_posting_audit_exploration.errors import ExplorationValidationError
from study_posting_audit_exploration.models import DescriptiveStatistics

type QuantileInterpolation = Literal[
    "linear",
    "lower",
    "higher",
    "midpoint",
    "nearest",
]

_QUANTILE_INTERPOLATION: QuantileInterpolation = "linear"
_MINIMUM_SAMPLE_STANDARD_DEVIATION_COUNT = 2


def _finite_numeric_values(
    values: pd.Series,
    *,
    metric_name: str,
) -> pd.Series:
    """Return non-null finite numeric values as float64."""
    numeric = pd.to_numeric(
        values,
        errors="coerce",
    )
    nonmissing = numeric.dropna().astype("float64")
    invalid_count = int(
        nonmissing.map(
            lambda value: not math.isfinite(float(value)),
        ).sum()
    )

    if invalid_count:
        raise ExplorationValidationError(
            f"metric {metric_name!r} contains non-finite values: "
            f"{invalid_count} affected observations"
        )

    return nonmissing


def describe_numeric(
    values: pd.Series,
    *,
    metric_name: str,
) -> DescriptiveStatistics:
    """Return explicit descriptive statistics for one numeric series.

    Null and nonnumeric values count as missing. Standard deviation uses the
    sample definition with one degree of freedom. A single observation has an
    undefined standard deviation and therefore returns ``None``.
    """
    nonmissing = _finite_numeric_values(
        values,
        metric_name=metric_name,
    )
    missing_count = len(values) - len(nonmissing)

    if nonmissing.empty:
        return DescriptiveStatistics(
            nonmissing_count=0,
            missing_count=missing_count,
            minimum=None,
            percentile_25=None,
            median=None,
            average=None,
            standard_deviation=None,
            percentile_75=None,
            percentile_90=None,
            maximum=None,
        )

    standard_deviation = (
        None
        if len(nonmissing) < _MINIMUM_SAMPLE_STANDARD_DEVIATION_COUNT
        else float(nonmissing.std(ddof=1))
    )

    return DescriptiveStatistics(
        nonmissing_count=len(nonmissing),
        missing_count=missing_count,
        minimum=float(nonmissing.min()),
        percentile_25=float(
            nonmissing.quantile(
                0.25,
                interpolation=_QUANTILE_INTERPOLATION,
            )
        ),
        median=float(nonmissing.median()),
        average=float(nonmissing.mean()),
        standard_deviation=standard_deviation,
        percentile_75=float(
            nonmissing.quantile(
                0.75,
                interpolation=_QUANTILE_INTERPOLATION,
            )
        ),
        percentile_90=float(
            nonmissing.quantile(
                0.90,
                interpolation=_QUANTILE_INTERPOLATION,
            )
        ),
        maximum=float(nonmissing.max()),
    )
