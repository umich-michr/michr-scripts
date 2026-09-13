from pathlib import Path

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationInputConfig,
    derive_role_columns,
    effective_author_role,
    load_audit_report,
)


@pytest.mark.parametrize(
    ("eresearch_role", "study_team_role", "expected"),
    [
        ("PI", "TEAM_MEMBER", "PI"),
        ("Research Staff", "PRINCIPAL_INVESTIGATOR", "Research Staff"),
        (None, "PRINCIPAL_INVESTIGATOR", "PRINCIPAL_INVESTIGATOR"),
        ("", "TEAM_MEMBER", "TEAM_MEMBER"),
        (None, None, "UNKNOWN"),
    ],
)
def test_effective_role_precedence(
    eresearch_role: object,
    study_team_role: object,
    expected: str,
) -> None:
    assert (
        effective_author_role(
            eresearch_role=eresearch_role,
            study_team_role=study_team_role,
        )
        == expected
    )


def test_derive_role_columns_preserves_all_pi_indicators(
    valid_report_directory: Path,
) -> None:
    report = load_audit_report(
        ExplorationInputConfig(
            report_directory=valid_report_directory,
        )
    )
    records = report.records.copy()
    records.loc[0, "AUTHOR_ERESEARCH_ROLE"] = "PI"
    records.loc[0, "AUTHOR_STUDY_TEAM_ROLE"] = "TEAM_MEMBER"
    records.loc[0, "PI_USER_NAME"] = "different-pi@example.edu"

    records.loc[1, "AUTHOR_ERESEARCH_ROLE"] = pd.NA
    records.loc[1, "AUTHOR_STUDY_TEAM_ROLE"] = "PRINCIPAL_INVESTIGATOR"
    records.loc[1, "PI_USER_NAME"] = records.loc[1, "AUTHOR_USER_NAME"]

    derived = derive_role_columns(records)

    assert tuple(derived.columns) == (
        "audit_record_id",
        "effective_attempt_author_role",
        "author_is_pi_by_eresearch_role",
        "author_is_pi_by_application_role",
        "author_matches_named_pi_user_name",
        "attempt_author_is_study_pi",
    )
    assert derived["audit_record_id"].tolist() == [1001, 1002]

    first = derived.iloc[0]
    assert first["effective_attempt_author_role"] == "PI"
    assert bool(first["author_is_pi_by_eresearch_role"]) is True
    assert bool(first["author_is_pi_by_application_role"]) is False
    assert bool(first["author_matches_named_pi_user_name"]) is False
    assert bool(first["attempt_author_is_study_pi"]) is True

    second = derived.iloc[1]
    assert second["effective_attempt_author_role"] == "PRINCIPAL_INVESTIGATOR"
    assert bool(second["author_is_pi_by_eresearch_role"]) is False
    assert bool(second["author_is_pi_by_application_role"]) is True
    assert bool(second["author_matches_named_pi_user_name"]) is True
    assert bool(second["attempt_author_is_study_pi"]) is True
