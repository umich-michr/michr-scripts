"""Exceptions raised by reusable program-configuration resolution."""

from collections.abc import Iterable
from pathlib import Path


class ConfigurationError(ValueError):
    """Base class for expected configuration failures."""


class SettingDefinitionError(ConfigurationError):
    """A setting specification is invalid or ambiguous."""


class ConfigurationValueError(ConfigurationError):
    """A supplied setting value cannot be parsed."""

    def __init__(
        self,
        *,
        setting_name: str,
        source_name: str,
        detail: str,
    ) -> None:
        self.setting_name = setting_name
        self.source_name = source_name
        self.detail = detail

        super().__init__(
            f"Configuration setting {setting_name!r} from "
            f"{source_name} is invalid: {detail}"
        )


class MissingConfigurationError(ConfigurationError):
    """One or more required settings remain unresolved."""

    def __init__(
        self,
        setting_names: Iterable[str],
    ) -> None:
        names = tuple(setting_names)

        if not names:
            raise SettingDefinitionError(
                "MissingConfigurationError requires at least one setting name"
            )

        self.setting_names = names
        formatted = "\n".join(f"- {name}" for name in names)

        super().__init__(f"Missing required configuration settings:\n{formatted}")


class UnknownExplicitSettingError(ConfigurationError):
    """Explicit configuration contains an undeclared setting."""

    def __init__(
        self,
        setting_names: Iterable[str],
    ) -> None:
        names = tuple(setting_names)

        if not names:
            raise SettingDefinitionError(
                "UnknownExplicitSettingError requires at least one setting name"
            )

        self.setting_names = names
        formatted = ", ".join(repr(name) for name in names)

        super().__init__(
            f"Explicit configuration contains unknown settings: {formatted}"
        )


class DotenvFileError(ConfigurationError):
    """A dotenv file path or file operation is invalid."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
    ) -> None:
        self.path = path
        super().__init__(message)


class PromptError(ConfigurationError):
    """An interactive configuration prompt cannot be completed."""
