"""Tests for explicit dotenv-file loading."""

import os
from pathlib import Path
from typing import cast

import pytest

from program_configuration import DotenvFileError, load_dotenv_file


def write_dotenv(
    tmp_path: Path,
    text: str,
    *,
    encoding: str = "utf-8",
) -> Path:
    """Write a dotenv fixture and return its path."""
    path = tmp_path / ".env"
    path.write_text(
        text,
        encoding=encoding,
    )

    return path


def test_load_dotenv_file_returns_values(tmp_path: Path) -> None:
    path = write_dotenv(
        tmp_path,
        ("EXAMPLE_NAME=example\nEXAMPLE_COUNT=42\nEXAMPLE_EMPTY=\nEXAMPLE_UNSET\n"),
    )

    result = load_dotenv_file(path)

    assert result == {
        "EXAMPLE_NAME": "example",
        "EXAMPLE_COUNT": "42",
        "EXAMPLE_EMPTY": "",
        "EXAMPLE_UNSET": None,
    }


def test_load_dotenv_file_supports_quotes_and_comments(
    tmp_path: Path,
) -> None:
    path = write_dotenv(
        tmp_path,
        (
            "# comment\n"
            'EXAMPLE_QUOTED="value with spaces"\n'
            "EXAMPLE_SINGLE='single quoted'\n"
            "export EXAMPLE_EXPORTED=exported\n"
        ),
    )

    result = load_dotenv_file(path)

    assert result == {
        "EXAMPLE_QUOTED": "value with spaces",
        "EXAMPLE_SINGLE": "single quoted",
        "EXAMPLE_EXPORTED": "exported",
    }


def test_dotenv_interpolation_is_disabled(tmp_path: Path) -> None:
    path = write_dotenv(
        tmp_path,
        ("EXAMPLE_BASE=base\nEXAMPLE_REFERENCE=${EXAMPLE_BASE}/child\n"),
    )

    result = load_dotenv_file(path)

    assert result["EXAMPLE_REFERENCE"] == "${EXAMPLE_BASE}/child"


def test_loading_dotenv_does_not_modify_process_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    variable_name = "PROGRAM_CONFIGURATION_SYNTHETIC_VALUE"
    monkeypatch.delenv(variable_name, raising=False)
    path = write_dotenv(
        tmp_path,
        f"{variable_name}=from-dotenv\n",
    )

    result = load_dotenv_file(path)

    assert result[variable_name] == "from-dotenv"

    assert variable_name not in os.environ


def test_missing_optional_dotenv_returns_empty_mapping(
    tmp_path: Path,
) -> None:
    result = load_dotenv_file(
        tmp_path / "missing.env",
        required=False,
    )

    assert result == {}


def test_missing_required_dotenv_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "missing.env"

    with pytest.raises(
        DotenvFileError,
        match="Required dotenv file does not exist",
    ) as captured:
        load_dotenv_file(
            path,
            required=True,
        )

    assert captured.value.path == path


def test_directory_path_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(
        DotenvFileError,
        match="Dotenv path is not a regular file",
    ) as captured:
        load_dotenv_file(tmp_path)

    assert captured.value.path == tmp_path


@pytest.mark.parametrize(
    "value",
    ["", "   ", "\n\t", 42, object()],
    ids=["empty", "spaces", "control-whitespace", "integer", "object"],
)
def test_dotenv_path_must_be_nonblank_string_or_path(
    value: object,
) -> None:
    invalid_path = cast("str | Path", value)

    with pytest.raises(
        DotenvFileError,
        match="Dotenv path must be a nonblank string or Path",
    ):
        load_dotenv_file(invalid_path)


@pytest.mark.parametrize(
    "value",
    ["", "   ", None, 42],
    ids=["empty", "spaces", "none", "integer"],
)
def test_dotenv_encoding_must_be_nonblank_string(
    tmp_path: Path,
    value: object,
) -> None:
    path = write_dotenv(tmp_path, "EXAMPLE=value\n")
    invalid_encoding = cast("str", value)

    with pytest.raises(
        DotenvFileError,
        match="Dotenv encoding must be a nonblank string",
    ):
        load_dotenv_file(
            path,
            encoding=invalid_encoding,
        )


@pytest.mark.parametrize(
    "value",
    [0, 1, None, "true"],
    ids=["zero", "one", "none", "text"],
)
def test_dotenv_required_must_be_exact_boolean(
    tmp_path: Path,
    value: object,
) -> None:
    path = tmp_path / "missing.env"
    invalid_required = cast("bool", value)

    with pytest.raises(
        DotenvFileError,
        match="Dotenv required must be a Boolean",
    ):
        load_dotenv_file(
            path,
            required=invalid_required,
        )


def test_unknown_encoding_is_wrapped(tmp_path: Path) -> None:
    path = write_dotenv(tmp_path, "EXAMPLE=value\n")

    with pytest.raises(
        DotenvFileError,
        match="Could not read dotenv file",
    ) as captured:
        load_dotenv_file(
            path,
            encoding="not-a-real-encoding",
        )

    assert captured.value.path == path
    assert captured.value.__cause__ is not None


def test_invalid_utf8_is_wrapped(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_bytes(b"EXAMPLE=\xff\n")

    with pytest.raises(
        DotenvFileError,
        match="Could not read dotenv file",
    ) as captured:
        load_dotenv_file(
            path,
            encoding="utf-8",
        )

    assert captured.value.path == path
    assert isinstance(captured.value.__cause__, UnicodeDecodeError)


def test_each_load_returns_a_fresh_dictionary(tmp_path: Path) -> None:
    path = write_dotenv(tmp_path, "EXAMPLE=value\n")

    first = load_dotenv_file(path)
    second = load_dotenv_file(path)

    assert first == second
    assert first is not second
