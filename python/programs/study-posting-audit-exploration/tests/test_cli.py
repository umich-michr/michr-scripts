from collections.abc import Sequence
from io import StringIO
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
    assert "error: Input report directory does not exist" in error_output.getvalue()


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
