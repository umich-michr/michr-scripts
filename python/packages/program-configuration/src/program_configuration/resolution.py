"""Pure layered resolution of declarative program settings."""

from collections.abc import Iterable, Mapping
from typing import cast

from program_configuration.errors import (
    ConfigurationValueError,
    MissingConfigurationError,
    SettingDefinitionError,
    UnknownExplicitSettingError,
)
from program_configuration.models import (
    MISSING,
    ResolvedConfiguration,
    ResolvedValue,
    SettingSpec,
    ValueSource,
)


def _copy_string_mapping(
    value: object,
    *,
    mapping_name: str,
) -> dict[str, object]:
    """Validate and copy a string-keyed mapping."""
    if not isinstance(value, Mapping):
        raise SettingDefinitionError(f"{mapping_name} must be a mapping")

    mapping = cast("Mapping[object, object]", value)
    result: dict[str, object] = {}

    for key, item in mapping.items():
        if not isinstance(key, str):
            raise SettingDefinitionError(f"{mapping_name} keys must be strings")

        result[key] = item

    return result


def _validate_specs(
    specs: Iterable[SettingSpec],
) -> tuple[SettingSpec, ...]:
    """Validate setting specifications and reject ambiguous names."""
    result: list[SettingSpec] = []
    names: set[str] = set()
    environment_variables: set[str] = set()

    for spec in specs:
        if not isinstance(spec, SettingSpec):
            raise SettingDefinitionError(
                "Configuration specifications must be SettingSpec instances"
            )

        if spec.name in names:
            raise SettingDefinitionError(
                f"Duplicate configuration setting name: {spec.name!r}"
            )

        names.add(spec.name)

        environment_variable = spec.environment_variable

        if environment_variable is not None:
            if environment_variable in environment_variables:
                raise SettingDefinitionError(
                    "Duplicate configuration environment variable: "
                    f"{environment_variable!r}"
                )

            environment_variables.add(environment_variable)

        result.append(spec)

    return tuple(result)


def _is_missing(
    value: object,
    *,
    spec: SettingSpec,
) -> bool:
    """Return whether one raw value should permit source fallback."""
    if value is None:
        return True

    return spec.blank_is_missing and isinstance(value, str) and not value.strip()


def _candidate(
    spec: SettingSpec,
    *,
    explicit: Mapping[str, object],
    environment: Mapping[str, object],
    dotenv: Mapping[str, object],
) -> tuple[object, ValueSource] | None:
    """Return the highest-precedence nonmissing raw value."""
    if spec.name in explicit:
        value = explicit[spec.name]

        if not _is_missing(value, spec=spec):
            return value, ValueSource.EXPLICIT

    environment_variable = spec.environment_variable

    if environment_variable is not None:
        if environment_variable in environment:
            value = environment[environment_variable]

            if not _is_missing(value, spec=spec):
                return value, ValueSource.ENVIRONMENT

        if environment_variable in dotenv:
            value = dotenv[environment_variable]

            if not _is_missing(value, spec=spec):
                return value, ValueSource.DOTENV

    if spec.default is not MISSING:
        return spec.default, ValueSource.DEFAULT

    return None


def _parse_candidate(
    spec: SettingSpec,
    *,
    raw_value: object,
    source: ValueSource,
) -> ResolvedValue:
    """Parse one raw candidate without disclosing secret values."""
    try:
        parsed = spec.parser(raw_value)
    except (TypeError, ValueError) as error:
        if not spec.secret:
            detail = str(error).strip() or "value was rejected by its parser"

            raise ConfigurationValueError(
                setting_name=spec.name,
                source_name=source.value,
                detail=detail,
            ) from error
    else:
        return ResolvedValue(
            name=spec.name,
            value=parsed,
            source=source,
            secret=spec.secret,
        )

    # Raise outside the exception handler so a secret-bearing parser exception
    # is not retained as __cause__ or __context__.
    raise ConfigurationValueError(
        setting_name=spec.name,
        source_name=source.value,
        detail="secret value was rejected by its parser",
    )


def resolve_configuration(
    specs: Iterable[SettingSpec],
    *,
    explicit: Mapping[str, object] | None = None,
    environment: Mapping[str, object] | None = None,
    dotenv: Mapping[str, object] | None = None,
) -> ResolvedConfiguration:
    """Resolve settings using deterministic layered precedence.

    Precedence is:

    ```text
    explicit → environment → dotenv → default → unresolved
    ```

    Missing required settings are reported together in declaration order.
    Values are parsed only after their highest-precedence source is selected.
    """
    validated_specs = _validate_specs(specs)
    explicit_values = _copy_string_mapping(
        {} if explicit is None else explicit,
        mapping_name="Explicit configuration",
    )
    environment_values = _copy_string_mapping(
        {} if environment is None else environment,
        mapping_name="Environment configuration",
    )
    dotenv_values = _copy_string_mapping(
        {} if dotenv is None else dotenv,
        mapping_name="Dotenv configuration",
    )

    declared_names = {spec.name for spec in validated_specs}
    unknown_names = sorted(set(explicit_values) - declared_names)

    if unknown_names:
        raise UnknownExplicitSettingError(unknown_names)

    entries: list[ResolvedValue] = []
    missing_names: list[str] = []

    for spec in validated_specs:
        candidate = _candidate(
            spec,
            explicit=explicit_values,
            environment=environment_values,
            dotenv=dotenv_values,
        )

        if candidate is None:
            missing_names.append(spec.name)
            continue

        raw_value, source = candidate
        entries.append(
            _parse_candidate(
                spec,
                raw_value=raw_value,
                source=source,
            )
        )

    if missing_names:
        raise MissingConfigurationError(missing_names)

    return ResolvedConfiguration(tuple(entries))
