"""Layered resolution of declarative program settings."""

from collections.abc import Iterable, Mapping
from typing import cast

from program_configuration.errors import (
    ConfigurationValueError,
    MissingConfigurationError,
    PromptError,
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
from program_configuration.prompting import PromptProvider


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
    """Return the highest-precedence nonmissing non-prompt value."""
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

    raise ConfigurationValueError(
        setting_name=spec.name,
        source_name=source.value,
        detail="secret value was rejected by its parser",
    )


def _require_prompt_enabled(value: object) -> bool:
    """Return an exact Boolean prompt-enabled flag."""
    if type(value) is not bool:
        raise SettingDefinitionError("prompt_enabled must be a Boolean")

    return value


def _require_prompt_provider(
    value: object,
) -> PromptProvider | None:
    """Return a structurally valid prompt provider or ``None``."""
    if value is None:
        return None

    if not isinstance(value, PromptProvider):
        raise SettingDefinitionError("prompt_provider must implement PromptProvider")

    return value


def _prompt_provider_is_interactive(
    provider: PromptProvider,
) -> bool:
    """Return an exact interactive-capability value."""
    try:
        result = provider.is_interactive
    except PromptError:
        raise
    except (AttributeError, OSError) as error:
        raise PromptError(
            "Could not determine whether prompting is interactive"
        ) from error

    if type(result) is not bool:
        raise PromptError("PromptProvider.is_interactive must return a Boolean")

    return result


def _prompt_candidate(
    spec: SettingSpec,
    *,
    provider: PromptProvider | None,
    prompt_enabled: bool,
    interactive: bool,
) -> ResolvedValue | None:
    """Prompt for one unresolved setting when permitted."""
    if not prompt_enabled or provider is None or not interactive or spec.prompt is None:
        return None

    try:
        raw_value = provider.read(
            spec.prompt,
            secret=spec.secret,
        )
    except PromptError:
        raise
    except (EOFError, KeyboardInterrupt, OSError) as error:
        raise PromptError(
            f"Could not read configuration prompt for setting {spec.name!r}"
        ) from error

    if _is_missing(raw_value, spec=spec):
        return None

    return _parse_candidate(
        spec,
        raw_value=raw_value,
        source=ValueSource.PROMPT,
    )


def resolve_configuration(
    specs: Iterable[SettingSpec],
    *,
    explicit: Mapping[str, object] | None = None,
    environment: Mapping[str, object] | None = None,
    dotenv: Mapping[str, object] | None = None,
    prompt_provider: PromptProvider | None = None,
    prompt_enabled: bool = True,
) -> ResolvedConfiguration:
    """Resolve settings using deterministic layered precedence.

    Precedence is:

    ```text
    explicit → environment → dotenv → default → prompt → unresolved
    ```

    Prompting occurs only for settings that remain unresolved, declare prompt
    text, have an interactive provider, and are resolved with prompting enabled.

    Missing required settings are reported together in declaration order.
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
    prompting_enabled = _require_prompt_enabled(prompt_enabled)
    provider = _require_prompt_provider(prompt_provider)

    declared_names = {spec.name for spec in validated_specs}
    unknown_names = sorted(set(explicit_values) - declared_names)

    if unknown_names:
        raise UnknownExplicitSettingError(unknown_names)

    interactive: bool | None = None
    entries: list[ResolvedValue] = []
    missing_names: list[str] = []

    for spec in validated_specs:
        candidate = _candidate(
            spec,
            explicit=explicit_values,
            environment=environment_values,
            dotenv=dotenv_values,
        )

        if candidate is not None:
            raw_value, source = candidate
            entries.append(
                _parse_candidate(
                    spec,
                    raw_value=raw_value,
                    source=source,
                )
            )
            continue

        if prompting_enabled and provider is not None and spec.prompt is not None:
            if interactive is None:
                interactive = _prompt_provider_is_interactive(provider)

            prompt_is_interactive = interactive
        else:
            prompt_is_interactive = False

        prompted = _prompt_candidate(
            spec,
            provider=provider,
            prompt_enabled=prompting_enabled,
            interactive=prompt_is_interactive,
        )

        if prompted is None:
            missing_names.append(spec.name)
        else:
            entries.append(prompted)

    if missing_names:
        raise MissingConfigurationError(missing_names)

    return ResolvedConfiguration(tuple(entries))
