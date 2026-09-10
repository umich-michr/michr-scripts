"""Layered configuration for the study-posting audit-report CSV command."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Protocol, cast

from program_configuration import (
    PromptProvider,
    SettingSpec,
    load_dotenv_file,
    parse_boolean,
    parse_nonblank_string,
    parse_path,
    resolve_configuration,
)
from study_posting_audit_report.paths import (
    default_dotenv_path,
    default_output_directory,
    default_schema_path,
)

_ENV_FILE = "STUDY_POSTING_AUDIT_ENV_FILE"
_PROMPT = "STUDY_POSTING_AUDIT_PROMPT"
_CSV_INPUT = "STUDY_POSTING_AUDIT_CSV_INPUT"
_SCHEMA = "STUDY_POSTING_AUDIT_SCHEMA"
_OUTPUT = "STUDY_POSTING_AUDIT_OUTPUT"
_INCLUDE_TEXT = "STUDY_POSTING_AUDIT_INCLUDE_TEXT"
_CSV_ENCODING = "STUDY_POSTING_AUDIT_CSV_ENCODING"
_CSV_DELIMITER = "STUDY_POSTING_AUDIT_CSV_DELIMITER"
_CSV_QUOTECHAR = "STUDY_POSTING_AUDIT_CSV_QUOTECHAR"
_CSV_ESCAPECHAR = "STUDY_POSTING_AUDIT_CSV_ESCAPECHAR"
_CSV_NULL_VALUES = "STUDY_POSTING_AUDIT_CSV_NULL_VALUES"

_DEFAULT_NULL_VALUES = ("", "\\N")


class CommandConfigurationArguments(Protocol):
    """Common unresolved arguments used before command-specific resolution."""

    @property
    def env_file(self) -> object:
        """Return the unresolved dotenv-file argument."""
        ...

    @property
    def no_env_file(self) -> bool:
        """Return whether dotenv loading is disabled."""
        ...

    @property
    def prompt_enabled(self) -> object:
        """Return the unresolved prompting flag."""
        ...


@dataclass(frozen=True, slots=True)
class CsvCommandArguments:
    """Unresolved command-line arguments for the CSV command."""

    input_path: object = None
    schema_path: object = None
    output_directory: object = None
    include_text: object = None
    encoding: object = None
    delimiter: object = None
    quotechar: object = None
    escapechar: object = None
    null_values: object = None
    env_file: object = None
    no_env_file: bool = False
    prompt_enabled: object = None


@dataclass(frozen=True, slots=True)
class CsvCommandConfig:
    """Typed configuration required to run the CSV command."""

    input_path: Path
    schema_path: Path
    output_directory: Path
    include_text: bool
    encoding: str
    delimiter: str
    quotechar: str
    escapechar: str | None
    null_values: frozenset[str]


def _parse_single_character(value: object) -> str:
    """Parse exactly one character."""
    if not isinstance(value, str) or len(value) != 1:
        raise ValueError("expected exactly one character")

    return value


def _parse_optional_single_character(value: object) -> str | None:
    """Parse one character or ``None``."""
    if value is None:
        return None

    return _parse_single_character(value)


def _parse_null_values(value: object) -> frozenset[str]:
    """Parse CSV null markers from a sequence or JSON-array string."""
    decoded: object = value

    if isinstance(value, str):
        if not value.strip():
            raise ValueError("expected a JSON array of strings")

        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"invalid JSON at line {error.lineno}, "
                f"column {error.colno}: {error.msg}"
            ) from error

    if not isinstance(decoded, Sequence) or isinstance(
        decoded,
        (str, bytes, bytearray),
    ):
        raise TypeError("expected a sequence of CSV null-marker strings")

    values = cast("Sequence[object]", decoded)
    markers: set[str] = set()

    for marker in values:
        if not isinstance(marker, str):
            raise TypeError("CSV null markers must be strings")

        markers.add(marker)

    return frozenset(markers)


def _environment_value(
    environment: Mapping[str, object],
    name: str,
) -> object:
    """Return one environment value or ``None``."""
    return environment.get(name)


def load_command_dotenv(
    arguments: CommandConfigurationArguments,
    *,
    environment: Mapping[str, object],
) -> dict[str, object]:
    """Load the selected command dotenv file.

    The dotenv path is resolved before the main configuration because a dotenv
    file cannot select itself.

    Precedence is:

    ```text
    --no-env-file
    → --env-file
    → process environment
    → workspace default
    ```
    """
    if arguments.no_env_file:
        return {}

    if arguments.env_file is not None:
        path = parse_path(arguments.env_file)

        return load_dotenv_file(
            path,
            required=True,
        )

    environment_path = _environment_value(
        environment,
        _ENV_FILE,
    )

    if (isinstance(environment_path, str) and environment_path.strip()) or isinstance(
        environment_path, Path
    ):
        path = parse_path(environment_path)

        return load_dotenv_file(
            path,
            required=True,
        )

    return load_dotenv_file(
        default_dotenv_path(),
        required=False,
    )


def resolve_prompt_enabled(
    arguments: CommandConfigurationArguments,
    *,
    environment: Mapping[str, object],
    dotenv: Mapping[str, object],
) -> bool:
    """Resolve whether interactive prompting is enabled."""
    resolved = resolve_configuration(
        (
            SettingSpec(
                name="prompt_enabled",
                environment_variable=_PROMPT,
                parser=parse_boolean,
                default=True,
            ),
        ),
        explicit={
            "prompt_enabled": arguments.prompt_enabled,
        },
        environment=environment,
        dotenv=dotenv,
        prompt_enabled=False,
    )
    value = resolved["prompt_enabled"]

    if type(value) is not bool:
        raise TypeError("Resolved prompt_enabled value must be a Boolean")

    return value


def _csv_setting_specs() -> tuple[SettingSpec, ...]:
    """Return declarative settings for the CSV command."""
    return (
        SettingSpec(
            name="input_path",
            environment_variable=_CSV_INPUT,
            parser=parse_path,
            prompt="CSV input path",
        ),
        SettingSpec(
            name="schema_path",
            environment_variable=_SCHEMA,
            parser=parse_path,
            default=default_schema_path(),
        ),
        SettingSpec(
            name="output_directory",
            environment_variable=_OUTPUT,
            parser=parse_path,
            default=default_output_directory(),
        ),
        SettingSpec(
            name="include_text",
            environment_variable=_INCLUDE_TEXT,
            parser=parse_boolean,
            default=False,
        ),
        SettingSpec(
            name="encoding",
            environment_variable=_CSV_ENCODING,
            parser=parse_nonblank_string,
            default="utf-8-sig",
        ),
        SettingSpec(
            name="delimiter",
            environment_variable=_CSV_DELIMITER,
            parser=_parse_single_character,
            default=",",
        ),
        SettingSpec(
            name="quotechar",
            environment_variable=_CSV_QUOTECHAR,
            parser=_parse_single_character,
            default='"',
        ),
        SettingSpec(
            name="escapechar",
            environment_variable=_CSV_ESCAPECHAR,
            parser=_parse_optional_single_character,
            default=None,
        ),
        SettingSpec(
            name="null_values",
            environment_variable=_CSV_NULL_VALUES,
            parser=_parse_null_values,
            default=_DEFAULT_NULL_VALUES,
        ),
    )


def _require_path(value: object, *, setting_name: str) -> Path:
    """Return one resolved path."""
    if not isinstance(value, Path):
        raise TypeError(f"Resolved {setting_name} value must be a Path")

    return value


def _require_string(value: object, *, setting_name: str) -> str:
    """Return one resolved string."""
    if not isinstance(value, str):
        raise TypeError(f"Resolved {setting_name} value must be a string")

    return value


def _require_boolean(value: object, *, setting_name: str) -> bool:
    """Return one resolved Boolean."""
    if type(value) is not bool:
        raise TypeError(f"Resolved {setting_name} value must be a Boolean")

    return value


def _require_optional_string(
    value: object,
    *,
    setting_name: str,
) -> str | None:
    """Return one resolved optional string."""
    if value is None:
        return None

    return _require_string(
        value,
        setting_name=setting_name,
    )


def _require_null_values(value: object) -> frozenset[str]:
    """Return resolved CSV null markers."""
    if not isinstance(value, frozenset):
        raise TypeError("Resolved null_values value must be a frozenset")

    values = cast("frozenset[object]", value)

    if not all(isinstance(marker, str) for marker in values):
        raise TypeError("Resolved null_values must contain strings")

    return cast("frozenset[str]", value)


def resolve_csv_command_config(
    arguments: CsvCommandArguments,
    *,
    environment: Mapping[str, object],
    dotenv: Mapping[str, object],
    prompt_provider: PromptProvider | None,
) -> CsvCommandConfig:
    """Resolve and type the CSV command configuration."""
    prompting_enabled = resolve_prompt_enabled(
        arguments,
        environment=environment,
        dotenv=dotenv,
    )
    resolved = resolve_configuration(
        _csv_setting_specs(),
        explicit={
            "input_path": arguments.input_path,
            "schema_path": arguments.schema_path,
            "output_directory": arguments.output_directory,
            "include_text": arguments.include_text,
            "encoding": arguments.encoding,
            "delimiter": arguments.delimiter,
            "quotechar": arguments.quotechar,
            "escapechar": arguments.escapechar,
            "null_values": arguments.null_values,
        },
        environment=environment,
        dotenv=dotenv,
        prompt_provider=prompt_provider,
        prompt_enabled=prompting_enabled,
    )

    return CsvCommandConfig(
        input_path=_require_path(
            resolved["input_path"],
            setting_name="input_path",
        ),
        schema_path=_require_path(
            resolved["schema_path"],
            setting_name="schema_path",
        ),
        output_directory=_require_path(
            resolved["output_directory"],
            setting_name="output_directory",
        ),
        include_text=_require_boolean(
            resolved["include_text"],
            setting_name="include_text",
        ),
        encoding=_require_string(
            resolved["encoding"],
            setting_name="encoding",
        ),
        delimiter=_require_string(
            resolved["delimiter"],
            setting_name="delimiter",
        ),
        quotechar=_require_string(
            resolved["quotechar"],
            setting_name="quotechar",
        ),
        escapechar=_require_optional_string(
            resolved["escapechar"],
            setting_name="escapechar",
        ),
        null_values=_require_null_values(
            resolved["null_values"],
        ),
    )
