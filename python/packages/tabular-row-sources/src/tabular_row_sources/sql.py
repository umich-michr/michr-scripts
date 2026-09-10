"""Loading of SQL text from files.

The DB-API query source executes SQL text and intentionally knows nothing about
files. This helper provides an explicit file-loading boundary for consumers that
store queries in version-controlled SQL files.

The helper does not parse, split, interpolate, normalize, or execute SQL.
"""

from pathlib import Path

from tabular_row_sources.errors import (
    SourceConfigurationError,
    SourceExecutionError,
)


def _require_sql_path(value: object) -> Path:
    """Return a nonblank SQL-file path."""
    if isinstance(value, str):
        if not value.strip():
            raise SourceConfigurationError("SQL file path must not be blank")

        return Path(value)

    if isinstance(value, Path):
        return value

    raise SourceConfigurationError("SQL file path must be a string or Path")


def _require_encoding(value: object) -> str:
    """Return a nonblank encoding name."""
    if not isinstance(value, str) or not value.strip():
        raise SourceConfigurationError("SQL file encoding must be a nonblank string")

    return value


def read_sql_file(
    path: str | Path,
    *,
    encoding: str = "utf-8-sig",
) -> str:
    """Read nonblank SQL text from a file.

    Parameters
    ----------
    path
        Path to the SQL file.
    encoding
        File encoding. Defaults to ``"utf-8-sig"`` so an optional UTF-8
        byte-order mark is removed while ordinary UTF-8 remains supported.

    Returns
    -------
    str
        SQL text exactly as stored after text decoding. Leading and trailing
        whitespace are preserved.

    Raises
    ------
    SourceConfigurationError
        If the path or encoding is invalid, or the file contains only
        whitespace.
    SourceExecutionError
        If the file cannot be opened, decoded, or read.

    Notes
    -----
    This function does not:

    - execute SQL;
    - split multiple statements;
    - interpolate variables;
    - validate database-specific syntax;
    - remove comments;
    - strip a trailing semicolon.
    """
    sql_path = _require_sql_path(path)
    validated_encoding = _require_encoding(encoding)

    try:
        sql = sql_path.read_text(encoding=validated_encoding)
    except (LookupError, OSError, UnicodeError) as error:
        raise SourceExecutionError(
            f"Could not read SQL file {sql_path}: {error}"
        ) from error

    if not sql.strip():
        raise SourceConfigurationError(f"SQL file {sql_path} is blank")

    return sql
