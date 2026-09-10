"""Exceptions raised by schema-aware tabular row sources.

Consumers may catch ``RowSourceError`` for any expected package failure, or
catch a more specific subtype for schema, configuration, format, conversion,
and source-execution failures.
"""


class RowSourceError(Exception):
    """Base class for expected tabular row-source failures."""


class SchemaDefinitionError(RowSourceError):
    """A supplied row schema is malformed or internally inconsistent."""


class SourceConfigurationError(RowSourceError):
    """A row source has missing, invalid, or inconsistent configuration."""


class SourceFormatError(RowSourceError):
    """Source columns or row structure do not match the required schema."""


class ValueConversionError(SourceFormatError):
    """A source value cannot be converted to its declared schema type."""


class SourceExecutionError(RowSourceError):
    """A source cannot be opened, queried, fetched, or read."""
