"""Tests for layered program-configuration resolution."""

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import cast

import pytest

from program_configuration import (
    ConfigurationValueError,
    MissingConfigurationError,
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


@pytest.mark.parametrize(
    ("argument_name", "keyword"),
    [
        ("Explicit configuration", "explicit"),
        ("Environment configuration", "environment"),
        ("Dotenv configuration", "dotenv"),
    ],
    ids=["explicit", "environment", "dotenv"],
)
def test_configuration_layer_keys_must_be_strings(
    argument_name: str,
    keyword: str,
) -> None:
    invalid_mapping = cast(
        "Mapping[str, object]",
        {1: "value"},
    )

    with pytest.raises(
        SettingDefinitionError,
        match=rf"{argument_name} keys must be strings",
    ):
        resolve_configuration(
            (),
            **{keyword: invalid_mapping},
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
