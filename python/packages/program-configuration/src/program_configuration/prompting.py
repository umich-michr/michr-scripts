"""Injectable prompting for unresolved program settings."""

from collections.abc import Callable
import getpass
import sys
from typing import Protocol, TextIO, runtime_checkable

from program_configuration.errors import PromptError


@runtime_checkable
class PromptProvider(Protocol):
    """Interface used to obtain unresolved configuration values."""

    @property
    def is_interactive(self) -> bool:
        """Return whether prompting is currently possible."""
        ...

    def read(
        self,
        prompt: str,
        *,
        secret: bool,
    ) -> str:
        """Read one raw configuration value."""
        ...


def _require_prompt_text(value: object) -> str:
    """Return nonblank prompt text."""
    if not isinstance(value, str) or not value.strip():
        raise PromptError("Prompt text must be a nonblank string")

    return value


class TerminalPromptProvider:
    """Prompt through the process terminal.

    Normal values use ``input()``. Secret values use ``getpass.getpass()``.
    Interactive capability is determined from the configured input stream.

    Parameters
    ----------
    input_stream
        Stream used only to determine interactive capability. Defaults to
        ``sys.stdin``.
    input_reader
        Callable used for ordinary prompts. Defaults to ``input``.
    secret_reader
        Callable used for secret prompts. Defaults to ``getpass.getpass``.
    """

    def __init__(
        self,
        *,
        input_stream: TextIO | None = None,
        input_reader: Callable[[str], str] | None = None,
        secret_reader: Callable[[str], str] | None = None,
    ) -> None:
        self._input_stream = sys.stdin if input_stream is None else input_stream
        self._input_reader = input if input_reader is None else input_reader
        self._secret_reader = (
            getpass.getpass if secret_reader is None else secret_reader
        )

        if not callable(self._input_reader):
            raise PromptError("Prompt input_reader must be callable")

        if not callable(self._secret_reader):
            raise PromptError("Prompt secret_reader must be callable")

    @property
    def is_interactive(self) -> bool:
        """Return whether the configured input stream is interactive."""
        try:
            return self._input_stream.isatty()
        except (AttributeError, OSError) as error:
            raise PromptError(
                "Could not determine whether prompting is interactive"
            ) from error

    def read(
        self,
        prompt: str,
        *,
        secret: bool,
    ) -> str:
        """Read one terminal value using the appropriate reader."""
        prompt_text = _require_prompt_text(prompt)

        if type(secret) is not bool:
            raise PromptError("Prompt secret flag must be a Boolean")

        rendered_prompt = f"{prompt_text}: "

        try:
            if secret:
                return self._secret_reader(rendered_prompt)

            return self._input_reader(rendered_prompt)
        except (EOFError, KeyboardInterrupt, OSError) as error:
            raise PromptError(
                f"Could not read configuration prompt {prompt_text!r}"
            ) from error
