"""Tests for the text-readability-metrics public contract."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import text_readability_metrics as package


def test_package_is_not_an_implicit_namespace() -> None:
    assert package.__file__ is not None


def test_package_exposes_version_and_typing_marker() -> None:
    assert package.__version__ == "0.1.0"
    assert "__version__" in package.__all__
    assert package.__file__ is not None

    package_directory = Path(package.__file__).parent

    assert (package_directory / "py.typed").is_file()


def test_public_api_exposes_readability_contract() -> None:
    assert "ReadabilityError" in package.__all__
    assert "InvalidReadabilityTextError" in package.__all__
    assert "InvalidReadabilityResultError" in package.__all__
    assert "ReadabilityResult" in package.__all__
    assert "analyze_readability" in package.__all__


def test_readability_result_is_immutable() -> None:
    result = package.ReadabilityResult(
        flesch_kincaid_grade=1.0,
        automated_readability_index=2.0,
        coleman_liau_index=3.0,
        gunning_fog=4.0,
        dale_chall_readability_score=5.0,
        estimated_reading_time_seconds=6.0,
        sentence_count=7,
        word_count=8,
        syllable_count=9,
        letter_count=10,
        polysyllable_count=11,
    )

    with pytest.raises(FrozenInstanceError):
        type(result).__setattr__(result, "word_count", 12)


def test_errors_share_one_public_base_class() -> None:
    assert issubclass(package.InvalidReadabilityTextError, package.ReadabilityError)
    assert issubclass(package.InvalidReadabilityResultError, package.ReadabilityError)
    assert issubclass(package.ReadabilityError, ValueError)
