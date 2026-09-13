import json
from pathlib import Path

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationConfigurationError,
    ExplorationInputConfig,
    ExplorationRunConfig,
    LoadedAuditReport,
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


def test_publish_exploration_writes_atomic_batch_three_output(
    valid_report_directory: Path,
    tmp_path: Path,
) -> None:
    report = loaded_report(valid_report_directory)
    histories = derive_attempt_histories(report.records)
    output_directory = tmp_path / "nested" / "exploration"

    publication = publish_exploration(
        config=ExplorationRunConfig(
            input_report_directory=valid_report_directory,
            output_directory=output_directory,
        ),
        report=report,
        histories=histories,
    )

    assert publication.output_directory == output_directory
    assert publication.output_file_count == 4
    assert publication.manifest_path.is_file()
    assert publication.study_attempt_author_history_path.is_file()
    assert publication.study_attempt_history_path.is_file()
    assert publication.author_history_path.is_file()
    assert list(tmp_path.glob(".exploration.*")) == []

    attempts = pd.read_csv(
        publication.study_attempt_author_history_path,
        keep_default_na=False,
        na_values=["\\N"],
    )
    studies = pd.read_csv(
        publication.study_attempt_history_path,
        keep_default_na=False,
        na_values=["\\N"],
    )
    authors = pd.read_csv(
        publication.author_history_path,
        keep_default_na=False,
        na_values=["\\N"],
    )

    assert len(attempts) == 2
    assert len(studies) == 1
    assert len(authors) == 2
    assert attempts["audit_record_id"].tolist() == [1001, 1002]


def test_manifest_contains_only_minimal_expected_sections(
    valid_report_directory: Path,
    tmp_path: Path,
) -> None:
    report = loaded_report(valid_report_directory)
    histories = derive_attempt_histories(report.records)

    publication = publish_exploration(
        config=ExplorationRunConfig(
            input_report_directory=valid_report_directory,
            output_directory=tmp_path / "exploration",
        ),
        report=report,
        histories=histories,
    )

    manifest = json.loads(publication.manifest_path.read_text(encoding="utf-8"))

    assert set(manifest) == {
        "analysis_audit_record_row_counts",
        "analysis_program_version",
        "edit_intensity_threshold_scheme",
        "generated_at_utc",
        "output_file_count",
        "readability_unchanged_tolerance",
        "source_files",
        "source_report_directory",
        "source_row_counts",
        "warning_count",
    }
    assert "environment" not in manifest
    assert "dependencies" not in manifest
    assert "schema" not in manifest
    assert manifest_filename() == "analysis_manifest.json"


def test_existing_output_is_not_overwritten(
    valid_report_directory: Path,
    tmp_path: Path,
) -> None:
    report = loaded_report(valid_report_directory)
    histories = derive_attempt_histories(report.records)
    output_directory = tmp_path / "exploration"
    output_directory.mkdir()
    marker = output_directory / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(
        ExplorationConfigurationError,
        match="Output directory already exists",
    ):
        publish_exploration(
            config=ExplorationRunConfig(
                input_report_directory=valid_report_directory,
                output_directory=output_directory,
            ),
            report=report,
            histories=histories,
        )

    assert marker.read_text(encoding="utf-8") == "keep"
