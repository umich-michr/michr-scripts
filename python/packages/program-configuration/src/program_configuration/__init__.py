"""Reusable layered, typed, and secret-aware program configuration.

The core resolver accepts explicit, process-environment, and dotenv mappings.
Dotenv files are loaded explicitly without mutating the process environment.
Interactive prompting is injectable and can be disabled by consumers.
"""

from program_configuration.dotenv import load_dotenv_file
from program_configuration.errors import (
    ConfigurationError,
    ConfigurationValueError,
    DotenvFileError,
    MissingConfigurationError,
    PromptError,
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
from program_configuration.prompting import (
    PromptProvider,
    TerminalPromptProvider,
)
from program_configuration.resolution import resolve_configuration

__version__ = "0.1.0"

__all__ = [
    "MISSING",
    "ConfigurationError",
    "ConfigurationValueError",
    "DotenvFileError",
    "MissingConfigurationError",
    "PromptError",
    "PromptProvider",
    "ResolvedConfiguration",
    "ResolvedValue",
    "SettingDefinitionError",
    "SettingParser",
    "SettingSpec",
    "TerminalPromptProvider",
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
