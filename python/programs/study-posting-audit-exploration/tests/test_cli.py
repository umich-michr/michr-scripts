from collections.abc import Sequence
from io import StringIO
import json
from pathlib import Path
import runpy
import sys

import pytest

from study_posting_audit_exploration.cli import (
    build_parser,
    main,
)


def test_parser_exposes_validate_command() -> None:
    namespace = build_parser().parse_args(
        [
            "validate",
            "--input-report",
            "synthetic-report",
        ]
    )

    assert namespace.command == "validate"
    assert namespace.input_report == "synthetic-report"


def test_parser_exposes_analyze_command() -> None:
    namespace = build_parser().parse_args(
        [
            "analyze",
            "--input-report",
            "synthetic-report",
            "--output",
            "synthetic-output",
        ]
    )

    assert namespace.command == "analyze"
    assert namespace.input_report == "synthetic-report"
    assert namespace.output == "synthetic-output"


def test_cli_validates_report_without_printing_identifiers(
    valid_report_directory: Path,
) -> None:
    output = StringIO()
    error_output = StringIO()

    status = main(
        [
            "validate",
            "--input-report",
            str(valid_report_directory),
        ],
        output=output,
        error_output=error_output,
    )

    assert status == 0
    assert error_output.getvalue() == ""

    text = output.getvalue()

    assert "Audit report validation passed." in text
    assert "Attempts: 2" in text
    assert "Distinct studies: 1" in text
    assert "Completed attempts: 1" in text
    assert "Incomplete attempts: 1" in text
    assert "AI-assistance metric rows: 1" in text
    assert "Readability metric rows: 2" in text
    assert "SYNTHETIC-STUDY-1" not in text
    assert "completion-author@example.edu" not in text


def test_analyze_command_publishes_field_analysis_output(
    valid_report_directory: Path,
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "exploration"
    output = StringIO()
    error_output = StringIO()

    status = main(
        [
            "analyze",
            "--input-report",
            str(valid_report_directory),
            "--output",
            str(output_directory),
        ],
        output=output,
        error_output=error_output,
    )

    assert status == 0
    assert error_output.getvalue() == ""

    manifest_path = output_directory / "analysis_manifest.json"
    audit_path = (
        output_directory / "analysis-audit-records" / "completed_ai_field_analysis.csv"
    )
    fields_directory = output_directory / "fields"
    adoption_path = fields_directory / "field_adoption_editing_summary.csv"
    nontext_path = fields_directory / "nontext_field_adoption_summary.csv"
    selection_path = fields_directory / "suggestion_selection_summary.csv"
    compensation_path = fields_directory / "compensation_analysis_summary.csv"

    assert manifest_path.is_file()
    assert audit_path.is_file()
    assert adoption_path.is_file()
    assert nontext_path.is_file()
    assert selection_path.is_file()
    assert compensation_path.is_file()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert (
        manifest["analysis_audit_record_row_counts"]["completed_ai_field_analysis"] > 0
    )
    assert manifest["field_analysis_row_counts"]["field_adoption_editing_summary"] > 0
    assert manifest["field_analysis_row_counts"]["suggestion_selection_summary"] > 0
    assert manifest["output_file_count"] == 19
    assert manifest["warning_count"] == 0

    text = output.getvalue()

    assert f"Exploration directory: {output_directory}" in text
    assert f"Manifest: {manifest_path}" in text
    assert f"Completed AI field analysis CSV: {audit_path}" in text
    assert f"Field adoption and editing summary CSV: {adoption_path}" in text
    assert f"Nontext field adoption summary CSV: {nontext_path}" in text
    assert f"Suggestion selection summary CSV: {selection_path}" in text
    assert f"Compensation analysis summary CSV: {compensation_path}" in text
    assert "Published files: 19" in text
    assert "SYNTHETIC-STUDY-1" not in text
    assert "completion-author@example.edu" not in text


def test_cli_reports_expected_failure_without_traceback(
    tmp_path: Path,
) -> None:
    output = StringIO()
    error_output = StringIO()

    status = main(
        [
            "validate",
            "--input-report",
            str(tmp_path / "missing"),
        ],
        output=output,
        error_output=error_output,
    )

    assert status == 2
    assert output.getvalue() == ""
    assert "error: Input report directory does not exist" in (error_output.getvalue())


def test_analyze_rejects_existing_output_directory(
    valid_report_directory: Path,
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "existing"
    output_directory.mkdir()
    error_output = StringIO()

    status = main(
        [
            "analyze",
            "--input-report",
            str(valid_report_directory),
            "--output",
            str(output_directory),
        ],
        output=StringIO(),
        error_output=error_output,
    )

    assert status == 2
    assert "Output directory already exists" in error_output.getvalue()


def test_main_uses_default_streams(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = StringIO()
    error_output = StringIO()
    monkeypatch.setattr(sys, "stdout", output)
    monkeypatch.setattr(sys, "stderr", error_output)

    status = main(
        [
            "validate",
            "--input-report",
            str(tmp_path / "missing"),
        ]
    )

    assert status == 2
    assert output.getvalue() == ""
    assert "error:" in error_output.getvalue()


def test_module_execution_calls_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_main(
        argv: Sequence[str] | None = None,
        **_kwargs: object,
    ) -> int:
        calls.append(tuple(() if argv is None else argv))
        return 7

    monkeypatch.setattr(
        "study_posting_audit_exploration.cli.main",
        fake_main,
    )

    with pytest.raises(SystemExit) as captured:
        runpy.run_module(
            "study_posting_audit_exploration.__main__",
            run_name="__main__",
        )

    assert captured.value.code == 7
    assert calls == [()]
