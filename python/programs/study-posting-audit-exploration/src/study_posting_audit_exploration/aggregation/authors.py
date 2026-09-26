"""Grouped author and experience summaries."""

from dataclasses import dataclass
import json
import math
from numbers import Real

import pandas as pd

from study_posting_audit_exploration.statistics import describe_numeric

_ALL = "ALL"
_AI = "AI"
_MANUAL = "MANUAL"
_COMPLETE = "COMPLETE"
_INCOMPLETE = "INCOMPLETE"
_ALL_AUTHORS = "ALL_AUTHORS"
_MISSING = "MISSING"

_ADOPTION_GROUPS: tuple[str, ...] = (
    _ALL_AUTHORS,
    "AI_ONLY",
    "MANUAL_ONLY",
    "BOTH_AI_AND_MANUAL",
)
_COMPLETION_GROUPS: tuple[str, ...] = (
    _ALL,
    _COMPLETE,
    _INCOMPLETE,
)
_AUTHORING_MODES: tuple[str, ...] = (
    _ALL,
    _AI,
    _MANUAL,
)

GROUPED_AUTHOR_COLUMNS: tuple[str, ...] = (
    "author_population_name",
    "attempt_completion_group",
    "attempt_authoring_mode",
    "effective_author_role",
    "grouping_dimension_name",
    "grouping_dimension_value",
    "group_values_are_mutually_exclusive",
    "distinct_author_count",
    "population_distinct_author_count",
    "distinct_author_percentage_within_population",
    "distinct_author_count_with_any_ai_attempt",
    "distinct_author_count_with_any_manual_attempt",
    "distinct_author_count_with_both_modes",
    "distinct_author_count_with_completed_attempt",
    "distinct_author_count_with_incomplete_attempt",
    "distinct_named_pi_count",
    "distinct_author_count_classified_as_pi",
)

ATTEMPT_START_EXPERIENCE_COLUMNS: tuple[str, ...] = (
    "author_adoption_group",
    "attempt_completion_group",
    "attempt_authoring_mode",
    "experience_metric_name",
    "experience_metric_unit",
    "author_attempt_count_with_nonmissing_metric",
    "author_attempt_count_missing_metric",
    "minimum_author_attempt_value",
    "percentile_25_author_attempt_value",
    "median_author_attempt_value",
    "average_author_attempt_value",
    "standard_deviation_author_attempt_value",
    "percentile_75_author_attempt_value",
    "percentile_90_author_attempt_value",
    "maximum_author_attempt_value",
    "experience_value_definition",
)

CURRENT_AUTHOR_EXPERIENCE_COLUMNS: tuple[str, ...] = (
    "author_adoption_group",
    "experience_metric_name",
    "experience_metric_unit",
    "author_count_with_nonmissing_metric",
    "author_count_missing_metric",
    "minimum_author_value",
    "percentile_25_author_value",
    "median_author_value",
    "average_author_value",
    "standard_deviation_author_value",
    "percentile_75_author_value",
    "percentile_90_author_value",
    "maximum_author_value",
    "experience_value_definition",
    "author_activity_percentile_bins_json",
)

_CURRENT_EXPERIENCE_METRICS: tuple[
    tuple[str, str, str],
    ...,
] = (
    (
        "total_studies_created_as_of_report_query_count",
        "studies",
        "Total studies created by the author when the report query ran.",
    ),
    (
        "other_study_memberships_as_of_report_query_count",
        "studies",
        "Other study memberships when the report query ran.",
    ),
    (
        "distinct_login_days_as_of_report_query_count",
        "days",
        "Distinct calendar login days available when the report query ran.",
    ),
    (
        "login_history_span_days_as_of_report_query",
        "days",
        "Elapsed days from first to latest login available at query time.",
    ),
)
_AUTHOR_ACTIVITY_BIN_METRICS: tuple[str, ...] = (
    "total_studies_created_as_of_report_query_count",
    "other_study_memberships_as_of_report_query_count",
)
_AUTHOR_ACTIVITY_BIN_SCHEME = "OVERALL_AUTHOR_PERCENTILES_50_75_90"
_AUTHOR_ACTIVITY_UPPER_TAIL_BIN_SEQUENCE = 4


@dataclass(frozen=True, slots=True)
class _AuthorGroupLabels:
    """Labels for one grouped-author population."""

    population_name: str
    completion_group: str
    authoring_mode: str
    effective_role: str
    dimension_name: str
    dimension_value: str
    values_are_mutually_exclusive: bool = True


def _percentage(
    numerator: int,
    denominator: int,
) -> float | None:
    """Return a percentage or ``None`` for an empty denominator."""
    if denominator == 0:
        return None

    return 100.0 * numerator / denominator


def _group_value(value: object) -> str:
    """Return one explicit group value."""
    if value is None or value is pd.NA or value is pd.NaT:
        return _MISSING

    return str(value)


def _author_names(attempts: pd.DataFrame) -> frozenset[str]:
    """Return exact source usernames represented in one attempt set."""
    return frozenset(
        str(value) for value in attempts["attempt_author_user_name"].dropna().unique()
    )


def _author_counts(
    attempts: pd.DataFrame,
) -> dict[str, int]:
    """Return mode, completion, PI, and named-PI counts."""
    if attempts.empty:
        return {
            "distinct_author_count_with_any_ai_attempt": 0,
            "distinct_author_count_with_any_manual_attempt": 0,
            "distinct_author_count_with_both_modes": 0,
            "distinct_author_count_with_completed_attempt": 0,
            "distinct_author_count_with_incomplete_attempt": 0,
            "distinct_named_pi_count": 0,
            "distinct_author_count_classified_as_pi": 0,
        }

    per_author = attempts.groupby(
        "attempt_author_user_name",
        sort=False,
        dropna=False,
    )
    has_ai = per_author["attempt_authoring_mode"].apply(
        lambda values: bool(values.eq(_AI).any())
    )
    has_manual = per_author["attempt_authoring_mode"].apply(
        lambda values: bool(values.eq(_MANUAL).any())
    )
    has_complete = per_author["attempt_completion_group"].apply(
        lambda values: bool(values.eq(_COMPLETE).any())
    )
    has_incomplete = per_author["attempt_completion_group"].apply(
        lambda values: bool(values.eq(_INCOMPLETE).any())
    )
    is_pi = per_author["attempt_author_is_study_pi"].apply(
        lambda values: bool(values.eq(True).any())
    )

    return {
        "distinct_author_count_with_any_ai_attempt": int(has_ai.sum()),
        "distinct_author_count_with_any_manual_attempt": int(has_manual.sum()),
        "distinct_author_count_with_both_modes": int((has_ai & has_manual).sum()),
        "distinct_author_count_with_completed_attempt": int(has_complete.sum()),
        "distinct_author_count_with_incomplete_attempt": int(has_incomplete.sum()),
        "distinct_named_pi_count": int(
            attempts["study_pi_user_name"].dropna().nunique()
        ),
        "distinct_author_count_classified_as_pi": int(is_pi.sum()),
    }


def _summary_row(
    attempts: pd.DataFrame,
    *,
    population_author_names: frozenset[str],
    labels: _AuthorGroupLabels,
) -> dict[str, object]:
    """Return one grouped-author summary row."""
    names = _author_names(attempts)
    author_count = len(names)
    population_count = len(population_author_names)

    return {
        "author_population_name": labels.population_name,
        "attempt_completion_group": labels.completion_group,
        "attempt_authoring_mode": labels.authoring_mode,
        "effective_author_role": labels.effective_role,
        "grouping_dimension_name": labels.dimension_name,
        "grouping_dimension_value": labels.dimension_value,
        "group_values_are_mutually_exclusive": (labels.values_are_mutually_exclusive),
        "distinct_author_count": author_count,
        "population_distinct_author_count": population_count,
        "distinct_author_percentage_within_population": _percentage(
            author_count,
            population_count,
        ),
        **_author_counts(attempts),
    }


def _attempt_population(
    attempts: pd.DataFrame,
    *,
    completion_group: str,
    authoring_mode: str,
) -> pd.DataFrame:
    """Return one attempt subset."""
    population = attempts

    if completion_group != _ALL:
        population = population.loc[
            population["attempt_completion_group"].eq(completion_group)
        ]

    if authoring_mode != _ALL:
        population = population.loc[
            population["attempt_authoring_mode"].eq(authoring_mode)
        ]

    return population


def _base_author_rows(
    attempts: pd.DataFrame,
) -> list[dict[str, object]]:
    """Return all nonempty completion/mode author populations."""
    population_author_names = _author_names(attempts)
    rows: list[dict[str, object]] = []

    for completion_group in _COMPLETION_GROUPS:
        for authoring_mode in _AUTHORING_MODES:
            population = _attempt_population(
                attempts,
                completion_group=completion_group,
                authoring_mode=authoring_mode,
            )

            if population.empty and (
                completion_group != _ALL or authoring_mode != _ALL
            ):
                continue

            rows.append(
                _summary_row(
                    population,
                    population_author_names=population_author_names,
                    labels=_AuthorGroupLabels(
                        population_name=_ALL_AUTHORS,
                        completion_group=completion_group,
                        authoring_mode=authoring_mode,
                        effective_role=_ALL,
                        dimension_name="ALL",
                        dimension_value="ALL",
                    ),
                )
            )

    return rows


def _role_rows(
    attempts: pd.DataFrame,
) -> list[dict[str, object]]:
    """Return effective-role author groups."""
    population_author_names = _author_names(attempts)

    return [
        _summary_row(
            group,
            population_author_names=population_author_names,
            labels=_AuthorGroupLabels(
                population_name=_ALL_AUTHORS,
                completion_group=_ALL,
                authoring_mode=_ALL,
                effective_role=_group_value(role),
                dimension_name="EFFECTIVE_AUTHOR_ROLE",
                dimension_value=_group_value(role),
            ),
        )
        for role, group in attempts.groupby(
            "effective_attempt_author_role",
            sort=True,
            dropna=False,
        )
    ]


def _appointment_rows(
    attempts: pd.DataFrame,
    appointments: pd.DataFrame,
) -> list[dict[str, object]]:
    """Return non-mutually-exclusive author and PI appointment groups."""
    population_author_names = _author_names(attempts)
    rows: list[dict[str, object]] = []
    specs = (
        ("AUTHOR", "appointment_title", "AUTHOR_APPOINTMENT_TITLE"),
        (
            "AUTHOR",
            "appointment_department",
            "AUTHOR_APPOINTMENT_DEPARTMENT",
        ),
        ("AUTHOR", "appointment_school", "AUTHOR_APPOINTMENT_SCHOOL"),
        ("PI", "appointment_title", "PI_APPOINTMENT_TITLE"),
        ("PI", "appointment_department", "PI_APPOINTMENT_DEPARTMENT"),
        ("PI", "appointment_school", "PI_APPOINTMENT_SCHOOL"),
    )

    for source, column_name, dimension_name in specs:
        selected = appointments.loc[appointments["appointment_source"].eq(source)]
        joined = attempts.merge(
            selected[
                [
                    "audit_record_id",
                    column_name,
                ]
            ],
            on="audit_record_id",
            how="inner",
            validate="one_to_many",
        )

        for value, group in joined.groupby(
            column_name,
            sort=True,
            dropna=False,
        ):
            rows.append(
                _summary_row(
                    group.drop_duplicates(subset=["attempt_author_user_name"]),
                    population_author_names=population_author_names,
                    labels=_AuthorGroupLabels(
                        population_name=_ALL_AUTHORS,
                        completion_group=_ALL,
                        authoring_mode=_ALL,
                        effective_role=_ALL,
                        dimension_name=dimension_name,
                        dimension_value=_group_value(value),
                        values_are_mutually_exclusive=False,
                    ),
                )
            )

    return rows


def build_grouped_author_summary(
    attempts: pd.DataFrame,
    *,
    appointments: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return grouped distinct-author summaries."""
    rows = [
        *_base_author_rows(attempts),
        *_role_rows(attempts),
    ]

    if appointments is not None and not appointments.empty:
        rows.extend(
            _appointment_rows(
                attempts,
                appointments,
            )
        )

    return pd.DataFrame.from_records(
        rows,
        columns=list(GROUPED_AUTHOR_COLUMNS),
    )


def _attempt_experience_row(
    attempts: pd.DataFrame,
    *,
    adoption_group: str,
    completion_group: str,
    authoring_mode: str,
) -> dict[str, object]:
    """Return one attempt-start experience distribution."""
    population = attempts

    if adoption_group != _ALL_AUTHORS:
        population = population.loc[
            population["author_adoption_group"].eq(adoption_group)
        ]

    if completion_group != _ALL:
        population = population.loc[
            population["attempt_completion_group"].eq(completion_group)
        ]

    if authoring_mode != _ALL:
        population = population.loc[
            population["attempt_authoring_mode"].eq(authoring_mode)
        ]

    statistics = describe_numeric(
        population["prior_studies_created_before_attempt_start_count"],
        metric_name="prior_studies_created_before_attempt_start_count",
    )

    return {
        "author_adoption_group": adoption_group,
        "attempt_completion_group": completion_group,
        "attempt_authoring_mode": authoring_mode,
        "experience_metric_name": ("prior_studies_created_before_attempt_start_count"),
        "experience_metric_unit": "studies",
        "author_attempt_count_with_nonmissing_metric": (statistics.nonmissing_count),
        "author_attempt_count_missing_metric": statistics.missing_count,
        "minimum_author_attempt_value": statistics.minimum,
        "percentile_25_author_attempt_value": statistics.percentile_25,
        "median_author_attempt_value": statistics.median,
        "average_author_attempt_value": statistics.average,
        "standard_deviation_author_attempt_value": (statistics.standard_deviation),
        "percentile_75_author_attempt_value": statistics.percentile_75,
        "percentile_90_author_attempt_value": statistics.percentile_90,
        "maximum_author_attempt_value": statistics.maximum,
        "experience_value_definition": (
            "Studies created by the attempt author before START_TIME."
        ),
    }


def build_attempt_start_experience_summary(
    attempts: pd.DataFrame,
    authors: pd.DataFrame,
) -> pd.DataFrame:
    """Return attempt-start experience distributions by adoption and mode."""
    attempts_with_adoption = attempts.merge(
        authors[
            [
                "author_user_name",
                "author_adoption_group",
            ]
        ],
        left_on="attempt_author_user_name",
        right_on="author_user_name",
        how="left",
        validate="many_to_one",
    )
    rows = [
        _attempt_experience_row(
            attempts_with_adoption,
            adoption_group=adoption_group,
            completion_group=completion_group,
            authoring_mode=authoring_mode,
        )
        for adoption_group in _ADOPTION_GROUPS
        for completion_group in _COMPLETION_GROUPS
        for authoring_mode in _AUTHORING_MODES
    ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(ATTEMPT_START_EXPERIENCE_COLUMNS),
    )


def _current_experience_row(
    authors: pd.DataFrame,
    *,
    adoption_group: str,
    metric_name: str,
    metric_unit: str,
    definition: str,
) -> dict[str, object]:
    """Return one current author-experience distribution."""
    population = authors

    if adoption_group != _ALL_AUTHORS:
        population = population.loc[
            population["author_adoption_group"].eq(adoption_group)
        ]

    statistics = describe_numeric(
        population[metric_name],
        metric_name=metric_name,
    )

    return {
        "author_adoption_group": adoption_group,
        "experience_metric_name": metric_name,
        "experience_metric_unit": metric_unit,
        "author_count_with_nonmissing_metric": statistics.nonmissing_count,
        "author_count_missing_metric": statistics.missing_count,
        "minimum_author_value": statistics.minimum,
        "percentile_25_author_value": statistics.percentile_25,
        "median_author_value": statistics.median,
        "average_author_value": statistics.average,
        "standard_deviation_author_value": statistics.standard_deviation,
        "percentile_75_author_value": statistics.percentile_75,
        "percentile_90_author_value": statistics.percentile_90,
        "maximum_author_value": statistics.maximum,
        "experience_value_definition": definition,
    }


def _json_number(value: object) -> int | float:
    """Return one finite nonnegative integral count value for JSON."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError("author activity values must be numeric")

    number = float(value)
    if not math.isfinite(number):
        raise ValueError("author activity values must be finite")
    if number < 0:
        raise ValueError("author activity values must be nonnegative")
    if not number.is_integer():
        raise ValueError("author activity values must be integral")

    return int(number)


def _observed_author_activity_values(
    authors: pd.DataFrame,
    metric_name: str,
) -> pd.Series:
    """Return validated observed values for one author activity metric."""
    source = authors[metric_name]
    numeric = pd.to_numeric(source, errors="coerce")
    invalid = source.notna() & numeric.isna()

    if invalid.any():
        raise TypeError(f"{metric_name} contains nonnumeric author activity values")

    observed = numeric.loc[numeric.notna()]
    for value in observed.tolist():
        _json_number(value)

    return observed.astype("float64")


def _author_activity_boundaries(
    authors: pd.DataFrame,
    metric_name: str,
) -> tuple[float, float, float] | None:
    """Return shared overall P50, P75, and P90 boundaries."""
    observed = _observed_author_activity_values(authors, metric_name)
    if observed.empty:
        return None

    return (
        float(observed.quantile(0.50)),
        float(observed.quantile(0.75)),
        float(observed.quantile(0.90)),
    )


def _author_activity_bin_specs(
    boundaries: tuple[float, float, float],
) -> tuple[
    tuple[int, float | None, float | None, bool, bool, str],
    ...,
]:
    """Return deterministic mutually exclusive percentile-bin rules."""
    median, percentile_75, percentile_90 = boundaries
    return (
        (
            1,
            None,
            median,
            False,
            True,
            f"At or below overall median ({median:g})",
        ),
        (
            2,
            median,
            percentile_75,
            False,
            True,
            f"Above median through overall 75th percentile ({percentile_75:g})",
        ),
        (
            3,
            percentile_75,
            percentile_90,
            False,
            True,
            f"Above 75th through overall 90th percentile ({percentile_90:g})",
        ),
        (
            4,
            percentile_90,
            None,
            False,
            False,
            f"Above overall 90th percentile ({percentile_90:g})",
        ),
    )


def _author_activity_bin_contains(
    value: float,
    *,
    sequence: int,
    lower_bound: float | None,
    upper_bound: float | None,
) -> bool:
    """Return whether one observed value belongs to one bin."""
    if sequence == 1:
        return upper_bound is not None and value <= upper_bound
    if sequence in (2, 3):
        return (
            lower_bound is not None
            and upper_bound is not None
            and value > lower_bound
            and value <= upper_bound
        )
    if sequence == _AUTHOR_ACTIVITY_UPPER_TAIL_BIN_SEQUENCE:
        return lower_bound is not None and value > lower_bound

    raise ValueError("unsupported author activity bin sequence")


def _author_activity_bin_rows(
    authors: pd.DataFrame,
    metric_name: str,
) -> list[dict[str, object]]:
    """Return identifier-free aggregate bin rows for one metric."""
    boundaries = _author_activity_boundaries(authors, metric_name)
    if boundaries is None:
        return []

    rows: list[dict[str, object]] = []
    specs = _author_activity_bin_specs(boundaries)

    for adoption_group in _ADOPTION_GROUPS:
        population = authors
        if adoption_group != _ALL_AUTHORS:
            population = population.loc[
                population["author_adoption_group"].eq(adoption_group)
            ]

        observed = _observed_author_activity_values(
            population,
            metric_name,
        )

        denominator = len(observed)
        missing_count = len(population) - denominator
        counts: list[int] = []
        for (
            sequence,
            lower_bound,
            upper_bound,
            _lower_inclusive,
            _upper_inclusive,
            _label,
        ) in specs:
            count = sum(
                _author_activity_bin_contains(
                    float(value),
                    sequence=sequence,
                    lower_bound=lower_bound,
                    upper_bound=upper_bound,
                )
                for value in observed.tolist()
            )
            counts.append(count)

        if sum(counts) != denominator:
            raise ValueError("author activity percentile-bin counts do not reconcile")

        for spec, count in zip(specs, counts, strict=True):
            (
                sequence,
                lower_bound,
                upper_bound,
                lower_inclusive,
                upper_inclusive,
                label,
            ) = spec
            rows.append(
                {
                    "metric_name": metric_name,
                    "author_adoption_group": adoption_group,
                    "bin_sequence": sequence,
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                    "lower_bound_inclusive": lower_inclusive,
                    "upper_bound_inclusive": upper_inclusive,
                    "display_label": label,
                    "author_count": count,
                    "observed_value_denominator": denominator,
                    "author_percentage": (
                        100.0 * count / denominator if denominator > 0 else None
                    ),
                    "missing_author_count": missing_count,
                    "binning_scheme": _AUTHOR_ACTIVITY_BIN_SCHEME,
                }
            )

    return rows


def _author_activity_percentile_bins_json(
    authors: pd.DataFrame,
) -> str:
    """Return canonical identifier-free author activity bin aggregates."""
    records = [
        row
        for metric_name in _AUTHOR_ACTIVITY_BIN_METRICS
        for row in _author_activity_bin_rows(authors, metric_name)
    ]
    return json.dumps(
        records,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def build_current_author_experience_summary(
    authors: pd.DataFrame,
) -> pd.DataFrame:
    """Return query-time author experience and activity distributions."""
    payload = _author_activity_percentile_bins_json(authors)
    rows = [
        {
            **_current_experience_row(
                authors,
                adoption_group=adoption_group,
                metric_name=metric_name,
                metric_unit=metric_unit,
                definition=definition,
            ),
            "author_activity_percentile_bins_json": payload,
        }
        for adoption_group in _ADOPTION_GROUPS
        for metric_name, metric_unit, definition in (_CURRENT_EXPERIENCE_METRICS)
    ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(CURRENT_AUTHOR_EXPERIENCE_COLUMNS),
    )
