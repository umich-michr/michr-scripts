"""Human-readable definitions for published aggregate analysis columns."""

from dataclasses import asdict, dataclass
from typing import Final

import pandas as pd

METRIC_DEFINITION_COLUMNS: tuple[str, ...] = (
    "metric_name",
    "plain_language_label",
    "analytical_unit",
    "calculation_definition",
    "numerator_definition",
    "denominator_definition",
    "measurement_unit",
    "value_selection_rule",
    "missing_value_treatment",
    "source_file_names",
    "source_column_names",
    "interpretation_notes",
)

AGGREGATE_FILE_ORDER: tuple[str, ...] = (
    "quality/data_quality_summary.csv",
    "overview/overview_summary.csv",
    "overview/study_attempt_history_summary.csv",
    "overview/author_handoff_summary.csv",
    "overview/repeated_attempt_source_consistency_summary.csv",
    "attempts/grouped_attempt_summary.csv",
    "attempts/source_context_distribution_summary.csv",
    "attempts/source_size_latency_summary.csv",
    "attempts/content_source_concordance_summary.csv",
    "attempts/content_source_concordance_matrix.csv",
    "studies/completed_study_author_context_summary.csv",
    "studies/grouped_study_summary.csv",
    "authors/grouped_author_summary.csv",
    "authors/attempt_start_experience_summary.csv",
    "authors/current_author_experience_summary.csv",
    "fields/field_adoption_editing_summary.csv",
    "fields/nontext_field_adoption_summary.csv",
    "fields/suggestion_selection_summary.csv",
    "fields/compensation_analysis_summary.csv",
    "readability/selected_vs_unselected_readability_summary.csv",
    "readability/field_readability_change_summary.csv",
    "readability/field_readability_target_summary.csv",
    "readability/field_edit_readability_cross_summary.csv",
    "readability/final_text_metric_summary.csv",
)

_PERCENTAGE_NOTE: Final = (
    "Percentages are descriptive. A missing value means the denominator was zero."
)
_READABILITY_NOTE: Final = (
    "Readability formulas are indicators only and do not establish "
    "comprehension, accuracy, accessibility, usefulness, or ethical adequacy."
)
_EDIT_NOTE: Final = (
    "Edit-intensity categories use the exploratory configured threshold "
    "scheme and are not literature-standard classifications."
)
_VALUE_SELECTION_RULE: Final = (
    "Use the population and grouping dimensions published in the same aggregate row."
)

_STATISTIC_DEFINITIONS: tuple[tuple[str, str], ...] = (
    (
        "standard_deviation_",
        "Sample standard deviation of observed nonmissing values.",
    ),
    (
        "percentile_25_",
        "Twenty-fifth percentile of observed nonmissing values.",
    ),
    (
        "percentile_75_",
        "Seventy-fifth percentile of observed nonmissing values.",
    ),
    (
        "percentile_90_",
        "Ninetieth percentile of observed nonmissing values.",
    ),
    (
        "minimum_",
        "Minimum observed nonmissing value in the row population.",
    ),
    (
        "median_",
        "Median of observed nonmissing values.",
    ),
    (
        "average_",
        "Arithmetic mean of observed nonmissing values.",
    ),
    (
        "maximum_",
        "Maximum observed nonmissing value in the row population.",
    ),
)

_UNIT_RULES: tuple[tuple[str, str], ...] = (
    ("percentage", "percent"),
    ("minutes", "minutes"),
    ("seconds", "seconds"),
    ("ratio", "ratio"),
    ("rate", "ratio"),
    ("similarity", "score"),
    ("readability", "source metric unit"),
    ("count", "count"),
)

_FILE_ANALYTICAL_UNITS: tuple[tuple[str, str], ...] = (
    ("quality/", "quality check"),
    ("overview/overview_summary", "overview metric"),
    ("overview/study_attempt", "study"),
    ("overview/author_handoff", "study"),
    ("attempts/", "attempt"),
    ("studies/", "study"),
    ("authors/attempt_start", "author attempt"),
    ("authors/", "author"),
    ("fields/suggestion", "suggestion instance"),
    ("fields/", "completed AI attempt and field"),
    (
        "readability/selected",
        "completed AI attempt, field, and readability measure",
    ),
    (
        "readability/",
        "text instance or selected-final readability pair",
    ),
)

_DENOMINATOR_RULES: tuple[tuple[str, str], ...] = (
    (
        "among_comparable",
        "AI attempts with both comparison values present.",
    ),
    (
        "among_attempts_with_offer",
        "Completed AI attempts with at least one offered suggestion.",
    ),
    (
        "among_selected",
        "Attempts or suggestions with a selected AI value.",
    ),
    (
        "within_reported_source",
        "Comparable AI attempts with the same reported source.",
    ),
    (
        "within_edit_intensity_category",
        "Completed AI attempts in the same field and edit-intensity category.",
    ),
    (
        "category_",
        "Eligible unit count published in the same aggregate row.",
    ),
    (
        "band_",
        (
            "Successful AI generation attempts with nonmissing source size "
            "in the same population."
        ),
    ),
    (
        "within_population",
        "Population count published in the same aggregate row.",
    ),
    (
        "at_or_below_grade_8",
        "Observed nonblank final texts with the same mode, field, and formula.",
    ),
)


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    """One stable human-readable aggregate-column definition."""

    metric_name: str
    plain_language_label: str
    analytical_unit: str
    calculation_definition: str
    numerator_definition: str
    denominator_definition: str
    measurement_unit: str
    value_selection_rule: str
    missing_value_treatment: str
    source_file_names: str
    source_column_names: str
    interpretation_notes: str


def _first_matching_value(
    value: str,
    rules: tuple[tuple[str, str], ...],
    *,
    default: str,
    prefix_match: bool = False,
) -> str:
    """Return the first rule value whose token matches."""
    matches = (
        value.startswith(token) if prefix_match else token in value
        for token, _ in rules
    )

    return next(
        (
            rule_value
            for matches_rule, (_, rule_value) in zip(
                matches,
                rules,
                strict=True,
            )
            if matches_rule
        ),
        default,
    )


def _label(metric_name: str) -> str:
    """Return a readable fallback label for one snake-case column."""
    return metric_name.replace("_", " ").capitalize()


def _unit(metric_name: str) -> str:
    """Return the measurement unit implied by one aggregate-column name."""
    return _first_matching_value(
        metric_name,
        _UNIT_RULES,
        default="category or text",
    )


def _analytical_unit(file_name: str) -> str:
    """Return the grain represented by one aggregate file."""
    return _first_matching_value(
        file_name,
        _FILE_ANALYTICAL_UNITS,
        default="aggregate row",
        prefix_match=True,
    )


def _definition(metric_name: str) -> str:
    """Return a calculation definition from the stable column vocabulary."""
    statistic_definition = _first_matching_value(
        metric_name,
        _STATISTIC_DEFINITIONS,
        default="",
        prefix_match=True,
    )

    if statistic_definition:
        return statistic_definition

    if "percentage" in metric_name:
        return "One hundred times the documented numerator divided by its denominator."

    if metric_name.startswith("total_"):
        return "Sum of the named count across the row population."

    if metric_name.endswith("_count") or "_count_" in metric_name:
        return (
            "Count of rows or distinct analytical units satisfying the "
            "column condition."
        )

    suffix_definitions = {
        "_name": "Dimension, category, or metric name identifying the row.",
        "_value": "Dimension, category, or metric value identifying the row.",
        "_rule": "Human-readable rule used by the analysis.",
        "_definition": "Human-readable definition used by the analysis.",
        "_note": "Interpretation guidance published with the aggregate row.",
        "_caution": "Interpretation caution published with the aggregate row.",
    }

    return next(
        (
            definition
            for suffix, definition in suffix_definitions.items()
            if metric_name.endswith(suffix)
        ),
        ("Published aggregate value described by the column name and source table."),
    )


def _numerator(metric_name: str) -> str:
    """Return numerator guidance for one aggregate column."""
    if "percentage" in metric_name:
        return "Count represented by the corresponding condition-specific count column."

    return "Not applicable."


def _denominator(metric_name: str) -> str:
    """Return denominator guidance for one aggregate column."""
    if "percentage" not in metric_name:
        return "Not applicable."

    return _first_matching_value(
        metric_name,
        _DENOMINATOR_RULES,
        default=(
            "The explicit population or paired-observation count for the same row."
        ),
    )


def _is_distribution_column(metric_name: str) -> bool:
    """Return whether one column contains a descriptive statistic."""
    return any(metric_name.startswith(prefix) for prefix, _ in _STATISTIC_DEFINITIONS)


def _missing_treatment(metric_name: str) -> str:
    """Return missing-value treatment for one aggregate column."""
    if metric_name == "final_text_attempt_count_missing_or_blank":
        return (
            "Unavailable under the normalized input contract and always "
            "published as missing."
        )

    if "percentage" in metric_name:
        return "Published as missing when the denominator is zero."

    if _is_distribution_column(metric_name):
        return (
            "Missing source observations are excluded; the result is "
            "missing when no usable observations exist."
        )

    return "Missing values follow the source aggregate table's policy."


def _interpretation(metric_name: str) -> str:
    """Return interpretation guidance for one aggregate column."""
    notes = [
        note
        for applies, note in (
            ("percentage" in metric_name, _PERCENTAGE_NOTE),
            (
                "readability" in metric_name or "grade" in metric_name,
                _READABILITY_NOTE,
            ),
            (
                "edit_intensity" in metric_name or "edit_ratio" in metric_name,
                _EDIT_NOTE,
            ),
            (
                "appointment" in metric_name,
                (
                    "Appointment groups may overlap and are not intended "
                    "to sum to 100 percent."
                ),
            ),
            (
                "source_signature" in metric_name,
                (
                    "Equal source size and reported source are an "
                    "unchanged-source proxy, not proof of identical text."
                ),
            ),
            (
                "latency" in metric_name,
                (
                    "Latency is descriptive and may reflect source size, "
                    "service conditions, and other unmeasured factors."
                ),
            ),
        )
        if applies
    ]

    return " ".join(notes)


def _metric_definition(
    *,
    file_name: str,
    column_name: str,
) -> MetricDefinition:
    """Return one aggregate-column definition."""
    return MetricDefinition(
        metric_name=column_name,
        plain_language_label=_label(column_name),
        analytical_unit=_analytical_unit(file_name),
        calculation_definition=_definition(column_name),
        numerator_definition=_numerator(column_name),
        denominator_definition=_denominator(column_name),
        measurement_unit=_unit(column_name),
        value_selection_rule=_VALUE_SELECTION_RULE,
        missing_value_treatment=_missing_treatment(column_name),
        source_file_names=file_name,
        source_column_names=column_name,
        interpretation_notes=_interpretation(column_name),
    )


def _definition_rows(
    aggregate_columns: dict[str, tuple[str, ...]],
) -> list[MetricDefinition]:
    """Return one deterministic definition for every aggregate column."""
    rows: list[MetricDefinition] = []

    for file_name in AGGREGATE_FILE_ORDER:
        rows.extend(
            _metric_definition(
                file_name=file_name,
                column_name=column_name,
            )
            for column_name in aggregate_columns[file_name]
        )

    return rows


def build_metric_definitions(
    aggregate_columns: dict[str, tuple[str, ...]],
) -> pd.DataFrame:
    """Return definitions covering every current aggregate output column."""
    rows = _definition_rows(aggregate_columns)

    return pd.DataFrame.from_records(
        [asdict(row) for row in rows],
        columns=list(METRIC_DEFINITION_COLUMNS),
    )
