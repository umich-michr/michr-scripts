"""Layered configuration for the audit-report database command."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from program_configuration import (
    ConfigurationValueError,
    PromptProvider,
    SettingSpec,
    parse_boolean,
    parse_json_object,
    parse_nonblank_string,
    parse_path,
    parse_positive_integer,
    resolve_configuration,
)
from study_posting_audit_report.cli_config import (
    load_command_dotenv,
    resolve_prompt_enabled,
)
from study_posting_audit_report.paths import (
    default_output_directory,
    default_schema_path,
    default_sql_path,
)

_DB_DRIVER = "STUDY_POSTING_AUDIT_DB_DRIVER"
_DB_DSN = "STUDY_POSTING_AUDIT_DB_DSN"
_DB_USERNAME = "STUDY_POSTING_AUDIT_DB_USERNAME"
# This constant is an environment-variable name, not a credential value.
_DB_SECRET_ENVIRONMENT_VARIABLE = "STUDY_POSTING_AUDIT_DB_PASSWORD"  # noqa: S105  # nosec B105
_DB_FETCH_SIZE = "STUDY_POSTING_AUDIT_DB_FETCH_SIZE"
_SQL_FILE = "STUDY_POSTING_AUDIT_SQL_FILE"
_SQL_PARAMETERS = "STUDY_POSTING_AUDIT_SQL_PARAMS"
_SCHEMA = "STUDY_POSTING_AUDIT_SCHEMA"
_OUTPUT = "STUDY_POSTING_AUDIT_OUTPUT"
_INCLUDE_TEXT = "STUDY_POSTING_AUDIT_INCLUDE_TEXT"


@dataclass(frozen=True, slots=True)
class DatabaseCommandArguments:
    """Unresolved command-line arguments for the database command.

    Password is intentionally absent because literal command-line passwords
    are not supported.
    """

    driver: object = None
    dsn: object = None
    username: object = None
    sql_path: object = None
    schema_path: object = None
    output_directory: object = None
    fetch_size: object = None
    sql_parameters_json: object = None
    sql_parameter_overrides: object = None
    include_text: object = None
    env_file: object = None
    no_env_file: bool = False
    prompt_enabled: object = None


@dataclass(frozen=True, slots=True, repr=False)
class DatabaseCommandConfig:
    """Typed configuration required to run the database command."""

    driver: str
    dsn: str
    username: str
    password: str
    sql_path: Path
    schema_path: Path
    output_directory: Path
    fetch_size: int
    sql_parameters: dict[str, object]
    include_text: bool

    def __repr__(self) -> str:
        """Return a representation that omits sensitive configuration values."""
        parameter_names = tuple(self.sql_parameters)

        return (
            "DatabaseCommandConfig("
            f"driver={self.driver!r}, "
            "dsn=<redacted>, "
            f"username={self.username!r}, "
            "password=<redacted>, "
            f"sql_path={self.sql_path!r}, "
            f"schema_path={self.schema_path!r}, "
            f"output_directory={self.output_directory!r}, "
            f"fetch_size={self.fetch_size!r}, "
            f"sql_parameter_names={parameter_names!r}, "
            f"include_text={self.include_text!r})"
        )


def _database_setting_specs() -> tuple[SettingSpec, ...]:
    """Return declarative settings for the database command."""
    return (
        SettingSpec(
            name="driver",
            environment_variable=_DB_DRIVER,
            parser=parse_nonblank_string,
            default="oracle",
        ),
        SettingSpec(
            name="dsn",
            environment_variable=_DB_DSN,
            parser=parse_nonblank_string,
            prompt="Database DSN",
        ),
        SettingSpec(
            name="username",
            environment_variable=_DB_USERNAME,
            parser=parse_nonblank_string,
            prompt="Database username",
        ),
        SettingSpec(
            name="password",
            environment_variable=_DB_SECRET_ENVIRONMENT_VARIABLE,
            parser=parse_nonblank_string,
            prompt="Database password",
            secret=True,
        ),
        SettingSpec(
            name="sql_path",
            environment_variable=_SQL_FILE,
            parser=parse_path,
            default=default_sql_path(),
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
            name="fetch_size",
            environment_variable=_DB_FETCH_SIZE,
            parser=parse_positive_integer,
            default=500,
        ),
        SettingSpec(
            name="sql_parameters",
            environment_variable=_SQL_PARAMETERS,
            parser=parse_json_object,
            default={},
        ),
        SettingSpec(
            name="include_text",
            environment_variable=_INCLUDE_TEXT,
            parser=parse_boolean,
            default=False,
        ),
    )


def _parse_cli_sql_parameters(value: object) -> dict[str, object] | None:
    """Parse an optional CLI JSON object containing SQL parameters."""
    if value is None:
        return None

    try:
        return parse_json_object(value)
    except (TypeError, ValueError) as error:
        detail = str(error).strip() or "value was rejected"

        raise ConfigurationValueError(
            setting_name="sql_parameters",
            source_name="explicit",
            detail=detail,
        ) from error


def _parse_sql_parameter_overrides_unchecked(
    value: object,
) -> tuple[tuple[str, str], ...]:
    """Parse repeated ``NAME=VALUE`` SQL parameter overrides."""
    if value is None:
        return ()

    if not isinstance(value, Sequence) or isinstance(
        value,
        (str, bytes, bytearray),
    ):
        raise TypeError(
            "SQL parameter overrides must be a sequence of NAME=VALUE strings"
        )

    values = cast("Sequence[object]", value)
    result: list[tuple[str, str]] = []
    names: set[str] = set()

    for position, item in enumerate(values, start=1):
        if not isinstance(item, str):
            raise TypeError(f"SQL parameter override {position} must be a string")

        name, separator, parameter_value = item.partition("=")

        if not separator or not name.strip():
            raise ValueError(f"SQL parameter override {position} must use NAME=VALUE")

        normalized_name = name.strip()

        if normalized_name in names:
            raise ValueError(f"Duplicate SQL parameter override: {normalized_name!r}")

        names.add(normalized_name)
        result.append((normalized_name, parameter_value))

    return tuple(result)


def _parse_sql_parameter_overrides(
    value: object,
) -> tuple[tuple[str, str], ...]:
    """Parse CLI SQL overrides as expected configuration input."""
    try:
        return _parse_sql_parameter_overrides_unchecked(value)
    except (TypeError, ValueError) as error:
        detail = str(error).strip() or "value was rejected"

        raise ConfigurationValueError(
            setting_name="sql_parameter_overrides",
            source_name="explicit",
            detail=detail,
        ) from error


def _explicit_sql_parameters(
    arguments: DatabaseCommandArguments,
) -> object:
    """Return the explicit base SQL-parameter value, when supplied."""
    return _parse_cli_sql_parameters(arguments.sql_parameters_json)


def _apply_sql_parameter_overrides(
    parameters: Mapping[str, object],
    overrides: tuple[tuple[str, str], ...],
) -> dict[str, object]:
    """Return SQL parameters with CLI overrides applied last."""
    result = dict(parameters)
    result.update(overrides)

    return result


def _require_string(
    value: object,
    *,
    setting_name: str,
) -> str:
    """Return one resolved string."""
    if not isinstance(value, str):
        raise TypeError(f"Resolved {setting_name} value must be a string")

    return value


def _require_path(
    value: object,
    *,
    setting_name: str,
) -> Path:
    """Return one resolved path."""
    if not isinstance(value, Path):
        raise TypeError(f"Resolved {setting_name} value must be a Path")

    return value


def _require_integer(
    value: object,
    *,
    setting_name: str,
) -> int:
    """Return one resolved non-Boolean integer."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"Resolved {setting_name} value must be an integer")

    return value


def _require_boolean(
    value: object,
    *,
    setting_name: str,
) -> bool:
    """Return one resolved Boolean."""
    if type(value) is not bool:
        raise TypeError(f"Resolved {setting_name} value must be a Boolean")

    return value


def _require_parameter_mapping(
    value: object,
) -> dict[str, object]:
    """Return a fresh string-keyed SQL-parameter mapping."""
    if not isinstance(value, Mapping):
        raise TypeError("Resolved sql_parameters value must be a mapping")

    mapping = cast("Mapping[object, object]", value)
    result: dict[str, object] = {}

    for key, item in mapping.items():
        if not isinstance(key, str):
            raise TypeError("Resolved SQL parameter names must be strings")

        result[key] = item

    return result


def resolve_database_command_config(
    arguments: DatabaseCommandArguments,
    *,
    environment: Mapping[str, object],
    dotenv: Mapping[str, object],
    prompt_provider: PromptProvider | None,
) -> DatabaseCommandConfig:
    """Resolve and type the database command configuration."""
    prompting_enabled = resolve_prompt_enabled(
        arguments,
        environment=environment,
        dotenv=dotenv,
    )
    explicit_sql_parameters = _explicit_sql_parameters(arguments)
    overrides = _parse_sql_parameter_overrides(arguments.sql_parameter_overrides)
    resolved = resolve_configuration(
        _database_setting_specs(),
        explicit={
            "driver": arguments.driver,
            "dsn": arguments.dsn,
            "username": arguments.username,
            "sql_path": arguments.sql_path,
            "schema_path": arguments.schema_path,
            "output_directory": arguments.output_directory,
            "fetch_size": arguments.fetch_size,
            "sql_parameters": explicit_sql_parameters,
            "include_text": arguments.include_text,
        },
        environment=environment,
        dotenv=dotenv,
        prompt_provider=prompt_provider,
        prompt_enabled=prompting_enabled,
    )
    parameters = _require_parameter_mapping(resolved["sql_parameters"])

    return DatabaseCommandConfig(
        driver=_require_string(
            resolved["driver"],
            setting_name="driver",
        ),
        dsn=_require_string(
            resolved["dsn"],
            setting_name="dsn",
        ),
        username=_require_string(
            resolved["username"],
            setting_name="username",
        ),
        password=_require_string(
            resolved["password"],
            setting_name="password",
        ),
        sql_path=_require_path(
            resolved["sql_path"],
            setting_name="sql_path",
        ),
        schema_path=_require_path(
            resolved["schema_path"],
            setting_name="schema_path",
        ),
        output_directory=_require_path(
            resolved["output_directory"],
            setting_name="output_directory",
        ),
        fetch_size=_require_integer(
            resolved["fetch_size"],
            setting_name="fetch_size",
        ),
        sql_parameters=_apply_sql_parameter_overrides(
            parameters,
            overrides,
        ),
        include_text=_require_boolean(
            resolved["include_text"],
            setting_name="include_text",
        ),
    )


__all__ = [
    "DatabaseCommandArguments",
    "DatabaseCommandConfig",
    "load_command_dotenv",
    "resolve_database_command_config",
]
