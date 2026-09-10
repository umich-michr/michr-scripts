"""Tests for layered program-configuration resolution."""

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import cast

import pytest

from program_configuration import (
    ConfigurationValueError,
    MissingConfigurationError,
    PromptError,
    PromptProvider,
    SettingDefinitionError,
    SettingSpec,
    UnknownExplicitSettingError,
    ValueSource,
    parse_boolean,
    parse_nonblank_string,
    parse_path,
    parse_positive_integer,
    resolve_configuration,
)


def example_specs() -> tuple[SettingSpec, ...]:
    """Return representative setting specifications."""
    return (
        SettingSpec(
            name="input_path",
            environment_variable="EXAMPLE_INPUT",
            parser=parse_path,
        ),
        SettingSpec(
            name="include_text",
            environment_variable="EXAMPLE_INCLUDE_TEXT",
            parser=parse_boolean,
            default=False,
        ),
        SettingSpec(
            name="fetch_size",
            environment_variable="EXAMPLE_FETCH_SIZE",
            parser=parse_positive_integer,
            default=500,
        ),
    )


def test_explicit_value_has_highest_precedence() -> None:
    configuration = resolve_configuration(
        example_specs(),
        explicit={"input_path": "explicit.csv"},
        environment={"EXAMPLE_INPUT": "environment.csv"},
        dotenv={"EXAMPLE_INPUT": "dotenv.csv"},
    )

    assert configuration["input_path"] == Path("explicit.csv")
    assert configuration.source_for("input_path") is ValueSource.EXPLICIT


def test_environment_precedes_dotenv_and_default() -> None:
    configuration = resolve_configuration(
        example_specs(),
        explicit={"input_path": None},
        environment={
            "EXAMPLE_INPUT": "environment.csv",
            "EXAMPLE_FETCH_SIZE": "250",
        },
        dotenv={
            "EXAMPLE_INPUT": "dotenv.csv",
            "EXAMPLE_FETCH_SIZE": "125",
        },
    )

    assert configuration["input_path"] == Path("environment.csv")
    assert configuration.source_for("input_path") is ValueSource.ENVIRONMENT
    assert configuration["fetch_size"] == 250
    assert configuration.source_for("fetch_size") is ValueSource.ENVIRONMENT


def test_dotenv_precedes_default() -> None:
    configuration = resolve_configuration(
        example_specs(),
        dotenv={
            "EXAMPLE_INPUT": "dotenv.csv",
            "EXAMPLE_INCLUDE_TEXT": "true",
            "EXAMPLE_FETCH_SIZE": "100",
        },
    )

    assert configuration["input_path"] == Path("dotenv.csv")
    assert configuration.source_for("input_path") is ValueSource.DOTENV
    assert configuration["include_text"] is True
    assert configuration.source_for("include_text") is ValueSource.DOTENV
    assert configuration["fetch_size"] == 100
    assert configuration.source_for("fetch_size") is ValueSource.DOTENV


def test_defaults_are_used_after_layered_sources() -> None:
    configuration = resolve_configuration(
        example_specs(),
        explicit={"input_path": "input.csv"},
    )

    assert configuration["include_text"] is False
    assert configuration.source_for("include_text") is ValueSource.DEFAULT
    assert configuration["fetch_size"] == 500
    assert configuration.source_for("fetch_size") is ValueSource.DEFAULT


def test_none_allows_fallback_at_every_layer() -> None:
    configuration = resolve_configuration(
        example_specs(),
        explicit={
            "input_path": None,
            "include_text": None,
            "fetch_size": None,
        },
        environment={
            "EXAMPLE_INPUT": None,
            "EXAMPLE_INCLUDE_TEXT": None,
            "EXAMPLE_FETCH_SIZE": None,
        },
        dotenv={
            "EXAMPLE_INPUT": "dotenv.csv",
            "EXAMPLE_INCLUDE_TEXT": None,
            "EXAMPLE_FETCH_SIZE": None,
        },
    )

    assert configuration["input_path"] == Path("dotenv.csv")
    assert configuration.source_for("input_path") is ValueSource.DOTENV
    assert configuration["include_text"] is False
    assert configuration.source_for("include_text") is ValueSource.DEFAULT
    assert configuration["fetch_size"] == 500
    assert configuration.source_for("fetch_size") is ValueSource.DEFAULT


def test_blank_strings_allow_fallback_by_default() -> None:
    configuration = resolve_configuration(
        example_specs(),
        explicit={
            "input_path": "   ",
            "include_text": "",
        },
        environment={
            "EXAMPLE_INPUT": "\n",
            "EXAMPLE_INCLUDE_TEXT": "  ",
        },
        dotenv={
            "EXAMPLE_INPUT": "dotenv.csv",
            "EXAMPLE_INCLUDE_TEXT": "true",
        },
    )

    assert configuration["input_path"] == Path("dotenv.csv")
    assert configuration["include_text"] is True


def test_blank_string_can_be_meaningful() -> None:
    spec = SettingSpec(
        name="marker",
        environment_variable="EXAMPLE_MARKER",
        parser=lambda value: value,
        default="default",
        blank_is_missing=False,
    )

    configuration = resolve_configuration(
        (spec,),
        explicit={"marker": ""},
        environment={"EXAMPLE_MARKER": "environment"},
    )

    assert configuration["marker"] == ""
    assert configuration.source_for("marker") is ValueSource.EXPLICIT


def test_setting_without_environment_variable_ignores_environment_mapping() -> None:
    spec = SettingSpec(
        name="region",
        parser=parse_nonblank_string,
        default="default",
    )

    configuration = resolve_configuration(
        (spec,),
        environment={"region": "environment"},
        dotenv={"region": "dotenv"},
    )

    assert configuration["region"] == "default"
    assert configuration.source_for("region") is ValueSource.DEFAULT


def test_irrelevant_environment_and_dotenv_keys_are_ignored() -> None:
    configuration = resolve_configuration(
        example_specs(),
        explicit={"input_path": "input.csv"},
        environment={"UNRELATED": "value"},
        dotenv={"OTHER": "value"},
    )

    assert configuration["input_path"] == Path("input.csv")


def test_missing_settings_are_reported_together_in_declaration_order() -> None:
    specs = (
        SettingSpec(
            name="input_path",
            parser=parse_path,
        ),
        SettingSpec(
            name="output_path",
            parser=parse_path,
        ),
        SettingSpec(
            name="username",
            parser=parse_nonblank_string,
        ),
    )

    with pytest.raises(
        MissingConfigurationError,
        match=(
            "Missing required configuration settings:\n"
            "- input_path\n"
            "- output_path\n"
            "- username"
        ),
    ) as captured:
        resolve_configuration(specs)

    assert captured.value.setting_names == (
        "input_path",
        "output_path",
        "username",
    )


def test_unknown_explicit_settings_are_rejected_in_sorted_order() -> None:
    with pytest.raises(
        UnknownExplicitSettingError,
        match="unknown settings: 'alpha', 'zeta'",
    ) as captured:
        resolve_configuration(
            example_specs(),
            explicit={
                "input_path": "input.csv",
                "zeta": 1,
                "alpha": 2,
            },
        )

    assert captured.value.setting_names == ("alpha", "zeta")


def test_duplicate_setting_names_are_rejected() -> None:
    specs = (
        SettingSpec(
            name="region",
            parser=parse_nonblank_string,
        ),
        SettingSpec(
            name="region",
            parser=parse_nonblank_string,
        ),
    )

    with pytest.raises(
        SettingDefinitionError,
        match="Duplicate configuration setting name: 'region'",
    ):
        resolve_configuration(specs)


def test_duplicate_environment_variables_are_rejected() -> None:
    specs = (
        SettingSpec(
            name="first",
            environment_variable="EXAMPLE_VALUE",
            parser=parse_nonblank_string,
        ),
        SettingSpec(
            name="second",
            environment_variable="EXAMPLE_VALUE",
            parser=parse_nonblank_string,
        ),
    )

    with pytest.raises(
        SettingDefinitionError,
        match="Duplicate configuration environment variable",
    ):
        resolve_configuration(specs)


def test_invalid_specification_entry_is_rejected() -> None:
    specs = cast(
        "Iterable[SettingSpec]",
        [object()],
    )

    with pytest.raises(
        SettingDefinitionError,
        match="must be SettingSpec instances",
    ):
        resolve_configuration(specs)


@pytest.mark.parametrize(
    ("argument_name", "kwargs"),
    [
        ("Explicit configuration", {"explicit": 42}),
        ("Environment configuration", {"environment": []}),
        ("Dotenv configuration", {"dotenv": object()}),
    ],
    ids=["explicit", "environment", "dotenv"],
)
def test_configuration_layers_must_be_mappings(
    argument_name: str,
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(
        SettingDefinitionError,
        match=rf"{argument_name} must be a mapping",
    ):
        resolve_configuration(
            (),
            **kwargs,  # type: ignore[arg-type]
        )


def invalid_configuration_mapping() -> Mapping[str, object]:
    """Return a mapping with an invalid non-string key."""
    return cast(
        "Mapping[str, object]",
        {1: "value"},
    )


def test_explicit_configuration_keys_must_be_strings() -> None:
    with pytest.raises(
        SettingDefinitionError,
        match="Explicit configuration keys must be strings",
    ):
        resolve_configuration(
            (),
            explicit=invalid_configuration_mapping(),
        )


def test_environment_configuration_keys_must_be_strings() -> None:
    with pytest.raises(
        SettingDefinitionError,
        match="Environment configuration keys must be strings",
    ):
        resolve_configuration(
            (),
            environment=invalid_configuration_mapping(),
        )


def test_dotenv_configuration_keys_must_be_strings() -> None:
    with pytest.raises(
        SettingDefinitionError,
        match="Dotenv configuration keys must be strings",
    ):
        resolve_configuration(
            (),
            dotenv=invalid_configuration_mapping(),
        )


def test_invalid_explicit_value_reports_setting_and_source() -> None:
    with pytest.raises(
        ConfigurationValueError,
        match=(
            "Configuration setting 'fetch_size' from explicit is invalid: "
            "expected a positive integer"
        ),
    ) as captured:
        resolve_configuration(
            example_specs(),
            explicit={
                "input_path": "input.csv",
                "fetch_size": "0",
            },
        )

    assert captured.value.setting_name == "fetch_size"
    assert captured.value.source_name == "explicit"
    assert captured.value.detail == "expected a positive integer"
    assert isinstance(captured.value.__cause__, ValueError)


def test_invalid_environment_value_does_not_fall_back() -> None:
    with pytest.raises(
        ConfigurationValueError,
        match="from environment is invalid",
    ):
        resolve_configuration(
            example_specs(),
            explicit={"input_path": "input.csv"},
            environment={"EXAMPLE_INCLUDE_TEXT": "not-a-boolean"},
            dotenv={"EXAMPLE_INCLUDE_TEXT": "true"},
        )


def test_invalid_dotenv_value_does_not_fall_back_to_default() -> None:
    with pytest.raises(
        ConfigurationValueError,
        match="from dotenv is invalid",
    ):
        resolve_configuration(
            example_specs(),
            explicit={"input_path": "input.csv"},
            dotenv={"EXAMPLE_FETCH_SIZE": "invalid"},
        )


def test_invalid_default_is_reported() -> None:
    spec = SettingSpec(
        name="fetch_size",
        parser=parse_positive_integer,
        default=0,
    )

    with pytest.raises(
        ConfigurationValueError,
        match="from default is invalid",
    ):
        resolve_configuration((spec,))


def test_empty_parser_error_uses_generic_detail() -> None:
    def reject(_value: object) -> object:
        raise ValueError

    spec = SettingSpec(
        name="value",
        parser=reject,
        default="raw",
    )

    with pytest.raises(
        ConfigurationValueError,
        match="value was rejected by its parser",
    ):
        resolve_configuration((spec,))


def test_secret_parser_error_does_not_expose_secret_value() -> None:
    sensitive_value = "synthetic-sensitive-value"

    def reject(value: object) -> object:
        raise ValueError(f"rejected value {value!r}")

    spec = SettingSpec(
        name="password",
        environment_variable="EXAMPLE_PASSWORD",
        parser=reject,
        secret=True,
    )

    with pytest.raises(ConfigurationValueError) as captured:
        resolve_configuration(
            (spec,),
            environment={"EXAMPLE_PASSWORD": sensitive_value},
        )

    message = str(captured.value)

    assert "password" in message
    assert "environment" in message
    assert "secret value was rejected by its parser" in message
    assert sensitive_value not in message
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


def test_resolved_secret_remains_available_to_consumer() -> None:
    sensitive_value = "synthetic-sensitive-value"
    spec = SettingSpec(
        name="password",
        environment_variable="EXAMPLE_PASSWORD",
        parser=parse_nonblank_string,
        secret=True,
    )

    configuration = resolve_configuration(
        (spec,),
        environment={"EXAMPLE_PASSWORD": sensitive_value},
    )

    assert configuration["password"] == sensitive_value
    assert sensitive_value not in repr(configuration)


def test_no_specs_produces_empty_configuration() -> None:
    configuration = resolve_configuration(())

    assert len(configuration) == 0
    assert configuration.as_dict() == {}


class FakePromptProvider:
    """Configurable prompt provider for resolver tests."""

    def __init__(
        self,
        values: list[str],
        *,
        interactive: object = True,
        read_error: BaseException | None = None,
        interactive_error: Exception | None = None,
    ) -> None:
        self._values = list(values)
        self._interactive = interactive
        self._read_error = read_error
        self._interactive_error = interactive_error
        self.interactive_checks = 0
        self.read_calls: list[tuple[str, bool]] = []

    @property
    def is_interactive(self) -> bool:
        """Return configured interactivity."""
        self.interactive_checks += 1

        if self._interactive_error is not None:
            raise self._interactive_error

        return cast("bool", self._interactive)

    def read(
        self,
        prompt: str,
        *,
        secret: bool,
    ) -> str:
        """Return the next configured prompt value."""
        self.read_calls.append((prompt, secret))

        if self._read_error is not None:
            raise self._read_error

        if not self._values:
            raise RuntimeError("No configured prompt value remains")

        return self._values.pop(0)


def prompted_spec(
    *,
    secret: bool = False,
    blank_is_missing: bool = True,
) -> SettingSpec:
    """Return one required prompted setting."""
    return SettingSpec(
        name="value",
        environment_variable="EXAMPLE_VALUE",
        parser=parse_nonblank_string if blank_is_missing else lambda value: value,
        prompt="Configured value",
        secret=secret,
        blank_is_missing=blank_is_missing,
    )


def test_unresolved_setting_is_prompted() -> None:
    provider = FakePromptProvider(["prompted-value"])

    configuration = resolve_configuration(
        (prompted_spec(),),
        prompt_provider=provider,
    )

    assert configuration["value"] == "prompted-value"
    assert configuration.source_for("value") is ValueSource.PROMPT
    assert provider.interactive_checks == 1
    assert provider.read_calls == [("Configured value", False)]


def test_secret_setting_requests_secret_prompt() -> None:
    provider = FakePromptProvider(["sensitive-value"])

    configuration = resolve_configuration(
        (prompted_spec(secret=True),),
        prompt_provider=provider,
    )

    assert configuration["value"] == "sensitive-value"
    assert provider.read_calls == [("Configured value", True)]
    assert "sensitive-value" not in repr(configuration)


def test_explicit_value_prevents_prompting() -> None:
    provider = FakePromptProvider(["unused"])

    configuration = resolve_configuration(
        (prompted_spec(),),
        explicit={"value": "explicit-value"},
        prompt_provider=provider,
    )

    assert configuration["value"] == "explicit-value"
    assert configuration.source_for("value") is ValueSource.EXPLICIT
    assert provider.interactive_checks == 0
    assert provider.read_calls == []


def test_environment_value_prevents_prompting() -> None:
    provider = FakePromptProvider(["unused"])

    configuration = resolve_configuration(
        (prompted_spec(),),
        environment={"EXAMPLE_VALUE": "environment-value"},
        prompt_provider=provider,
    )

    assert configuration["value"] == "environment-value"
    assert configuration.source_for("value") is ValueSource.ENVIRONMENT
    assert provider.interactive_checks == 0
    assert provider.read_calls == []


def test_dotenv_value_prevents_prompting() -> None:
    provider = FakePromptProvider(["unused"])

    configuration = resolve_configuration(
        (prompted_spec(),),
        dotenv={"EXAMPLE_VALUE": "dotenv-value"},
        prompt_provider=provider,
    )

    assert configuration["value"] == "dotenv-value"
    assert configuration.source_for("value") is ValueSource.DOTENV
    assert provider.interactive_checks == 0
    assert provider.read_calls == []


def test_default_prevents_prompting() -> None:
    spec = SettingSpec(
        name="value",
        parser=parse_nonblank_string,
        default="default-value",
        prompt="Configured value",
    )
    provider = FakePromptProvider(["unused"])

    configuration = resolve_configuration(
        (spec,),
        prompt_provider=provider,
    )

    assert configuration["value"] == "default-value"
    assert configuration.source_for("value") is ValueSource.DEFAULT
    assert provider.interactive_checks == 0
    assert provider.read_calls == []


def test_unresolved_setting_without_prompt_does_not_inspect_provider() -> None:
    spec = SettingSpec(
        name="value",
        parser=parse_nonblank_string,
    )
    provider = FakePromptProvider(["unused"])

    with pytest.raises(MissingConfigurationError):
        resolve_configuration(
            (spec,),
            prompt_provider=provider,
        )

    assert provider.interactive_checks == 0
    assert provider.read_calls == []


def test_prompting_can_be_disabled() -> None:
    provider = FakePromptProvider(["unused"])

    with pytest.raises(MissingConfigurationError):
        resolve_configuration(
            (prompted_spec(),),
            prompt_provider=provider,
            prompt_enabled=False,
        )

    assert provider.interactive_checks == 0
    assert provider.read_calls == []


def test_noninteractive_provider_does_not_read() -> None:
    provider = FakePromptProvider(
        ["unused"],
        interactive=False,
    )

    with pytest.raises(MissingConfigurationError):
        resolve_configuration(
            (prompted_spec(),),
            prompt_provider=provider,
        )

    assert provider.interactive_checks == 1
    assert provider.read_calls == []


def test_blank_prompt_response_remains_missing() -> None:
    provider = FakePromptProvider(["   "])

    with pytest.raises(
        MissingConfigurationError,
        match="- value",
    ):
        resolve_configuration(
            (prompted_spec(),),
            prompt_provider=provider,
        )

    assert provider.read_calls == [("Configured value", False)]


def test_blank_prompt_response_can_be_meaningful() -> None:
    provider = FakePromptProvider([""])
    spec = prompted_spec(blank_is_missing=False)

    configuration = resolve_configuration(
        (spec,),
        prompt_provider=provider,
    )

    assert configuration["value"] == ""
    assert configuration.source_for("value") is ValueSource.PROMPT


def test_invalid_prompted_value_reports_prompt_source() -> None:
    spec = SettingSpec(
        name="fetch_size",
        parser=parse_positive_integer,
        prompt="Fetch size",
    )
    provider = FakePromptProvider(["0"])

    with pytest.raises(
        ConfigurationValueError,
        match="from prompt is invalid",
    ) as captured:
        resolve_configuration(
            (spec,),
            prompt_provider=provider,
        )

    assert captured.value.source_name == "prompt"


def test_secret_prompt_parser_error_is_redacted() -> None:
    sensitive_value = "synthetic-sensitive-value"

    def reject(value: object) -> object:
        raise ValueError(f"rejected {value!r}")

    spec = SettingSpec(
        name="password",
        parser=reject,
        prompt="Password",
        secret=True,
    )
    provider = FakePromptProvider([sensitive_value])

    with pytest.raises(ConfigurationValueError) as captured:
        resolve_configuration(
            (spec,),
            prompt_provider=provider,
        )

    assert sensitive_value not in str(captured.value)
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


def test_prompt_error_from_provider_is_preserved() -> None:
    error = PromptError("prompt failed")
    provider = FakePromptProvider(
        [],
        read_error=error,
    )

    with pytest.raises(PromptError) as captured:
        resolve_configuration(
            (prompted_spec(),),
            prompt_provider=provider,
        )

    assert captured.value is error


@pytest.mark.parametrize(
    "error",
    [
        EOFError(),
        KeyboardInterrupt(),
        OSError("terminal failed"),
    ],
    ids=["end-of-file", "keyboard-interrupt", "operating-system"],
)
def test_raw_prompt_reader_errors_are_wrapped(
    error: BaseException,
) -> None:
    provider = FakePromptProvider(
        [],
        read_error=error,
    )

    with pytest.raises(
        PromptError,
        match="Could not read configuration prompt for setting 'value'",
    ) as captured:
        resolve_configuration(
            (prompted_spec(),),
            prompt_provider=provider,
        )

    assert captured.value.__cause__ is error


def test_interactivity_error_is_wrapped() -> None:
    provider = FakePromptProvider(
        [],
        interactive_error=OSError("terminal failed"),
    )

    with pytest.raises(
        PromptError,
        match="Could not determine whether prompting is interactive",
    ) as captured:
        resolve_configuration(
            (prompted_spec(),),
            prompt_provider=provider,
        )

    assert isinstance(captured.value.__cause__, OSError)


def test_interactivity_must_be_boolean() -> None:
    provider = FakePromptProvider(
        [],
        interactive="yes",
    )

    with pytest.raises(
        PromptError,
        match=r"PromptProvider\.is_interactive must return a Boolean",
    ):
        resolve_configuration(
            (prompted_spec(),),
            prompt_provider=provider,
        )


def test_prompt_enabled_must_be_boolean() -> None:
    with pytest.raises(
        SettingDefinitionError,
        match="prompt_enabled must be a Boolean",
    ):
        resolve_configuration(
            (),
            prompt_enabled=cast("bool", 1),
        )


def test_prompt_provider_must_satisfy_protocol() -> None:
    with pytest.raises(
        SettingDefinitionError,
        match="prompt_provider must implement PromptProvider",
    ):
        resolve_configuration(
            (),
            prompt_provider=cast("PromptProvider", object()),
        )


def test_multiple_prompted_values_preserve_declaration_order() -> None:
    specs = (
        SettingSpec(
            name="first",
            parser=parse_nonblank_string,
            prompt="First",
        ),
        SettingSpec(
            name="second",
            parser=parse_nonblank_string,
            prompt="Second",
        ),
    )
    provider = FakePromptProvider(["one", "two"])

    configuration = resolve_configuration(
        specs,
        prompt_provider=provider,
    )

    assert tuple(configuration) == ("first", "second")
    assert configuration.as_dict() == {
        "first": "one",
        "second": "two",
    }
    assert provider.interactive_checks == 1
    assert provider.read_calls == [
        ("First", False),
        ("Second", False),
    ]
