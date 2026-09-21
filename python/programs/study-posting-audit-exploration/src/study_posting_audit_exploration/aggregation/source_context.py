"""Aggregate successful-generation source context, size, and pathways."""

from dataclasses import dataclass
import math
from typing import cast

import pandas as pd

from study_posting_audit_exploration.derivation.source_context import (
    SourceContextTables,
)
from study_posting_audit_exploration.errors import ExplorationValidationError
from study_posting_audit_exploration.models import SourceContextAnalysisTables
from study_posting_audit_exploration.statistics import describe_numeric

_ALL_SUCCESSFUL = "ALL_SUCCESSFUL_AI_GENERATIONS"
_COMPLETED = "COMPLETED_AI_ATTEMPTS"
_ALL = "ALL"
_MISSING = "MISSING"
_NONE = "NONE"
_QUANTILE_BAND_SCHEME = "ALL_SUCCESSFUL_AI_GENERATION_SOURCE_SIZE_QUARTILES_LINEAR"

SOURCE_CONTEXT_DISTRIBUTION_COLUMNS: tuple[str, ...] = (
    "population_name",
    "summary_dimension_name",
    "summary_dimension_value",
    "population_attempt_count",
    "eligible_attempt_count",
    "category_attempt_count",
    "category_attempt_percentage",
    "attempt_count_with_source_size",
    "attempt_count_missing_source_size",
    "minimum_source_size_chars",
    "percentile_25_source_size_chars",
    "median_source_size_chars",
    "average_source_size_chars",
    "standard_deviation_source_size_chars",
    "percentile_75_source_size_chars",
    "percentile_90_source_size_chars",
    "maximum_source_size_chars",
    "attempt_count_with_latency",
    "attempt_count_missing_latency",
    "minimum_latency_ms",
    "percentile_25_latency_ms",
    "median_latency_ms",
    "average_latency_ms",
    "standard_deviation_latency_ms",
    "percentile_75_latency_ms",
    "percentile_90_latency_ms",
    "maximum_latency_ms",
    "comparable_content_source_attempt_count",
    "matching_content_source_attempt_count",
    "different_content_source_attempt_count",
    "content_source_match_percentage",
    "other_category_attempt_count",
    "other_category_attempt_count_with_nonblank_detail",
    "other_detail_completeness_percentage",
    "both_other_category_attempt_count",
    "both_other_detail_attempt_count",
    "matching_other_detail_attempt_count",
    "other_detail_match_percentage",
    "comparison_normalization_rule",
)

SOURCE_SIZE_LATENCY_COLUMNS: tuple[str, ...] = (
    "population_name",
    "source_size_band_scheme_name",
    "source_size_band_name",
    "source_size_band_sequence",
    "source_size_band_lower_bound_chars",
    "source_size_band_upper_bound_chars",
    "source_size_band_q25_edge_chars",
    "source_size_band_q50_edge_chars",
    "source_size_band_q75_edge_chars",
    "reported_source_group",
    "population_attempt_count_with_source_size",
    "band_attempt_count",
    "band_attempt_percentage",
    "attempt_count_with_latency",
    "attempt_count_missing_latency",
    "minimum_source_size_chars",
    "median_source_size_chars",
    "maximum_source_size_chars",
    "minimum_latency_ms",
    "percentile_25_latency_ms",
    "median_latency_ms",
    "average_latency_ms",
    "standard_deviation_latency_ms",
    "percentile_75_latency_ms",
    "percentile_90_latency_ms",
    "maximum_latency_ms",
)

REPEATED_ATTEMPT_SOURCE_CONSISTENCY_COLUMNS: tuple[str, ...] = (
    "summary_grain",
    "comparison_dimension_name",
    "comparison_category",
    "population_unit_count",
    "eligible_unit_count",
    "category_unit_count",
    "category_unit_percentage",
    "unit_count_with_latency_change",
    "unit_count_missing_latency_change",
    "minimum_latency_change_ms",
    "percentile_25_latency_change_ms",
    "median_latency_change_ms",
    "average_latency_change_ms",
    "standard_deviation_latency_change_ms",
    "percentile_75_latency_change_ms",
    "percentile_90_latency_change_ms",
    "maximum_latency_change_ms",
    "latency_decrease_count",
    "latency_no_change_count",
    "latency_increase_count",
    "median_absolute_source_size_change_chars",
    "source_signature_interpretation",
)

_COMPARISON_RULE = (
    "Trim surrounding whitespace and compare using Unicode casefold; "
    "null and blank remain missing."
)
_SIGNATURE_NOTE = (
    "Equal source size and reported source form an unchanged-source proxy; "
    "they do not prove identical source text."
)


@dataclass(frozen=True, slots=True)
class SourceSizeBandScheme:
    """Quartile-ranked source-size boundaries derived from one population."""

    q25: float | None
    q50: float | None
    q75: float | None
    boundaries: tuple[float, ...]


def _percentage(
    numerator: int,
    denominator: int,
) -> float | None:
    """Return one percentage or ``None`` for an empty denominator."""
    if denominator == 0:
        return None

    return 100.0 * numerator / denominator


def _normalized_text(value: object) -> str | None:
    """Return one normalized nonblank category."""
    if not isinstance(value, str):
        return None

    stripped = value.strip()

    return stripped.casefold() if stripped else None


def _valid_nonnegative_numeric(
    values: pd.Series,
    *,
    metric_name: str,
) -> pd.Series:
    """Return finite nonnegative numeric values while preserving indexes."""
    numeric = pd.to_numeric(values, errors="coerce")
    invalid_finite = numeric.dropna().map(lambda value: not math.isfinite(float(value)))

    if bool(invalid_finite.any()):
        raise ExplorationValidationError(
            f"source-context metric {metric_name!r} contains non-finite values"
        )

    negative_count = int(numeric.dropna().lt(0).sum())

    if negative_count:
        raise ExplorationValidationError(
            f"source-context metric {metric_name!r} contains negative values: "
            f"{negative_count} affected observations"
        )

    return numeric.astype("Float64")


def _population(
    attempts: pd.DataFrame,
    population_name: str,
) -> pd.DataFrame:
    """Return one successful-generation attempt population."""
    if population_name == _ALL_SUCCESSFUL:
        return attempts

    return attempts.loc[attempts["is_completed_ai_attempt"].eq(True)]


def _comparison_counts(
    population: pd.DataFrame,
    *,
    left_column: str,
    right_column: str,
) -> tuple[int, int, int]:
    """Return comparable, matching, and different category counts."""
    pairs = [
        (
            _normalized_text(left),
            _normalized_text(right),
        )
        for left, right in zip(
            population[left_column],
            population[right_column],
            strict=True,
        )
    ]
    comparable = [pair for pair in pairs if pair[0] is not None and pair[1] is not None]
    matching = sum(left == right for left, right in comparable)

    return len(comparable), matching, len(comparable) - matching


def _distribution_row(
    population: pd.DataFrame,
    *,
    population_name: str,
    dimension_name: str,
    dimension_value: str,
    category: pd.DataFrame,
) -> dict[str, object]:
    """Return one source-context distribution row."""
    source_size = describe_numeric(
        _valid_nonnegative_numeric(
            category["source_size_chars"],
            metric_name="source_size_chars",
        ),
        metric_name="source_size_chars",
    )
    latency = describe_numeric(
        _valid_nonnegative_numeric(
            category["latency_ms"],
            metric_name="latency_ms",
        ),
        metric_name="latency_ms",
    )
    comparable, matching, different = _comparison_counts(
        category,
        left_column="study_content_source",
        right_column="llm_inferred_study_content_source",
    )
    reported_other = [
        _normalized_text(value) == "other" for value in category["study_content_source"]
    ]
    inferred_other = [
        _normalized_text(value) == "other"
        for value in category["llm_inferred_study_content_source"]
    ]
    reported_details = [
        _normalized_text(value)
        for value in category["study_content_source_other_value"]
    ]
    inferred_details = [
        _normalized_text(value)
        for value in category["llm_inferred_study_content_source_other_value"]
    ]
    reported_other_count = sum(reported_other)
    reported_other_with_detail = sum(
        is_other and detail is not None
        for is_other, detail in zip(
            reported_other,
            reported_details,
            strict=True,
        )
    )
    inferred_other_count = sum(inferred_other)
    inferred_other_with_detail = sum(
        is_other and detail is not None
        for is_other, detail in zip(
            inferred_other,
            inferred_details,
            strict=True,
        )
    )
    both_other = sum(
        left and right
        for left, right in zip(
            reported_other,
            inferred_other,
            strict=True,
        )
    )
    both_detail_pairs = [
        (reported, inferred)
        for is_reported_other, is_inferred_other, reported, inferred in zip(
            reported_other,
            inferred_other,
            reported_details,
            inferred_details,
            strict=True,
        )
        if is_reported_other
        and is_inferred_other
        and reported is not None
        and inferred is not None
    ]
    matching_other = sum(left == right for left, right in both_detail_pairs)
    category_count = len(category)
    eligible_count = (
        len(population)
        if dimension_name == _ALL
        else int(
            pd.Series(
                [
                    _normalized_text(value)
                    for value in population[
                        {
                            "INPUT_METHOD": "source_type",
                            "REPORTED_CONTENT_SOURCE": ("study_content_source"),
                            "INFERRED_CONTENT_SOURCE": (
                                "llm_inferred_study_content_source"
                            ),
                        }[dimension_name]
                    ]
                ]
            )
            .notna()
            .sum()
        )
    )

    is_population_row = dimension_name == _ALL

    if dimension_name == "INFERRED_CONTENT_SOURCE":
        other_count = inferred_other_count
        other_with_detail = inferred_other_with_detail
    else:
        other_count = reported_other_count
        other_with_detail = reported_other_with_detail

    return {
        "population_name": population_name,
        "summary_dimension_name": dimension_name,
        "summary_dimension_value": dimension_value,
        "population_attempt_count": len(population),
        "eligible_attempt_count": eligible_count,
        "category_attempt_count": category_count,
        "category_attempt_percentage": _percentage(
            category_count,
            eligible_count,
        ),
        "attempt_count_with_source_size": source_size.nonmissing_count,
        "attempt_count_missing_source_size": source_size.missing_count,
        "minimum_source_size_chars": source_size.minimum,
        "percentile_25_source_size_chars": source_size.percentile_25,
        "median_source_size_chars": source_size.median,
        "average_source_size_chars": source_size.average,
        "standard_deviation_source_size_chars": (source_size.standard_deviation),
        "percentile_75_source_size_chars": source_size.percentile_75,
        "percentile_90_source_size_chars": source_size.percentile_90,
        "maximum_source_size_chars": source_size.maximum,
        "attempt_count_with_latency": latency.nonmissing_count,
        "attempt_count_missing_latency": latency.missing_count,
        "minimum_latency_ms": latency.minimum,
        "percentile_25_latency_ms": latency.percentile_25,
        "median_latency_ms": latency.median,
        "average_latency_ms": latency.average,
        "standard_deviation_latency_ms": latency.standard_deviation,
        "percentile_75_latency_ms": latency.percentile_75,
        "percentile_90_latency_ms": latency.percentile_90,
        "maximum_latency_ms": latency.maximum,
        "comparable_content_source_attempt_count": (
            comparable if is_population_row else None
        ),
        "matching_content_source_attempt_count": (
            matching if is_population_row else None
        ),
        "different_content_source_attempt_count": (
            different if is_population_row else None
        ),
        "content_source_match_percentage": (
            _percentage(
                matching,
                comparable,
            )
            if is_population_row
            else None
        ),
        "other_category_attempt_count": (other_count if is_population_row else None),
        "other_category_attempt_count_with_nonblank_detail": (
            other_with_detail if is_population_row else None
        ),
        "other_detail_completeness_percentage": (
            _percentage(
                other_with_detail,
                other_count,
            )
            if is_population_row
            else None
        ),
        "both_other_category_attempt_count": (
            both_other if is_population_row else None
        ),
        "both_other_detail_attempt_count": (
            len(both_detail_pairs) if is_population_row else None
        ),
        "matching_other_detail_attempt_count": (
            matching_other if is_population_row else None
        ),
        "other_detail_match_percentage": (
            _percentage(
                matching_other,
                len(both_detail_pairs),
            )
            if is_population_row
            else None
        ),
        "comparison_normalization_rule": _COMPARISON_RULE,
    }


def _dimension_rows(
    population: pd.DataFrame,
    *,
    population_name: str,
    dimension_name: str,
    column_name: str,
) -> list[dict[str, object]]:
    """Return normalized nonmissing category rows for one dimension."""
    normalized = pd.Series(
        [_normalized_text(value) for value in population[column_name]],
        index=population.index,
        dtype="string",
    )
    return [
        _distribution_row(
            population,
            population_name=population_name,
            dimension_name=dimension_name,
            dimension_value=value,
            category=population.loc[normalized.eq(value)],
        )
        for value in sorted(str(item) for item in normalized.dropna().unique())
    ]


def build_source_context_distribution_summary(
    attempts: pd.DataFrame,
) -> pd.DataFrame:
    """Return source-context summaries for all successful and completed AI attempts."""
    rows: list[dict[str, object]] = []

    for population_name in (
        _ALL_SUCCESSFUL,
        _COMPLETED,
    ):
        population = _population(attempts, population_name)
        rows.append(
            _distribution_row(
                population,
                population_name=population_name,
                dimension_name=_ALL,
                dimension_value=_ALL,
                category=population,
            )
        )

        for dimension_name, column_name in (
            ("INPUT_METHOD", "source_type"),
            ("REPORTED_CONTENT_SOURCE", "study_content_source"),
            (
                "INFERRED_CONTENT_SOURCE",
                "llm_inferred_study_content_source",
            ),
        ):
            rows.extend(
                _dimension_rows(
                    population,
                    population_name=population_name,
                    dimension_name=dimension_name,
                    column_name=column_name,
                )
            )

    return pd.DataFrame.from_records(
        rows,
        columns=list(SOURCE_CONTEXT_DISTRIBUTION_COLUMNS),
    )


def _band_scheme(
    attempts: pd.DataFrame,
) -> SourceSizeBandScheme:
    """Return deterministic quartile-ranked source-size boundaries."""
    values = _valid_nonnegative_numeric(
        attempts["source_size_chars"],
        metric_name="source_size_chars",
    ).dropna()

    if values.empty:
        return SourceSizeBandScheme(
            q25=None,
            q50=None,
            q75=None,
            boundaries=(),
        )

    q25 = float(values.quantile(0.25, interpolation="linear"))
    q50 = float(values.quantile(0.50, interpolation="linear"))
    q75 = float(values.quantile(0.75, interpolation="linear"))

    return SourceSizeBandScheme(
        q25=q25,
        q50=q50,
        q75=q75,
        boundaries=tuple(sorted({q25, q50, q75})),
    )


def _band_sequence(
    value: float,
    scheme: SourceSizeBandScheme,
) -> int:
    """Return a one-based right-closed quantile band sequence."""
    return 1 + sum(value > boundary for boundary in scheme.boundaries)


def _band_name(
    sequence: int,
    band_count: int,
) -> str:
    """Return one stable quantile-ranked source-size band name."""
    return f"Q{sequence}_OF_{band_count}"


def _size_latency_row(
    *,
    population_name: str,
    population_with_size_count: int,
    scheme: SourceSizeBandScheme,
    band_sequence: int,
    band_count: int,
    band: pd.DataFrame,
    source_group: str,
    group: pd.DataFrame,
) -> dict[str, object]:
    """Return one source-size-band latency summary row."""
    source_size = describe_numeric(
        group["_source_size_numeric"],
        metric_name="source_size_chars",
    )
    latency = describe_numeric(
        group["_latency_numeric"],
        metric_name="latency_ms",
    )
    band_size = describe_numeric(
        band["_source_size_numeric"],
        metric_name="source_size_chars",
    )

    return {
        "population_name": population_name,
        "source_size_band_scheme_name": _QUANTILE_BAND_SCHEME,
        "source_size_band_name": _band_name(
            band_sequence,
            band_count,
        ),
        "source_size_band_sequence": band_sequence,
        "source_size_band_lower_bound_chars": band_size.minimum,
        "source_size_band_upper_bound_chars": band_size.maximum,
        "source_size_band_q25_edge_chars": scheme.q25,
        "source_size_band_q50_edge_chars": scheme.q50,
        "source_size_band_q75_edge_chars": scheme.q75,
        "reported_source_group": source_group,
        "population_attempt_count_with_source_size": (population_with_size_count),
        "band_attempt_count": len(group),
        "band_attempt_percentage": _percentage(
            len(group),
            population_with_size_count,
        ),
        "attempt_count_with_latency": latency.nonmissing_count,
        "attempt_count_missing_latency": latency.missing_count,
        "minimum_source_size_chars": source_size.minimum,
        "median_source_size_chars": source_size.median,
        "maximum_source_size_chars": source_size.maximum,
        "minimum_latency_ms": latency.minimum,
        "percentile_25_latency_ms": latency.percentile_25,
        "median_latency_ms": latency.median,
        "average_latency_ms": latency.average,
        "standard_deviation_latency_ms": latency.standard_deviation,
        "percentile_75_latency_ms": latency.percentile_75,
        "percentile_90_latency_ms": latency.percentile_90,
        "maximum_latency_ms": latency.maximum,
    }


def build_source_size_latency_summary(
    attempts: pd.DataFrame,
) -> pd.DataFrame:
    """Return quartile-ranked source-size and latency summaries."""
    scheme = _band_scheme(attempts)
    rows: list[dict[str, object]] = []

    if not scheme.boundaries:
        return pd.DataFrame(columns=list(SOURCE_SIZE_LATENCY_COLUMNS))

    band_count = len(scheme.boundaries) + 1

    for population_name in (
        _ALL_SUCCESSFUL,
        _COMPLETED,
    ):
        population = _population(attempts, population_name).copy()
        population["_source_size_numeric"] = _valid_nonnegative_numeric(
            population["source_size_chars"],
            metric_name="source_size_chars",
        )
        population["_latency_numeric"] = _valid_nonnegative_numeric(
            population["latency_ms"],
            metric_name="latency_ms",
        )
        population = population.loc[population["_source_size_numeric"].notna()].copy()
        population["_band_sequence"] = [
            _band_sequence(
                float(value),
                scheme,
            )
            for value in population["_source_size_numeric"]
        ]
        population["_reported_source_normalized"] = [
            _normalized_text(value) for value in population["study_content_source"]
        ]
        population_count = len(population)

        for sequence, band in population.groupby(
            "_band_sequence",
            sort=True,
            dropna=False,
        ):
            sequence_value = int(cast("int", sequence))
            rows.append(
                _size_latency_row(
                    population_name=population_name,
                    population_with_size_count=population_count,
                    scheme=scheme,
                    band_sequence=sequence_value,
                    band_count=band_count,
                    band=band,
                    source_group=_ALL,
                    group=band,
                )
            )

            source_values = sorted(
                str(value)
                for value in band["_reported_source_normalized"].dropna().unique()
            )

            for source_value in source_values:
                source_group = band.loc[
                    band["_reported_source_normalized"].eq(source_value)
                ]
                rows.append(
                    _size_latency_row(
                        population_name=population_name,
                        population_with_size_count=population_count,
                        scheme=scheme,
                        band_sequence=sequence_value,
                        band_count=band_count,
                        band=band,
                        source_group=source_value,
                        group=source_group,
                    )
                )

    return pd.DataFrame.from_records(
        rows,
        columns=list(SOURCE_SIZE_LATENCY_COLUMNS),
    )


def _latency_summary(
    values: pd.Series,
) -> dict[str, object]:
    """Return stable latency-change summary columns."""
    distribution = describe_numeric(
        values,
        metric_name="latency_change_ms",
    )
    numeric = pd.to_numeric(values, errors="coerce").dropna()

    return {
        "unit_count_with_latency_change": distribution.nonmissing_count,
        "unit_count_missing_latency_change": distribution.missing_count,
        "minimum_latency_change_ms": distribution.minimum,
        "percentile_25_latency_change_ms": distribution.percentile_25,
        "median_latency_change_ms": distribution.median,
        "average_latency_change_ms": distribution.average,
        "standard_deviation_latency_change_ms": (distribution.standard_deviation),
        "percentile_75_latency_change_ms": distribution.percentile_75,
        "percentile_90_latency_change_ms": distribution.percentile_90,
        "maximum_latency_change_ms": distribution.maximum,
        "latency_decrease_count": int(numeric.lt(0).sum()),
        "latency_no_change_count": int(numeric.eq(0).sum()),
        "latency_increase_count": int(numeric.gt(0).sum()),
    }


def _consistency_row(
    population: pd.DataFrame,
    *,
    summary_grain: str,
    dimension_name: str,
    category: str,
    category_mask: pd.Series,
    eligible_mask: pd.Series,
    latency_column: str,
    absolute_size_change_column: str | None = None,
) -> dict[str, object]:
    """Return one repeated-attempt consistency summary row."""
    eligible = population.loc[eligible_mask]
    selected = population.loc[category_mask & eligible_mask]
    absolute_change = (
        None
        if absolute_size_change_column is None
        else describe_numeric(
            selected[absolute_size_change_column],
            metric_name=absolute_size_change_column,
        ).median
    )

    return {
        "summary_grain": summary_grain,
        "comparison_dimension_name": dimension_name,
        "comparison_category": category,
        "population_unit_count": len(population),
        "eligible_unit_count": len(eligible),
        "category_unit_count": len(selected),
        "category_unit_percentage": _percentage(
            len(selected),
            len(eligible),
        ),
        **_latency_summary(selected[latency_column]),
        "median_absolute_source_size_change_chars": absolute_change,
        "source_signature_interpretation": _SIGNATURE_NOTE,
    }


def _comparison_rows(
    population: pd.DataFrame,
    *,
    summary_grain: str,
    dimension_name: str,
    comparison_column: str,
    latency_column: str,
    absolute_size_change_column: str | None = None,
) -> list[dict[str, object]]:
    """Return SAME, CHANGED, and MISSING rows for one comparison."""
    values = population[comparison_column].astype("string")
    comparable = values.isin(
        [
            "SAME",
            "CHANGED",
        ]
    )
    missing = values.eq("MISSING") | values.isna()

    return [
        _consistency_row(
            population,
            summary_grain=summary_grain,
            dimension_name=dimension_name,
            category=category,
            category_mask=(missing if category == "MISSING" else values.eq(category)),
            eligible_mask=(missing if category == "MISSING" else comparable),
            latency_column=latency_column,
            absolute_size_change_column=absolute_size_change_column,
        )
        for category in (
            "SAME",
            "CHANGED",
            "MISSING",
        )
    ]


def _study_any_change_rows(
    pathways: pd.DataFrame,
) -> list[dict[str, object]]:
    """Return study-level changed and unchanged rows."""
    rows: list[dict[str, object]] = []
    eligible = pathways.loc[pathways["preceding_successful_ai_attempt_count"].gt(0)]

    for dimension_name, column_name in (
        ("SOURCE_SIZE", "any_source_size_change"),
        ("REPORTED_CONTENT_SOURCE", "any_reported_source_change"),
        ("INPUT_METHOD", "any_input_method_change"),
        ("SOURCE_SIGNATURE_PROXY", "any_source_signature_change"),
    ):
        changed = eligible[column_name].eq(True)
        for category, mask in (
            ("UNCHANGED", ~changed),
            ("CHANGED", changed),
        ):
            rows.append(
                _consistency_row(
                    eligible,
                    summary_grain="COMPLETED_AI_STUDY",
                    dimension_name=dimension_name,
                    category=category,
                    category_mask=mask,
                    eligible_mask=pd.Series(
                        True,
                        index=eligible.index,
                        dtype="boolean",
                    ),
                    latency_column="first_to_completion_latency_change_ms",
                )
            )

    return rows


def build_repeated_attempt_source_consistency_summary(
    source_context: SourceContextTables,
) -> pd.DataFrame:
    """Return completed-study and transition source-consistency summaries."""
    transitions = source_context.successful_ai_transitions
    pathways = source_context.completed_ai_source_pathways
    completed_path_transition_parts: list[pd.DataFrame] = []

    for _, pathway in pathways.iterrows():
        transition_count = int(pathway["comparable_successful_ai_transition_count"])

        if transition_count == 0:
            continue

        study_transitions = transitions.loc[
            transitions["study_num"].astype("string").eq(str(pathway["study_num"]))
        ].sort_values(
            by="transition_sequence_number",
            kind="stable",
        )

        if len(study_transitions) < transition_count:
            raise ExplorationValidationError(
                "completed AI source pathway transition count exceeds "
                "the available successful-generation transitions"
            )

        completed_path_transition_parts.append(
            study_transitions.iloc[:transition_count]
        )

    completed_path_transitions = (
        pd.concat(
            completed_path_transition_parts,
            ignore_index=True,
        )
        if completed_path_transition_parts
        else transitions.iloc[0:0].copy()
    )
    rows = _study_any_change_rows(pathways)

    for transition_population, grain in (
        (
            transitions,
            "ALL_CONSECUTIVE_SUCCESSFUL_AI_TRANSITION",
        ),
        (
            completed_path_transitions,
            ("COMPLETED_AI_PATH_CONSECUTIVE_SUCCESSFUL_AI_TRANSITION"),
        ),
    ):
        for dimension_name, comparison_column in (
            ("SOURCE_SIZE", "source_size_comparison"),
            (
                "REPORTED_CONTENT_SOURCE",
                "reported_source_comparison",
            ),
            ("INPUT_METHOD", "input_method_comparison"),
            (
                "SOURCE_SIGNATURE_PROXY",
                "source_signature_comparison",
            ),
        ):
            rows.extend(
                _comparison_rows(
                    transition_population,
                    summary_grain=grain,
                    dimension_name=dimension_name,
                    comparison_column=comparison_column,
                    latency_column="latency_change_ms",
                    absolute_size_change_column=(
                        "absolute_source_size_change_chars"
                        if dimension_name == "SOURCE_SIZE"
                        else None
                    ),
                )
            )

    for prefix, grain in (
        ("first_to_completion", "FIRST_SUCCESSFUL_AI_TO_COMPLETION"),
        (
            "preceding_to_completion",
            "PRECEDING_SUCCESSFUL_AI_TO_COMPLETION",
        ),
    ):
        for dimension_name, suffix in (
            ("SOURCE_SIZE", "source_size_comparison"),
            ("REPORTED_CONTENT_SOURCE", "reported_source_comparison"),
            ("INPUT_METHOD", "input_method_comparison"),
            (
                "SOURCE_SIGNATURE_PROXY",
                "source_signature_comparison",
            ),
        ):
            rows.extend(
                _comparison_rows(
                    pathways,
                    summary_grain=grain,
                    dimension_name=dimension_name,
                    comparison_column=f"{prefix}_{suffix}",
                    latency_column=f"{prefix}_latency_change_ms",
                    absolute_size_change_column=None,
                )
            )

    return pd.DataFrame.from_records(
        rows,
        columns=list(REPEATED_ATTEMPT_SOURCE_CONSISTENCY_COLUMNS),
    )


def build_source_context_analysis_tables(
    source_context: SourceContextTables,
) -> SourceContextAnalysisTables:
    """Return all identifier-free source-context aggregate tables."""
    attempts = source_context.successful_ai_generations

    return SourceContextAnalysisTables(
        source_context_distribution_summary=(
            build_source_context_distribution_summary(attempts)
        ),
        source_size_latency_summary=(build_source_size_latency_summary(attempts)),
        repeated_attempt_source_consistency_summary=(
            build_repeated_attempt_source_consistency_summary(source_context)
        ),
    )
