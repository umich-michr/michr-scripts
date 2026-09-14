"""Cross-file validation required for readability pairing."""

import pandas as pd

from study_posting_audit_exploration.errors import ExplorationValidationError

_COMPLETE = "COMPLETE"
_AI = "AI"
_SELECTED_TRUE = "true"
_CLEARED_MATCH_TYPE = "REMOVED"
_UNASSISTED_MATCH_TYPE = "UNASSISTED"


def _selected_suggestions(readability: pd.DataFrame) -> pd.DataFrame:
    """Return readability suggestion rows marked selected."""
    selected = readability["selected"].astype("string").str.lower()

    return readability.loc[
        readability["text_role"].eq("SUGGESTED") & selected.eq(_SELECTED_TRUE)
    ]


def _require_completed_ownership(
    records: pd.DataFrame,
    readability: pd.DataFrame,
) -> None:
    """Require readability rows to belong to matching completed attempts."""
    context = records.loc[
        :,
        [
            "ID",
            "ATTEMPT_TYPE",
            "ATTEMPT_RESULT",
        ],
    ].rename(
        columns={
            "ID": "record_id",
            "ATTEMPT_TYPE": "record_attempt_type",
        }
    )
    joined = readability.merge(
        context,
        on="record_id",
        how="left",
        validate="many_to_one",
    )
    incomplete_count = int((~joined["ATTEMPT_RESULT"].eq(_COMPLETE)).sum())

    if incomplete_count:
        raise ExplorationValidationError(
            "readability_metrics.csv rows must belong to completed attempts: "
            f"{incomplete_count} affected rows"
        )

    mismatched_type_count = int(
        joined["attempt_type"].ne(joined["record_attempt_type"]).sum()
    )

    if mismatched_type_count:
        raise ExplorationValidationError(
            "readability_metrics.csv attempt_type values do not match records.csv: "
            f"{mismatched_type_count} affected rows"
        )


def _require_unique_pair_components(
    readability: pd.DataFrame,
) -> None:
    """Require at most one final and selected row per attempt and field."""
    final = readability.loc[readability["text_role"].eq("FINAL")]
    duplicate_final_count = int(
        final.duplicated(
            subset=[
                "record_id",
                "field_name",
            ],
            keep=False,
        ).sum()
    )

    if duplicate_final_count:
        raise ExplorationValidationError(
            "readability_metrics.csv contains multiple final rows per audit field: "
            f"{duplicate_final_count} affected rows"
        )

    selected = _selected_suggestions(readability)
    duplicate_selected_count = int(
        selected.duplicated(
            subset=[
                "record_id",
                "field_name",
            ],
            keep=False,
        ).sum()
    )

    if duplicate_selected_count:
        raise ExplorationValidationError(
            "readability_metrics.csv contains multiple selected suggestions "
            f"per audit field: {duplicate_selected_count} affected rows"
        )


def _require_selected_suggestion_matches_pick(
    records: pd.DataFrame,
    ai_assistance: pd.DataFrame,
    readability: pd.DataFrame,
) -> None:
    """Require selected readability identities to match AI field picks."""
    selected = _selected_suggestions(readability)
    ai_context = ai_assistance.loc[
        :,
        [
            "record_id",
            "field_name",
            "picked_kind",
            "picked_index",
        ],
    ]
    joined = selected.merge(
        ai_context,
        on=[
            "record_id",
            "field_name",
        ],
        how="left",
        validate="one_to_one",
    )
    mismatch_count = int(
        (
            joined["picked_kind"].isna()
            | joined["picked_index"].isna()
            | joined["suggestion_kind"].ne(joined["picked_kind"])
            | joined["suggestion_index"].ne(joined["picked_index"])
        ).sum()
    )

    if mismatch_count:
        raise ExplorationValidationError(
            "selected readability suggestions do not match AI-assistance picks: "
            f"{mismatch_count} affected rows"
        )

    attempt_context = records.loc[
        :,
        [
            "ID",
            "ATTEMPT_TYPE",
            "ATTEMPT_RESULT",
        ],
    ].rename(columns={"ID": "record_id"})
    selected_attempts = selected.merge(
        attempt_context,
        on="record_id",
        how="left",
        validate="many_to_one",
    )
    invalid_owner_count = int(
        (
            ~selected_attempts["ATTEMPT_TYPE"].eq(_AI)
            | ~selected_attempts["ATTEMPT_RESULT"].eq(_COMPLETE)
        ).sum()
    )

    if invalid_owner_count:
        raise ExplorationValidationError(
            "selected readability suggestions must belong to completed AI attempts: "
            f"{invalid_owner_count} affected rows"
        )


def _require_assisted_pair_components(
    ai_assistance: pd.DataFrame,
    readability: pd.DataFrame,
) -> None:
    """Require pair rows for selected, retained AI text outcomes."""
    assisted = ai_assistance.loc[
        ai_assistance["analysis_type"].isin(
            {
                "TEXT",
                "COMPENSATION",
            }
        )
        & ~ai_assistance["match_type"].isin(
            {
                _CLEARED_MATCH_TYPE,
                _UNASSISTED_MATCH_TYPE,
            }
        )
    ]
    selected = (
        _selected_suggestions(readability)
        .loc[
            :,
            [
                "record_id",
                "field_name",
            ],
        ]
        .assign(has_selected_readability=True)
    )
    final = readability.loc[
        readability["text_role"].eq("FINAL"),
        [
            "record_id",
            "field_name",
        ],
    ].assign(has_final_readability=True)
    joined = assisted.merge(
        selected,
        on=[
            "record_id",
            "field_name",
        ],
        how="left",
        validate="one_to_one",
    ).merge(
        final,
        on=[
            "record_id",
            "field_name",
        ],
        how="left",
        validate="one_to_one",
    )
    missing_selected_count = int(joined["has_selected_readability"].isna().sum())

    if missing_selected_count:
        raise ExplorationValidationError(
            "assisted AI text fields lack selected readability rows: "
            f"{missing_selected_count} affected rows"
        )

    missing_final_count = int(joined["has_final_readability"].isna().sum())

    if missing_final_count:
        raise ExplorationValidationError(
            "assisted AI text fields lack final readability rows: "
            f"{missing_final_count} affected rows"
        )


def validate_readability_pairing_contract(
    records: pd.DataFrame,
    ai_assistance: pd.DataFrame,
    readability: pd.DataFrame,
) -> None:
    """Validate cross-file relationships required for readability pairing."""
    _require_completed_ownership(
        records,
        readability,
    )
    _require_unique_pair_components(readability)
    _require_selected_suggestion_matches_pick(
        records,
        ai_assistance,
        readability,
    )
    _require_assisted_pair_components(
        ai_assistance,
        readability,
    )
