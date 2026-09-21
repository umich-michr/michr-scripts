"""Faculty-facing aggregate tables for audit exploration."""

import pandas as pd

from study_posting_audit_exploration.aggregation.attempt_histories import (
    AUTHOR_HANDOFF_COLUMNS,
    STUDY_ATTEMPT_HISTORY_COLUMNS,
    build_author_handoff_summary,
    build_study_attempt_history_summary,
)
from study_posting_audit_exploration.aggregation.attempts import (
    GROUPED_ATTEMPT_COLUMNS,
    build_grouped_attempt_summary,
)
from study_posting_audit_exploration.aggregation.authors import (
    ATTEMPT_START_EXPERIENCE_COLUMNS,
    CURRENT_AUTHOR_EXPERIENCE_COLUMNS,
    GROUPED_AUTHOR_COLUMNS,
    build_attempt_start_experience_summary,
    build_current_author_experience_summary,
    build_grouped_author_summary,
)
from study_posting_audit_exploration.aggregation.compensation import (
    COMPENSATION_ANALYSIS_COLUMNS,
    build_compensation_analysis_summary,
)
from study_posting_audit_exploration.aggregation.completed_study_context import (
    COMPLETED_STUDY_AUTHOR_CONTEXT_COLUMNS,
    build_completed_study_author_context_summary,
)
from study_posting_audit_exploration.aggregation.content_sources import (
    CONTENT_SOURCE_CONCORDANCE_MATRIX_COLUMNS,
    CONTENT_SOURCE_CONCORDANCE_SUMMARY_COLUMNS,
    build_content_source_concordance_matrix,
    build_content_source_concordance_summary,
)
from study_posting_audit_exploration.aggregation.fields import (
    FIELD_ADOPTION_EDITING_COLUMNS,
    build_field_adoption_editing_summary,
)
from study_posting_audit_exploration.aggregation.final_readability import (
    FIELD_READABILITY_TARGET_COLUMNS,
    FINAL_TEXT_METRIC_COLUMNS,
    build_field_readability_target_summary,
    build_final_text_metric_summary,
)
from study_posting_audit_exploration.aggregation.nontext_fields import (
    NONTEXT_FIELD_ADOPTION_COLUMNS,
    build_nontext_field_adoption_summary,
)
from study_posting_audit_exploration.aggregation.overview import (
    OVERVIEW_COLUMNS,
    build_overview_summary,
)
from study_posting_audit_exploration.aggregation.readability import (
    FIELD_EDIT_READABILITY_CROSS_COLUMNS,
    FIELD_READABILITY_CHANGE_COLUMNS,
    SELECTED_VS_UNSELECTED_READABILITY_COLUMNS,
    build_field_edit_readability_cross_summary,
    build_field_readability_change_summary,
    build_selected_vs_unselected_readability_summary,
)
from study_posting_audit_exploration.aggregation.source_context import (
    REPEATED_ATTEMPT_SOURCE_CONSISTENCY_COLUMNS,
    SOURCE_CONTEXT_DISTRIBUTION_COLUMNS,
    SOURCE_SIZE_LATENCY_COLUMNS,
    build_repeated_attempt_source_consistency_summary,
    build_source_context_analysis_tables,
    build_source_context_distribution_summary,
    build_source_size_latency_summary,
)
from study_posting_audit_exploration.aggregation.studies import (
    GROUPED_STUDY_COLUMNS,
    build_grouped_study_summary,
)
from study_posting_audit_exploration.aggregation.suggestions import (
    SUGGESTION_SELECTION_COLUMNS,
    build_suggestion_selection_summary,
)
from study_posting_audit_exploration.models import (
    AppointmentQualityFinding,
    AttemptAnalysisTables,
    AttemptHistoryTables,
    AuthorAnalysisTables,
    FieldAnalysisTables,
    LoadedAuditReport,
    OverviewTables,
    QualityAnalysisTables,
    ReadabilityAnalysisTables,
    SourceContextAnalysisTables,
    StudyAnalysisTables,
)
from study_posting_audit_exploration.quality import (
    DATA_QUALITY_SUMMARY_COLUMNS,
    build_data_quality_summary,
)
from study_posting_audit_exploration.quality_findings import (
    build_data_quality_findings,
)

AGGREGATE_OUTPUT_COLUMNS: dict[str, tuple[str, ...]] = {
    "quality/data_quality_summary.csv": DATA_QUALITY_SUMMARY_COLUMNS,
    "overview/overview_summary.csv": OVERVIEW_COLUMNS,
    "overview/study_attempt_history_summary.csv": (STUDY_ATTEMPT_HISTORY_COLUMNS),
    "overview/author_handoff_summary.csv": AUTHOR_HANDOFF_COLUMNS,
    "overview/repeated_attempt_source_consistency_summary.csv": (
        REPEATED_ATTEMPT_SOURCE_CONSISTENCY_COLUMNS
    ),
    "attempts/grouped_attempt_summary.csv": GROUPED_ATTEMPT_COLUMNS,
    "attempts/source_context_distribution_summary.csv": (
        SOURCE_CONTEXT_DISTRIBUTION_COLUMNS
    ),
    "attempts/source_size_latency_summary.csv": SOURCE_SIZE_LATENCY_COLUMNS,
    "attempts/content_source_concordance_summary.csv": (
        CONTENT_SOURCE_CONCORDANCE_SUMMARY_COLUMNS
    ),
    "attempts/content_source_concordance_matrix.csv": (
        CONTENT_SOURCE_CONCORDANCE_MATRIX_COLUMNS
    ),
    "studies/completed_study_author_context_summary.csv": (
        COMPLETED_STUDY_AUTHOR_CONTEXT_COLUMNS
    ),
    "studies/grouped_study_summary.csv": GROUPED_STUDY_COLUMNS,
    "authors/grouped_author_summary.csv": GROUPED_AUTHOR_COLUMNS,
    "authors/attempt_start_experience_summary.csv": (ATTEMPT_START_EXPERIENCE_COLUMNS),
    "authors/current_author_experience_summary.csv": (
        CURRENT_AUTHOR_EXPERIENCE_COLUMNS
    ),
    "fields/field_adoption_editing_summary.csv": (FIELD_ADOPTION_EDITING_COLUMNS),
    "fields/nontext_field_adoption_summary.csv": (NONTEXT_FIELD_ADOPTION_COLUMNS),
    "fields/suggestion_selection_summary.csv": (SUGGESTION_SELECTION_COLUMNS),
    "fields/compensation_analysis_summary.csv": (COMPENSATION_ANALYSIS_COLUMNS),
    "readability/selected_vs_unselected_readability_summary.csv": (
        SELECTED_VS_UNSELECTED_READABILITY_COLUMNS
    ),
    "readability/field_readability_change_summary.csv": (
        FIELD_READABILITY_CHANGE_COLUMNS
    ),
    "readability/field_readability_target_summary.csv": (
        FIELD_READABILITY_TARGET_COLUMNS
    ),
    "readability/field_edit_readability_cross_summary.csv": (
        FIELD_EDIT_READABILITY_CROSS_COLUMNS
    ),
    "readability/final_text_metric_summary.csv": FINAL_TEXT_METRIC_COLUMNS,
}


def build_quality_analysis_tables(
    *,
    report: LoadedAuditReport,
    histories: AttemptHistoryTables,
    appointment_quality_findings: tuple[
        AppointmentQualityFinding,
        ...,
    ] = (),
) -> QualityAnalysisTables:
    """Build identifier-free quality analysis tables."""
    return QualityAnalysisTables(
        data_quality_summary=build_data_quality_summary(
            report=report,
            histories=histories,
            appointment_quality_findings=appointment_quality_findings,
        ),
        data_quality_findings=build_data_quality_findings(
            report=report,
            histories=histories,
            appointment_quality_findings=appointment_quality_findings,
        ),
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
    *,
    successful_ai_generations: pd.DataFrame,
) -> AttemptAnalysisTables:
    """Build grouped-attempt and successful-generation source tables."""
    return AttemptAnalysisTables(
        grouped_attempt_summary=build_grouped_attempt_summary(attempts),
        content_source_concordance_summary=(
            build_content_source_concordance_summary(successful_ai_generations)
        ),
        content_source_concordance_matrix=(
            build_content_source_concordance_matrix(successful_ai_generations)
        ),
    )


def build_study_analysis_tables(
    studies: pd.DataFrame,
    *,
    study_attempt_author_history: pd.DataFrame,
    appointments: pd.DataFrame | None = None,
    appointment_quality_findings: tuple[
        AppointmentQualityFinding,
        ...,
    ] = (),
) -> StudyAnalysisTables:
    """Build completed-study context and grouped study aggregates."""
    return StudyAnalysisTables(
        completed_study_author_context_summary=(
            build_completed_study_author_context_summary(study_attempt_author_history)
        ),
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
    readability_pairs: pd.DataFrame | None = None,
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
            build_compensation_analysis_summary(
                completed_ai_fields,
                readability_pairs,
            )
        ),
    )


def build_readability_analysis_tables(
    *,
    readability: pd.DataFrame,
    readability_pairs: pd.DataFrame,
    completed_ai_fields: pd.DataFrame,
) -> ReadabilityAnalysisTables:
    """Build readability audit pairs and aggregate summaries."""
    return ReadabilityAnalysisTables(
        completed_ai_readability_pairs=readability_pairs,
        selected_vs_unselected_readability_summary=(
            build_selected_vs_unselected_readability_summary(readability)
        ),
        field_readability_change_summary=(
            build_field_readability_change_summary(readability_pairs)
        ),
        field_readability_target_summary=(
            build_field_readability_target_summary(readability)
        ),
        field_edit_readability_cross_summary=(
            build_field_edit_readability_cross_summary(
                readability_pairs,
                completed_ai_fields,
            )
        ),
        final_text_metric_summary=(
            build_final_text_metric_summary(
                readability,
                completed_ai_fields,
            )
        ),
    )


__all__ = [
    "AGGREGATE_OUTPUT_COLUMNS",
    "COMPLETED_STUDY_AUTHOR_CONTEXT_COLUMNS",
    "DATA_QUALITY_SUMMARY_COLUMNS",
    "REPEATED_ATTEMPT_SOURCE_CONSISTENCY_COLUMNS",
    "SOURCE_CONTEXT_DISTRIBUTION_COLUMNS",
    "SOURCE_SIZE_LATENCY_COLUMNS",
    "AttemptAnalysisTables",
    "AuthorAnalysisTables",
    "FieldAnalysisTables",
    "OverviewTables",
    "QualityAnalysisTables",
    "ReadabilityAnalysisTables",
    "SourceContextAnalysisTables",
    "StudyAnalysisTables",
    "build_attempt_analysis_tables",
    "build_attempt_start_experience_summary",
    "build_author_analysis_tables",
    "build_author_handoff_summary",
    "build_compensation_analysis_summary",
    "build_completed_study_author_context_summary",
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
    "build_quality_analysis_tables",
    "build_readability_analysis_tables",
    "build_repeated_attempt_source_consistency_summary",
    "build_selected_vs_unselected_readability_summary",
    "build_source_context_analysis_tables",
    "build_source_context_distribution_summary",
    "build_source_size_latency_summary",
    "build_study_analysis_tables",
    "build_study_attempt_history_summary",
    "build_suggestion_selection_summary",
]
