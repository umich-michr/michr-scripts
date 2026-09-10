"""Models for declarative configuration resolution."""

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum

from program_configuration.errors import SettingDefinitionError


class _MissingValue:
    """Sentinel distinguishing no default from a default value."""

    __slots__ = ()

    def __repr__(self) -> str:
        """Return a stable debugging representation."""
        return "MISSING"


MISSING = _MissingValue()
type SettingParser = Callable[[object], object]


class ValueSource(StrEnum):
    """Source from which one configuration value was resolved."""

    EXPLICIT = "explicit"
    ENVIRONMENT = "environment"
    DOTENV = "dotenv"
    DEFAULT = "default"
    PROMPT = "prompt"


def _require_nonblank_string(
    value: object,
    *,
    field_name: str,
) -> str:
    """Return a nonblank string."""
    if not isinstance(value, str) or not value.strip():
        raise SettingDefinitionError(f"{field_name} must be a nonblank string")

    return value


def _require_optional_nonblank_string(
    value: object,
    *,
    field_name: str,
) -> str | None:
    """Return a nonblank string or ``None``."""
    if value is None:
        return None

    return _require_nonblank_string(
        value,
        field_name=field_name,
    )


def _require_boolean(
    value: object,
    *,
    field_name: str,
) -> bool:
    """Return an exact Boolean."""
    if type(value) is not bool:
        raise SettingDefinitionError(f"{field_name} must be a Boolean")

    return value


@dataclass(frozen=True, slots=True)
class SettingSpec:
    """Declarative specification for one configuration setting.

    Parameters
    ----------
    name
        Program-local setting name used for explicit values and resolved
        lookups.
    parser
        Callable that validates and converts a raw value.
    environment_variable
        Optional process-environment and dotenv key.
    default
        Optional default value. ``MISSING`` means that the setting is required
        when no higher-precedence source supplies it.
    secret
        Whether the resolved value must be redacted from representations.
    blank_is_missing
        Whether a blank string should be treated as absent and allow fallback
        to a lower-precedence source.
    prompt
        Optional nonblank text used to request a missing value. A setting is
        not prompted when this is ``None``.
    """

    name: str
    parser: SettingParser
    environment_variable: str | None = None
    default: object = MISSING
    prompt: str | None = None
    secret: bool = False
    blank_is_missing: bool = True

    def __post_init__(self) -> None:
        """Validate the setting definition."""
        _require_nonblank_string(
            self.name,
            field_name="Setting name",
        )
        _require_optional_nonblank_string(
            self.environment_variable,
            field_name=f"Environment variable for setting {self.name!r}",
        )

        _require_optional_nonblank_string(
            self.prompt,
            field_name=f"Prompt for setting {self.name!r}",
        )

        if not callable(self.parser):
            raise SettingDefinitionError(
                f"Parser for setting {self.name!r} must be callable"
            )

        _require_boolean(
            self.secret,
            field_name=f"secret for setting {self.name!r}",
        )
        _require_boolean(
            self.blank_is_missing,
            field_name=f"blank_is_missing for setting {self.name!r}",
        )


@dataclass(frozen=True, slots=True, repr=False)
class ResolvedValue:
    """One parsed configuration value with safe provenance."""

    name: str
    value: object
    source: ValueSource
    secret: bool

    def __repr__(self) -> str:
        """Return a representation that redacts secret values."""
        rendered_value = "<redacted>" if self.secret else repr(self.value)

        return (
            f"ResolvedValue(name={self.name!r}, value={rendered_value}, "
            f"source={self.source!r}, secret={self.secret!r})"
        )


class ResolvedConfiguration(Mapping[str, object]):
    """Immutable mapping of resolved values with source provenance."""

    __slots__ = ("_entries", "_values")

    def __init__(
        self,
        entries: tuple[ResolvedValue, ...],
    ) -> None:
        names: set[str] = set()
        values: dict[str, ResolvedValue] = {}

        for entry in entries:
            if not isinstance(entry, ResolvedValue):
                raise SettingDefinitionError(
                    "Resolved configuration entries must be ResolvedValue instances"
                )

            if entry.name in names:
                raise SettingDefinitionError(
                    f"Resolved configuration contains duplicate setting {entry.name!r}"
                )

            names.add(entry.name)
            values[entry.name] = entry

        self._entries = entries
        self._values = values

    def __getitem__(self, name: str) -> object:
        """Return one resolved value."""
        return self._values[name].value

    def __iter__(self) -> Iterator[str]:
        """Iterate over setting names in declaration order."""
        return (entry.name for entry in self._entries)

    def __len__(self) -> int:
        """Return the number of resolved settings."""
        return len(self._entries)

    def __repr__(self) -> str:
        """Return a representation with secret values redacted."""
        values = ", ".join(
            (
                f"{entry.name}=<redacted>"
                if entry.secret
                else f"{entry.name}={entry.value!r}"
            )
            for entry in self._entries
        )

        return f"ResolvedConfiguration({values})"

    @property
    def entries(self) -> tuple[ResolvedValue, ...]:
        """Return resolved entries in declaration order."""
        return self._entries

    def source_for(self, name: str) -> ValueSource:
        """Return the source used for one setting."""
        return self._values[name].source

    def resolved_value(self, name: str) -> ResolvedValue:
        """Return one value together with safe provenance metadata."""
        return self._values[name]

    def as_dict(self) -> dict[str, object]:
        """Return a fresh dictionary containing resolved values."""
        return {entry.name: entry.value for entry in self._entries}
