"""Tests for declarative configuration models."""

from typing import cast

import pytest

from program_configuration import (
    MISSING,
    ResolvedConfiguration,
    ResolvedValue,
    SettingDefinitionError,
    SettingSpec,
    ValueSource,
    parse_nonblank_string,
)


def test_missing_sentinel_has_stable_representation() -> None:
    assert repr(MISSING) == "MISSING"


def test_value_source_values_are_stable() -> None:
    assert ValueSource.EXPLICIT.value == "explicit"
    assert ValueSource.ENVIRONMENT.value == "environment"
    assert ValueSource.DOTENV.value == "dotenv"
    assert ValueSource.DEFAULT.value == "default"
    assert ValueSource.PROMPT.value == "prompt"


def test_setting_spec_preserves_configuration() -> None:
    spec = SettingSpec(
        name="input_path",
        parser=parse_nonblank_string,
        environment_variable="EXAMPLE_INPUT",
        default="input.csv",
        prompt="Input path",
        secret=True,
        blank_is_missing=False,
    )

    assert spec.prompt == "Input path"
    assert spec.name == "input_path"
    assert spec.parser is parse_nonblank_string
    assert spec.environment_variable == "EXAMPLE_INPUT"
    assert spec.default == "input.csv"
    assert spec.secret is True
    assert spec.blank_is_missing is False


def test_setting_without_default_uses_missing_sentinel() -> None:
    spec = SettingSpec(
        name="input_path",
        parser=parse_nonblank_string,
    )

    assert spec.default is MISSING


@pytest.mark.parametrize(
    "name",
    ["", "   ", "\n\t"],
    ids=["empty", "spaces", "control-whitespace"],
)
def test_setting_name_must_be_nonblank(name: str) -> None:
    with pytest.raises(
        SettingDefinitionError,
        match="Setting name must be a nonblank string",
    ):
        SettingSpec(
            name=name,
            parser=parse_nonblank_string,
        )


def test_setting_name_must_be_string() -> None:
    with pytest.raises(
        SettingDefinitionError,
        match="Setting name must be a nonblank string",
    ):
        SettingSpec(
            name=cast("str", 42),
            parser=parse_nonblank_string,
        )


@pytest.mark.parametrize(
    "environment_variable",
    ["", "   ", "\n"],
    ids=["empty", "spaces", "newline"],
)
def test_environment_variable_must_be_nonblank(
    environment_variable: str,
) -> None:
    with pytest.raises(
        SettingDefinitionError,
        match="Environment variable for setting 'input_path'",
    ):
        SettingSpec(
            name="input_path",
            parser=parse_nonblank_string,
            environment_variable=environment_variable,
        )


def test_environment_variable_must_be_string_or_none() -> None:
    with pytest.raises(
        SettingDefinitionError,
        match="Environment variable for setting 'input_path'",
    ):
        SettingSpec(
            name="input_path",
            parser=parse_nonblank_string,
            environment_variable=cast("str | None", 42),
        )


@pytest.mark.parametrize(
    "prompt",
    ["", "   ", "\n\t"],
    ids=["empty", "spaces", "control-whitespace"],
)
def test_setting_prompt_must_be_nonblank(prompt: str) -> None:
    with pytest.raises(
        SettingDefinitionError,
        match="Prompt for setting 'input_path' must be a nonblank string",
    ):
        SettingSpec(
            name="input_path",
            parser=parse_nonblank_string,
            prompt=prompt,
        )


def test_setting_prompt_must_be_string_or_none() -> None:
    with pytest.raises(
        SettingDefinitionError,
        match="Prompt for setting 'input_path' must be a nonblank string",
    ):
        SettingSpec(
            name="input_path",
            parser=parse_nonblank_string,
            prompt=cast("str | None", 42),
        )


def test_setting_parser_must_be_callable() -> None:
    with pytest.raises(
        SettingDefinitionError,
        match="Parser for setting 'input_path' must be callable",
    ):
        SettingSpec(
            name="input_path",
            parser=cast("object", 42),  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        ("secret", {"secret": 1}),
        ("blank_is_missing", {"blank_is_missing": "true"}),
    ],
    ids=["secret", "blank-is-missing"],
)
def test_setting_boolean_fields_require_exact_booleans(
    field_name: str,
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(
        SettingDefinitionError,
        match=rf"{field_name} for setting 'input_path' must be a Boolean",
    ):
        SettingSpec(
            name="input_path",
            parser=parse_nonblank_string,
            **kwargs,  # type: ignore[arg-type]
        )


def test_resolved_value_exposes_nonsecret_value_in_representation() -> None:
    entry = ResolvedValue(
        name="region",
        value="east",
        source=ValueSource.ENVIRONMENT,
        secret=False,
    )

    representation = repr(entry)

    assert "region" in representation
    assert "east" in representation
    assert "environment" in representation


def test_resolved_value_redacts_secret_in_representation() -> None:
    sensitive_value = "synthetic-sensitive-value"
    entry = ResolvedValue(
        name="password",
        value=sensitive_value,
        source=ValueSource.ENVIRONMENT,
        secret=True,
    )

    representation = repr(entry)

    assert "<redacted>" in representation
    assert sensitive_value not in representation


def test_resolved_configuration_behaves_as_ordered_mapping() -> None:
    configuration = ResolvedConfiguration(
        (
            ResolvedValue(
                name="region",
                value="east",
                source=ValueSource.EXPLICIT,
                secret=False,
            ),
            ResolvedValue(
                name="count",
                value=3,
                source=ValueSource.DEFAULT,
                secret=False,
            ),
        )
    )

    assert len(configuration) == 2
    assert tuple(configuration) == ("region", "count")
    assert configuration["region"] == "east"
    assert configuration["count"] == 3


def test_resolved_configuration_exposes_entries_and_provenance() -> None:
    region = ResolvedValue(
        name="region",
        value="east",
        source=ValueSource.DOTENV,
        secret=False,
    )
    configuration = ResolvedConfiguration((region,))

    assert configuration.entries == (region,)
    assert configuration.source_for("region") is ValueSource.DOTENV
    assert configuration.resolved_value("region") is region


def test_resolved_configuration_as_dict_returns_fresh_dictionary() -> None:
    configuration = ResolvedConfiguration(
        (
            ResolvedValue(
                name="region",
                value="east",
                source=ValueSource.DEFAULT,
                secret=False,
            ),
        )
    )

    first = configuration.as_dict()
    second = configuration.as_dict()

    assert first == {"region": "east"}
    assert second == first
    assert second is not first


def test_resolved_configuration_redacts_secret_representation() -> None:
    sensitive_value = "synthetic-sensitive-value"
    configuration = ResolvedConfiguration(
        (
            ResolvedValue(
                name="password",
                value=sensitive_value,
                source=ValueSource.ENVIRONMENT,
                secret=True,
            ),
            ResolvedValue(
                name="region",
                value="east",
                source=ValueSource.DEFAULT,
                secret=False,
            ),
        )
    )

    representation = repr(configuration)

    assert "password=<redacted>" in representation
    assert "region='east'" in representation
    assert sensitive_value not in representation


def test_resolved_configuration_allows_no_entries() -> None:
    configuration = ResolvedConfiguration(())

    assert len(configuration) == 0
    assert tuple(configuration) == ()
    assert configuration.as_dict() == {}


def test_resolved_configuration_rejects_invalid_entry() -> None:
    entries = cast(
        "tuple[ResolvedValue, ...]",
        (object(),),
    )

    with pytest.raises(
        SettingDefinitionError,
        match="entries must be ResolvedValue instances",
    ):
        ResolvedConfiguration(entries)


def test_resolved_configuration_rejects_duplicate_names() -> None:
    entries = (
        ResolvedValue(
            name="region",
            value="east",
            source=ValueSource.EXPLICIT,
            secret=False,
        ),
        ResolvedValue(
            name="region",
            value="west",
            source=ValueSource.DEFAULT,
            secret=False,
        ),
    )

    with pytest.raises(
        SettingDefinitionError,
        match="duplicate setting 'region'",
    ):
        ResolvedConfiguration(entries)


def test_unknown_configuration_name_raises_key_error() -> None:
    configuration = ResolvedConfiguration(())

    with pytest.raises(KeyError):
        _ = configuration["missing"]

    with pytest.raises(KeyError):
        configuration.source_for("missing")

    with pytest.raises(KeyError):
        configuration.resolved_value("missing")
