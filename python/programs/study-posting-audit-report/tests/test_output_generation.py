"""Tests for atomic two-file study-posting report generation."""

from collections.abc import Generator, Iterator
from contextlib import AbstractContextManager, contextmanager
import csv
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from study_posting_ai_analysis import FLATTENED_COLUMNS
from study_posting_audit_report import (
    AI_ASSISTANCE_METRICS_FILENAME,
    RECORDS_FILENAME,
    AuditOutputError,
    AuditReportConfig,
    AuditReportConfigurationError,
    AuditRowError,
    AuditSourceError,
    CsvOutputOptions,
    generate_csv_report,
)
from tabular_row_sources import (
    ColumnSpec,
    ColumnType,
    Row,
    RowSchema,
    SourceExecutionError,
)


def valid_analysis_objects() -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    """Return valid synthetic suggested, selected, and final objects."""
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
            "name": "Test Person",
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

    return suggested, selected, final


def audit_schema() -> RowSchema:
    """Return a source schema containing audit and provenance columns."""
    return RowSchema(
        columns=(
            ColumnSpec(
                name="ID",
                data_type=ColumnType.INTEGER,
            ),
            ColumnSpec(
                name="END_TIME",
                data_type=ColumnType.DATETIME,
                nullable=True,
            ),
            ColumnSpec(
                name="ATTEMPT_TYPE",
                data_type=ColumnType.STRING,
            ),
            ColumnSpec(
                name="ATTEMPT_RESULT",
                data_type=ColumnType.STRING,
            ),
            ColumnSpec(
                name="STUDY_NUM",
                data_type=ColumnType.STRING,
                nullable=True,
            ),
            ColumnSpec(
                name="CREATED_DATE",
                data_type=ColumnType.DATE,
                nullable=True,
            ),
            ColumnSpec(
                name="LATENCY_MS",
                data_type=ColumnType.DECIMAL,
                nullable=True,
            ),
            ColumnSpec(
                name="LLM_SUGGESTIONS",
                data_type=ColumnType.JSON_OBJECT,
                nullable=True,
            ),
            ColumnSpec(
                name="SELECTED_SUGGESTIONS",
                data_type=ColumnType.JSON_OBJECT,
                nullable=True,
            ),
            ColumnSpec(
                name="FINAL_SUBMISSION",
                data_type=ColumnType.JSON_OBJECT,
                nullable=True,
            ),
        )
    )


def completed_ai_row(
    *,
    record_id: int = 1001,
) -> Row:
    """Return one valid completed AI source row."""
    suggested, selected, final = valid_analysis_objects()

    return {
        "ID": record_id,
        "END_TIME": datetime.fromisoformat("2026-09-09T15:04:35.123456"),
        "ATTEMPT_TYPE": "AI",
        "ATTEMPT_RESULT": "COMPLETE",
        "STUDY_NUM": "SYNTHETIC-0001",
        "CREATED_DATE": date(2026, 9, 9),
        "LATENCY_MS": Decimal("125.50"),
        "LLM_SUGGESTIONS": suggested,
        "SELECTED_SUGGESTIONS": selected,
        "FINAL_SUBMISSION": final,
    }


def manual_row(
    *,
    record_id: int = 1002,
) -> Row:
    """Return one completed manual row preserved without analysis."""
    _, _, final = valid_analysis_objects()

    return {
        "ID": record_id,
        "END_TIME": datetime.fromisoformat("2026-09-09T15:04:35"),
        "ATTEMPT_TYPE": "MANUAL",
        "ATTEMPT_RESULT": "COMPLETE",
        "STUDY_NUM": "SYNTHETIC-0002",
        "CREATED_DATE": None,
        "LATENCY_MS": None,
        "LLM_SUGGESTIONS": None,
        "SELECTED_SUGGESTIONS": None,
        "FINAL_SUBMISSION": final,
    }


def incomplete_ai_row(
    *,
    record_id: int = 1003,
    attempt_result: str = "USER_DROPPED",
) -> Row:
    """Return one incomplete AI row preserved without analysis."""
    return {
        "ID": record_id,
        "END_TIME": None,
        "ATTEMPT_TYPE": "AI",
        "ATTEMPT_RESULT": attempt_result,
        "STUDY_NUM": "SYNTHETIC-0003",
        "CREATED_DATE": None,
        "LATENCY_MS": None,
        "LLM_SUGGESTIONS": None,
        "SELECTED_SUGGESTIONS": None,
        "FINAL_SUBMISSION": None,
    }


class InMemoryRowSource:
    """Context-managed synthetic source for report-generation tests."""

    def __init__(
        self,
        *,
        schema: RowSchema,
        rows: list[Row],
        failure: Exception | None = None,
    ) -> None:
        self._schema = schema
        self._rows = rows
        self._failure = failure
        self.open_count = 0
        self.closed = False

    @property
    def schema(self) -> RowSchema:
        """Return the source schema."""
        return self._schema

    def open_rows(
        self,
    ) -> AbstractContextManager[Iterator[Row]]:
        """Return a new source context manager."""
        return self._open_rows()

    @contextmanager
    def _open_rows(self) -> Generator[Iterator[Row]]:
        """Yield fresh rows and record context closure."""
        self.open_count += 1
        self.closed = False

        def iterate() -> Iterator[Row]:
            for row in self._rows:
                yield dict(row)

            if self._failure is not None:
                raise self._failure

        try:
            yield iterate()
        finally:
            self.closed = True


def read_csv_rows(
    path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    """Return one CSV header and all rows."""
    with path.open(
        mode="r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames

        assert fieldnames is not None

        return list(fieldnames), list(reader)


def staging_directories(parent: Path, destination_name: str) -> list[Path]:
    """Return temporary report directories left beside a destination."""
    return sorted(parent.glob(f".{destination_name}.*"))


# ---------------------------------------------------------------------------
# Successful report publication
# ---------------------------------------------------------------------------


def test_generate_report_writes_two_files_and_summary(
    tmp_path: Path,
) -> None:
    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[
            manual_row(record_id=1001),
            incomplete_ai_row(record_id=1002),
            completed_ai_row(record_id=1003),
        ],
    )
    output_directory = tmp_path / "report"

    report = generate_csv_report(
        source,
        output_directory=output_directory,
    )

    assert report.output_directory == output_directory
    assert report.records_path == output_directory / RECORDS_FILENAME
    assert report.ai_assistance_metrics_path == (
        output_directory / AI_ASSISTANCE_METRICS_FILENAME
    )

    assert output_directory.is_dir()
    assert report.records_path.is_file()
    assert report.ai_assistance_metrics_path.is_file()

    assert report.summary.source_rows == 3
    assert report.summary.analyzable_rows == 1
    assert report.summary.analyzed_rows == 1
    assert report.summary.skipped_rows == 2
    assert report.summary.failed_rows == 0
    assert report.summary.ai_assistance_rows == 12

    assert source.open_count == 1
    assert source.closed is True
    assert staging_directories(tmp_path, "report") == []


def test_records_csv_preserves_schema_columns_and_every_source_row(
    tmp_path: Path,
) -> None:
    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[
            manual_row(record_id=1001),
            incomplete_ai_row(record_id=1002),
            completed_ai_row(record_id=1003),
        ],
    )

    report = generate_csv_report(
        source,
        output_directory=tmp_path / "report",
    )

    header, rows = read_csv_rows(report.records_path)

    assert tuple(header) == audit_schema().column_names
    assert len(rows) == 3

    assert rows[0]["ID"] == "1001"
    assert rows[0]["ATTEMPT_TYPE"] == "MANUAL"
    assert rows[0]["ATTEMPT_RESULT"] == "COMPLETE"
    assert rows[0]["END_TIME"] == "2026-09-09T15:04:35"
    assert rows[0]["CREATED_DATE"] == "\\N"
    assert rows[0]["LATENCY_MS"] == "\\N"
    assert rows[0]["LLM_SUGGESTIONS"] == "\\N"
    assert rows[0]["FINAL_SUBMISSION"].startswith("{")

    assert rows[1]["ID"] == "1002"
    assert rows[1]["ATTEMPT_TYPE"] == "AI"
    assert rows[1]["ATTEMPT_RESULT"] == "USER_DROPPED"
    assert rows[1]["END_TIME"] == "\\N"
    assert rows[1]["LLM_SUGGESTIONS"] == "\\N"
    assert rows[1]["SELECTED_SUGGESTIONS"] == "\\N"
    assert rows[1]["FINAL_SUBMISSION"] == "\\N"

    assert rows[2]["ID"] == "1003"
    assert rows[2]["ATTEMPT_TYPE"] == "AI"
    assert rows[2]["ATTEMPT_RESULT"] == "COMPLETE"
    assert rows[2]["END_TIME"] == "2026-09-09T15:04:35.123456"
    assert rows[2]["CREATED_DATE"] == "2026-09-09"
    assert rows[2]["LATENCY_MS"] == "125.50"

    suggestions = rows[2]["LLM_SUGGESTIONS"]

    assert suggestions.startswith("{")
    assert '"title":["Title suggestion"]' in suggestions


def test_only_completed_ai_rows_produce_field_metrics(
    tmp_path: Path,
) -> None:
    manual = manual_row(record_id=1001)
    manual["LLM_SUGGESTIONS"] = "not-json"
    manual["SELECTED_SUGGESTIONS"] = "also-not-json"

    incomplete = incomplete_ai_row(record_id=1002)
    incomplete["LLM_SUGGESTIONS"] = "not-json"
    incomplete["SELECTED_SUGGESTIONS"] = "also-not-json"

    completed = completed_ai_row(record_id=1003)

    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[
            manual,
            incomplete,
            completed,
        ],
    )

    report = generate_csv_report(
        source,
        output_directory=tmp_path / "report",
    )

    _, record_rows = read_csv_rows(report.records_path)
    _, ai_assistance_rows = read_csv_rows(report.ai_assistance_metrics_path)

    assert len(record_rows) == 3
    assert report.summary.source_rows == 3
    assert report.summary.analyzable_rows == 1
    assert report.summary.analyzed_rows == 1
    assert report.summary.skipped_rows == 2
    assert report.summary.failed_rows == 0
    assert report.summary.ai_assistance_rows == 12
    assert {row["record_id"] for row in ai_assistance_rows} == {"1003"}


def test_ai_assistance_metrics_csv_uses_canonical_columns(
    tmp_path: Path,
) -> None:
    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[completed_ai_row()],
    )

    report = generate_csv_report(
        source,
        output_directory=tmp_path / "report",
    )

    header, rows = read_csv_rows(report.ai_assistance_metrics_path)

    assert tuple(header) == tuple(FLATTENED_COLUMNS)
    assert len(rows) == 12
    assert {row["record_id"] for row in rows} == {"1001"}
    assert {row["field_name"] for row in rows} == {
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


def test_ai_assistance_metrics_exclude_free_text_by_default(
    tmp_path: Path,
) -> None:
    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[completed_ai_row()],
    )

    report = generate_csv_report(
        source,
        output_directory=tmp_path / "report",
    )

    _, rows = read_csv_rows(report.ai_assistance_metrics_path)

    assert all(row["selected_text"] == "\\N" for row in rows)
    assert all(row["final_text"] == "\\N" for row in rows)


def test_ai_assistance_metrics_include_text_when_enabled(
    tmp_path: Path,
) -> None:
    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[completed_ai_row()],
    )

    report = generate_csv_report(
        source,
        output_directory=tmp_path / "report",
        config=AuditReportConfig(include_text=True),
    )

    _, rows = read_csv_rows(report.ai_assistance_metrics_path)
    title = next(row for row in rows if row["field_name"] == "title")

    assert title["selected_text"] == "Title suggestion"
    assert title["final_text"] == "Title suggestion"


def test_empty_source_publishes_header_only_files(
    tmp_path: Path,
) -> None:
    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[],
    )

    report = generate_csv_report(
        source,
        output_directory=tmp_path / "report",
    )

    record_header, record_rows = read_csv_rows(report.records_path)
    metric_header, ai_assistance_rows = read_csv_rows(report.ai_assistance_metrics_path)

    assert tuple(record_header) == audit_schema().column_names
    assert tuple(metric_header) == tuple(FLATTENED_COLUMNS)
    assert record_rows == []
    assert ai_assistance_rows == []

    assert report.summary.source_rows == 0
    assert report.summary.analyzable_rows == 0
    assert report.summary.analyzed_rows == 0
    assert report.summary.skipped_rows == 0
    assert report.summary.failed_rows == 0
    assert report.summary.ai_assistance_rows == 0


def test_custom_output_options_apply_to_both_files(
    tmp_path: Path,
) -> None:
    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[manual_row()],
    )
    output_directory = tmp_path / "report"

    generate_csv_report(
        source,
        output_directory=output_directory,
        output_options=CsvOutputOptions(
            encoding="utf-8",
            null_value="NULL",
            lineterminator="\r\n",
        ),
    )

    records_bytes = (output_directory / RECORDS_FILENAME).read_bytes()
    metrics_bytes = (output_directory / AI_ASSISTANCE_METRICS_FILENAME).read_bytes()

    assert b"\r\n" in records_bytes
    assert b"\r\n" in metrics_bytes

    _, rows = read_csv_rows(output_directory / RECORDS_FILENAME)

    assert rows[0]["CREATED_DATE"] == "NULL"


def test_parent_directories_are_created(
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "nested" / "reports" / "run-1"
    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[],
    )

    report = generate_csv_report(
        source,
        output_directory=output_directory,
    )

    assert report.output_directory == output_directory
    assert output_directory.is_dir()


# ---------------------------------------------------------------------------
# Configuration validation
# ---------------------------------------------------------------------------


def test_existing_output_directory_is_rejected(
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "report"
    output_directory.mkdir()
    marker = output_directory / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[],
    )

    with pytest.raises(
        AuditReportConfigurationError,
        match="Output directory already exists",
    ):
        generate_csv_report(
            source,
            output_directory=output_directory,
        )

    assert marker.read_text(encoding="utf-8") == "keep"


def test_existing_output_file_is_rejected(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "report"
    output_path.write_text("existing", encoding="utf-8")

    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[],
    )

    with pytest.raises(
        AuditReportConfigurationError,
        match="Output directory already exists",
    ):
        generate_csv_report(
            source,
            output_directory=output_path,
        )

    assert output_path.read_text(encoding="utf-8") == "existing"


@pytest.mark.parametrize(
    "value",
    ["", "   ", "\n\t"],
    ids=["empty", "spaces", "tabs-newlines"],
)
def test_output_directory_must_not_be_blank(value: str) -> None:
    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[],
    )

    with pytest.raises(
        AuditReportConfigurationError,
        match="output_directory must not be blank",
    ):
        generate_csv_report(
            source,
            output_directory=value,
        )


def test_output_directory_must_be_string_or_path() -> None:
    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[],
    )
    invalid_path = cast("str | Path", 42)

    with pytest.raises(
        AuditReportConfigurationError,
        match="output_directory must be a string or Path",
    ):
        generate_csv_report(
            source,
            output_directory=invalid_path,
        )


def test_config_must_be_report_config(tmp_path: Path) -> None:
    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[],
    )
    invalid_config = cast("AuditReportConfig", object())

    with pytest.raises(
        AuditReportConfigurationError,
        match="config must be an AuditReportConfig",
    ):
        generate_csv_report(
            source,
            output_directory=tmp_path / "report",
            config=invalid_config,
        )


def test_output_options_must_be_csv_options(
    tmp_path: Path,
) -> None:
    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[],
    )
    invalid_options = cast("CsvOutputOptions", object())

    with pytest.raises(
        AuditReportConfigurationError,
        match="output_options must be CsvOutputOptions",
    ):
        generate_csv_report(
            source,
            output_directory=tmp_path / "report",
            output_options=invalid_options,
        )


# ---------------------------------------------------------------------------
# Fail-fast publication and cleanup
# ---------------------------------------------------------------------------


def test_missing_required_schema_column_publishes_nothing(
    tmp_path: Path,
) -> None:
    incomplete_schema = RowSchema(
        columns=(
            ColumnSpec(
                name="ID",
                data_type=ColumnType.INTEGER,
            ),
        )
    )
    source = InMemoryRowSource(
        schema=incomplete_schema,
        rows=[],
    )
    output_directory = tmp_path / "report"

    with pytest.raises(
        AuditRowError,
        match="source schema is missing required columns",
    ):
        generate_csv_report(
            source,
            output_directory=output_directory,
        )

    assert not output_directory.exists()
    assert staging_directories(tmp_path, "report") == []


def test_duplicate_record_id_publishes_nothing(
    tmp_path: Path,
) -> None:
    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[
            manual_row(record_id=1001),
            completed_ai_row(record_id=1001),
        ],
    )
    output_directory = tmp_path / "report"

    with pytest.raises(
        AuditRowError,
        match="duplicate record ID",
    ):
        generate_csv_report(
            source,
            output_directory=output_directory,
        )

    assert source.closed is True
    assert not output_directory.exists()
    assert staging_directories(tmp_path, "report") == []


def test_completed_ai_row_with_missing_payload_publishes_nothing(
    tmp_path: Path,
) -> None:
    row = completed_ai_row()
    row["SELECTED_SUGGESTIONS"] = None

    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[row],
    )
    output_directory = tmp_path / "report"

    with pytest.raises(
        AuditRowError,
        match="completed AI row requires all analysis payloads",
    ):
        generate_csv_report(
            source,
            output_directory=output_directory,
        )

    assert source.closed is True
    assert not output_directory.exists()
    assert staging_directories(tmp_path, "report") == []


def test_completed_ai_row_without_end_time_publishes_nothing(
    tmp_path: Path,
) -> None:
    row = completed_ai_row()
    row["END_TIME"] = None

    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[row],
    )
    output_directory = tmp_path / "report"

    with pytest.raises(
        AuditRowError,
        match="completed AI row requires non-null column 'END_TIME'",
    ):
        generate_csv_report(
            source,
            output_directory=output_directory,
        )

    assert source.closed is True
    assert not output_directory.exists()
    assert staging_directories(tmp_path, "report") == []


def test_analysis_failure_publishes_nothing(
    tmp_path: Path,
) -> None:
    row = completed_ai_row()
    final = row["FINAL_SUBMISSION"]

    assert isinstance(final, dict)

    final["title"] = ""

    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[row],
    )
    output_directory = tmp_path / "report"

    with pytest.raises(
        AuditRowError,
        match="analysis failed",
    ):
        generate_csv_report(
            source,
            output_directory=output_directory,
        )

    assert source.closed is True
    assert not output_directory.exists()
    assert staging_directories(tmp_path, "report") == []


def test_row_source_failure_is_wrapped_and_publishes_nothing(
    tmp_path: Path,
) -> None:
    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[manual_row()],
        failure=SourceExecutionError("source failed"),
    )
    output_directory = tmp_path / "report"

    with pytest.raises(
        AuditSourceError,
        match="Could not read audit source: source failed",
    ) as captured:
        generate_csv_report(
            source,
            output_directory=output_directory,
        )

    assert isinstance(captured.value.__cause__, SourceExecutionError)
    assert source.closed is True
    assert not output_directory.exists()
    assert staging_directories(tmp_path, "report") == []


def test_reserved_null_marker_string_publishes_nothing(
    tmp_path: Path,
) -> None:
    row = manual_row()
    row["STUDY_NUM"] = "\\N"

    source = InMemoryRowSource(
        schema=audit_schema(),
        rows=[row],
    )
    output_directory = tmp_path / "report"

    with pytest.raises(
        AuditOutputError,
        match="contains the reserved null marker",
    ):
        generate_csv_report(
            source,
            output_directory=output_directory,
        )

    assert source.closed is True
    assert not output_directory.exists()
    assert staging_directories(tmp_path, "report") == []


def test_unsupported_output_value_publishes_nothing(
    tmp_path: Path,
) -> None:
    schema = RowSchema(
        columns=(
            *audit_schema().columns,
            ColumnSpec(
                name="UNSUPPORTED",
                data_type=ColumnType.STRING,
                nullable=True,
            ),
        )
    )
    row = manual_row()
    row["UNSUPPORTED"] = cast("str", ["not", "serializable"])

    source = InMemoryRowSource(
        schema=schema,
        rows=[row],
    )
    output_directory = tmp_path / "report"

    with pytest.raises(
        AuditOutputError,
        match="unsupported output type list",
    ):
        generate_csv_report(
            source,
            output_directory=output_directory,
        )

    assert source.closed is True
    assert not output_directory.exists()
    assert staging_directories(tmp_path, "report") == []


# ---------------------------------------------------------------------------
# Public constants and report model
# ---------------------------------------------------------------------------


def test_output_filenames_are_stable() -> None:
    assert RECORDS_FILENAME == "records.csv"
    assert AI_ASSISTANCE_METRICS_FILENAME == "ai_assistance_metrics.csv"
