import pandas as pd

from study_posting_audit_exploration import (
    CANDIDATE_RESEARCH_QUESTION_COLUMNS,
    CandidateResearchQuestion,
    build_candidate_research_questions,
)


def test_candidate_research_question_model_is_immutable() -> None:
    question = CandidateResearchQuestion(
        research_question_id="RQ-TEST",
        research_question="Synthetic question?",
        primary_analytical_unit="synthetic unit",
        comparison_or_grouping="synthetic comparison",
        outcome_or_measure="synthetic measure",
        supporting_output_files="synthetic/output.csv",
        interpretation_cautions="Synthetic caution.",
        priority_tier="CORE",
        analysis_status="DESCRIPTIVE_READY",
    )

    assert question.research_question_id == "RQ-TEST"
    assert question.analysis_status == "DESCRIPTIVE_READY"


def test_candidate_research_questions_are_stable_and_identifier_free() -> None:
    questions = build_candidate_research_questions()

    assert isinstance(questions, pd.DataFrame)
    assert tuple(questions.columns) == CANDIDATE_RESEARCH_QUESTION_COLUMNS
    assert questions["research_question_id"].tolist() == [
        f"RQ-{index:03d}" for index in range(1, 17)
    ]
    assert questions["research_question_id"].is_unique
    assert questions["analysis_status"].eq("DESCRIPTIVE_READY").all()
    assert set(questions["priority_tier"]) == {
        "CORE",
        "SECONDARY",
    }
    assert not questions.isna().any().any()
    assert (
        questions.astype("string")
        .apply(lambda column: column.str.strip().ne("").all())
        .all()
    )

    published_text = questions.to_csv(
        index=False,
        lineterminator="\n",
    )

    for forbidden_value in (
        "audit_record_id",
        "study_num",
        "author_user_name",
        "selected_text",
        "final_text",
        "LLM_SUGGESTIONS",
        "FINAL_SUBMISSION",
    ):
        assert forbidden_value not in published_text


def test_candidate_questions_reference_published_aggregate_outputs() -> None:
    questions = build_candidate_research_questions()
    references = "; ".join(questions["supporting_output_files"].tolist())

    for expected_file in (
        "overview/study_attempt_history_summary.csv",
        "authors/current_author_experience_summary.csv",
        "fields/field_adoption_editing_summary.csv",
        "readability/field_edit_readability_cross_summary.csv",
        "attempts/content_source_concordance_matrix.csv",
        "studies/grouped_study_summary.csv",
    ):
        assert expected_file in references
