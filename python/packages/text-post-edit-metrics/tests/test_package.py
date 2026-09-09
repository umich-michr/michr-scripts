"""Tests for package metadata and typing support."""

from pathlib import Path

import text_post_edit_metrics as package
from text_post_edit_metrics.metrics import (
    analyze_post_edit,
    calculate_character_metrics,
    calculate_soft_word_metrics,
    calculate_ter_metrics,
    normalized_word_distance,
    weighted_soft_word_distance,
)
from text_post_edit_metrics.normalization import (
    clamp01,
    count_whitespace_tokens,
    normalize_metric_text,
)


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


def test_package_exports_normalization_helpers() -> None:
    assert package.normalize_metric_text is normalize_metric_text
    assert package.count_whitespace_tokens is count_whitespace_tokens
    assert package.clamp01 is clamp01


def test_package_exports_metric_api() -> None:
    assert package.analyze_post_edit is analyze_post_edit
    assert package.calculate_ter_metrics is calculate_ter_metrics
    assert package.calculate_character_metrics is calculate_character_metrics
    assert package.calculate_soft_word_metrics is calculate_soft_word_metrics
    assert package.normalized_word_distance is normalized_word_distance
    assert package.weighted_soft_word_distance is weighted_soft_word_distance
