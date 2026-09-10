"""Reusable layered, typed, and secret-aware program configuration.

The core resolver is pure: callers supply explicit, process-environment, and
dotenv mappings. Dotenv files are loaded explicitly without mutating the
process environment. Prompting remains a separate concern.
"""

from program_configuration.dotenv import load_dotenv_file
from program_configuration.errors import (
    ConfigurationError,
    ConfigurationValueError,
    DotenvFileError,
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
    "DotenvFileError",
    "MissingConfigurationError",
    "ResolvedConfiguration",
    "ResolvedValue",
    "SettingDefinitionError",
    "SettingParser",
    "SettingSpec",
    "UnknownExplicitSettingError",
    "ValueSource",
    "__version__",
    "load_dotenv_file",
    "parse_boolean",
    "parse_integer",
    "parse_json_object",
    "parse_nonblank_string",
    "parse_path",
    "parse_positive_integer",
    "resolve_configuration",
]
