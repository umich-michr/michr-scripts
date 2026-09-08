"""Tests for package metadata and typing support."""

from pathlib import Path

import michr_text_post_editing as package


def test_package_is_not_an_implicit_namespace() -> None:
    """A missing __init__.py would produce an implicit namespace package."""
    assert package.__file__ is not None


def test_package_exposes_its_version() -> None:
    assert package.__version__ == "0.1.0"
    assert "__version__" in package.__all__


def test_package_ships_typing_marker() -> None:
    """PEP 561 marker lets consumers use the package's inline annotations."""
    assert package.__file__ is not None

    package_directory = Path(package.__file__).parent

    assert (package_directory / "py.typed").is_file()
