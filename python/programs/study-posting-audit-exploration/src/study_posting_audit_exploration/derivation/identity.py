"""Attempt-author identity comparisons within one study."""

from study_posting_audit_exploration.errors import ExplorationValidationError


def _require_nonblank_string(
    value: object,
    *,
    field_name: str,
) -> str:
    """Return a nonblank identity value without normalizing it."""
    if not isinstance(value, str) or not value.strip():
        raise ExplorationValidationError(f"{field_name} must be a nonblank string")

    return value


def same_author_within_study(
    *,
    attempt_study_num: object,
    attempt_author_user_name: object,
    comparison_study_num: object,
    comparison_author_user_name: object,
) -> bool:
    """Return whether two attempts belong to one study and have one author.

    Comparisons use source values exactly as stored. Usernames are not trimmed,
    case-folded, prefixed, hashed, or pseudonymized.
    """
    attempt_study = _require_nonblank_string(
        attempt_study_num,
        field_name="attempt_study_num",
    )
    attempt_author = _require_nonblank_string(
        attempt_author_user_name,
        field_name="attempt_author_user_name",
    )
    comparison_study = _require_nonblank_string(
        comparison_study_num,
        field_name="comparison_study_num",
    )
    comparison_author = _require_nonblank_string(
        comparison_author_user_name,
        field_name="comparison_author_user_name",
    )

    return attempt_study == comparison_study and attempt_author == comparison_author


def author_changed(
    *,
    previous_study_num: object,
    previous_author_user_name: object,
    current_study_num: object,
    current_author_user_name: object,
) -> bool:
    """Return whether consecutive attempts for one study changed authors.

    Raises
    ------
    ExplorationValidationError
        If attempts belong to different studies. A cross-study author change is
        not a meaningful study-attempt transition.
    """
    previous_study = _require_nonblank_string(
        previous_study_num,
        field_name="previous_study_num",
    )
    current_study = _require_nonblank_string(
        current_study_num,
        field_name="current_study_num",
    )

    if previous_study != current_study:
        raise ExplorationValidationError(
            "author-change comparison requires attempts from the same study"
        )

    previous_author = _require_nonblank_string(
        previous_author_user_name,
        field_name="previous_author_user_name",
    )
    current_author = _require_nonblank_string(
        current_author_user_name,
        field_name="current_author_user_name",
    )

    return previous_author != current_author
