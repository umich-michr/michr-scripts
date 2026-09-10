"""Lazy, schema-aware CSV row source.

The CSV source validates its header against a ``RowSchema``, reads records
lazily, applies explicit null markers, converts values through the shared
canonical conversion layer, and closes the input file deterministically.

CSV fields remain strings unless the schema converts them. An empty CSV field is
preserved as ``""`` unless the caller explicitly includes ``""`` in
``null_values``.
"""

from collections import Counter
from collections.abc import Generator, Iterator
from contextlib import AbstractContextManager, contextmanager
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO, cast

from tabular_row_sources.conversion import convert_row
from tabular_row_sources.errors import (
    SourceConfigurationError,
    SourceExecutionError,
    SourceFormatError,
)
from tabular_row_sources.models import Row, RowSchema


def _require_single_character(
    value: object,
    *,
    field_name: str,
) -> str:
    """Return a string containing exactly one character."""
    if not isinstance(value, str) or len(value) != 1:
        raise SourceConfigurationError(f"{field_name} must be exactly one character")

    return value


def _require_optional_single_character(
    value: object,
    *,
    field_name: str,
) -> str | None:
    """Return ``None`` or a string containing exactly one character."""
    if value is None:
        return None

    return _require_single_character(
        value,
        field_name=field_name,
    )


def _require_boolean(
    value: object,
    *,
    field_name: str,
) -> bool:
    """Return an exact Boolean configuration value."""
    if type(value) is not bool:
        raise SourceConfigurationError(f"{field_name} must be a Boolean")

    return value


@dataclass(frozen=True, slots=True)
class CsvReadOptions:
    """CSV parser configuration.

    Parameters
    ----------
    delimiter
        Field delimiter. Must contain exactly one character.
    quotechar
        Quoting character. Must contain exactly one character.
    escapechar
        Optional escape character.
    doublequote
        Whether two consecutive quote characters represent one quote.
    skipinitialspace
        Whether spaces immediately following a delimiter are ignored.
    strict
        Whether malformed CSV input raises ``csv.Error``.
    """

    delimiter: str = ","
    quotechar: str = '"'
    escapechar: str | None = None
    doublequote: bool = True
    skipinitialspace: bool = False
    strict: bool = True

    def __post_init__(self) -> None:
        """Validate parser options."""
        delimiter = _require_single_character(
            self.delimiter,
            field_name="CSV delimiter",
        )
        quotechar = _require_single_character(
            self.quotechar,
            field_name="CSV quotechar",
        )
        _require_optional_single_character(
            self.escapechar,
            field_name="CSV escapechar",
        )
        _require_boolean(
            self.doublequote,
            field_name="CSV doublequote",
        )
        _require_boolean(
            self.skipinitialspace,
            field_name="CSV skipinitialspace",
        )
        _require_boolean(
            self.strict,
            field_name="CSV strict",
        )

        if delimiter == quotechar:
            raise SourceConfigurationError(
                "CSV delimiter and quotechar must be different"
            )


def _require_schema(value: object) -> RowSchema:
    """Return a valid row schema."""
    if not isinstance(value, RowSchema):
        raise SourceConfigurationError("CSV schema must be a RowSchema")

    return value


def _require_encoding(value: object) -> str:
    """Return a nonblank text encoding name."""
    if not isinstance(value, str) or not value.strip():
        raise SourceConfigurationError("CSV encoding must be a nonblank string")

    return value


def _require_null_values(
    value: object,
) -> frozenset[str]:
    """Return validated CSV null markers."""
    if value is None:
        return frozenset()

    if not isinstance(value, frozenset):
        raise SourceConfigurationError("CSV null_values must be a frozenset of strings")

    untyped_markers = cast("frozenset[object]", value)
    markers: set[str] = set()

    for marker in untyped_markers:
        if not isinstance(marker, str):
            raise SourceConfigurationError("CSV null_values must contain strings only")

        markers.add(marker)

    return frozenset(markers)


def _duplicate_names(names: list[str]) -> list[str]:
    """Return duplicate names in sorted order."""
    counts = Counter(names)

    return sorted(name for name, count in counts.items() if count > 1)


def _validate_header(
    header: list[str],
    *,
    schema: RowSchema,
) -> None:
    """Validate CSV header names against the schema."""
    if not header:
        raise SourceFormatError("CSV file does not contain a header row")

    blank_positions = [
        position for position, name in enumerate(header, start=1) if not name.strip()
    ]

    if blank_positions:
        raise SourceFormatError(
            f"CSV header contains blank column names at positions: {blank_positions}"
        )

    duplicates = _duplicate_names(header)

    if duplicates:
        raise SourceFormatError(
            f"CSV header contains duplicate column names: {duplicates}"
        )

    expected_names = schema.column_names
    actual_name_set = set(header)
    expected_name_set = set(expected_names)

    missing = [name for name in expected_names if name not in actual_name_set]
    unexpected = [name for name in header if name not in expected_name_set]

    if missing or unexpected:
        raise SourceFormatError(
            "CSV header columns do not match schema names: "
            f"missing {missing!r}; unexpected {unexpected!r}"
        )


def _apply_null_markers(
    values: list[str],
    *,
    null_values: frozenset[str],
) -> list[object]:
    """Replace explicitly configured CSV null markers with ``None``."""
    return [None if value in null_values else value for value in values]


def _read_header(
    reader: Iterator[list[str]],
    *,
    path: Path,
) -> list[str]:
    """Read one CSV header and translate parser failures."""
    try:
        return next(reader)
    except StopIteration as error:
        raise SourceFormatError(
            f"CSV file {path} is empty and has no header row"
        ) from error
    except csv.Error as error:
        raise SourceFormatError(
            f"Could not parse CSV header in {path}: {error}"
        ) from error
    except UnicodeDecodeError as error:
        raise SourceExecutionError(
            f"Could not decode CSV file {path}: {error}"
        ) from error


def _iter_csv_rows(
    reader: Iterator[list[str]],
    *,
    path: Path,
    header: tuple[str, ...],
    schema: RowSchema,
    null_values: frozenset[str],
) -> Iterator[Row]:
    """Lazily read, validate, and convert CSV data records."""
    record_number = 1
    expected_count = len(header)

    while True:
        try:
            values = next(reader)
        except StopIteration:
            return
        except csv.Error as error:
            raise SourceFormatError(
                f"Could not parse CSV record after record "
                f"{record_number} in {path}: {error}"
            ) from error
        except UnicodeDecodeError as error:
            # TextIO may decode ahead of the logical record currently being
            # requested, so a byte's record cannot be identified reliably.
            raise SourceExecutionError(
                f"Could not decode CSV file {path}: {error}"
            ) from error

        record_number += 1

        if len(values) != expected_count:
            raise SourceFormatError(
                f"CSV record {record_number} in {path} has "
                f"{len(values)} fields; expected {expected_count}"
            )

        source_values = _apply_null_markers(
            values,
            null_values=null_values,
        )

        source_row: dict[object, object] = dict(
            zip(
                header,
                source_values,
                strict=True,
            )
        )

        yield convert_row(
            source_row,
            schema=schema,
            row_number=record_number,
        )


class CsvRowSource:
    """Lazy, schema-aware CSV source.

    Parameters
    ----------
    path
        CSV file path.
    schema
        Exact schema required of the CSV header and data rows.
    encoding
        File encoding. Defaults to ``"utf-8-sig"`` so an optional UTF-8 byte
        order mark is removed while ordinary UTF-8 remains supported.
    null_values
        Explicit CSV field values converted to ``None``. Defaults to no null
        markers, so an empty field remains ``""``.
    options
        CSV parser options.

    Notes
    -----
    Data-record numbers begin at 2 because record 1 is the header. They count
    logical CSV records rather than physical lines; quoted fields may span more
    than one physical line.
    """

    def __init__(
        self,
        *,
        path: str | Path,
        schema: RowSchema,
        encoding: str = "utf-8-sig",
        null_values: frozenset[str] | None = None,
        options: CsvReadOptions | None = None,
    ) -> None:
        if isinstance(path, str) and not path.strip():
            raise SourceConfigurationError("CSV path must not be blank")

        self._path = Path(path)
        self._schema = _require_schema(schema)
        self._encoding = _require_encoding(encoding)
        self._null_values = _require_null_values(null_values)
        self._options = options if options is not None else CsvReadOptions()

        if not isinstance(self._options, CsvReadOptions):
            raise SourceConfigurationError("CSV options must be CsvReadOptions")

    @property
    def path(self) -> Path:
        """Return the configured CSV path."""
        return self._path

    @property
    def schema(self) -> RowSchema:
        """Return the canonical output schema."""
        return self._schema

    @property
    def encoding(self) -> str:
        """Return the configured text encoding."""
        return self._encoding

    @property
    def null_values(self) -> frozenset[str]:
        """Return explicit CSV null markers."""
        return self._null_values

    @property
    def options(self) -> CsvReadOptions:
        """Return CSV parser options."""
        return self._options

    def _open_file(self) -> TextIO:
        """Open the configured CSV file."""
        try:
            return self._path.open(
                mode="r",
                encoding=self._encoding,
                newline="",
            )
        except (LookupError, OSError) as error:
            raise SourceExecutionError(
                f"Could not open CSV file {self._path}: {error}"
            ) from error

    def open_rows(
        self,
    ) -> AbstractContextManager[Iterator[Row]]:
        """Return a new context manager for lazily reading CSV rows."""
        return self._open_rows()

    @contextmanager
    def _open_rows(self) -> Generator[Iterator[Row]]:
        """Open the CSV file and lazily yield canonical rows.

        The file closes when the context exits, including on early termination or
        an exception.
        """
        handle = self._open_file()

        try:
            reader = csv.reader(
                handle,
                delimiter=self._options.delimiter,
                quotechar=self._options.quotechar,
                escapechar=self._options.escapechar,
                doublequote=self._options.doublequote,
                skipinitialspace=self._options.skipinitialspace,
                strict=self._options.strict,
            )

            header = _read_header(
                reader,
                path=self._path,
            )
            _validate_header(
                header,
                schema=self._schema,
            )

            yield _iter_csv_rows(
                reader,
                path=self._path,
                header=tuple(header),
                schema=self._schema,
                null_values=self._null_values,
            )
        finally:
            handle.close()
