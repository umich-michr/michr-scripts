"""Tests for layered database-command configuration."""

from collections.abc import Mapping
from pathlib import Path

import pytest

from program_configuration import (
    ConfigurationValueError,
    MissingConfigurationError,
    PromptProvider,
)
from study_posting_audit_report.database_config import (
    DatabaseCommandArguments,
    DatabaseCommandConfig,
    resolve_database_command_config,
)
from study_posting_audit_report.paths import (
    default_output_directory,
    default_schema_path,
    default_sql_path,
)

_ENVIRONMENT_SENSITIVE_VALUE = "synthetic-sensitive-value"
_DOTENV_SENSITIVE_VALUE = "dotenv-sensitive-value"
_PROMPTED_SENSITIVE_VALUE = "prompted-sensitive-value"


class FakePromptProvider:
    """Interactive provider returning configured values."""

    def __init__(
        self,
        values: list[str],
        *,
        interactive: bool = True,
    ) -> None:
        self._values = list(values)
        self._interactive = interactive
        self.calls: list[tuple[str, bool]] = []

    @property
    def is_interactive(self) -> bool:
        """Return configured interactivity."""
        return self._interactive

    def read(
        self,
        prompt: str,
        *,
        secret: bool,
    ) -> str:
        """Return the next configured prompt value."""
        self.calls.append((prompt, secret))

        if not self._values:
            raise RuntimeError("No configured prompt value remains")

        return self._values.pop(0)


def resolve(
    arguments: DatabaseCommandArguments,
    *,
    environment: Mapping[str, object] | None = None,
    dotenv: Mapping[str, object] | None = None,
    prompt_provider: PromptProvider | None = None,
) -> DatabaseCommandConfig:
    """Resolve database arguments with empty mappings by default."""
    return resolve_database_command_config(
        arguments,
        environment={} if environment is None else environment,
        dotenv={} if dotenv is None else dotenv,
        prompt_provider=prompt_provider,
    )


def minimum_arguments() -> DatabaseCommandArguments:
    """Return explicit non-secret settings for one database command."""
    return DatabaseCommandArguments(
        dsn="database.example:1521/service",
        username="report_user",
        prompt_enabled=False,
    )


def minimum_environment() -> dict[str, object]:
    """Return the required synthetic secret environment setting."""
    return {
        "STUDY_POSTING_AUDIT_DB_PASSWORD": _ENVIRONMENT_SENSITIVE_VALUE,
    }


def test_database_defaults_are_stable() -> None:
    config = resolve(
        minimum_arguments(),
        environment=minimum_environment(),
    )

    assert config.driver == "oracle"
    assert config.dsn == "database.example:1521/service"
    assert config.username == "report_user"
    assert config.password == _ENVIRONMENT_SENSITIVE_VALUE
    assert config.sql_path == default_sql_path()
    assert config.schema_path == default_schema_path()
    assert config.output_directory == default_output_directory()
    assert config.fetch_size == 500
    assert config.sql_parameters == {}
    assert config.include_text is False


def test_cli_values_have_highest_precedence(tmp_path: Path) -> None:
    config = resolve(
        DatabaseCommandArguments(
            driver="oracle",
            dsn="explicit-dsn",
            username="explicit-user",
            sql_path=tmp_path / "explicit.sql",
            schema_path=tmp_path / "schema.json",
            output_directory=tmp_path / "output",
            fetch_size="250",
            sql_parameters_json='{"limit":100,"active":true}',
            sql_parameter_overrides=[
                "limit=200",
                "status=ACTIVE",
            ],
            include_text=True,
            prompt_enabled=False,
        ),
        environment={
            "STUDY_POSTING_AUDIT_DB_DSN": "environment-dsn",
            "STUDY_POSTING_AUDIT_DB_USERNAME": "environment-user",
            "STUDY_POSTING_AUDIT_DB_PASSWORD": _ENVIRONMENT_SENSITIVE_VALUE,
            "STUDY_POSTING_AUDIT_DB_FETCH_SIZE": "100",
            "STUDY_POSTING_AUDIT_SQL_PARAMS": '{"limit":50}',
        },
        dotenv={
            "STUDY_POSTING_AUDIT_DB_DSN": "dotenv-dsn",
        },
    )

    assert config.driver == "oracle"
    assert config.dsn == "explicit-dsn"
    assert config.username == "explicit-user"
    assert config.sql_path == tmp_path / "explicit.sql"
    assert config.schema_path == tmp_path / "schema.json"
    assert config.output_directory == tmp_path / "output"
    assert config.fetch_size == 250
    assert config.sql_parameters == {
        "limit": "200",
        "active": True,
        "status": "ACTIVE",
    }
    assert config.include_text is True


def test_environment_precedes_dotenv() -> None:
    config = resolve(
        DatabaseCommandArguments(
            prompt_enabled=False,
        ),
        environment={
            "STUDY_POSTING_AUDIT_DB_DSN": "environment-dsn",
            "STUDY_POSTING_AUDIT_DB_USERNAME": "environment-user",
            "STUDY_POSTING_AUDIT_DB_PASSWORD": _ENVIRONMENT_SENSITIVE_VALUE,
            "STUDY_POSTING_AUDIT_DB_FETCH_SIZE": "250",
            "STUDY_POSTING_AUDIT_SQL_PARAMS": '{"status":"ENV"}',
        },
        dotenv={
            "STUDY_POSTING_AUDIT_DB_DSN": "dotenv-dsn",
            "STUDY_POSTING_AUDIT_DB_USERNAME": "dotenv-user",
            "STUDY_POSTING_AUDIT_DB_PASSWORD": _DOTENV_SENSITIVE_VALUE,
            "STUDY_POSTING_AUDIT_DB_FETCH_SIZE": "125",
            "STUDY_POSTING_AUDIT_SQL_PARAMS": '{"status":"DOTENV"}',
        },
    )

    assert config.dsn == "environment-dsn"
    assert config.username == "environment-user"
    assert config.password == _ENVIRONMENT_SENSITIVE_VALUE
    assert config.fetch_size == 250
    assert config.sql_parameters == {"status": "ENV"}


def test_dotenv_values_are_used() -> None:
    config = resolve(
        DatabaseCommandArguments(
            prompt_enabled=False,
        ),
        dotenv={
            "STUDY_POSTING_AUDIT_DB_DSN": "dotenv-dsn",
            "STUDY_POSTING_AUDIT_DB_USERNAME": "dotenv-user",
            "STUDY_POSTING_AUDIT_DB_PASSWORD": _DOTENV_SENSITIVE_VALUE,
            "STUDY_POSTING_AUDIT_DB_DRIVER": "ORACLE",
            "STUDY_POSTING_AUDIT_INCLUDE_TEXT": "true",
        },
    )

    assert config.driver == "ORACLE"
    assert config.dsn == "dotenv-dsn"
    assert config.username == "dotenv-user"
    assert config.password == _DOTENV_SENSITIVE_VALUE
    assert config.include_text is True


def test_missing_connection_values_are_prompted() -> None:
    provider = FakePromptProvider(
        [
            "prompted-dsn",
            "prompted-user",
            _PROMPTED_SENSITIVE_VALUE,
        ]
    )

    config = resolve(
        DatabaseCommandArguments(),
        prompt_provider=provider,
    )

    assert config.dsn == "prompted-dsn"
    assert config.username == "prompted-user"
    assert config.password == _PROMPTED_SENSITIVE_VALUE
    assert provider.calls == [
        ("Database DSN", False),
        ("Database username", False),
        ("Database password", True),
    ]


def test_missing_connection_values_are_reported_together() -> None:
    with pytest.raises(
        MissingConfigurationError,
    ) as captured:
        resolve(
            DatabaseCommandArguments(
                prompt_enabled=False,
            )
        )

    assert captured.value.setting_names == (
        "dsn",
        "username",
        "password",
    )


def test_password_is_not_available_as_command_argument() -> None:
    assert "password" not in DatabaseCommandArguments.__dataclass_fields__


def test_database_config_representation_redacts_sensitive_values() -> None:
    config = resolve(
        DatabaseCommandArguments(
            dsn="sensitive-dsn",
            username="report_user",
            sql_parameters_json='{"sensitive_parameter":"sensitive-bind-value"}',
            prompt_enabled=False,
        ),
        environment=minimum_environment(),
    )

    representation = repr(config)

    assert "dsn=<redacted>" in representation
    assert "password=<redacted>" in representation
    assert "sensitive_parameter" in representation
    assert "sensitive-dsn" not in representation
    assert _ENVIRONMENT_SENSITIVE_VALUE not in representation
    assert "sensitive-bind-value" not in representation


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("", "expected a nonblank JSON object"),
        ("[]", "expected a JSON object"),
        ('{"valid":1', "invalid JSON"),
    ],
    ids=["blank", "array", "malformed"],
)
def test_invalid_cli_sql_parameter_json_is_rejected(
    value: str,
    message: str,
) -> None:
    with pytest.raises(
        ConfigurationValueError,
        match=message,
    ):
        resolve(
            DatabaseCommandArguments(
                dsn="dsn",
                username="user",
                sql_parameters_json=value,
                prompt_enabled=False,
            ),
            environment=minimum_environment(),
        )


@pytest.mark.parametrize(
    "value",
    [
        "missing-separator",
        "=missing-name",
        "   =missing-name",
    ],
    ids=[
        "missing-separator",
        "empty-name",
        "blank-name",
    ],
)
def test_invalid_sql_parameter_override_is_rejected(
    value: str,
) -> None:
    with pytest.raises(
        ConfigurationValueError,
        match="must use NAME=VALUE",
    ):
        resolve(
            DatabaseCommandArguments(
                dsn="dsn",
                username="user",
                sql_parameter_overrides=[value],
                prompt_enabled=False,
            ),
            environment=minimum_environment(),
        )


def test_duplicate_sql_parameter_override_is_rejected() -> None:
    with pytest.raises(
        ConfigurationValueError,
        match="Duplicate SQL parameter override",
    ):
        resolve(
            DatabaseCommandArguments(
                dsn="dsn",
                username="user",
                sql_parameter_overrides=[
                    "status=ACTIVE",
                    "status=COMPLETE",
                ],
                prompt_enabled=False,
            ),
            environment=minimum_environment(),
        )


def test_sql_parameter_override_preserves_equals_in_value() -> None:
    config = resolve(
        DatabaseCommandArguments(
            dsn="dsn",
            username="user",
            sql_parameter_overrides=[
                "expression=left=right",
            ],
            prompt_enabled=False,
        ),
        environment=minimum_environment(),
    )

    assert config.sql_parameters == {
        "expression": "left=right",
    }


def test_sql_parameter_override_must_be_sequence() -> None:
    with pytest.raises(
        ConfigurationValueError,
        match="must be a sequence",
    ):
        resolve(
            DatabaseCommandArguments(
                dsn="dsn",
                username="user",
                sql_parameter_overrides=42,
                prompt_enabled=False,
            ),
            environment=minimum_environment(),
        )


def test_sql_parameter_override_item_must_be_string() -> None:
    with pytest.raises(
        ConfigurationValueError,
        match="override 1 must be a string",
    ):
        resolve(
            DatabaseCommandArguments(
                dsn="dsn",
                username="user",
                sql_parameter_overrides=[42],
                prompt_enabled=False,
            ),
            environment=minimum_environment(),
        )


@pytest.mark.parametrize(
    ("fetch_size", "message"),
    [
        (0, "expected a positive integer"),
        ("0", "expected a positive integer"),
        ("invalid", "expected base-10 integer text"),
    ],
    ids=["zero", "zero-text", "invalid-text"],
)
def test_invalid_fetch_size_is_rejected(
    fetch_size: object,
    message: str,
) -> None:
    with pytest.raises(
        ConfigurationValueError,
        match=message,
    ):
        resolve(
            DatabaseCommandArguments(
                dsn="dsn",
                username="user",
                fetch_size=fetch_size,
                prompt_enabled=False,
            ),
            environment=minimum_environment(),
        )


def test_environment_sql_parameters_accept_json_types() -> None:
    config = resolve(
        minimum_arguments(),
        environment={
            **minimum_environment(),
            "STUDY_POSTING_AUDIT_SQL_PARAMS": (
                '{"limit":100,"active":true,"optional":null}'
            ),
        },
    )

    assert config.sql_parameters == {
        "limit": 100,
        "active": True,
        "optional": None,
    }
