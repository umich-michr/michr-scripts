"""Tests for injectable terminal prompting."""

from typing import TextIO, cast

import pytest

from program_configuration import (
    PromptError,
    PromptProvider,
    TerminalPromptProvider,
)


class FakeInputStream:
    """Configurable input stream exposing only ``isatty()``."""

    def __init__(
        self,
        *,
        interactive: bool = True,
        error: Exception | None = None,
    ) -> None:
        self._interactive = interactive
        self._error = error
        self.calls = 0

    def isatty(self) -> bool:
        """Return configured interactivity or raise a configured error."""
        self.calls += 1

        if self._error is not None:
            raise self._error

        return self._interactive


class RecordingReader:
    """Callable prompt reader returning configured values."""

    def __init__(
        self,
        values: list[str],
        *,
        error: BaseException | None = None,
    ) -> None:
        self._values = list(values)
        self._error = error
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        """Record a prompt and return the next value."""
        self.prompts.append(prompt)

        if self._error is not None:
            raise self._error

        if not self._values:
            raise RuntimeError("No configured prompt value remains")

        return self._values.pop(0)


def make_provider(
    *,
    stream: FakeInputStream | None = None,
    input_reader: RecordingReader | None = None,
    sensitive_reader: RecordingReader | None = None,
) -> TerminalPromptProvider:
    """Return a terminal provider with inspectable dependencies."""
    return TerminalPromptProvider(
        input_stream=cast(
            "TextIO",
            FakeInputStream() if stream is None else stream,
        ),
        input_reader=RecordingReader(["ordinary"])
        if input_reader is None
        else input_reader,
        secret_reader=RecordingReader(["sensitive"])
        if sensitive_reader is None
        else sensitive_reader,
    )


def test_terminal_provider_satisfies_prompt_protocol() -> None:
    provider = make_provider()

    assert isinstance(provider, PromptProvider)


@pytest.mark.parametrize(
    ("interactive", "expected"),
    [
        (True, True),
        (False, False),
    ],
    ids=["interactive", "noninteractive"],
)
def test_terminal_provider_reports_stream_interactivity(
    interactive: bool,
    expected: bool,
) -> None:
    stream = FakeInputStream(interactive=interactive)
    provider = make_provider(stream=stream)

    assert provider.is_interactive is expected
    assert stream.calls == 1


def test_interactivity_failure_is_wrapped() -> None:
    stream = FakeInputStream(error=OSError("terminal failed"))
    provider = make_provider(stream=stream)

    with pytest.raises(
        PromptError,
        match="Could not determine whether prompting is interactive",
    ) as captured:
        _ = provider.is_interactive

    assert isinstance(captured.value.__cause__, OSError)


def test_ordinary_prompt_uses_input_reader() -> None:
    ordinary_reader = RecordingReader(["configured-value"])
    sensitive_reader = RecordingReader(["unused"])
    provider = make_provider(
        input_reader=ordinary_reader,
        sensitive_reader=sensitive_reader,
    )

    result = provider.read(
        "Input path",
        secret=False,
    )

    assert result == "configured-value"
    assert ordinary_reader.prompts == ["Input path: "]
    assert sensitive_reader.prompts == []


def test_secret_prompt_uses_secret_reader() -> None:
    ordinary_reader = RecordingReader(["unused"])
    sensitive_reader = RecordingReader(["configured-sensitive-value"])
    provider = make_provider(
        input_reader=ordinary_reader,
        sensitive_reader=sensitive_reader,
    )

    result = provider.read(
        "Database password",
        secret=True,
    )

    assert result == "configured-sensitive-value"
    assert ordinary_reader.prompts == []
    assert sensitive_reader.prompts == ["Database password: "]


@pytest.mark.parametrize(
    "prompt",
    ["", "   ", "\n\t"],
    ids=["empty", "spaces", "control-whitespace"],
)
def test_prompt_text_must_be_nonblank(prompt: str) -> None:
    provider = make_provider()

    with pytest.raises(
        PromptError,
        match="Prompt text must be a nonblank string",
    ):
        provider.read(
            prompt,
            secret=False,
        )


def test_prompt_text_must_be_string() -> None:
    provider = make_provider()

    with pytest.raises(
        PromptError,
        match="Prompt text must be a nonblank string",
    ):
        provider.read(
            cast("str", 42),
            secret=False,
        )


def test_prompt_secret_flag_must_be_boolean() -> None:
    provider = make_provider()

    with pytest.raises(
        PromptError,
        match="Prompt secret flag must be a Boolean",
    ):
        provider.read(
            "Value",
            secret=cast("bool", 1),
        )


@pytest.mark.parametrize(
    "error",
    [
        EOFError(),
        KeyboardInterrupt(),
        OSError("terminal failed"),
    ],
    ids=["end-of-file", "keyboard-interrupt", "operating-system"],
)
def test_reader_failures_are_wrapped(error: BaseException) -> None:
    reader = RecordingReader([], error=error)
    provider = make_provider(input_reader=reader)

    with pytest.raises(
        PromptError,
        match="Could not read configuration prompt 'Input path'",
    ) as captured:
        provider.read(
            "Input path",
            secret=False,
        )

    assert captured.value.__cause__ is error


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        ("input_reader", {"input_reader": 42}),
        ("secret_reader", {"secret_reader": object()}),
    ],
    ids=["input-reader", "secret-reader"],
)
def test_readers_must_be_callable(
    field_name: str,
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(
        PromptError,
        match=rf"Prompt {field_name} must be callable",
    ):
        TerminalPromptProvider(
            **kwargs,  # type: ignore[arg-type]
        )


def test_injected_reader_may_be_plain_callable() -> None:
    def reader(_prompt: str) -> str:
        return "value"

    provider = TerminalPromptProvider(
        input_stream=cast("TextIO", FakeInputStream()),
        input_reader=reader,
    )

    assert provider.read("Value", secret=False) == "value"
