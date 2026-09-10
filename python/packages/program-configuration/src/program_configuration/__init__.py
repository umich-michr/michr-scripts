"""Reusable layered, typed, and secret-aware program configuration.

The core resolver is pure: callers supply explicit, process-environment, and
dotenv mappings. Filesystem dotenv loading and prompting are separate concerns.
"""

from program_configuration.errors import (
    ConfigurationError,
    ConfigurationValueError,
    MissingConfigurationError,
    SettingDefinitionError,
    UnknownExplicitSettingError,
)
from program_configuration.models import (
    MISSING,
    ResolvedConfiguration,
    ResolvedValue,
    SettingParser,
    SettingSpec,
    ValueSource,
)
from program_configuration.parsing import (
    parse_boolean,
    parse_integer,
    parse_json_object,
    parse_nonblank_string,
    parse_path,
    parse_positive_integer,
)
from program_configuration.resolution import resolve_configuration

__version__ = "0.1.0"

__all__ = [
    "MISSING",
    "ConfigurationError",
    "ConfigurationValueError",
    "MissingConfigurationError",
    "ResolvedConfiguration",
    "ResolvedValue",
    "SettingDefinitionError",
    "SettingParser",
    "SettingSpec",
    "UnknownExplicitSettingError",
    "ValueSource",
    "__version__",
    "parse_boolean",
    "parse_integer",
    "parse_json_object",
    "parse_nonblank_string",
    "parse_path",
    "parse_positive_integer",
    "resolve_configuration",
]
