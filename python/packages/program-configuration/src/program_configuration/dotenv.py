"""Explicit dotenv-file loading without process-environment mutation."""

from pathlib import Path

from dotenv import dotenv_values

from program_configuration.errors import DotenvFileError


def _require_dotenv_path(value: object) -> Path:
    """Return a nonblank dotenv file path."""
    if isinstance(value, Path):
        return value

    if isinstance(value, str):
        if not value.strip():
            raise DotenvFileError("Dotenv path must be a nonblank string or Path")

        return Path(value)

    raise DotenvFileError("Dotenv path must be a nonblank string or Path")


def _require_encoding(value: object) -> str:
    """Return a nonblank text encoding."""
    if not isinstance(value, str) or not value.strip():
        raise DotenvFileError("Dotenv encoding must be a nonblank string")

    return value


def load_dotenv_file(
    path: str | Path,
    *,
    required: bool = False,
    encoding: str = "utf-8",
) -> dict[str, object]:
    """Load dotenv values without changing ``os.environ``.

    Parameters
    ----------
    path
        Dotenv file path.
    required
        Whether a missing file is an error. An implicitly selected default
        dotenv file should normally use ``False``. An explicitly requested file
        should normally use ``True``.
    encoding
        Text encoding used to read the file.

    Returns
    -------
    dict[str, object]
        Fresh mapping of dotenv keys to strings or ``None``. A key declared
        without a value is represented by ``None`` and is treated as missing by
        the core resolver.

    Raises
    ------
    DotenvFileError
        If arguments are invalid, a required file is absent, the path is not a
        regular file, or the file cannot be read or decoded.

    Notes
    -----
    Variable interpolation is disabled. This keeps dotenv loading deterministic
    and prevents values from depending implicitly on ``os.environ``.
    """
    dotenv_path = _require_dotenv_path(path)
    dotenv_encoding = _require_encoding(encoding)

    if type(required) is not bool:
        raise DotenvFileError(
            "Dotenv required must be a Boolean",
            path=dotenv_path,
        )

    if not dotenv_path.exists():
        if required:
            raise DotenvFileError(
                f"Required dotenv file does not exist: {dotenv_path}",
                path=dotenv_path,
            )

        return {}

    if not dotenv_path.is_file():
        raise DotenvFileError(
            f"Dotenv path is not a regular file: {dotenv_path}",
            path=dotenv_path,
        )

    try:
        values = dotenv_values(
            dotenv_path=dotenv_path,
            encoding=dotenv_encoding,
            interpolate=False,
        )
    except (LookupError, OSError, UnicodeError) as error:
        raise DotenvFileError(
            f"Could not read dotenv file {dotenv_path}: {error}",
            path=dotenv_path,
        ) from error

    return dict(values)
