from typing import Any, cast

import pytest

from study_posting_audit_exploration import (
    ExplorationValidationError,
    author_changed,
    same_author_within_study,
)


def test_same_author_requires_matching_study_and_exact_username() -> None:
    assert (
        same_author_within_study(
            attempt_study_num="SYNTHETIC-STUDY-1",
            attempt_author_user_name="person@example.edu",
            comparison_study_num="SYNTHETIC-STUDY-1",
            comparison_author_user_name="person@example.edu",
        )
        is True
    )


@pytest.mark.parametrize(
    (
        "attempt_study",
        "attempt_author",
        "comparison_study",
        "comparison_author",
    ),
    [
        (
            "SYNTHETIC-STUDY-1",
            "person@example.edu",
            "SYNTHETIC-STUDY-2",
            "person@example.edu",
        ),
        (
            "SYNTHETIC-STUDY-1",
            "person@example.edu",
            "SYNTHETIC-STUDY-1",
            "other@example.edu",
        ),
        (
            "SYNTHETIC-STUDY-1",
            "Person@example.edu",
            "SYNTHETIC-STUDY-1",
            "person@example.edu",
        ),
    ],
)
def test_same_author_comparison_does_not_normalize_source_values(
    attempt_study: str,
    attempt_author: str,
    comparison_study: str,
    comparison_author: str,
) -> None:
    assert (
        same_author_within_study(
            attempt_study_num=attempt_study,
            attempt_author_user_name=attempt_author,
            comparison_study_num=comparison_study,
            comparison_author_user_name=comparison_author,
        )
        is False
    )


def test_author_changed_within_study() -> None:
    assert (
        author_changed(
            previous_study_num="SYNTHETIC-STUDY-1",
            previous_author_user_name="first@example.edu",
            current_study_num="SYNTHETIC-STUDY-1",
            current_author_user_name="second@example.edu",
        )
        is True
    )


def test_author_unchanged_within_study() -> None:
    assert (
        author_changed(
            previous_study_num="SYNTHETIC-STUDY-1",
            previous_author_user_name="person@example.edu",
            current_study_num="SYNTHETIC-STUDY-1",
            current_author_user_name="person@example.edu",
        )
        is False
    )


def test_author_change_rejects_cross_study_comparison() -> None:
    with pytest.raises(
        ExplorationValidationError,
        match="requires attempts from the same study",
    ):
        author_changed(
            previous_study_num="SYNTHETIC-STUDY-1",
            previous_author_user_name="person@example.edu",
            current_study_num="SYNTHETIC-STUDY-2",
            current_author_user_name="person@example.edu",
        )


@pytest.mark.parametrize(
    ("field_name", "arguments"),
    [
        (
            "attempt_study_num",
            {
                "attempt_study_num": "",
                "attempt_author_user_name": "person@example.edu",
                "comparison_study_num": "SYNTHETIC-STUDY-1",
                "comparison_author_user_name": "person@example.edu",
            },
        ),
        (
            "attempt_author_user_name",
            {
                "attempt_study_num": "SYNTHETIC-STUDY-1",
                "attempt_author_user_name": None,
                "comparison_study_num": "SYNTHETIC-STUDY-1",
                "comparison_author_user_name": "person@example.edu",
            },
        ),
    ],
)
def test_identity_values_must_be_nonblank(
    field_name: str,
    arguments: dict[str, object],
) -> None:
    with pytest.raises(
        ExplorationValidationError,
        match=rf"{field_name} must be a nonblank string",
    ):
        same_author_within_study(**cast("dict[str, Any]", arguments))
