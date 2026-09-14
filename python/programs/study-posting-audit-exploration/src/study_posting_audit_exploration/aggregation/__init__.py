"""Faculty-facing aggregate tables for audit exploration."""

import pandas as pd

from study_posting_audit_exploration.aggregation.attempt_histories import (
    build_author_handoff_summary,
    build_study_attempt_history_summary,
)
from study_posting_audit_exploration.aggregation.attempts import (
    build_grouped_attempt_summary,
)
from study_posting_audit_exploration.aggregation.authors import (
    build_attempt_start_experience_summary,
    build_current_author_experience_summary,
    build_grouped_author_summary,
)
from study_posting_audit_exploration.aggregation.compensation import (
    build_compensation_analysis_summary,
)
from study_posting_audit_exploration.aggregation.content_sources import (
    build_content_source_concordance_matrix,
    build_content_source_concordance_summary,
)
from study_posting_audit_exploration.aggregation.fields import (
    build_field_adoption_editing_summary,
)
from study_posting_audit_exploration.aggregation.final_readability import (
    build_field_readability_target_summary,
    build_final_text_metric_summary,
)
from study_posting_audit_exploration.aggregation.nontext_fields import (
    build_nontext_field_adoption_summary,
)
from study_posting_audit_exploration.aggregation.overview import (
    build_overview_summary,
)
from study_posting_audit_exploration.aggregation.readability import (
    build_field_edit_readability_cross_summary,
    build_field_readability_change_summary,
    build_selected_vs_unselected_readability_summary,
)
from study_posting_audit_exploration.aggregation.studies import (
    build_grouped_study_summary,
)
from study_posting_audit_exploration.aggregation.suggestions import (
    build_suggestion_selection_summary,
)
from study_posting_audit_exploration.models import (
    AppointmentQualityFinding,
    AttemptAnalysisTables,
    AuthorAnalysisTables,
    FieldAnalysisTables,
    OverviewTables,
    StudyAnalysisTables,
)


def build_overview_tables(
    *,
    attempts: pd.DataFrame,
    studies: pd.DataFrame,
    authors: pd.DataFrame,
) -> OverviewTables:
    """Build all overview aggregate tables."""
    return OverviewTables(
        overview_summary=build_overview_summary(
            attempts=attempts,
            studies=studies,
            authors=authors,
        ),
        study_attempt_history_summary=build_study_attempt_history_summary(studies),
        author_handoff_summary=build_author_handoff_summary(
            attempts=attempts,
            studies=studies,
        ),
    )


def build_attempt_analysis_tables(
    attempts: pd.DataFrame,
) -> AttemptAnalysisTables:
    """Build grouped attempt and content-source aggregate tables."""
    return AttemptAnalysisTables(
        grouped_attempt_summary=build_grouped_attempt_summary(attempts),
        content_source_concordance_summary=(
            build_content_source_concordance_summary(attempts)
        ),
        content_source_concordance_matrix=(
            build_content_source_concordance_matrix(attempts)
        ),
    )


def build_study_analysis_tables(
    studies: pd.DataFrame,
    *,
    appointments: pd.DataFrame | None = None,
    appointment_quality_findings: tuple[
        AppointmentQualityFinding,
        ...,
    ] = (),
) -> StudyAnalysisTables:
    """Build grouped study aggregate tables."""
    return StudyAnalysisTables(
        grouped_study_summary=build_grouped_study_summary(
            studies,
            appointments=appointments,
        ),
        appointment_quality_findings=appointment_quality_findings,
    )


def build_author_analysis_tables(
    *,
    attempts: pd.DataFrame,
    authors: pd.DataFrame,
    appointments: pd.DataFrame | None = None,
) -> AuthorAnalysisTables:
    """Build grouped author and experience aggregate tables."""
    return AuthorAnalysisTables(
        grouped_author_summary=build_grouped_author_summary(
            attempts,
            appointments=appointments,
        ),
        attempt_start_experience_summary=(
            build_attempt_start_experience_summary(
                attempts,
                authors,
            )
        ),
        current_author_experience_summary=(
            build_current_author_experience_summary(authors)
        ),
    )


def build_field_analysis_tables(
    completed_ai_fields: pd.DataFrame,
) -> FieldAnalysisTables:
    """Build completed-AI field audit rows and aggregate summaries."""
    return FieldAnalysisTables(
        completed_ai_field_analysis=completed_ai_fields,
        field_adoption_editing_summary=(
            build_field_adoption_editing_summary(completed_ai_fields)
        ),
        nontext_field_adoption_summary=(
            build_nontext_field_adoption_summary(completed_ai_fields)
        ),
        suggestion_selection_summary=(
            build_suggestion_selection_summary(completed_ai_fields)
        ),
        compensation_analysis_summary=(
            build_compensation_analysis_summary(completed_ai_fields)
        ),
    )


__all__ = [
    "AttemptAnalysisTables",
    "AuthorAnalysisTables",
    "FieldAnalysisTables",
    "OverviewTables",
    "StudyAnalysisTables",
    "build_attempt_analysis_tables",
    "build_attempt_start_experience_summary",
    "build_author_analysis_tables",
    "build_author_handoff_summary",
    "build_compensation_analysis_summary",
    "build_content_source_concordance_matrix",
    "build_content_source_concordance_summary",
    "build_current_author_experience_summary",
    "build_field_adoption_editing_summary",
    "build_field_analysis_tables",
    "build_field_edit_readability_cross_summary",
    "build_field_readability_change_summary",
    "build_field_readability_target_summary",
    "build_final_text_metric_summary",
    "build_grouped_attempt_summary",
    "build_grouped_author_summary",
    "build_grouped_study_summary",
    "build_nontext_field_adoption_summary",
    "build_overview_summary",
    "build_overview_tables",
    "build_selected_vs_unselected_readability_summary",
    "build_study_analysis_tables",
    "build_study_attempt_history_summary",
    "build_suggestion_selection_summary",
]
