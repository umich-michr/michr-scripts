import json
from pathlib import Path

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    AppointmentQualityFinding,
    AttemptHistoryTables,
    ExplorationConfigurationError,
    ExplorationInputConfig,
    ExplorationPublication,
    ExplorationRunConfig,
    LoadedAuditReport,
    build_attempt_analysis_tables,
    build_overview_tables,
    build_study_analysis_tables,
    derive_appointments,
    derive_attempt_histories,
    load_audit_report,
    publish_exploration,
)
from study_posting_audit_exploration.publication import manifest_filename


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


def publish_valid_report(
    input_directory: Path,
    output_directory: Path,
) -> ExplorationPublication:
    """Publish one synthetic exploration report."""
    report = loaded_report(input_directory)
    histories = derive_attempt_histories(report.records)
    attempts = _attempts_with_source_columns(
        report,
        histories,
    )
    studies, appointments, findings = _study_analysis_inputs(
        report,
        histories,
    )
    overview_tables = build_overview_tables(
        attempts=attempts,
        studies=histories.study_attempt_history,
        authors=histories.author_history,
    )
    attempt_tables = build_attempt_analysis_tables(attempts)
    study_tables = build_study_analysis_tables(
        studies,
        appointments=appointments,
        appointment_quality_findings=findings,
    )

    return publish_exploration(
        config=ExplorationRunConfig(
            input_report_directory=input_directory,
            output_directory=output_directory,
        ),
        report=report,
        histories=histories,
        overview_tables=overview_tables,
        attempt_tables=attempt_tables,
        study_tables=study_tables,
    )


def test_publish_exploration_writes_atomic_study_analysis_output(
    valid_report_directory: Path,
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "nested" / "exploration"

    publication = publish_valid_report(
        valid_report_directory,
        output_directory,
    )

    assert publication.output_directory == output_directory
    assert publication.output_file_count == 11
    assert publication.manifest_path.is_file()
    assert publication.study_attempt_author_history_path.is_file()
    assert publication.study_attempt_history_path.is_file()
    assert publication.author_history_path.is_file()
    assert publication.overview_summary_path.is_file()
    assert publication.study_attempt_history_summary_path.is_file()
    assert publication.author_handoff_summary_path.is_file()
    assert publication.grouped_attempt_summary_path.is_file()
    assert publication.content_source_concordance_summary_path.is_file()
    assert publication.content_source_concordance_matrix_path.is_file()
    assert publication.grouped_study_summary_path.is_file()
    assert list(tmp_path.glob(".exploration.*")) == []

    grouped_studies = pd.read_csv(publication.grouped_study_summary_path)

    assert not grouped_studies.empty
    assert "STUDY_PARTICIPANT_TYPE" in set(grouped_studies["grouping_dimension_1_name"])
    assert "AUTHOR_APPOINTMENT_SCHOOL" in set(
        grouped_studies["grouping_dimension_1_name"]
    )


def test_manifest_contains_study_analysis_counts(
    valid_report_directory: Path,
    tmp_path: Path,
) -> None:
    publication = publish_valid_report(
        valid_report_directory,
        tmp_path / "exploration",
    )
    manifest = json.loads(publication.manifest_path.read_text(encoding="utf-8"))

    assert "study_analysis_row_counts" in manifest
    assert manifest["study_analysis_row_counts"]["grouped_study_summary"] > 0
    assert manifest["output_file_count"] == 11
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
