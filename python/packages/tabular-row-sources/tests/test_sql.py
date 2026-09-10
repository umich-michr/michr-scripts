"""Tests for SQL-file loading."""

from pathlib import Path
import re

import pytest

from tabular_row_sources import (
    SourceConfigurationError,
    SourceExecutionError,
    read_sql_file,
)


def test_read_sql_file_returns_text_unchanged(
    tmp_path: Path,
) -> None:
    path = tmp_path / "query.sql"
    sql = "  SELECT ID\n  FROM RECORDS;\n"
    path.write_text(sql, encoding="utf-8")

    assert read_sql_file(path) == sql


def test_read_sql_file_accepts_string_path(
    tmp_path: Path,
) -> None:
    path = tmp_path / "query.sql"
    path.write_text("SELECT 1", encoding="utf-8")

    assert read_sql_file(str(path)) == "SELECT 1"


def test_default_encoding_removes_utf8_bom(
    tmp_path: Path,
) -> None:
    path = tmp_path / "query.sql"
    path.write_text("SELECT 1", encoding="utf-8-sig")

    assert read_sql_file(path) == "SELECT 1"


def test_read_sql_file_supports_explicit_encoding(
    tmp_path: Path,
) -> None:
    path = tmp_path / "query.sql"
    path.write_text(
        "SELECT 'café'",
        encoding="utf-16",
    )

    assert (
        read_sql_file(
            path,
            encoding="utf-16",
        )
        == "SELECT 'café'"
    )


@pytest.mark.parametrize(
    "path",
    ["", "   ", "\n\t"],
    ids=["empty", "spaces", "tabs-newlines"],
)
def test_sql_file_path_must_not_be_blank(path: str) -> None:
    with pytest.raises(
        SourceConfigurationError,
        match="SQL file path must not be blank",
    ):
        read_sql_file(path)


def test_sql_file_path_must_be_string_or_path() -> None:
    with pytest.raises(
        SourceConfigurationError,
        match="SQL file path must be a string or Path",
    ):
        read_sql_file(42)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "encoding",
    ["", "   "],
    ids=["empty", "spaces"],
)
def test_sql_file_encoding_must_not_be_blank(
    tmp_path: Path,
    encoding: str,
) -> None:
    path = tmp_path / "query.sql"
    path.write_text("SELECT 1", encoding="utf-8")

    with pytest.raises(
        SourceConfigurationError,
        match="SQL file encoding must be a nonblank string",
    ):
        read_sql_file(
            path,
            encoding=encoding,
        )


def test_missing_sql_file_is_reported(
    tmp_path: Path,
) -> None:
    path = tmp_path / "missing.sql"

    with pytest.raises(
        SourceExecutionError,
        match="Could not read SQL file",
    ):
        read_sql_file(path)


def test_directory_path_is_reported(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        SourceExecutionError,
        match="Could not read SQL file",
    ):
        read_sql_file(tmp_path)


def test_unknown_encoding_is_reported(
    tmp_path: Path,
) -> None:
    path = tmp_path / "query.sql"
    path.write_text("SELECT 1", encoding="utf-8")

    with pytest.raises(
        SourceExecutionError,
        match="Could not read SQL file",
    ):
        read_sql_file(
            path,
            encoding="not-a-real-encoding",
        )


def test_invalid_text_encoding_is_reported(
    tmp_path: Path,
) -> None:
    path = tmp_path / "query.sql"
    path.write_bytes(b"SELECT '\xff'")

    with pytest.raises(
        SourceExecutionError,
        match="Could not read SQL file",
    ):
        read_sql_file(
            path,
            encoding="utf-8",
        )


@pytest.mark.parametrize(
    "sql",
    ["", "   ", "\n\t"],
    ids=["empty", "spaces", "tabs-newlines"],
)
def test_blank_sql_file_is_rejected(
    tmp_path: Path,
    sql: str,
) -> None:
    path = tmp_path / "query.sql"
    path.write_text(sql, encoding="utf-8")
    expected = f"SQL file {path} is blank"

    with pytest.raises(
        SourceConfigurationError,
        match=re.escape(expected),
    ):
        read_sql_file(path)


def test_sql_loader_does_not_strip_semicolon_or_comments(
    tmp_path: Path,
) -> None:
    path = tmp_path / "query.sql"
    sql = "-- report query\nSELECT * FROM RECORDS;\n"
    path.write_text(sql, encoding="utf-8")

    assert read_sql_file(path) == sql
