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


def _run_analyze(
    input_directory: Path,
    output_directory: Path,
) -> tuple[int, str, str]:
    """Run analyze and return status, standard output, and error output."""
    output = StringIO()
    error_output = StringIO()
    status = main(
        [
            "analyze",
            "--input-report",
            str(input_directory),
            "--output",
            str(output_directory),
        ],
        output=output,
        error_output=error_output,
    )

    return status, output.getvalue(), error_output.getvalue()


def _expected_paths(
    output_directory: Path,
) -> dict[str, Path]:
    """Return the published paths checked by the CLI integration test."""
    audit_directory = output_directory / "analysis-audit-records"
    fields_directory = output_directory / "fields"
    readability_directory = output_directory / "readability"

    return {
        "manifest": output_directory / "analysis_manifest.json",
        "report": output_directory / "report.html",
        "definitions": (output_directory / "definitions" / "metric_definitions.csv"),
        "field_audit": (audit_directory / "completed_ai_field_analysis.csv"),
        "readability_pairs": (audit_directory / "completed_ai_readability_pairs.csv"),
        "field_adoption": (fields_directory / "field_adoption_editing_summary.csv"),
        "nontext": (fields_directory / "nontext_field_adoption_summary.csv"),
        "selection": (fields_directory / "suggestion_selection_summary.csv"),
        "compensation": (fields_directory / "compensation_analysis_summary.csv"),
        "selected_comparison": (
            readability_directory / "selected_vs_unselected_readability_summary.csv"
        ),
        "change": (readability_directory / "field_readability_change_summary.csv"),
        "target": (readability_directory / "field_readability_target_summary.csv"),
        "cross": (readability_directory / "field_edit_readability_cross_summary.csv"),
        "final_metric": (readability_directory / "final_text_metric_summary.csv"),
    }


def _assert_manifest(manifest: dict[str, object]) -> None:
    """Assert current field and readability manifest counts."""
    audit_counts = manifest["analysis_audit_record_row_counts"]
    readability_counts = manifest["readability_analysis_row_counts"]

    assert isinstance(audit_counts, dict)
    assert isinstance(readability_counts, dict)

    assert audit_counts["completed_ai_field_analysis"] > 0
    assert audit_counts["completed_ai_readability_pairs"] > 0
    assert readability_counts["field_readability_change_summary"] > 0
    assert readability_counts["field_readability_target_summary"] > 0
    assert readability_counts["final_text_metric_summary"] > 0
    definition_counts = manifest["definition_row_counts"]

    assert isinstance(definition_counts, dict)
    assert definition_counts["metric_definitions"] > 0
    assert manifest["output_file_count"] == 27
    assert manifest["warning_count"] == 0


def _assert_cli_paths_printed(
    text: str,
    *,
    output_directory: Path,
    paths: dict[str, Path],
) -> None:
    """Assert the CLI prints every new HTML and readability path."""
    expected_lines = (
        f"Exploration directory: {output_directory}",
        f"Manifest: {paths['manifest']}",
        f"HTML report: {paths['report']}",
        f"Metric definitions CSV: {paths['definitions']}",
        f"Completed AI field analysis CSV: {paths['field_audit']}",
        (f"Completed AI readability pairs CSV: {paths['readability_pairs']}"),
        (f"Field adoption and editing summary CSV: {paths['field_adoption']}"),
        f"Nontext field adoption summary CSV: {paths['nontext']}",
        f"Suggestion selection summary CSV: {paths['selection']}",
        f"Compensation analysis summary CSV: {paths['compensation']}",
        (
            "Selected versus unselected readability summary CSV: "
            f"{paths['selected_comparison']}"
        ),
        f"Field readability change summary CSV: {paths['change']}",
        f"Field readability target summary CSV: {paths['target']}",
        f"Field edit/readability cross summary CSV: {paths['cross']}",
        f"Final text metric summary CSV: {paths['final_metric']}",
        "Published files: 27",
    )

    for expected_line in expected_lines:
        assert expected_line in text


def test_analyze_command_publishes_html_report(
    valid_report_directory: Path,
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "exploration"
    status, text, error_text = _run_analyze(
        valid_report_directory,
        output_directory,
    )
    paths = _expected_paths(output_directory)

    assert status == 0
    assert error_text == ""

    for path in paths.values():
        assert path.is_file()

    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    _assert_manifest(manifest)
    _assert_cli_paths_printed(
        text,
        output_directory=output_directory,
        paths=paths,
    )

    report_html = paths["report"].read_text(encoding="utf-8")
    assert "<h1>Study Posting Audit Exploration</h1>" in report_html
    assert "SYNTHETIC-STUDY-1" not in report_html
    assert "completion-author@example.edu" not in report_html

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
