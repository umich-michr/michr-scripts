"""Loaded-input, derived-data, aggregation, publication, and validation models."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True, slots=True)
class LoadedAuditReport:
    """Typed DataFrames loaded from one normalized report directory."""

    records: pd.DataFrame
    ai_assistance_metrics: pd.DataFrame
    readability_metrics: pd.DataFrame


@dataclass(frozen=True, slots=True)
class ValidationSummary:
    """Counts from a successfully validated normalized report."""

    record_attempt_count: int
    distinct_study_count: int
    completed_attempt_count: int
    incomplete_attempt_count: int
    ai_assistance_metric_row_count: int
    readability_metric_row_count: int


@dataclass(frozen=True, slots=True)
class DescriptiveStatistics:
    """One explicit descriptive summary for numeric observations."""

    nonmissing_count: int
    missing_count: int
    minimum: float | None
    percentile_25: float | None
    median: float | None
    average: float | None
    standard_deviation: float | None
    percentile_75: float | None
    percentile_90: float | None
    maximum: float | None


@dataclass(frozen=True, slots=True)
class AppointmentQualityFinding:
    """One malformed source appointment value."""

    audit_record_id: int
    appointment_source: str
    appointment_index: int
    issue_name: str


@dataclass(frozen=True, slots=True)
class AttemptHistoryTables:
    """Derived audit tables with explicit attempt, study, and author grains."""

    study_attempt_author_history: pd.DataFrame
    study_attempt_history: pd.DataFrame
    author_history: pd.DataFrame


@dataclass(frozen=True, slots=True)
class RetryAnalysisTables:
    """Internal retry context and identifier-free faculty aggregates."""

    study_retry_context: pd.DataFrame
    retry_card_summary: pd.DataFrame
    study_retry_pathway_summary: pd.DataFrame
    retry_characteristics_summary: pd.DataFrame


@dataclass(frozen=True, slots=True)
class QualityAnalysisTables:
    """Aggregate quality summary and restricted internal findings."""

    data_quality_summary: pd.DataFrame
    data_quality_findings: pd.DataFrame


@dataclass(frozen=True, slots=True)
class OverviewTables:
    """Faculty-facing overview and attempt-history aggregate tables."""

    overview_summary: pd.DataFrame
    study_attempt_history_summary: pd.DataFrame
    author_handoff_summary: pd.DataFrame


@dataclass(frozen=True, slots=True)
class AttemptAnalysisTables:
    """Attempt timing and content-source aggregate tables."""

    grouped_attempt_summary: pd.DataFrame
    content_source_concordance_summary: pd.DataFrame
    content_source_concordance_matrix: pd.DataFrame


@dataclass(frozen=True, slots=True)
class StudyAnalysisTables:
    """Completed-study context, grouped studies, and quality findings."""

    completed_study_author_context_summary: pd.DataFrame
    grouped_study_summary: pd.DataFrame
    appointment_quality_findings: tuple[AppointmentQualityFinding, ...]


@dataclass(frozen=True, slots=True)
class AuthorAnalysisTables:
    """Grouped author and experience aggregate tables."""

    grouped_author_summary: pd.DataFrame
    attempt_start_experience_summary: pd.DataFrame
    current_author_experience_summary: pd.DataFrame


@dataclass(frozen=True, slots=True)
class FieldAnalysisTables:
    """Completed-AI field audit rows and faculty-facing field summaries."""

    completed_ai_field_analysis: pd.DataFrame
    field_adoption_editing_summary: pd.DataFrame
    nontext_field_adoption_summary: pd.DataFrame
    suggestion_selection_summary: pd.DataFrame
    compensation_analysis_summary: pd.DataFrame


@dataclass(frozen=True, slots=True)
class ReadabilityAnalysisTables:
    """Readability audit pairs and faculty-facing readability summaries."""

    completed_ai_readability_pairs: pd.DataFrame
    selected_vs_unselected_readability_summary: pd.DataFrame
    field_readability_change_summary: pd.DataFrame
    field_readability_target_summary: pd.DataFrame
    field_edit_readability_cross_summary: pd.DataFrame
    final_text_metric_summary: pd.DataFrame


@dataclass(frozen=True, slots=True)
class SourceContextAnalysisTables:
    """Identifier-free source-context aggregate tables."""

    source_context_distribution_summary: pd.DataFrame
    source_size_latency_summary: pd.DataFrame
    repeated_attempt_source_consistency_summary: pd.DataFrame


@dataclass(frozen=True, slots=True)
class ExplorationAnalysisTables:
    """All derived and aggregate tables published by one analysis run."""

    histories: AttemptHistoryTables
    retry: RetryAnalysisTables
    source_context: SourceContextAnalysisTables
    quality: QualityAnalysisTables
    overview: OverviewTables
    attempts: AttemptAnalysisTables
    studies: StudyAnalysisTables
    authors: AuthorAnalysisTables
    fields: FieldAnalysisTables
    readability: ReadabilityAnalysisTables


@dataclass(frozen=True, slots=True)
class ExplorationPublication:
    """Successfully published exploration output."""

    output_directory: Path
    manifest_path: Path
    report_path: Path
    metric_definitions_path: Path
    data_quality_summary_path: Path
    data_quality_findings_path: Path
    study_attempt_author_history_path: Path
    study_attempt_history_path: Path
    author_history_path: Path
    completed_ai_field_analysis_path: Path
    completed_ai_readability_pairs_path: Path
    overview_summary_path: Path
    study_attempt_history_summary_path: Path
    author_handoff_summary_path: Path
    study_retry_pathway_summary_path: Path
    retry_characteristics_summary_path: Path
    repeated_attempt_source_consistency_summary_path: Path
    grouped_attempt_summary_path: Path
    source_context_distribution_summary_path: Path
    source_size_latency_summary_path: Path
    content_source_concordance_summary_path: Path
    content_source_concordance_matrix_path: Path
    completed_study_author_context_summary_path: Path
    grouped_study_summary_path: Path
    grouped_author_summary_path: Path
    attempt_start_experience_summary_path: Path
    current_author_experience_summary_path: Path
    field_adoption_editing_summary_path: Path
    nontext_field_adoption_summary_path: Path
    suggestion_selection_summary_path: Path
    compensation_analysis_summary_path: Path
    selected_vs_unselected_readability_summary_path: Path
    field_readability_change_summary_path: Path
    field_readability_target_summary_path: Path
    field_edit_readability_cross_summary_path: Path
    final_text_metric_summary_path: Path
    candidate_research_questions_path: Path
    output_file_count: int
