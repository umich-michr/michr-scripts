"""Final-text readability target and metric summaries."""

import pandas as pd

from study_posting_audit_exploration.input_contracts import (
    READABILITY_FLOAT_COLUMNS,
    READABILITY_INTEGER_COLUMNS,
)
from study_posting_audit_exploration.statistics import describe_numeric

_GRADE_MEASURES: tuple[str, ...] = (
    "flesch_kincaid_grade",
    "automated_readability_index",
    "coleman_liau_index",
    "gunning_fog",
)

_FINAL_METRICS: tuple[tuple[str, str], ...] = (
    *(
        (metric_name, "score")
        for metric_name in READABILITY_FLOAT_COLUMNS
        if metric_name != "estimated_reading_time_seconds"
    ),
    ("estimated_reading_time_seconds", "seconds"),
    *(
        (metric_name, "count")
        for metric_name in READABILITY_INTEGER_COLUMNS
        if metric_name not in {"record_id", "suggestion_index"}
    ),
)

_FIELD_READABILITY_TARGET_COLUMNS: tuple[str, ...] = (
    "attempt_authoring_mode",
    "field_name",
    "readability_measure_name",
    "final_text_attempt_count",
    "attempt_count_at_or_below_grade_6",
    "attempt_count_above_grade_6_through_grade_8",
    "attempt_count_above_grade_8_through_grade_10",
    "attempt_count_above_grade_10",
    "percentage_at_or_below_grade_8",
    "short_text_readability_caution",
    "target_interpretation_note",
)

_FINAL_TEXT_METRIC_COLUMNS: tuple[str, ...] = (
    "attempt_authoring_mode",
    "field_name",
    "compensation_selected_suggestion_kind",
    "metric_name",
    "metric_unit",
    "final_text_attempt_count_with_metric",
    "final_text_attempt_count_missing_or_blank",
    "minimum_final_metric_value",
    "percentile_25_final_metric_value",
    "median_final_metric_value",
    "average_final_metric_value",
    "standard_deviation_final_metric_value",
    "percentile_75_final_metric_value",
    "percentile_90_final_metric_value",
    "maximum_final_metric_value",
)

_TARGET_INTERPRETATION_NOTE = (
    "Grade-level formulas are indicators only and do not establish "
    "comprehension, accuracy, cultural appropriateness, layout quality, "
    "accessibility, or ethical adequacy."
)


def _percentage(
    numerator: int,
    denominator: int,
) -> float | None:
    """Return a percentage or ``None`` for an empty denominator."""
    if denominator == 0:
        return None

    return 100.0 * numerator / denominator


def _final_rows(readability: pd.DataFrame) -> pd.DataFrame:
    """Return observed nonblank final readability rows."""
    return readability.loc[readability["text_role"].eq("FINAL")].copy()


def _target_summary_row(
    group: pd.DataFrame,
) -> dict[str, object]:
    """Return one authoring-mode, field, and grade-measure target summary."""
    measure_name = str(group["readability_measure_name"].iloc[0])
    values = group["readability_measure_value"]
    final_count = len(group)
    at_or_below_6 = int(values.le(6.0).sum())
    above_6_through_8 = int((values.gt(6.0) & values.le(8.0)).sum())
    above_8_through_10 = int((values.gt(8.0) & values.le(10.0)).sum())
    above_10 = int(values.gt(10.0).sum())

    return {
        "attempt_authoring_mode": str(group["attempt_authoring_mode"].iloc[0]),
        "field_name": str(group["field_name"].iloc[0]),
        "readability_measure_name": measure_name,
        "final_text_attempt_count": final_count,
        "attempt_count_at_or_below_grade_6": at_or_below_6,
        "attempt_count_above_grade_6_through_grade_8": (above_6_through_8),
        "attempt_count_above_grade_8_through_grade_10": (above_8_through_10),
        "attempt_count_above_grade_10": above_10,
        "percentage_at_or_below_grade_8": _percentage(
            at_or_below_6 + above_6_through_8,
            final_count,
        ),
        "short_text_readability_caution": (str(group["field_name"].iloc[0]) == "title"),
        "target_interpretation_note": _TARGET_INTERPRETATION_NOTE,
    }


def build_field_readability_target_summary(
    readability: pd.DataFrame,
) -> pd.DataFrame:
    """Return final grade-target bands for AI and manual attempts."""
    final = _final_rows(readability)
    rows_long: list[dict[str, object]] = []

    for measure_name in _GRADE_MEASURES:
        rows_long.extend(
            {
                "attempt_authoring_mode": row["attempt_type"],
                "field_name": row["field_name"],
                "readability_measure_name": measure_name,
                "readability_measure_value": row[measure_name],
            }
            for row in final.to_dict(orient="records")
        )

    long_frame = pd.DataFrame.from_records(
        rows_long,
        columns=[
            "attempt_authoring_mode",
            "field_name",
            "readability_measure_name",
            "readability_measure_value",
        ],
    )
    rows = [
        _target_summary_row(group)
        for _, group in long_frame.groupby(
            [
                "attempt_authoring_mode",
                "field_name",
                "readability_measure_name",
            ],
            sort=True,
            dropna=False,
        )
    ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(_FIELD_READABILITY_TARGET_COLUMNS),
    )


def _final_with_compensation_kind(
    readability: pd.DataFrame,
    completed_ai_fields: pd.DataFrame,
) -> pd.DataFrame:
    """Attach selected compensation suggestion kind to final rows."""
    final = _final_rows(readability).rename(
        columns={"attempt_type": "attempt_authoring_mode"}
    )
    compensation_context = completed_ai_fields.loc[
        completed_ai_fields["field_name"].eq("compensation"),
        [
            "audit_record_id",
            "field_name",
            "picked_kind",
        ],
    ].rename(
        columns={
            "audit_record_id": "record_id",
            "picked_kind": "compensation_selected_suggestion_kind",
        }
    )

    return final.merge(
        compensation_context,
        on=[
            "record_id",
            "field_name",
        ],
        how="left",
        validate="one_to_one",
    )


def _metric_summary_row(
    group: pd.DataFrame,
) -> dict[str, object]:
    """Return one final-text metric distribution."""
    metric_name = str(group["metric_name"].iloc[0])
    statistics = describe_numeric(
        group["metric_value"],
        metric_name=metric_name,
    )
    compensation_kind = group["compensation_selected_suggestion_kind"].iloc[0]

    return {
        "attempt_authoring_mode": str(group["attempt_authoring_mode"].iloc[0]),
        "field_name": str(group["field_name"].iloc[0]),
        "compensation_selected_suggestion_kind": (
            None if pd.isna(compensation_kind) else str(compensation_kind)
        ),
        "metric_name": metric_name,
        "metric_unit": str(group["metric_unit"].iloc[0]),
        "final_text_attempt_count_with_metric": (statistics.nonmissing_count),
        "final_text_attempt_count_missing_or_blank": None,
        "minimum_final_metric_value": statistics.minimum,
        "percentile_25_final_metric_value": statistics.percentile_25,
        "median_final_metric_value": statistics.median,
        "average_final_metric_value": statistics.average,
        "standard_deviation_final_metric_value": (statistics.standard_deviation),
        "percentile_75_final_metric_value": statistics.percentile_75,
        "percentile_90_final_metric_value": statistics.percentile_90,
        "maximum_final_metric_value": statistics.maximum,
    }


def build_final_text_metric_summary(
    readability: pd.DataFrame,
    completed_ai_fields: pd.DataFrame,
) -> pd.DataFrame:
    """Return observed nonblank final readability and length distributions."""
    final = _final_with_compensation_kind(
        readability,
        completed_ai_fields,
    )
    rows_long: list[dict[str, object]] = []

    for metric_name, metric_unit in _FINAL_METRICS:
        rows_long.extend(
            {
                "attempt_authoring_mode": row["attempt_authoring_mode"],
                "field_name": row["field_name"],
                "compensation_selected_suggestion_kind": row[
                    "compensation_selected_suggestion_kind"
                ],
                "metric_name": metric_name,
                "metric_unit": metric_unit,
                "metric_value": row[metric_name],
            }
            for row in final.to_dict(orient="records")
        )

    long_frame = pd.DataFrame.from_records(
        rows_long,
        columns=[
            "attempt_authoring_mode",
            "field_name",
            "compensation_selected_suggestion_kind",
            "metric_name",
            "metric_unit",
            "metric_value",
        ],
    )
    rows = [
        _metric_summary_row(group)
        for _, group in long_frame.groupby(
            [
                "attempt_authoring_mode",
                "field_name",
                "compensation_selected_suggestion_kind",
                "metric_name",
                "metric_unit",
            ],
            sort=True,
            dropna=False,
        )
    ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(_FINAL_TEXT_METRIC_COLUMNS),
    )
