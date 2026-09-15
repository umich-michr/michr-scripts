"""Bird's-eye attempt, study, author, PI, and pathway counts."""

import pandas as pd

_COMPLETE = "COMPLETE"
_INCOMPLETE = "INCOMPLETE"
_AI = "AI"
_MANUAL = "MANUAL"
_AI_ERROR = "AI_ERROR"
_AI_ERROR_WITHOUT_STACK_TRACE = "AI_ERROR_WITHOUT_STACK_TRACE"
_USER_DROPPED = "USER_DROPPED"

OVERVIEW_COLUMNS: tuple[str, ...] = (
    "overview_section_name",
    "overview_metric_name",
    "overview_metric_label",
    "metric_count",
    "metric_denominator_count",
    "metric_percentage",
    "metric_denominator_definition",
    "metric_notes",
)


def _percentage(
    numerator: int,
    denominator: int,
) -> float | None:
    """Return a percentage or ``None`` for an empty denominator."""
    if denominator == 0:
        return None

    return 100.0 * numerator / denominator


def _row(
    *,
    section: str,
    metric_name: str,
    label: str,
    count: int,
    denominator_count: int,
    denominator_definition: str,
    notes: str = "",
) -> dict[str, object]:
    """Return one explicit overview metric row."""
    return {
        "overview_section_name": section,
        "overview_metric_name": metric_name,
        "overview_metric_label": label,
        "metric_count": count,
        "metric_denominator_count": denominator_count,
        "metric_percentage": _percentage(
            count,
            denominator_count,
        ),
        "metric_denominator_definition": denominator_definition,
        "metric_notes": notes,
    }


def _attempt_rows(attempts: pd.DataFrame) -> list[dict[str, object]]:
    """Return attempt-level overview rows."""
    all_attempt_count = len(attempts)
    completed = attempts["attempt_result"].eq(_COMPLETE)
    incomplete = attempts["attempt_completion_group"].eq(_INCOMPLETE)
    completed_count = int(completed.sum())
    incomplete_count = int(incomplete.sum())

    definitions = {
        "all": "All audit attempts.",
        "complete": "All attempts with ATTEMPT_RESULT equal to COMPLETE.",
        "incomplete": "All attempts with ATTEMPT_RESULT other than COMPLETE.",
    }

    metrics = (
        (
            "all_attempt_count",
            "All attempts",
            all_attempt_count,
            all_attempt_count,
            definitions["all"],
        ),
        (
            "complete_attempt_count",
            "Completed attempts",
            completed_count,
            all_attempt_count,
            definitions["all"],
        ),
        (
            "incomplete_attempt_count",
            "Incomplete attempts",
            incomplete_count,
            all_attempt_count,
            definitions["all"],
        ),
        (
            "ai_error_attempt_count",
            "AI error attempts",
            int(attempts["attempt_result"].eq(_AI_ERROR).sum()),
            incomplete_count,
            definitions["incomplete"],
        ),
        (
            "ai_error_without_stack_trace_attempt_count",
            "AI errors without stack trace",
            int(attempts["attempt_result"].eq(_AI_ERROR_WITHOUT_STACK_TRACE).sum()),
            incomplete_count,
            definitions["incomplete"],
        ),
        (
            "user_dropped_attempt_count",
            "User-dropped attempts",
            int(attempts["attempt_result"].eq(_USER_DROPPED).sum()),
            incomplete_count,
            definitions["incomplete"],
        ),
        (
            "completed_ai_attempt_count",
            "Completed AI attempts",
            int((completed & attempts["attempt_authoring_mode"].eq(_AI)).sum()),
            completed_count,
            definitions["complete"],
        ),
        (
            "completed_manual_attempt_count",
            "Completed manual attempts",
            int((completed & attempts["attempt_authoring_mode"].eq(_MANUAL)).sum()),
            completed_count,
            definitions["complete"],
        ),
        (
            "incomplete_ai_attempt_count",
            "Incomplete AI attempts",
            int((incomplete & attempts["attempt_authoring_mode"].eq(_AI)).sum()),
            incomplete_count,
            definitions["incomplete"],
        ),
        (
            "incomplete_manual_attempt_count",
            "Incomplete manual attempts",
            int((incomplete & attempts["attempt_authoring_mode"].eq(_MANUAL)).sum()),
            incomplete_count,
            definitions["incomplete"],
        ),
    )

    return [
        _row(
            section="ATTEMPTS",
            metric_name=name,
            label=label,
            count=count,
            denominator_count=denominator,
            denominator_definition=definition,
        )
        for name, label, count, denominator, definition in metrics
    ]


def _study_rows(studies: pd.DataFrame) -> list[dict[str, object]]:
    """Return study-level overview rows."""
    all_studies = len(studies)
    completed = studies["study_is_completed"].eq(True)
    completed_count = int(completed.sum())
    not_completed_count = all_studies - completed_count
    has_ai = studies["ai_attempt_count"].gt(0)
    has_manual = studies["manual_attempt_count"].gt(0)

    study_metrics = (
        (
            "distinct_study_count_with_any_attempt",
            "Distinct studies with any attempt",
            all_studies,
            all_studies,
            "All distinct studies represented by at least one attempt.",
        ),
        (
            "distinct_completed_study_count",
            "Distinct completed studies",
            completed_count,
            all_studies,
            "All distinct studies represented by at least one attempt.",
        ),
        (
            "distinct_study_count_without_completion",
            "Distinct studies without completion",
            not_completed_count,
            all_studies,
            "All distinct studies represented by at least one attempt.",
        ),
        (
            "distinct_study_count_with_any_ai_attempt",
            "Studies with any AI attempt",
            int(has_ai.sum()),
            all_studies,
            "All distinct studies represented by at least one attempt.",
        ),
        (
            "distinct_study_count_with_any_manual_attempt",
            "Studies with any manual attempt",
            int(has_manual.sum()),
            all_studies,
            "All distinct studies represented by at least one attempt.",
        ),
        (
            "distinct_study_count_with_both_ai_and_manual_attempts",
            "Studies with both AI and manual attempts",
            int((has_ai & has_manual).sum()),
            all_studies,
            "All distinct studies represented by at least one attempt.",
        ),
        (
            "distinct_completed_study_count_final_mode_ai",
            "Completed studies authored with AI",
            int(
                (completed & studies["completed_attempt_authoring_mode"].eq(_AI)).sum()
            ),
            completed_count,
            "All distinct completed studies.",
        ),
        (
            "distinct_completed_study_count_final_mode_manual",
            "Completed studies authored manually",
            int(
                (
                    completed & studies["completed_attempt_authoring_mode"].eq(_MANUAL)
                ).sum()
            ),
            completed_count,
            "All distinct completed studies.",
        ),
        (
            "distinct_completed_study_count_with_preceding_incomplete_attempts",
            "Completed studies with preceding incomplete attempts",
            int(
                (completed & studies["preceding_incomplete_attempt_count"].gt(0)).sum()
            ),
            completed_count,
            "All distinct completed studies.",
        ),
        (
            "distinct_completed_study_count_with_preceding_ai_error_attempts",
            "Completed studies with preceding AI errors",
            int(
                (
                    completed
                    & (
                        studies["preceding_ai_error_attempt_count"].gt(0)
                        | studies[
                            "preceding_ai_error_without_stack_trace_attempt_count"
                        ].gt(0)
                    )
                ).sum()
            ),
            completed_count,
            "All distinct completed studies.",
        ),
        (
            "distinct_completed_study_count_with_preceding_user_dropped_attempts",
            "Completed studies with preceding user-dropped attempts",
            int(
                (
                    completed & studies["preceding_user_dropped_attempt_count"].gt(0)
                ).sum()
            ),
            completed_count,
            "All distinct completed studies.",
        ),
    )

    return [
        _row(
            section="STUDIES",
            metric_name=name,
            label=label,
            count=count,
            denominator_count=denominator,
            denominator_definition=definition,
        )
        for name, label, count, denominator, definition in study_metrics
    ]


def _author_rows(
    attempts: pd.DataFrame,
    authors: pd.DataFrame,
) -> list[dict[str, object]]:
    """Return attempt-author overview rows."""
    all_authors = len(authors)
    completed_author_names = frozenset(
        str(value)
        for value in attempts.loc[
            attempts["is_completed_attempt"].eq(True),
            "attempt_author_user_name",
        ]
    )
    incomplete_author_names = frozenset(
        str(value)
        for value in attempts.loc[
            attempts["attempt_completion_group"].eq(_INCOMPLETE),
            "attempt_author_user_name",
        ]
    )
    completed_ai_author_names = frozenset(
        str(value)
        for value in attempts.loc[
            attempts["is_completed_attempt"].eq(True)
            & attempts["attempt_authoring_mode"].eq(_AI),
            "attempt_author_user_name",
        ]
    )
    completed_manual_author_names = frozenset(
        str(value)
        for value in attempts.loc[
            attempts["is_completed_attempt"].eq(True)
            & attempts["attempt_authoring_mode"].eq(_MANUAL),
            "attempt_author_user_name",
        ]
    )

    metrics = (
        (
            "distinct_author_count_with_any_attempt",
            "Distinct authors with any attempt",
            all_authors,
        ),
        (
            "distinct_author_count_with_complete_attempt",
            "Distinct authors with a completed attempt",
            len(completed_author_names),
        ),
        (
            "distinct_author_count_with_incomplete_attempt",
            "Distinct authors with an incomplete attempt",
            len(incomplete_author_names),
        ),
        (
            "distinct_author_count_with_any_ai_attempt",
            "Distinct authors with any AI attempt",
            int(authors["ai_attempt_count"].gt(0).sum()),
        ),
        (
            "distinct_author_count_with_any_manual_attempt",
            "Distinct authors with any manual attempt",
            int(authors["manual_attempt_count"].gt(0).sum()),
        ),
        (
            "distinct_author_count_with_both_ai_and_manual_attempts",
            "Distinct authors using both AI and manual modes",
            int(authors["author_adoption_group"].eq("BOTH_AI_AND_MANUAL").sum()),
        ),
        (
            "distinct_author_count_with_completed_ai_attempt",
            "Distinct authors with a completed AI attempt",
            len(completed_ai_author_names),
        ),
        (
            "distinct_author_count_with_completed_manual_attempt",
            "Distinct authors with a completed manual attempt",
            len(completed_manual_author_names),
        ),
    )

    rows = [
        _row(
            section="AUTHORS",
            metric_name=name,
            label=label,
            count=count,
            denominator_count=all_authors,
            denominator_definition="All distinct attempt authors.",
        )
        for name, label, count in metrics
    ]

    named_pi_count = int(attempts["study_pi_user_name"].dropna().nunique())
    classified_pi_count = int(authors["author_is_pi_on_any_attempt"].eq(True).sum())
    rows.extend(
        [
            _row(
                section="PI_IDENTITIES",
                metric_name="distinct_named_pi_count",
                label="Distinct named study PIs",
                count=named_pi_count,
                denominator_count=named_pi_count,
                denominator_definition="All distinct nonmissing PI_USER_NAME values.",
                notes=(
                    "Named PIs and attempt authors classified as PI are "
                    "distinct concepts."
                ),
            ),
            _row(
                section="PI_IDENTITIES",
                metric_name="distinct_author_count_classified_as_pi",
                label="Distinct attempt authors classified as PI",
                count=classified_pi_count,
                denominator_count=all_authors,
                denominator_definition="All distinct attempt authors.",
                notes=(
                    "Uses eResearch role, fallback application role, or username match."
                ),
            ),
        ]
    )

    return rows


def build_overview_summary(
    *,
    attempts: pd.DataFrame,
    studies: pd.DataFrame,
    authors: pd.DataFrame,
) -> pd.DataFrame:
    """Return all bird's-eye overview metrics in canonical order."""
    rows = [
        *_attempt_rows(attempts),
        *_study_rows(studies),
        *_author_rows(
            attempts,
            authors,
        ),
    ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(OVERVIEW_COLUMNS),
    )
