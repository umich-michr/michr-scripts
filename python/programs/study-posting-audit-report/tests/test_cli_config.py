"""Tests for layered CSV command configuration."""

from collections.abc import Mapping
from pathlib import Path
from typing import cast

import pytest

from program_configuration import (
    ConfigurationValueError,
    DotenvFileError,
    MissingConfigurationError,
    PromptProvider,
)
from study_posting_audit_report.cli_config import (
    CsvCommandArguments,
    CsvCommandConfig,
    load_command_dotenv,
    resolve_csv_command_config,
)
from study_posting_audit_report.paths import (
    default_output_directory,
    default_schema_path,
)


class FakePromptProvider:
    """Interactive prompt provider returning configured values."""

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
        """Return configured terminal interactivity."""
        return self._interactive

    def read(
        self,
        prompt: str,
        *,
        secret: bool,
    ) -> str:
        """Return the next configured value."""
        self.calls.append((prompt, secret))

        if not self._values:
            raise RuntimeError("No configured prompt value remains")

        return self._values.pop(0)


def resolve(
    arguments: CsvCommandArguments,
    *,
    environment: Mapping[str, object] | None = None,
    dotenv: Mapping[str, object] | None = None,
    prompt_provider: PromptProvider | None = None,
) -> CsvCommandConfig:
    """Resolve CSV arguments with empty mappings by default."""
    return resolve_csv_command_config(
        arguments,
        environment={} if environment is None else environment,
        dotenv={} if dotenv is None else dotenv,
        prompt_provider=prompt_provider,
    )


def test_cli_values_have_highest_precedence(tmp_path: Path) -> None:
    input_path = tmp_path / "explicit.csv"
    schema_path = tmp_path / "explicit-schema.json"
    output_directory = tmp_path / "explicit-output"

    config = resolve(
        CsvCommandArguments(
            input_path=input_path,
            schema_path=schema_path,
            output_directory=output_directory,
            include_text=True,
            encoding="utf-16",
            delimiter="|",
            quotechar="'",
            escapechar="\\",
            null_values=["NULL", ""],
        ),
        environment={
            "STUDY_POSTING_AUDIT_CSV_INPUT": "environment.csv",
            "STUDY_POSTING_AUDIT_SCHEMA": "environment-schema.json",
            "STUDY_POSTING_AUDIT_OUTPUT": "environment-output",
            "STUDY_POSTING_AUDIT_INCLUDE_TEXT": "false",
        },
        dotenv={
            "STUDY_POSTING_AUDIT_CSV_INPUT": "dotenv.csv",
        },
    )

    assert config.input_path == input_path
    assert config.schema_path == schema_path
    assert config.output_directory == output_directory
    assert config.include_text is True
    assert config.encoding == "utf-16"
    assert config.delimiter == "|"
    assert config.quotechar == "'"
    assert config.escapechar == "\\"
    assert config.null_values == frozenset({"NULL", ""})


def test_environment_precedes_dotenv(tmp_path: Path) -> None:
    config = resolve(
        CsvCommandArguments(),
        environment={
            "STUDY_POSTING_AUDIT_CSV_INPUT": str(tmp_path / "environment.csv"),
            "STUDY_POSTING_AUDIT_INCLUDE_TEXT": "true",
            "STUDY_POSTING_AUDIT_CSV_ENCODING": "utf-16",
        },
        dotenv={
            "STUDY_POSTING_AUDIT_CSV_INPUT": str(tmp_path / "dotenv.csv"),
            "STUDY_POSTING_AUDIT_INCLUDE_TEXT": "false",
            "STUDY_POSTING_AUDIT_CSV_ENCODING": "ascii",
        },
    )

    assert config.input_path == tmp_path / "environment.csv"
    assert config.include_text is True
    assert config.encoding == "utf-16"


def test_dotenv_values_are_used(tmp_path: Path) -> None:
    config = resolve(
        CsvCommandArguments(),
        dotenv={
            "STUDY_POSTING_AUDIT_CSV_INPUT": str(tmp_path / "dotenv.csv"),
            "STUDY_POSTING_AUDIT_SCHEMA": str(tmp_path / "schema.json"),
            "STUDY_POSTING_AUDIT_OUTPUT": str(tmp_path / "output"),
            "STUDY_POSTING_AUDIT_CSV_DELIMITER": "|",
            "STUDY_POSTING_AUDIT_CSV_QUOTECHAR": "'",
            "STUDY_POSTING_AUDIT_CSV_ESCAPECHAR": "\\",
            "STUDY_POSTING_AUDIT_CSV_NULL_VALUES": '["", "NULL"]',
        },
    )

    assert config.input_path == tmp_path / "dotenv.csv"
    assert config.schema_path == tmp_path / "schema.json"
    assert config.output_directory == tmp_path / "output"
    assert config.delimiter == "|"
    assert config.quotechar == "'"
    assert config.escapechar == "\\"
    assert config.null_values == frozenset({"", "NULL"})


def test_defaults_are_stable(tmp_path: Path) -> None:
    config = resolve(
        CsvCommandArguments(
            input_path=tmp_path / "input.csv",
        )
    )

    assert config.schema_path == default_schema_path()
    assert config.output_directory == default_output_directory()
    assert config.include_text is False
    assert config.encoding == "utf-8-sig"
    assert config.delimiter == ","
    assert config.quotechar == '"'
    assert config.escapechar is None
    assert config.null_values == frozenset({"", "\\N"})


def test_missing_input_is_prompted(tmp_path: Path) -> None:
    provider = FakePromptProvider(
        [str(tmp_path / "prompted.csv")],
    )

    config = resolve(
        CsvCommandArguments(),
        prompt_provider=provider,
    )

    assert config.input_path == tmp_path / "prompted.csv"
    assert provider.calls == [("CSV input path", False)]


def test_missing_input_fails_without_provider() -> None:
    with pytest.raises(
        MissingConfigurationError,
        match="- input_path",
    ):
        resolve(CsvCommandArguments())


def test_prompt_can_be_disabled_by_cli() -> None:
    provider = FakePromptProvider(["unused"])

    with pytest.raises(MissingConfigurationError):
        resolve(
            CsvCommandArguments(
                prompt_enabled=False,
            ),
            prompt_provider=provider,
        )

    assert provider.calls == []


def test_environment_can_disable_prompting() -> None:
    provider = FakePromptProvider(["unused"])

    with pytest.raises(MissingConfigurationError):
        resolve(
            CsvCommandArguments(),
            environment={
                "STUDY_POSTING_AUDIT_PROMPT": "false",
            },
            prompt_provider=provider,
        )

    assert provider.calls == []


def test_cli_prompt_setting_overrides_environment() -> None:
    provider = FakePromptProvider(["prompted.csv"])

    config = resolve(
        CsvCommandArguments(
            prompt_enabled=True,
        ),
        environment={
            "STUDY_POSTING_AUDIT_PROMPT": "false",
        },
        prompt_provider=provider,
    )

    assert config.input_path == Path("prompted.csv")


def test_invalid_delimiter_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(
        ConfigurationValueError,
        match="expected exactly one character",
    ):
        resolve(
            CsvCommandArguments(
                input_path=tmp_path / "input.csv",
                delimiter="::",
            )
        )


def test_invalid_escape_character_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(
        ConfigurationValueError,
        match="expected exactly one character",
    ):
        resolve(
            CsvCommandArguments(
                input_path=tmp_path / "input.csv",
                escapechar="::",
            )
        )


def test_invalid_include_text_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(
        ConfigurationValueError,
        match="expected a Boolean",
    ):
        resolve(
            CsvCommandArguments(
                input_path=tmp_path / "input.csv",
                include_text="maybe",
            )
        )


def test_blank_quote_character_uses_default(tmp_path: Path) -> None:
    config = resolve(
        CsvCommandArguments(
            input_path=tmp_path / "input.csv",
            quotechar="",
        )
    )

    assert config.quotechar == '"'


def test_blank_encoding_uses_default(tmp_path: Path) -> None:
    config = resolve(
        CsvCommandArguments(
            input_path=tmp_path / "input.csv",
            encoding=" ",
        )
    )

    assert config.encoding == "utf-8-sig"


@pytest.mark.parametrize(
    "value",
    [
        "{}",
        '"text"',
        "42",
        '["valid", 1]',
    ],
    ids=["object", "string", "integer", "non-string-entry"],
)
def test_invalid_null_value_configuration_is_rejected(
    tmp_path: Path,
    value: str,
) -> None:
    with pytest.raises(ConfigurationValueError):
        resolve(
            CsvCommandArguments(
                input_path=tmp_path / "input.csv",
            ),
            environment={
                "STUDY_POSTING_AUDIT_CSV_NULL_VALUES": value,
            },
        )


def test_duplicate_cli_null_values_are_collapsed(tmp_path: Path) -> None:
    config = resolve(
        CsvCommandArguments(
            input_path=tmp_path / "input.csv",
            null_values=["NULL", "NULL", ""],
        )
    )

    assert config.null_values == frozenset({"NULL", ""})


def test_no_env_file_skips_all_dotenv_loading(
    tmp_path: Path,
) -> None:
    arguments = CsvCommandArguments(
        env_file=tmp_path / "explicit.env",
        no_env_file=True,
    )

    assert (
        load_command_dotenv(
            arguments,
            environment={
                "STUDY_POSTING_AUDIT_ENV_FILE": str(tmp_path / "environment.env"),
            },
        )
        == {}
    )


def test_explicit_env_file_is_required(tmp_path: Path) -> None:
    path = tmp_path / "missing.env"

    with pytest.raises(
        DotenvFileError,
        match="Required dotenv file does not exist",
    ):
        load_command_dotenv(
            CsvCommandArguments(
                env_file=path,
            ),
            environment={},
        )


def test_explicit_env_file_is_loaded(tmp_path: Path) -> None:
    path = tmp_path / "explicit.env"
    path.write_text(
        "EXAMPLE=value\n",
        encoding="utf-8",
    )

    result = load_command_dotenv(
        CsvCommandArguments(
            env_file=path,
        ),
        environment={},
    )

    assert result == {"EXAMPLE": "value"}


def test_environment_env_file_is_required(tmp_path: Path) -> None:
    path = tmp_path / "missing.env"

    with pytest.raises(
        DotenvFileError,
        match="Required dotenv file does not exist",
    ):
        load_command_dotenv(
            CsvCommandArguments(),
            environment={
                "STUDY_POSTING_AUDIT_ENV_FILE": str(path),
            },
        )


def test_environment_env_file_is_loaded(tmp_path: Path) -> None:
    path = tmp_path / "environment.env"
    path.write_text(
        "EXAMPLE=value\n",
        encoding="utf-8",
    )

    result = load_command_dotenv(
        CsvCommandArguments(),
        environment={
            "STUDY_POSTING_AUDIT_ENV_FILE": path,
        },
    )

    assert result == {"EXAMPLE": "value"}


def test_blank_environment_env_file_uses_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    default_file = tmp_path / ".env"
    default_file.write_text(
        "EXAMPLE=default\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "study_posting_audit_report.cli_config.default_dotenv_path",
        lambda: default_file,
    )

    result = load_command_dotenv(
        CsvCommandArguments(),
        environment={
            "STUDY_POSTING_AUDIT_ENV_FILE": " ",
        },
    )

    assert result == {"EXAMPLE": "default"}


def test_missing_default_env_file_is_allowed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "study_posting_audit_report.cli_config.default_dotenv_path",
        lambda: tmp_path / "missing.env",
    )

    assert (
        load_command_dotenv(
            CsvCommandArguments(),
            environment={},
        )
        == {}
    )


def test_invalid_environment_env_file_type_uses_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    default_file = tmp_path / ".env"
    default_file.write_text(
        "EXAMPLE=default\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "study_posting_audit_report.cli_config.default_dotenv_path",
        lambda: default_file,
    )

    result = load_command_dotenv(
        CsvCommandArguments(),
        environment={
            "STUDY_POSTING_AUDIT_ENV_FILE": 42,
        },
    )

    assert result == {"EXAMPLE": "default"}


def test_arguments_must_be_csv_arguments() -> None:
    invalid_arguments = cast(
        "CsvCommandArguments",
        object(),
    )

    with pytest.raises(AttributeError):
        load_command_dotenv(
            invalid_arguments,
            environment={},
        )
