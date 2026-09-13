"""Effective author-role and PI-indicator derivation."""

import pandas as pd

_UNKNOWN_ROLE = "UNKNOWN"
_ERESEARCH_PI_ROLE = "PI"
_APPLICATION_PI_ROLE = "PRINCIPAL_INVESTIGATOR"


def _optional_nonblank_string(value: object) -> str | None:
    """Return nonblank source text or ``None``."""
    if not isinstance(value, str):
        return None

    if not value.strip():
        return None

    return value


def effective_author_role(
    *,
    eresearch_role: object,
    study_team_role: object,
) -> str:
    """Return the authoritative available author role.

    eResearch role takes precedence. The application study-team role is used
    only when eResearch role is missing or blank.
    """
    authoritative_role = _optional_nonblank_string(eresearch_role)

    if authoritative_role is not None:
        return authoritative_role

    fallback_role = _optional_nonblank_string(study_team_role)

    return _UNKNOWN_ROLE if fallback_role is None else fallback_role


def _boolean_series(
    values: pd.Series,
) -> pd.Series:
    """Return an exact non-null pandas Boolean series."""
    return values.fillna(False).astype("boolean")


def derive_role_columns(records: pd.DataFrame) -> pd.DataFrame:
    """Return role and PI indicators keyed by audit record ID."""
    output = pd.DataFrame(
        {
            "audit_record_id": records["ID"].astype("Int64"),
            "effective_attempt_author_role": [
                effective_author_role(
                    eresearch_role=eresearch_role,
                    study_team_role=study_team_role,
                )
                for eresearch_role, study_team_role in zip(
                    records["AUTHOR_ERESEARCH_ROLE"],
                    records["AUTHOR_STUDY_TEAM_ROLE"],
                    strict=True,
                )
            ],
        }
    )
    output["author_is_pi_by_eresearch_role"] = _boolean_series(
        records["AUTHOR_ERESEARCH_ROLE"].eq(_ERESEARCH_PI_ROLE)
    )
    output["author_is_pi_by_application_role"] = _boolean_series(
        records["AUTHOR_ERESEARCH_ROLE"].isna()
        & records["AUTHOR_STUDY_TEAM_ROLE"].eq(_APPLICATION_PI_ROLE)
    )
    output["author_matches_named_pi_user_name"] = _boolean_series(
        records["AUTHOR_USER_NAME"].notna()
        & records["PI_USER_NAME"].notna()
        & records["AUTHOR_USER_NAME"].eq(records["PI_USER_NAME"])
    )
    output["attempt_author_is_study_pi"] = _boolean_series(
        output["author_is_pi_by_eresearch_role"]
        | output["author_is_pi_by_application_role"]
        | output["author_matches_named_pi_user_name"]
    )

    return output.loc[
        :,
        [
            "audit_record_id",
            "effective_attempt_author_role",
            "author_is_pi_by_eresearch_role",
            "author_is_pi_by_application_role",
            "author_matches_named_pi_user_name",
            "attempt_author_is_study_pi",
        ],
    ]
