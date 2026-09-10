"""Schema and row models for tabular row sources.

The schema defines one canonical row shape and the Python types produced by
every source implementation. CSV and database sources may receive different
native values, but after conversion they must yield values conforming to the
same ``RowSchema``.

Column order is significant and must be preserved.
"""

from dataclasses import dataclass
from enum import StrEnum

from tabular_row_sources.errors import SchemaDefinitionError

#: One canonical tabular row keyed by schema column name.
type Row = dict[str, object]


class ColumnType(StrEnum):
    """Supported canonical column types.

    Attributes
    ----------
    STRING
        Python ``str``.
    INTEGER
        Python ``int``, excluding ``bool``.
    DECIMAL
        Python ``decimal.Decimal``.
    FLOAT
        Python ``float``.
    BOOLEAN
        Python ``bool``.
    DATE
        Python ``datetime.date`` but not ``datetime.datetime``.
    DATETIME
        Python ``datetime.datetime``.
    JSON_OBJECT
        Python ``dict[str, object]``.
    """

    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    JSON_OBJECT = "json_object"


def _require_column_name(value: object) -> str:
    """Return a valid nonblank column name."""
    if not isinstance(value, str):
        raise SchemaDefinitionError("Column name must be a string")

    if not value.strip():
        raise SchemaDefinitionError("Column name must not be blank")

    return value


def _require_column_type(value: object) -> ColumnType:
    """Return a valid ``ColumnType`` member."""
    if not isinstance(value, ColumnType):
        raise SchemaDefinitionError("Column data_type must be a ColumnType member")

    return value


def _require_boolean(value: object, *, field_name: str) -> bool:
    """Return an exact Boolean value."""
    if type(value) is not bool:
        raise SchemaDefinitionError(f"{field_name} must be a Boolean")

    return value


@dataclass(frozen=True, slots=True)
class ColumnSpec:
    """Definition of one canonical output column.

    Parameters
    ----------
    name
        Nonblank, case-sensitive column name.
    data_type
        Canonical type produced by every source.
    nullable
        Whether the canonical value may be ``None``.
    """

    name: str
    data_type: ColumnType
    nullable: bool = False

    def __post_init__(self) -> None:
        """Validate the column definition."""
        _require_column_name(self.name)
        _require_column_type(self.data_type)
        _require_boolean(self.nullable, field_name="Column nullable")


def _require_columns(value: object) -> tuple[ColumnSpec, ...]:
    """Return a nonempty tuple containing only ``ColumnSpec`` values."""
    if not isinstance(value, tuple):
        raise SchemaDefinitionError("Schema columns must be a tuple")

    if not value:
        raise SchemaDefinitionError("Schema must define at least one column")

    columns: list[ColumnSpec] = []

    for column in value:
        if not isinstance(column, ColumnSpec):
            raise SchemaDefinitionError(
                "Schema columns must contain ColumnSpec values only"
            )

        columns.append(column)

    return tuple(columns)


@dataclass(frozen=True, slots=True)
class RowSchema:
    """Ordered schema shared by tabular row sources.

    Parameters
    ----------
    columns
        Ordered, nonempty tuple of unique column definitions.

    Notes
    -----
    Column names are case-sensitive. Every source must produce exactly these
    columns in this order unless a future explicitly documented projection mode
    is introduced.
    """

    columns: tuple[ColumnSpec, ...]

    def __post_init__(self) -> None:
        """Validate schema columns and reject duplicate names."""
        columns = _require_columns(self.columns)
        seen: set[str] = set()

        for column in columns:
            if column.name in seen:
                raise SchemaDefinitionError(
                    f"Schema contains duplicate column name: {column.name!r}"
                )

            seen.add(column.name)

    @property
    def column_names(self) -> tuple[str, ...]:
        """Return canonical column names in schema order."""
        return tuple(column.name for column in self.columns)

    @property
    def columns_by_name(self) -> dict[str, ColumnSpec]:
        """Return column definitions keyed by name in schema order."""
        return {column.name: column for column in self.columns}

    def __len__(self) -> int:
        """Return the number of schema columns."""
        return len(self.columns)
