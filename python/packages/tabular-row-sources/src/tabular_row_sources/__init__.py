"""Schema-aware lazy sources of canonical tabular rows.

CSV and database sources use a shared ``RowSchema`` and conversion layer to
produce the same ordered row shape and canonical Python value types.

The package contains no study-specific analysis, audit eligibility,
aggregation, report writing, application logging, or CLI policy.
"""

from tabular_row_sources.conversion import (
    convert_row,
    convert_value,
)
from tabular_row_sources.csv_source import (
    CsvReadOptions,
    CsvRowSource,
)
from tabular_row_sources.dbapi_source import (
    DbApiQuerySource,
    QueryParameters,
)
from tabular_row_sources.errors import (
    RowSourceError,
    SchemaDefinitionError,
    SourceConfigurationError,
    SourceExecutionError,
    SourceFormatError,
    ValueConversionError,
)
from tabular_row_sources.models import (
    ColumnSpec,
    ColumnType,
    Row,
    RowSchema,
)
from tabular_row_sources.protocols import RowSource
from tabular_row_sources.schema import (
    load_schema_json,
    parse_schema_json,
)
from tabular_row_sources.sql import read_sql_file

__version__ = "0.1.0"

__all__ = [
    "ColumnSpec",
    "ColumnType",
    "CsvReadOptions",
    "CsvRowSource",
    "DbApiQuerySource",
    "QueryParameters",
    "Row",
    "RowSchema",
    "RowSource",
    "RowSourceError",
    "SchemaDefinitionError",
    "SourceConfigurationError",
    "SourceExecutionError",
    "SourceFormatError",
    "ValueConversionError",
    "__version__",
    "convert_row",
    "convert_value",
    "load_schema_json",
    "parse_schema_json",
    "read_sql_file",
]
