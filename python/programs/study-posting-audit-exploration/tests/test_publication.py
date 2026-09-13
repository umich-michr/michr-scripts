import json
from pathlib import Path

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationConfigurationError,
    ExplorationInputConfig,
    ExplorationPublication,
    ExplorationRunConfig,
    LoadedAuditReport,
    build_attempt_analysis_tables,
    build_overview_tables,
    derive_attempt_histories,
    load_audit_report,
    publish_exploration,
)
from study_posting_audit_exploration.models import AttemptHistoryTables
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
    overview_tables = build_overview_tables(
        attempts=attempts,
        studies=histories.study_attempt_history,
        authors=histories.author_history,
    )
    attempt_tables = build_attempt_analysis_tables(attempts)

    return publish_exploration(
        config=ExplorationRunConfig(
            input_report_directory=input_directory,
            output_directory=output_directory,
        ),
        report=report,
        histories=histories,
        overview_tables=overview_tables,
        attempt_tables=attempt_tables,
    )


def test_publish_exploration_writes_atomic_attempt_analysis_output(
    valid_report_directory: Path,
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "nested" / "exploration"

    publication = publish_valid_report(
        valid_report_directory,
        output_directory,
    )

    assert publication.output_directory == output_directory
    assert publication.output_file_count == 10
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
    assert list(tmp_path.glob(".exploration.*")) == []

    attempts = pd.read_csv(publication.study_attempt_author_history_path)
    studies = pd.read_csv(publication.study_attempt_history_path)
    authors = pd.read_csv(publication.author_history_path)
    overview = pd.read_csv(publication.overview_summary_path)
    history_summary = pd.read_csv(publication.study_attempt_history_summary_path)
    handoff_summary = pd.read_csv(publication.author_handoff_summary_path)
    grouped_attempts = pd.read_csv(publication.grouped_attempt_summary_path)
    concordance_summary = pd.read_csv(
        publication.content_source_concordance_summary_path
    )
    concordance_matrix = pd.read_csv(publication.content_source_concordance_matrix_path)

    assert len(attempts) == 2
    assert len(studies) == 1
    assert len(authors) == 2
    assert attempts["audit_record_id"].tolist() == [1001, 1002]
    assert not overview.empty
    assert history_summary["final_completion_authoring_mode"].tolist() == [
        "ALL",
        "AI",
        "MANUAL",
        "NOT_COMPLETED",
    ]
    assert len(handoff_summary) == 1
    assert not grouped_attempts.empty
    assert concordance_summary["attempt_completion_group"].tolist() == [
        "ALL",
        "COMPLETE",
        "INCOMPLETE",
    ]
    assert set(concordance_matrix["attempt_completion_group"]) == {
        "ALL",
        "COMPLETE",
        "INCOMPLETE",
    }


def test_manifest_contains_attempt_analysis_counts(
    valid_report_directory: Path,
    tmp_path: Path,
) -> None:
    report = loaded_report(valid_report_directory)
    histories = derive_attempt_histories(report.records)
    attempts = _attempts_with_source_columns(
        report,
        histories,
    )
    overview_tables = build_overview_tables(
        attempts=attempts,
        studies=histories.study_attempt_history,
        authors=histories.author_history,
    )
    attempt_tables = build_attempt_analysis_tables(attempts)

    publication = publish_exploration(
        config=ExplorationRunConfig(
            input_report_directory=valid_report_directory,
            output_directory=tmp_path / "exploration",
        ),
        report=report,
        histories=histories,
        overview_tables=overview_tables,
        attempt_tables=attempt_tables,
    )

    manifest = json.loads(publication.manifest_path.read_text(encoding="utf-8"))

    assert set(manifest) == {
        "analysis_audit_record_row_counts",
        "analysis_program_version",
        "attempt_analysis_row_counts",
        "edit_intensity_threshold_scheme",
        "generated_at_utc",
        "output_file_count",
        "overview_row_counts",
        "readability_unchanged_tolerance",
        "source_files",
        "source_report_directory",
        "source_row_counts",
        "warning_count",
    }
    assert manifest["overview_row_counts"] == {
        "author_handoff_summary": 1,
        "overview_summary": len(overview_tables.overview_summary),
        "study_attempt_history_summary": 4,
    }
    assert manifest["attempt_analysis_row_counts"] == {
        "content_source_concordance_matrix": len(
            attempt_tables.content_source_concordance_matrix
        ),
        "content_source_concordance_summary": 3,
        "grouped_attempt_summary": len(attempt_tables.grouped_attempt_summary),
    }
    assert manifest["output_file_count"] == 10
    assert "environment" not in manifest
    assert "dependencies" not in manifest
    assert "schema" not in manifest
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
