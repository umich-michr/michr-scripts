import json
from pathlib import Path

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    AGGREGATE_OUTPUT_COLUMNS,
    METRIC_DEFINITION_COLUMNS,
    AppointmentQualityFinding,
    AttemptHistoryTables,
    ExplorationConfigurationError,
    ExplorationInputConfig,
    ExplorationPublication,
    ExplorationRunConfig,
    LoadedAuditReport,
    build_attempt_analysis_tables,
    build_author_analysis_tables,
    build_field_analysis_tables,
    build_overview_tables,
    build_quality_analysis_tables,
    build_readability_analysis_tables,
    build_study_analysis_tables,
    derive_appointments,
    derive_attempt_histories,
    derive_completed_ai_field_analysis,
    derive_completed_ai_readability_pairs,
    load_audit_report,
    publish_exploration,
)
from study_posting_audit_exploration.models import ExplorationAnalysisTables
from study_posting_audit_exploration.publication import manifest_filename


def read_published_csv(path: Path) -> pd.DataFrame:
    """Read a published CSV using the exploration null convention."""
    return pd.read_csv(
        path,
        keep_default_na=False,
        na_values=["\\N"],
    )


def loaded_report(path: Path) -> LoadedAuditReport:
    """Load one synthetic report."""
    return load_audit_report(
        ExplorationInputConfig(
            report_directory=path,
        )
    )


def _attempts_with_source_columns(
    report: LoadedAuditReport,
    histories: AttemptHistoryTables,
) -> pd.DataFrame:
    """Return attempt history joined to source-comparison columns."""
    source_columns = report.records.loc[
        :,
        [
            "ID",
            "SOURCE_TYPE",
            "STUDY_CONTENT_SOURCE",
            "LLM_INFERRED_STUDY_CONTENT_SOURCE",
            "STUDY_CONTENT_SOURCE_OTHER_VALUE",
            "LLM_INFERRED_STUDY_CONTENT_SOURCE_OTHER_VALUE",
        ],
    ].rename(
        columns={
            "ID": "audit_record_id",
            "SOURCE_TYPE": "source_type",
            "STUDY_CONTENT_SOURCE": "study_content_source",
            "LLM_INFERRED_STUDY_CONTENT_SOURCE": ("llm_inferred_study_content_source"),
            "STUDY_CONTENT_SOURCE_OTHER_VALUE": ("study_content_source_other_value"),
            "LLM_INFERRED_STUDY_CONTENT_SOURCE_OTHER_VALUE": (
                "llm_inferred_study_content_source_other_value"
            ),
        }
    )

    return histories.study_attempt_author_history.merge(
        source_columns,
        on="audit_record_id",
        how="left",
        validate="one_to_one",
    )


def _study_analysis_inputs(
    report: LoadedAuditReport,
    histories: AttemptHistoryTables,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    tuple[AppointmentQualityFinding, ...],
]:
    """Return study history, study-keyed appointments, and findings."""
    snapshot_records = report.records.loc[
        report.records["ATTEMPT_RESULT"].eq("COMPLETE")
    ]
    study_source = snapshot_records.loc[
        :,
        [
            "ID",
            "STUDY_NUM",
            "STUDY_PARTICIPANT_TYPE",
            "STUDY_DEPARTMENT",
            "SOURCE_TYPE",
            "STUDY_CONTENT_SOURCE",
        ],
    ].rename(
        columns={
            "ID": "audit_record_id",
            "STUDY_NUM": "study_num",
            "STUDY_PARTICIPANT_TYPE": "study_participant_type",
            "STUDY_DEPARTMENT": "study_department",
            "SOURCE_TYPE": "source_type",
            "STUDY_CONTENT_SOURCE": "study_content_source",
        }
    )
    studies = histories.study_attempt_history.merge(
        study_source.drop(columns=["audit_record_id"]),
        on="study_num",
        how="left",
        validate="one_to_one",
    )
    appointment_rows, findings = derive_appointments(snapshot_records)
    appointments = study_source[
        [
            "audit_record_id",
            "study_num",
        ]
    ].merge(
        appointment_rows,
        on="audit_record_id",
        how="inner",
        validate="one_to_many",
    )

    return studies, appointments, findings


def _analysis_tables(
    report: LoadedAuditReport,
) -> ExplorationAnalysisTables:
    """Build all current exploration tables for one synthetic report."""
    histories = derive_attempt_histories(report.records)
    attempts = _attempts_with_source_columns(
        report,
        histories,
    )
    studies, study_appointments, findings = _study_analysis_inputs(
        report,
        histories,
    )
    attempt_appointments, attempt_findings = derive_appointments(report.records)
    completed_ai_fields = derive_completed_ai_field_analysis(
        report.ai_assistance_metrics,
        report.records,
    )
    readability_pairs = derive_completed_ai_readability_pairs(
        report.readability_metrics,
        completed_ai_fields,
    )

    all_findings = (
        *findings,
        *attempt_findings,
    )

    return ExplorationAnalysisTables(
        histories=histories,
        quality=build_quality_analysis_tables(
            report=report,
            histories=histories,
            appointment_quality_findings=all_findings,
        ),
        overview=build_overview_tables(
            attempts=attempts,
            studies=histories.study_attempt_history,
            authors=histories.author_history,
        ),
        attempts=build_attempt_analysis_tables(attempts),
        studies=build_study_analysis_tables(
            studies,
            study_attempt_author_history=(histories.study_attempt_author_history),
            appointments=study_appointments,
            appointment_quality_findings=all_findings,
        ),
        authors=build_author_analysis_tables(
            attempts=attempts,
            authors=histories.author_history,
            appointments=attempt_appointments,
        ),
        fields=build_field_analysis_tables(
            completed_ai_fields,
            readability_pairs,
        ),
        readability=build_readability_analysis_tables(
            readability=report.readability_metrics,
            readability_pairs=readability_pairs,
            completed_ai_fields=completed_ai_fields,
        ),
    )


def publish_valid_report(
    input_directory: Path,
    output_directory: Path,
) -> ExplorationPublication:
    """Publish one synthetic exploration report."""
    report = loaded_report(input_directory)

    return publish_exploration(
        config=ExplorationRunConfig(
            input_report_directory=input_directory,
            output_directory=output_directory,
        ),
        report=report,
        tables=_analysis_tables(report),
    )


def _publication_paths(
    publication: ExplorationPublication,
) -> tuple[Path, ...]:
    """Return every current published output path."""
    return (
        publication.manifest_path,
        publication.report_path,
        publication.metric_definitions_path,
        publication.data_quality_summary_path,
        publication.study_attempt_author_history_path,
        publication.study_attempt_history_path,
        publication.author_history_path,
        publication.completed_ai_field_analysis_path,
        publication.completed_ai_readability_pairs_path,
        publication.overview_summary_path,
        publication.study_attempt_history_summary_path,
        publication.author_handoff_summary_path,
        publication.grouped_attempt_summary_path,
        publication.content_source_concordance_summary_path,
        publication.content_source_concordance_matrix_path,
        publication.completed_study_author_context_summary_path,
        publication.grouped_study_summary_path,
        publication.grouped_author_summary_path,
        publication.attempt_start_experience_summary_path,
        publication.current_author_experience_summary_path,
        publication.field_adoption_editing_summary_path,
        publication.nontext_field_adoption_summary_path,
        publication.suggestion_selection_summary_path,
        publication.compensation_analysis_summary_path,
        publication.selected_vs_unselected_readability_summary_path,
        publication.field_readability_change_summary_path,
        publication.field_readability_target_summary_path,
        publication.field_edit_readability_cross_summary_path,
        publication.final_text_metric_summary_path,
        publication.candidate_research_questions_path,
    )


def _assert_derived_outputs(
    publication: ExplorationPublication,
) -> None:
    """Assert derived CSV content and privacy boundaries."""
    quality_summary = read_published_csv(publication.data_quality_summary_path)
    completed_fields = read_published_csv(publication.completed_ai_field_analysis_path)
    readability_pairs = read_published_csv(
        publication.completed_ai_readability_pairs_path
    )
    field_summary = read_published_csv(publication.field_adoption_editing_summary_path)
    readability_change = read_published_csv(
        publication.field_readability_change_summary_path
    )
    readability_target = read_published_csv(
        publication.field_readability_target_summary_path
    )
    final_metrics = read_published_csv(publication.final_text_metric_summary_path)
    completed_study_context = read_published_csv(
        publication.completed_study_author_context_summary_path
    )

    for frame in (
        quality_summary,
        completed_fields,
        readability_pairs,
        field_summary,
        readability_change,
        readability_target,
        final_metrics,
        completed_study_context,
    ):
        assert not frame.empty

    for forbidden_column in (
        "selected_text",
        "final_text",
    ):
        assert forbidden_column not in completed_fields.columns
        assert forbidden_column not in readability_pairs.columns

    assert tuple(quality_summary.columns) == (
        "data_quality_check_name",
        "severity_level",
        "affected_attempt_count",
        "affected_distinct_study_count",
        "affected_distinct_author_count",
        "eligible_attempt_count",
        "affected_attempt_percentage",
        "check_definition",
        "analysis_consequence",
    )
    assert len(quality_summary) == 16
    assert "audit_record_id" not in quality_summary.columns
    assert "study_num" not in quality_summary.columns
    assert "author_user_name" not in quality_summary.columns

    assert final_metrics["final_text_attempt_count_missing_or_blank"].isna().all()
    assert tuple(completed_study_context.columns) == (
        "context_dimension_name",
        "context_dimension_value",
        "final_completion_authoring_mode",
        "completed_study_count",
        "mode_completed_study_count",
        "all_completed_study_count",
        "completed_study_percentage_within_mode",
        "completed_study_percentage_overall",
        "distinct_completion_author_count",
    )
    assert "study_num" not in completed_study_context.columns
    assert "attempt_author_user_name" not in completed_study_context.columns


def _assert_html_privacy(
    publication: ExplorationPublication,
) -> None:
    """Assert the faculty report excludes identifiers and source text."""
    report_html = publication.report_path.read_text(encoding="utf-8")

    assert "<h1>Study Posting Audit Exploration</h1>" in report_html

    for forbidden_value in (
        "SYNTHETIC-STUDY-1",
        "completion-author@example.edu",
        "selected_text",
        "final_text",
    ):
        assert forbidden_value not in report_html


def test_publish_exploration_writes_atomic_html_output(
    valid_report_directory: Path,
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "nested" / "exploration"
    publication = publish_valid_report(
        valid_report_directory,
        output_directory,
    )

    assert publication.output_directory == output_directory
    assert publication.output_file_count == 30

    for path in _publication_paths(publication):
        assert path.is_file()

    published_inventory = {
        path.relative_to(output_directory).as_posix()
        for path in output_directory.rglob("*")
        if path.is_file()
    }
    expected_inventory = {
        path.relative_to(output_directory).as_posix()
        for path in _publication_paths(publication)
    }

    assert published_inventory == expected_inventory
    assert len(published_inventory) == 30

    assert list(tmp_path.glob(".exploration.*")) == []

    _assert_derived_outputs(publication)
    _assert_html_privacy(publication)
    metric_definitions = read_published_csv(publication.metric_definitions_path)
    research_questions = read_published_csv(
        publication.candidate_research_questions_path
    )
    assert tuple(metric_definitions.columns) == METRIC_DEFINITION_COLUMNS
    assert tuple(research_questions.columns) == (
        "research_question_id",
        "research_question",
        "primary_analytical_unit",
        "comparison_or_grouping",
        "outcome_or_measure",
        "supporting_output_files",
        "interpretation_cautions",
        "priority_tier",
        "analysis_status",
    )
    assert len(research_questions) == 14
    assert len(metric_definitions) == sum(
        len(columns) for columns in AGGREGATE_OUTPUT_COLUMNS.values()
    )


def test_manifest_contains_readability_analysis_counts(
    valid_report_directory: Path,
    tmp_path: Path,
) -> None:
    publication = publish_valid_report(
        valid_report_directory,
        tmp_path / "exploration",
    )
    manifest = json.loads(publication.manifest_path.read_text(encoding="utf-8"))

    assert manifest["quality_analysis_row_counts"]["data_quality_summary"] == 16
    assert (
        manifest["analysis_audit_record_row_counts"]["completed_ai_field_analysis"] > 0
    )
    assert (
        manifest["analysis_audit_record_row_counts"]["completed_ai_readability_pairs"]
        > 0
    )
    assert (
        manifest["study_analysis_row_counts"]["completed_study_author_context_summary"]
        > 0
    )
    assert manifest["field_analysis_row_counts"]["field_adoption_editing_summary"] > 0
    assert manifest["field_analysis_row_counts"]["suggestion_selection_summary"] > 0
    assert (
        manifest["readability_analysis_row_counts"]["field_readability_change_summary"]
        > 0
    )
    assert (
        manifest["readability_analysis_row_counts"]["field_readability_target_summary"]
        > 0
    )
    assert manifest["readability_analysis_row_counts"]["final_text_metric_summary"] > 0
    assert manifest["definition_row_counts"]["metric_definitions"] > 0
    assert manifest["research_row_counts"]["candidate_research_questions"] == 14
    assert manifest["output_file_count"] == 30
    assert manifest["warning_count"] == 0
    assert manifest_filename() == "analysis_manifest.json"


def test_existing_output_is_not_overwritten(
    valid_report_directory: Path,
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "exploration"
    output_directory.mkdir()
    marker = output_directory / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(
        ExplorationConfigurationError,
        match="Output directory already exists",
    ):
        publish_valid_report(
            valid_report_directory,
            output_directory,
        )

    assert marker.read_text(encoding="utf-8") == "keep"
