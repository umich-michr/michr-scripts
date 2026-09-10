"""Tests for the schema-aware lazy CSV row source."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import TextIO

import pytest

from tabular_row_sources import (
    ColumnSpec,
    ColumnType,
    CsvReadOptions,
    CsvRowSource,
    Row,
    RowSchema,
    RowSource,
    SourceConfigurationError,
    SourceExecutionError,
    SourceFormatError,
    ValueConversionError,
)


def simple_schema() -> RowSchema:
    """Return a two-column schema used by most CSV tests."""
    return RowSchema(
        columns=(
            ColumnSpec(
                name="ID",
                data_type=ColumnType.INTEGER,
            ),
            ColumnSpec(
                name="TITLE",
                data_type=ColumnType.STRING,
            ),
        )
    )


def representative_schema() -> RowSchema:
    """Return a schema covering every canonical data type."""
    return RowSchema(
        columns=(
            ColumnSpec(
                name="ID",
                data_type=ColumnType.INTEGER,
            ),
            ColumnSpec(
                name="TITLE",
                data_type=ColumnType.STRING,
            ),
            ColumnSpec(
                name="AMOUNT",
                data_type=ColumnType.DECIMAL,
            ),
            ColumnSpec(
                name="SCORE",
                data_type=ColumnType.FLOAT,
            ),
            ColumnSpec(
                name="ACTIVE",
                data_type=ColumnType.BOOLEAN,
            ),
            ColumnSpec(
                name="CREATED_DATE",
                data_type=ColumnType.DATE,
            ),
            ColumnSpec(
                name="CREATED_AT",
                data_type=ColumnType.DATETIME,
            ),
            ColumnSpec(
                name="PAYLOAD",
                data_type=ColumnType.JSON_OBJECT,
            ),
            ColumnSpec(
                name="OPTIONAL_TEXT",
                data_type=ColumnType.STRING,
                nullable=True,
            ),
        )
    )


def write_csv(
    tmp_path: Path,
    text: str,
    *,
    encoding: str = "utf-8",
) -> Path:
    """Write a CSV fixture and return its path."""
    path = tmp_path / "input.csv"
    path.write_text(
        text,
        encoding=encoding,
        newline="",
    )

    return path


def collect_rows(source: RowSource) -> list[Row]:
    """Consume a row source through its public protocol."""
    with source.open_rows() as rows:
        return list(rows)


def consume_one_then_fail(source: RowSource) -> None:
    """Read one row, then simulate a consumer failure."""
    with source.open_rows() as rows:
        next(rows)
        raise RuntimeError("consumer failed")


# ---------------------------------------------------------------------------
# Basic behavior and canonical conversion
# ---------------------------------------------------------------------------


def test_csv_source_satisfies_row_source_protocol(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "ID,TITLE\n1,Example\n",
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    assert isinstance(source, RowSource)


def test_csv_source_converts_every_canonical_type(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        (
            "ID,TITLE,AMOUNT,SCORE,ACTIVE,CREATED_DATE,"
            "CREATED_AT,PAYLOAD,OPTIONAL_TEXT\n"
            "42,Example,12.50,0.75,true,2026-09-09,"
            '2026-09-09T14:59:35Z,"{""name"": ""Example""}",NULL\n'
        ),
    )
    source = CsvRowSource(
        path=path,
        schema=representative_schema(),
        null_values=frozenset({"NULL"}),
    )

    rows = collect_rows(source)

    assert len(rows) == 1

    row = rows[0]

    assert tuple(row) == representative_schema().column_names
    assert row["ID"] == 42
    assert row["TITLE"] == "Example"
    assert row["AMOUNT"] == Decimal("12.50")
    assert row["SCORE"] == pytest.approx(0.75)
    assert row["ACTIVE"] is True
    assert row["CREATED_DATE"] == date(2026, 9, 9)
    assert row["OPTIONAL_TEXT"] is None
    assert row["PAYLOAD"] == {"name": "Example"}

    created_at = row["CREATED_AT"]

    assert isinstance(created_at, datetime)
    assert created_at.utcoffset() == timedelta(0)


def test_csv_source_yields_multiple_rows_in_file_order(
    tmp_path: Path,
) -> None:
    path = write_csv(
        tmp_path,
        "ID,TITLE\n1,First\n2,Second\n3,Third\n",
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    assert collect_rows(source) == [
        {"ID": 1, "TITLE": "First"},
        {"ID": 2, "TITLE": "Second"},
        {"ID": 3, "TITLE": "Third"},
    ]


def test_csv_source_yields_fresh_dictionaries(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "ID,TITLE\n1,First\n1,First\n",
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    first, second = collect_rows(source)

    assert first == second
    assert first is not second


def test_csv_source_can_be_opened_repeatedly(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "ID,TITLE\n1,Example\n",
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    first = collect_rows(source)
    second = collect_rows(source)

    assert first == second
    assert first[0] is not second[0]


def test_csv_source_with_header_only_yields_no_rows(
    tmp_path: Path,
) -> None:
    path = write_csv(tmp_path, "ID,TITLE\n")
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    assert collect_rows(source) == []


# ---------------------------------------------------------------------------
# CSV syntax and encoding
# ---------------------------------------------------------------------------


def test_default_encoding_removes_utf8_bom(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "ID,TITLE\n1,Example\n",
        encoding="utf-8-sig",
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    assert collect_rows(source) == [{"ID": 1, "TITLE": "Example"}]


def test_quoted_comma_remains_inside_field(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        'ID,TITLE\n1,"First, second"\n',
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    assert collect_rows(source) == [{"ID": 1, "TITLE": "First, second"}]


def test_multiline_quoted_field_is_one_logical_record(
    tmp_path: Path,
) -> None:
    path = write_csv(
        tmp_path,
        'ID,TITLE\n1,"First line\nSecond line"\n2,Other\n',
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    assert collect_rows(source) == [
        {"ID": 1, "TITLE": "First line\nSecond line"},
        {"ID": 2, "TITLE": "Other"},
    ]


def test_custom_delimiter_is_supported(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "ID|TITLE\n1|Example\n",
    )
    options = CsvReadOptions(delimiter="|")
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
        options=options,
    )

    assert collect_rows(source) == [{"ID": 1, "TITLE": "Example"}]


def test_custom_quote_character_is_supported(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "ID,TITLE\n1,'First, second'\n",
    )
    options = CsvReadOptions(quotechar="'")
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
        options=options,
    )

    assert collect_rows(source) == [{"ID": 1, "TITLE": "First, second"}]


def test_escape_character_is_supported(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        'ID,TITLE\n1,"A \\"quoted\\" title"\n',
    )
    options = CsvReadOptions(
        escapechar="\\",
        doublequote=False,
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
        options=options,
    )

    assert collect_rows(source) == [{"ID": 1, "TITLE": 'A "quoted" title'}]


def test_skipinitialspace_is_supported(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "ID,TITLE\n1, Example\n",
    )
    options = CsvReadOptions(skipinitialspace=True)
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
        options=options,
    )

    assert collect_rows(source) == [{"ID": 1, "TITLE": "Example"}]


def test_invalid_utf8_in_header_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "input.csv"
    path.write_bytes(b"ID,TITL\xff\n1,Example\n")

    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
        encoding="utf-8",
    )

    with pytest.raises(
        SourceExecutionError,
        match="Could not decode CSV file",
    ):
        collect_rows(source)


def test_invalid_utf8_in_data_is_reported(
    tmp_path: Path,
) -> None:
    """Text buffering prevents reliable attribution to a logical record."""
    path = tmp_path / "input.csv"
    path.write_bytes(b"ID,TITLE\n1,Exam\xffple\n")

    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
        encoding="utf-8",
    )

    with pytest.raises(
        SourceExecutionError,
        match="Could not decode CSV file",
    ):
        collect_rows(source)


def test_malformed_csv_header_is_reported(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        'ID,"TITLE\n',
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    with pytest.raises(
        SourceFormatError,
        match="Could not parse CSV header",
    ):
        collect_rows(source)


def test_malformed_csv_data_is_reported(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        'ID,TITLE\n1,"unterminated\n',
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    with pytest.raises(
        SourceFormatError,
        match="Could not parse CSV record",
    ):
        collect_rows(source)


# ---------------------------------------------------------------------------
# Null markers
# ---------------------------------------------------------------------------


def test_empty_csv_field_is_preserved_by_default(
    tmp_path: Path,
) -> None:
    schema = RowSchema(
        columns=(
            ColumnSpec(
                name="ID",
                data_type=ColumnType.INTEGER,
            ),
            ColumnSpec(
                name="TITLE",
                data_type=ColumnType.STRING,
                nullable=True,
            ),
        )
    )
    path = write_csv(
        tmp_path,
        "ID,TITLE\n1,\n",
    )
    source = CsvRowSource(
        path=path,
        schema=schema,
    )

    assert collect_rows(source) == [{"ID": 1, "TITLE": ""}]


def test_explicit_null_marker_becomes_none(tmp_path: Path) -> None:
    schema = RowSchema(
        columns=(
            ColumnSpec(
                name="ID",
                data_type=ColumnType.INTEGER,
            ),
            ColumnSpec(
                name="TITLE",
                data_type=ColumnType.STRING,
                nullable=True,
            ),
        )
    )
    path = write_csv(
        tmp_path,
        "ID,TITLE\n1,NULL\n",
    )
    source = CsvRowSource(
        path=path,
        schema=schema,
        null_values=frozenset({"NULL"}),
    )

    assert collect_rows(source) == [{"ID": 1, "TITLE": None}]


def test_empty_string_can_be_an_explicit_null_marker(
    tmp_path: Path,
) -> None:
    schema = RowSchema(
        columns=(
            ColumnSpec(
                name="ID",
                data_type=ColumnType.INTEGER,
            ),
            ColumnSpec(
                name="TITLE",
                data_type=ColumnType.STRING,
                nullable=True,
            ),
        )
    )
    path = write_csv(
        tmp_path,
        "ID,TITLE\n1,\n",
    )
    source = CsvRowSource(
        path=path,
        schema=schema,
        null_values=frozenset({""}),
    )

    assert collect_rows(source) == [{"ID": 1, "TITLE": None}]


def test_null_marker_in_nonnullable_column_is_rejected(
    tmp_path: Path,
) -> None:
    path = write_csv(
        tmp_path,
        "ID,TITLE\nNULL,Example\n",
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
        null_values=frozenset({"NULL"}),
    )

    with pytest.raises(
        ValueConversionError,
        match="Row 2, column 'ID' is null",
    ):
        collect_rows(source)


def test_null_marker_matching_is_exact(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "ID,TITLE\n1,null\n",
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
        null_values=frozenset({"NULL"}),
    )

    assert collect_rows(source) == [{"ID": 1, "TITLE": "null"}]


# ---------------------------------------------------------------------------
# Header validation
# ---------------------------------------------------------------------------


def test_empty_file_is_rejected(tmp_path: Path) -> None:
    path = write_csv(tmp_path, "")
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    with pytest.raises(
        SourceFormatError,
        match="is empty and has no header row",
    ):
        collect_rows(source)


def test_blank_header_name_is_rejected(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "ID,\n1,Example\n",
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    with pytest.raises(
        SourceFormatError,
        match="blank column names at positions",
    ):
        collect_rows(source)


def test_whitespace_only_header_name_is_rejected(
    tmp_path: Path,
) -> None:
    path = write_csv(
        tmp_path,
        'ID,"   "\n1,Example\n',
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    with pytest.raises(
        SourceFormatError,
        match="blank column names at positions",
    ):
        collect_rows(source)


def test_duplicate_header_names_are_rejected(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "ID,ID\n1,2\n",
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    with pytest.raises(
        SourceFormatError,
        match="duplicate column names",
    ):
        collect_rows(source)


@pytest.mark.parametrize(
    "header",
    [
        "TITLE,ID",
        "ID",
        "ID,TITLE,EXTRA",
        "id,TITLE",
    ],
    ids=["reordered", "missing", "extra", "wrong-case"],
)
def test_header_must_match_exact_schema_order(
    tmp_path: Path,
    header: str,
) -> None:
    path = write_csv(
        tmp_path,
        f"{header}\n1,Example\n",
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    with pytest.raises(
        SourceFormatError,
        match="CSV header does not match schema order",
    ):
        collect_rows(source)


# ---------------------------------------------------------------------------
# Data-record shape and conversion
# ---------------------------------------------------------------------------


def test_record_with_too_few_fields_is_rejected(
    tmp_path: Path,
) -> None:
    path = write_csv(
        tmp_path,
        "ID,TITLE\n1\n",
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    with pytest.raises(
        SourceFormatError,
        match=r"CSV record 2 .* has 1 fields; expected 2",
    ):
        collect_rows(source)


def test_record_with_too_many_fields_is_rejected(
    tmp_path: Path,
) -> None:
    path = write_csv(
        tmp_path,
        "ID,TITLE\n1,Example,Unexpected\n",
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    with pytest.raises(
        SourceFormatError,
        match=r"CSV record 2 .* has 3 fields; expected 2",
    ):
        collect_rows(source)


def test_blank_physical_line_is_a_malformed_record(
    tmp_path: Path,
) -> None:
    path = write_csv(
        tmp_path,
        "ID,TITLE\n\n",
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    with pytest.raises(
        SourceFormatError,
        match=r"CSV record 2 .* has 0 fields; expected 2",
    ):
        collect_rows(source)


def test_conversion_failure_reports_logical_record_number(
    tmp_path: Path,
) -> None:
    path = write_csv(
        tmp_path,
        "ID,TITLE\n1,First\nnot-an-integer,Second\n",
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    with pytest.raises(
        ValueConversionError,
        match="Row 3, column 'ID'",
    ):
        collect_rows(source)


def test_multiline_record_uses_logical_record_number(
    tmp_path: Path,
) -> None:
    path = write_csv(
        tmp_path,
        'ID,TITLE\n1,"First\nSecond"\nnot-an-integer,Other\n',
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
    )

    with pytest.raises(
        ValueConversionError,
        match="Row 3, column 'ID'",
    ):
        collect_rows(source)


# ---------------------------------------------------------------------------
# Configuration validation and properties
# ---------------------------------------------------------------------------


def test_csv_source_exposes_configuration(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "ID,TITLE\n1,Example\n",
    )
    schema = simple_schema()
    options = CsvReadOptions(
        delimiter=",",
        quotechar='"',
        escapechar="\\",
        doublequote=False,
        skipinitialspace=True,
        strict=True,
    )
    null_values = frozenset({"NULL"})

    source = CsvRowSource(
        path=path,
        schema=schema,
        encoding="utf-8",
        null_values=null_values,
        options=options,
    )

    assert source.path == path
    assert source.schema is schema
    assert source.encoding == "utf-8"
    assert source.null_values == null_values
    assert source.options is options


def test_blank_string_path_is_rejected() -> None:
    with pytest.raises(
        SourceConfigurationError,
        match="CSV path must not be blank",
    ):
        CsvRowSource(
            path="   ",
            schema=simple_schema(),
        )


def test_non_schema_value_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(
        SourceConfigurationError,
        match="CSV schema must be a RowSchema",
    ):
        CsvRowSource(
            path=tmp_path / "input.csv",
            schema=None,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "encoding",
    ["", "   "],
    ids=["empty", "spaces"],
)
def test_blank_encoding_is_rejected(
    tmp_path: Path,
    encoding: str,
) -> None:
    with pytest.raises(
        SourceConfigurationError,
        match="CSV encoding must be a nonblank string",
    ):
        CsvRowSource(
            path=tmp_path / "input.csv",
            schema=simple_schema(),
            encoding=encoding,
        )


def test_non_frozenset_null_values_are_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        SourceConfigurationError,
        match="CSV null_values must be a frozenset",
    ):
        CsvRowSource(
            path=tmp_path / "input.csv",
            schema=simple_schema(),
            null_values={"NULL"},  # type: ignore[arg-type]
        )


def test_non_string_null_marker_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(
        SourceConfigurationError,
        match="null_values must contain strings only",
    ):
        CsvRowSource(
            path=tmp_path / "input.csv",
            schema=simple_schema(),
            null_values=frozenset({1}),  # type: ignore[arg-type]
        )


def test_non_options_value_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(
        SourceConfigurationError,
        match="CSV options must be CsvReadOptions",
    ):
        CsvRowSource(
            path=tmp_path / "input.csv",
            schema=simple_schema(),
            options="csv",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        ("delimiter", {"delimiter": ""}),
        ("delimiter", {"delimiter": "::"}),
        ("quotechar", {"quotechar": ""}),
        ("quotechar", {"quotechar": '""'}),
        ("escapechar", {"escapechar": "::"}),
    ],
    ids=[
        "empty-delimiter",
        "long-delimiter",
        "empty-quotechar",
        "long-quotechar",
        "long-escapechar",
    ],
)
def test_single_character_options_are_validated(
    field_name: str,
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(
        SourceConfigurationError,
        match=rf"CSV {field_name} must be exactly one character",
    ):
        CsvReadOptions(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        ("doublequote", {"doublequote": 1}),
        ("skipinitialspace", {"skipinitialspace": 0}),
        ("strict", {"strict": "true"}),
    ],
    ids=["doublequote", "skipinitialspace", "strict"],
)
def test_boolean_options_require_exact_booleans(
    field_name: str,
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(
        SourceConfigurationError,
        match=rf"CSV {field_name} must be a Boolean",
    ):
        CsvReadOptions(**kwargs)  # type: ignore[arg-type]


def test_delimiter_and_quotechar_must_differ() -> None:
    with pytest.raises(
        SourceConfigurationError,
        match="delimiter and quotechar must be different",
    ):
        CsvReadOptions(
            delimiter='"',
            quotechar='"',
        )


def test_default_options_are_documented_values() -> None:
    options = CsvReadOptions()

    assert options.delimiter == ","
    assert options.quotechar == '"'
    assert options.escapechar is None
    assert options.doublequote is True
    assert options.skipinitialspace is False
    assert options.strict is True


# ---------------------------------------------------------------------------
# File-opening and lifecycle behavior
# ---------------------------------------------------------------------------


def test_missing_file_is_reported(tmp_path: Path) -> None:
    source = CsvRowSource(
        path=tmp_path / "missing.csv",
        schema=simple_schema(),
    )

    with pytest.raises(
        SourceExecutionError,
        match="Could not open CSV file",
    ):
        collect_rows(source)


def test_directory_path_is_reported_as_open_failure(
    tmp_path: Path,
) -> None:
    source = CsvRowSource(
        path=tmp_path,
        schema=simple_schema(),
    )

    with pytest.raises(
        SourceExecutionError,
        match="Could not open CSV file",
    ):
        collect_rows(source)


def test_unknown_encoding_is_reported(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "ID,TITLE\n1,Example\n",
    )
    source = CsvRowSource(
        path=path,
        schema=simple_schema(),
        encoding="not-a-real-encoding",
    )

    with pytest.raises(
        SourceExecutionError,
        match="Could not open CSV file",
    ):
        collect_rows(source)


class TrackingCsvRowSource(CsvRowSource):
    """CSV source backed by an inspectable in-memory text handle."""

    def __init__(
        self,
        *,
        text: str,
        schema: RowSchema,
    ) -> None:
        super().__init__(
            path="memory.csv",
            schema=schema,
        )
        self.handle = StringIO(text)

    def _open_file(self) -> TextIO:
        """Return the in-memory handle."""
        return self.handle


def test_file_closes_after_normal_completion() -> None:
    source = TrackingCsvRowSource(
        text="ID,TITLE\n1,Example\n",
        schema=simple_schema(),
    )

    assert collect_rows(source) == [{"ID": 1, "TITLE": "Example"}]
    assert source.handle.closed is True


def test_file_closes_after_early_termination() -> None:
    source = TrackingCsvRowSource(
        text="ID,TITLE\n1,First\n2,Second\n",
        schema=simple_schema(),
    )

    with source.open_rows() as rows:
        assert next(rows) == {"ID": 1, "TITLE": "First"}

    assert source.handle.closed is True


def test_file_closes_after_conversion_failure() -> None:
    source = TrackingCsvRowSource(
        text="ID,TITLE\ninvalid,Example\n",
        schema=simple_schema(),
    )

    with pytest.raises(ValueConversionError):
        collect_rows(source)

    assert source.handle.closed is True


def test_file_closes_after_consumer_failure() -> None:
    source = TrackingCsvRowSource(
        text="ID,TITLE\n1,Example\n",
        schema=simple_schema(),
    )

    with pytest.raises(RuntimeError, match="consumer failed"):
        consume_one_then_fail(source)

    assert source.handle.closed is True


def test_data_records_are_not_read_until_iterator_advances() -> None:
    source = TrackingCsvRowSource(
        text='ID,TITLE\n1,"unterminated\n',
        schema=simple_schema(),
    )

    # Entering the context reads and validates the header only.
    with source.open_rows():
        pass

    assert source.handle.closed is True
