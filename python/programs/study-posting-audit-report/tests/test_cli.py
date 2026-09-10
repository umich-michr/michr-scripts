"""Tests for the study-posting audit-report command-line interface."""

from collections.abc import Sequence
import csv
from io import StringIO
import json
from pathlib import Path
import runpy
import sys

import pytest

from study_posting_ai_analysis import FLATTENED_COLUMNS
from study_posting_audit_report.cli import (
    build_parser,
    main,
)


class NoninteractivePromptProvider:
    """Prompt provider that fails if the CLI attempts to read."""

    def __init__(self) -> None:
        self.read_calls: list[tuple[str, bool]] = []

    @property
    def is_interactive(self) -> bool:
        """Return false so batch invocations never prompt."""
        return False

    def read(
        self,
        prompt: str,
        *,
        secret: bool,
    ) -> str:
        """Record an unexpected read attempt."""
        self.read_calls.append((prompt, secret))
        raise AssertionError("Noninteractive provider must not be read")


def minimal_schema_document() -> dict[str, object]:
    """Return the smallest schema accepted by the report program."""
    return {
        "columns": [
            {
                "name": "ID",
                "type": "integer",
                "nullable": False,
            },
            {
                "name": "END_TIME",
                "type": "datetime",
                "nullable": True,
            },
            {
                "name": "ATTEMPT_TYPE",
                "type": "string",
                "nullable": False,
            },
            {
                "name": "ATTEMPT_RESULT",
                "type": "string",
                "nullable": False,
            },
            {
                "name": "LLM_SUGGESTIONS",
                "type": "json_object",
                "nullable": True,
            },
            {
                "name": "SELECTED_SUGGESTIONS",
                "type": "json_object",
                "nullable": True,
            },
            {
                "name": "FINAL_SUBMISSION",
                "type": "json_object",
                "nullable": True,
            },
        ]
    }


def write_schema(tmp_path: Path) -> Path:
    """Write the synthetic minimal report schema."""
    path = tmp_path / "schema.json"
    path.write_text(
        json.dumps(minimal_schema_document()),
        encoding="utf-8",
    )

    return path


def write_csv_rows(
    tmp_path: Path,
    rows: list[list[object]],
) -> Path:
    """Write synthetic CSV rows using the minimal schema."""
    path = tmp_path / "audit.csv"

    with path.open(
        mode="w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "ID",
                "END_TIME",
                "ATTEMPT_TYPE",
                "ATTEMPT_RESULT",
                "LLM_SUGGESTIONS",
                "SELECTED_SUGGESTIONS",
                "FINAL_SUBMISSION",
            ]
        )
        writer.writerows(rows)

    return path


def manual_csv_row(
    *,
    record_id: int = 1001,
) -> list[object]:
    """Return one synthetic completed manual CSV row."""
    final = {
        "title": "Synthetic title",
    }

    return [
        record_id,
        "05/18/2026 10:00:00.000000",
        "MANUAL",
        "COMPLETE",
        "",
        "",
        json.dumps(final),
    ]


def incomplete_ai_csv_row(
    *,
    record_id: int = 1002,
) -> list[object]:
    """Return one synthetic incomplete AI CSV row."""
    return [
        record_id,
        "",
        "AI",
        "USER_DROPPED",
        "",
        "",
        "",
    ]


def completed_ai_csv_row(
    *,
    record_id: int = 1003,
) -> list[object]:
    """Return one valid completed AI CSV row."""
    suggested: dict[str, object] = {
        "about": ["About suggestion"],
        "compensation": {
            "genericCompensation": [],
            "specificCompensation": [],
        },
        "contact": {
            "email": "",
            "name": "",
            "phone": "",
            "website": "",
        },
        "department": [],
        "description": ["Description suggestion"],
        "locations": [],
        "offersCompensation": False,
        "purpose": ["Purpose suggestion"],
        "title": ["Title suggestion"],
        "topics": [],
    }
    selected: dict[str, object] = {
        "about": ["About suggestion"],
        "compensation": {
            "genericCompensation": [],
            "specificCompensation": [],
        },
        "contact": {
            "email": "",
            "name": "",
            "phone": "",
            "website": "",
        },
        "department": [],
        "description": ["Description suggestion"],
        "locations": [],
        "purpose": ["Purpose suggestion"],
        "title": ["Title suggestion"],
        "topics": [],
    }
    final: dict[str, object] = {
        "about": "About suggestion",
        "compensation": "",
        "contact": {
            "email": "person@example.edu",
            "name": "Synthetic Person",
            "phone": "",
            "website": "",
        },
        "department": [],
        "description": "Description suggestion",
        "locations": [],
        "offersCompensation": False,
        "purpose": "Purpose suggestion",
        "title": "Title suggestion",
        "topics": [],
    }

    return [
        record_id,
        "05/18/2026 10:00:00.123456",
        "AI",
        "COMPLETE",
        json.dumps(suggested),
        json.dumps(selected),
        json.dumps(final),
    ]


def read_csv(
    path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    """Read a generated CSV header and rows."""
    with path.open(
        mode="r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames

        assert fieldnames is not None

        return list(fieldnames), list(reader)


def base_arguments(
    *,
    input_path: Path,
    schema_path: Path,
    output_directory: Path,
) -> list[str]:
    """Return explicit noninteractive CSV command arguments."""
    return [
        "csv",
        "--input",
        str(input_path),
        "--schema",
        str(schema_path),
        "--output",
        str(output_directory),
        "--no-env-file",
        "--no-prompt",
    ]


def test_parser_exposes_csv_command() -> None:
    parser = build_parser()
    namespace = parser.parse_args(
        [
            "csv",
            "--input",
            "audit.csv",
            "--schema",
            "schema.json",
            "--output",
            "report",
            "--include-text",
            "--encoding",
            "utf-8",
            "--delimiter",
            "|",
            "--quotechar",
            "'",
            "--escapechar",
            "\\",
            "--null-value",
            "",
            "--null-value",
            "NULL",
            "--env-file",
            "settings.env",
            "--no-prompt",
        ]
    )

    assert namespace.command == "csv"
    assert namespace.input_path == "audit.csv"
    assert namespace.schema_path == "schema.json"
    assert namespace.output_directory == "report"
    assert namespace.include_text is True
    assert namespace.encoding == "utf-8"
    assert namespace.delimiter == "|"
    assert namespace.quotechar == "'"
    assert namespace.escapechar == "\\"
    assert namespace.null_values == ["", "NULL"]
    assert namespace.env_file == "settings.env"
    assert namespace.no_env_file is False
    assert namespace.prompt_enabled is False


def test_parser_supports_negative_boolean_options() -> None:
    namespace = build_parser().parse_args(
        [
            "csv",
            "--no-include-text",
            "--no-prompt",
            "--no-env-file",
        ]
    )

    assert namespace.include_text is False
    assert namespace.prompt_enabled is False
    assert namespace.no_env_file is True
    assert namespace.env_file is None


def test_parser_requires_subcommand() -> None:
    with pytest.raises(SystemExit) as captured:
        build_parser().parse_args([])

    assert captured.value.code == 2


def test_csv_command_generates_normalized_report(
    tmp_path: Path,
) -> None:
    schema_path = write_schema(tmp_path)
    input_path = write_csv_rows(
        tmp_path,
        [
            manual_csv_row(record_id=1001),
            incomplete_ai_csv_row(record_id=1002),
        ],
    )
    output_directory = tmp_path / "report"
    standard_output = StringIO()
    error_output = StringIO()
    provider = NoninteractivePromptProvider()

    status = main(
        base_arguments(
            input_path=input_path,
            schema_path=schema_path,
            output_directory=output_directory,
        ),
        environment={},
        prompt_provider=provider,
        output=standard_output,
        error_output=error_output,
    )

    assert status == 0
    assert error_output.getvalue() == ""
    assert provider.read_calls == []

    records_path = output_directory / "records.csv"
    metrics_path = output_directory / "field_metrics.csv"

    assert records_path.is_file()
    assert metrics_path.is_file()

    record_header, record_rows = read_csv(records_path)
    metric_header, metric_rows = read_csv(metrics_path)

    assert tuple(record_header) == (
        "ID",
        "END_TIME",
        "ATTEMPT_TYPE",
        "ATTEMPT_RESULT",
        "LLM_SUGGESTIONS",
        "SELECTED_SUGGESTIONS",
        "FINAL_SUBMISSION",
    )
    assert len(record_rows) == 2
    assert record_rows[0]["ID"] == "1001"
    assert record_rows[0]["ATTEMPT_TYPE"] == "MANUAL"
    assert record_rows[0]["LLM_SUGGESTIONS"] == "\\N"
    assert record_rows[0]["SELECTED_SUGGESTIONS"] == "\\N"
    assert record_rows[0]["FINAL_SUBMISSION"].startswith("{")
    assert record_rows[1]["ID"] == "1002"
    assert record_rows[1]["END_TIME"] == "\\N"

    assert tuple(metric_header) == tuple(FLATTENED_COLUMNS)
    assert metric_rows == []

    output_text = standard_output.getvalue()

    assert f"Report directory: {output_directory}" in output_text
    assert f"Records CSV: {records_path}" in output_text
    assert f"Field metrics CSV: {metrics_path}" in output_text
    assert "Source rows: 2" in output_text
    assert "Analyzed rows: 0" in output_text
    assert "Skipped rows: 2" in output_text
    assert "Field metric rows: 0" in output_text


def test_csv_command_analyzes_completed_ai_row(
    tmp_path: Path,
) -> None:
    schema_path = write_schema(tmp_path)
    input_path = write_csv_rows(
        tmp_path,
        [completed_ai_csv_row()],
    )
    output_directory = tmp_path / "report"
    standard_output = StringIO()
    error_output = StringIO()

    status = main(
        base_arguments(
            input_path=input_path,
            schema_path=schema_path,
            output_directory=output_directory,
        ),
        environment={},
        prompt_provider=NoninteractivePromptProvider(),
        output=standard_output,
        error_output=error_output,
    )

    assert status == 0
    assert error_output.getvalue() == ""

    _, record_rows = read_csv(output_directory / "records.csv")
    metric_header, metric_rows = read_csv(output_directory / "field_metrics.csv")

    assert len(record_rows) == 1
    assert record_rows[0]["ID"] == "1003"
    assert record_rows[0]["END_TIME"] == ("2026-05-18T10:00:00.123456")

    assert tuple(metric_header) == tuple(FLATTENED_COLUMNS)
    assert len(metric_rows) == 12
    assert {row["record_id"] for row in metric_rows} == {"1003"}
    assert {row["field_name"] for row in metric_rows} == {
        "about",
        "compensation",
        "contact.email",
        "contact.name",
        "contact.phone",
        "contact.website",
        "department",
        "description",
        "locations",
        "purpose",
        "title",
        "topics",
    }
    assert all(row["selected_text"] == "\\N" for row in metric_rows)
    assert all(row["final_text"] == "\\N" for row in metric_rows)

    output_text = standard_output.getvalue()

    assert "Source rows: 1" in output_text
    assert "Analyzed rows: 1" in output_text
    assert "Skipped rows: 0" in output_text
    assert "Field metric rows: 12" in output_text


def test_csv_command_uses_environment_configuration(
    tmp_path: Path,
) -> None:
    schema_path = write_schema(tmp_path)
    input_path = write_csv_rows(
        tmp_path,
        [manual_csv_row()],
    )
    output_directory = tmp_path / "environment-report"
    standard_output = StringIO()
    error_output = StringIO()

    status = main(
        [
            "csv",
            "--no-env-file",
            "--no-prompt",
        ],
        environment={
            "STUDY_POSTING_AUDIT_CSV_INPUT": str(input_path),
            "STUDY_POSTING_AUDIT_SCHEMA": str(schema_path),
            "STUDY_POSTING_AUDIT_OUTPUT": str(output_directory),
        },
        prompt_provider=NoninteractivePromptProvider(),
        output=standard_output,
        error_output=error_output,
    )

    assert status == 0
    assert output_directory.is_dir()
    assert error_output.getvalue() == ""


def test_csv_command_uses_explicit_dotenv_file(
    tmp_path: Path,
) -> None:
    schema_path = write_schema(tmp_path)
    input_path = write_csv_rows(
        tmp_path,
        [manual_csv_row()],
    )
    output_directory = tmp_path / "dotenv-report"
    dotenv_path = tmp_path / "settings.env"
    dotenv_path.write_text(
        "\n".join(
            [
                f"STUDY_POSTING_AUDIT_CSV_INPUT={input_path}",
                f"STUDY_POSTING_AUDIT_SCHEMA={schema_path}",
                f"STUDY_POSTING_AUDIT_OUTPUT={output_directory}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    status = main(
        [
            "csv",
            "--env-file",
            str(dotenv_path),
            "--no-prompt",
        ],
        environment={},
        prompt_provider=NoninteractivePromptProvider(),
        output=StringIO(),
        error_output=StringIO(),
    )

    assert status == 0
    assert output_directory.is_dir()


def test_csv_command_reports_missing_input_without_traceback() -> None:
    standard_output = StringIO()
    error_output = StringIO()
    provider = NoninteractivePromptProvider()

    status = main(
        [
            "csv",
            "--no-env-file",
            "--no-prompt",
        ],
        environment={},
        prompt_provider=provider,
        output=standard_output,
        error_output=error_output,
    )

    assert status == 2
    assert standard_output.getvalue() == ""
    assert "error: Missing required configuration settings:" in (
        error_output.getvalue()
    )
    assert "- input_path" in error_output.getvalue()
    assert provider.read_calls == []


def test_csv_command_reports_missing_explicit_dotenv() -> None:
    error_output = StringIO()

    status = main(
        [
            "csv",
            "--env-file",
            "missing-explicit.env",
            "--no-prompt",
        ],
        environment={},
        prompt_provider=NoninteractivePromptProvider(),
        output=StringIO(),
        error_output=error_output,
    )

    assert status == 2
    assert "Required dotenv file does not exist" in error_output.getvalue()


def test_csv_command_reports_missing_schema(
    tmp_path: Path,
) -> None:
    input_path = write_csv_rows(
        tmp_path,
        [manual_csv_row()],
    )
    error_output = StringIO()

    status = main(
        [
            "csv",
            "--input",
            str(input_path),
            "--schema",
            str(tmp_path / "missing-schema.json"),
            "--output",
            str(tmp_path / "report"),
            "--no-env-file",
            "--no-prompt",
        ],
        environment={},
        prompt_provider=NoninteractivePromptProvider(),
        output=StringIO(),
        error_output=error_output,
    )

    assert status == 2
    assert "Could not read schema file" in error_output.getvalue()
    assert not (tmp_path / "report").exists()


def test_csv_command_reports_existing_output_directory(
    tmp_path: Path,
) -> None:
    schema_path = write_schema(tmp_path)
    input_path = write_csv_rows(
        tmp_path,
        [manual_csv_row()],
    )
    output_directory = tmp_path / "report"
    output_directory.mkdir()
    error_output = StringIO()

    status = main(
        base_arguments(
            input_path=input_path,
            schema_path=schema_path,
            output_directory=output_directory,
        ),
        environment={},
        prompt_provider=NoninteractivePromptProvider(),
        output=StringIO(),
        error_output=error_output,
    )

    assert status == 2
    assert "Output directory already exists" in error_output.getvalue()


def test_csv_command_reports_invalid_delimiter(
    tmp_path: Path,
) -> None:
    error_output = StringIO()

    status = main(
        [
            "csv",
            "--input",
            str(tmp_path / "input.csv"),
            "--delimiter",
            "::",
            "--no-env-file",
            "--no-prompt",
        ],
        environment={},
        prompt_provider=NoninteractivePromptProvider(),
        output=StringIO(),
        error_output=error_output,
    )

    assert status == 2
    assert "expected exactly one character" in error_output.getvalue()


def test_main_uses_default_output_streams(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    standard_output = StringIO()
    error_output = StringIO()
    monkeypatch.setattr(sys, "stdout", standard_output)
    monkeypatch.setattr(sys, "stderr", error_output)

    status = main(
        [
            "csv",
            "--no-env-file",
            "--no-prompt",
        ],
        environment={},
        prompt_provider=NoninteractivePromptProvider(),
    )

    assert status == 2
    assert standard_output.getvalue() == ""
    assert "input_path" in error_output.getvalue()


def test_main_uses_process_environment_when_not_injected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schema_path = write_schema(tmp_path)
    input_path = write_csv_rows(
        tmp_path,
        [manual_csv_row()],
    )
    output_directory = tmp_path / "process-environment-report"
    standard_output = StringIO()
    error_output = StringIO()

    monkeypatch.setenv(
        "STUDY_POSTING_AUDIT_CSV_INPUT",
        str(input_path),
    )
    monkeypatch.setenv(
        "STUDY_POSTING_AUDIT_SCHEMA",
        str(schema_path),
    )
    monkeypatch.setenv(
        "STUDY_POSTING_AUDIT_OUTPUT",
        str(output_directory),
    )

    status = main(
        [
            "csv",
            "--no-env-file",
            "--no-prompt",
        ],
        prompt_provider=NoninteractivePromptProvider(),
        output=standard_output,
        error_output=error_output,
    )

    assert status == 0
    assert output_directory.is_dir()
    assert error_output.getvalue() == ""


def test_main_constructs_default_prompt_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: list[object] = []

    class FakeTerminalPromptProvider:
        """Noninteractive replacement for the terminal provider."""

        def __init__(self) -> None:
            created.append(self)

        @property
        def is_interactive(self) -> bool:
            return False

        def read(
            self,
            prompt: str,
            *,
            secret: bool,
        ) -> str:
            raise AssertionError(f"Unexpected prompt {prompt!r}, secret={secret!r}")

    monkeypatch.setattr(
        "study_posting_audit_report.cli.TerminalPromptProvider",
        FakeTerminalPromptProvider,
    )

    status = main(
        [
            "csv",
            "--no-env-file",
            "--no-prompt",
        ],
        environment={},
        output=StringIO(),
        error_output=StringIO(),
    )

    assert status == 2
    assert len(created) == 1


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
        "study_posting_audit_report.cli.main",
        fake_main,
    )

    with pytest.raises(SystemExit) as captured:
        runpy.run_module(
            "study_posting_audit_report.__main__",
            run_name="__main__",
        )

    assert captured.value.code == 7
    assert calls == [()]
