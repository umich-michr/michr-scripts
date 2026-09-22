"""Deterministic faculty-facing candidate research questions."""

from dataclasses import asdict, dataclass

import pandas as pd

CANDIDATE_RESEARCH_QUESTION_COLUMNS: tuple[str, ...] = (
    "research_question_id",
    "research_question",
    "primary_analytical_unit",
    "comparison_or_grouping",
    "outcome_or_measure",
    "supporting_output_files",
    "interpretation_cautions",
    "priority_tier",
    "analysis_status",
)


@dataclass(frozen=True, slots=True)
class CandidateResearchQuestion:
    """One identifier-free candidate question for later analysis."""

    research_question_id: str
    research_question: str
    primary_analytical_unit: str
    comparison_or_grouping: str
    outcome_or_measure: str
    supporting_output_files: str
    interpretation_cautions: str
    priority_tier: str
    analysis_status: str


_COMMON_CAUTION = (
    "Descriptive associations do not establish causality or evaluate "
    "individual authors."
)
_READABILITY_CAUTION = (
    "Readability formulas are descriptive indicators and do not establish "
    "comprehension, accuracy, accessibility, usefulness, or writing quality."
)
_TIMING_CAUTION = (
    "Elapsed time may include pauses or work outside the application and does "
    "not directly measure effort or efficiency."
)

_QUESTIONS: tuple[CandidateResearchQuestion, ...] = (
    CandidateResearchQuestion(
        research_question_id="RQ-001",
        research_question=(
            "How do completed-study pathways differ by final AI or manual "
            "authoring mode?"
        ),
        primary_analytical_unit="completed study",
        comparison_or_grouping="final completion authoring mode",
        outcome_or_measure=(
            "preceding incomplete attempts and first-attempt-to-completion time"
        ),
        supporting_output_files=(
            "overview/study_attempt_history_summary.csv; "
            "overview/author_handoff_summary.csv"
        ),
        interpretation_cautions=f"{_COMMON_CAUTION} {_TIMING_CAUTION}",
        priority_tier="CORE",
        analysis_status="DESCRIPTIVE_READY",
    ),
    CandidateResearchQuestion(
        research_question_id="RQ-002",
        research_question=(
            "Which incomplete-attempt outcomes most often precede a completed study?"
        ),
        primary_analytical_unit="completed study",
        comparison_or_grouping="preceding attempt result and final authoring mode",
        outcome_or_measure=(
            "counts of AI errors, errors without stack traces, and user drops"
        ),
        supporting_output_files=(
            "overview/study_attempt_history_summary.csv; "
            "overview/author_handoff_summary.csv"
        ),
        interpretation_cautions=_COMMON_CAUTION,
        priority_tier="CORE",
        analysis_status="DESCRIPTIVE_READY",
    ),
    CandidateResearchQuestion(
        research_question_id="RQ-003",
        research_question=(
            "How often do studies involve an author handoff before completion?"
        ),
        primary_analytical_unit="completed study",
        comparison_or_grouping=(
            "completion mode, preceding mode, preceding result, and handoff category"
        ),
        outcome_or_measure="distinct completed-study count and completion timing",
        supporting_output_files="overview/author_handoff_summary.csv",
        interpretation_cautions=f"{_COMMON_CAUTION} {_TIMING_CAUTION}",
        priority_tier="CORE",
        analysis_status="DESCRIPTIVE_READY",
    ),
    CandidateResearchQuestion(
        research_question_id="RQ-004",
        research_question=(
            "How does attempt-start author experience vary between AI and "
            "manual attempts?"
        ),
        primary_analytical_unit="author attempt",
        comparison_or_grouping=(
            "author adoption group, completion group, and attempt authoring mode"
        ),
        outcome_or_measure="prior studies created before attempt start",
        supporting_output_files="authors/attempt_start_experience_summary.csv",
        interpretation_cautions=(
            f"{_COMMON_CAUTION} One author may contribute multiple attempt "
            "observations."
        ),
        priority_tier="CORE",
        analysis_status="DESCRIPTIVE_READY",
    ),
    CandidateResearchQuestion(
        research_question_id="RQ-005",
        research_question=(
            "How do query-time experience and activity measures vary across "
            "author adoption groups?"
        ),
        primary_analytical_unit="distinct attempt author",
        comparison_or_grouping="AI-only, manual-only, and mixed-mode authors",
        outcome_or_measure=(
            "study creation, memberships, login days, and login-history span"
        ),
        supporting_output_files="authors/current_author_experience_summary.csv",
        interpretation_cautions=(
            f"{_COMMON_CAUTION} Query-time values are not historical "
            "attempt-level snapshots."
        ),
        priority_tier="CORE",
        analysis_status="DESCRIPTIVE_READY",
    ),
    CandidateResearchQuestion(
        research_question_id="RQ-006",
        research_question=(
            "Which study-posting fields most often receive and retain selected "
            "AI suggestions?"
        ),
        primary_analytical_unit="completed AI attempt and field",
        comparison_or_grouping="study-posting field",
        outcome_or_measure=(
            "suggestion offers, selections, exact retention, and edit outcomes"
        ),
        supporting_output_files=(
            "fields/field_adoption_editing_summary.csv; "
            "fields/suggestion_selection_summary.csv"
        ),
        interpretation_cautions=(
            f"{_COMMON_CAUTION} Selection and retention do not establish "
            "suggestion quality."
        ),
        priority_tier="CORE",
        analysis_status="DESCRIPTIVE_READY",
    ),
    CandidateResearchQuestion(
        research_question_id="RQ-007",
        research_question=(
            "How does edit intensity vary by field after an AI suggestion is selected?"
        ),
        primary_analytical_unit="completed AI attempt and field",
        comparison_or_grouping="field and operational edit-intensity category",
        outcome_or_measure="retention and edit-intensity counts and percentages",
        supporting_output_files="fields/field_adoption_editing_summary.csv",
        interpretation_cautions=(
            f"{_COMMON_CAUTION} Edit-intensity thresholds are exploratory and "
            "not literature-standard categories."
        ),
        priority_tier="CORE",
        analysis_status="DESCRIPTIVE_READY",
    ),
    CandidateResearchQuestion(
        research_question_id="RQ-008",
        research_question=(
            "How is edit intensity associated with selected-to-final "
            "grade-level direction?"
        ),
        primary_analytical_unit="completed AI attempt and field",
        comparison_or_grouping="field and operational edit-intensity category",
        outcome_or_measure="consensus grade-level direction and median change",
        supporting_output_files=(
            "readability/field_edit_readability_cross_summary.csv"
        ),
        interpretation_cautions=(
            f"{_COMMON_CAUTION} {_READABILITY_CAUTION} Missing readability "
            "pairs reduce the comparable sample."
        ),
        priority_tier="CORE",
        analysis_status="DESCRIPTIVE_READY",
    ),
    CandidateResearchQuestion(
        research_question_id="RQ-009",
        research_question=(
            "Do selected suggestions differ from unselected suggestions on "
            "readability indicators?"
        ),
        primary_analytical_unit=(
            "completed AI attempt, field, and readability measure"
        ),
        comparison_or_grouping="field and readability measure",
        outcome_or_measure="selected minus mean-unselected readability value",
        supporting_output_files=(
            "readability/selected_vs_unselected_readability_summary.csv"
        ),
        interpretation_cautions=(
            f"{_COMMON_CAUTION} {_READABILITY_CAUTION} Selection is not random."
        ),
        priority_tier="CORE",
        analysis_status="DESCRIPTIVE_READY",
    ),
    CandidateResearchQuestion(
        research_question_id="RQ-010",
        research_question=(
            "How do observed final-text grade-level bands differ by field and "
            "AI or manual authoring mode?"
        ),
        primary_analytical_unit="observed nonblank final text",
        comparison_or_grouping="field and attempt authoring mode",
        outcome_or_measure="Flesch-Kincaid grade-level bands",
        supporting_output_files=("readability/field_readability_target_summary.csv"),
        interpretation_cautions=(
            f"{_COMMON_CAUTION} {_READABILITY_CAUTION} Titles are short text "
            "with limited reliability."
        ),
        priority_tier="CORE",
        analysis_status="DESCRIPTIVE_READY",
    ),
    CandidateResearchQuestion(
        research_question_id="RQ-011",
        research_question=(
            "How do attempt and completion timing distributions vary by authoring mode?"
        ),
        primary_analytical_unit="attempt and completed study",
        comparison_or_grouping="attempt mode and final completion mode",
        outcome_or_measure=(
            "study-information-page time, total attempt time, and time to completion"
        ),
        supporting_output_files=(
            "attempts/grouped_attempt_summary.csv; "
            "overview/study_attempt_history_summary.csv"
        ),
        interpretation_cautions=f"{_COMMON_CAUTION} {_TIMING_CAUTION}",
        priority_tier="CORE",
        analysis_status="DESCRIPTIVE_READY",
    ),
    CandidateResearchQuestion(
        research_question_id="RQ-012",
        research_question=(
            "Where do reported and inferred study-content-source categories disagree?"
        ),
        primary_analytical_unit="AI attempt",
        comparison_or_grouping="reported and inferred content-source category",
        outcome_or_measure="agreement and disagreement counts and percentages",
        supporting_output_files=(
            "attempts/content_source_concordance_summary.csv; "
            "attempts/content_source_concordance_matrix.csv"
        ),
        interpretation_cautions=(
            f"{_COMMON_CAUTION} Disagreement does not establish which value is correct."
        ),
        priority_tier="SECONDARY",
        analysis_status="DESCRIPTIVE_READY",
    ),
    CandidateResearchQuestion(
        research_question_id="RQ-013",
        research_question=(
            "How do study completion pathways vary across participant type and "
            "department?"
        ),
        primary_analytical_unit="study",
        comparison_or_grouping="participant type and study department",
        outcome_or_measure=(
            "completion, preceding attempts, and time-to-completion distributions"
        ),
        supporting_output_files="studies/grouped_study_summary.csv",
        interpretation_cautions=(
            f"{_COMMON_CAUTION} Small groups may be unstable and should not be "
            "used to evaluate departments."
        ),
        priority_tier="SECONDARY",
        analysis_status="DESCRIPTIVE_READY",
    ),
    CandidateResearchQuestion(
        research_question_id="RQ-014",
        research_question=(
            "How do effective role, principal-investigator classification, and "
            "appointment context vary across author populations?"
        ),
        primary_analytical_unit="distinct attempt author",
        comparison_or_grouping="role, PI classification, and appointment group",
        outcome_or_measure="distinct-author counts and percentages",
        supporting_output_files="authors/grouped_author_summary.csv",
        interpretation_cautions=(
            f"{_COMMON_CAUTION} Appointment groups can overlap and are not "
            "intended to sum to 100 percent."
        ),
        priority_tier="SECONDARY",
        analysis_status="DESCRIPTIVE_READY",
    ),
    CandidateResearchQuestion(
        research_question_id="RQ-015",
        research_question=(
            "Among studies with repeated attempts, how often do mode, author, "
            "and source characteristics change before AI completion, manual "
            "completion, or no completion observed?"
        ),
        primary_analytical_unit="study",
        comparison_or_grouping=(
            "mutually exclusive retry pathway and observed completion group"
        ),
        outcome_or_measure=(
            "attempt count, mode change, author change, AI error, "
            "returned-result AI, source change, feedback presence, and timing"
        ),
        supporting_output_files=(
            "overview/study_retry_pathway_summary.csv; "
            "overview/retry_characteristics_summary.csv"
        ),
        interpretation_cautions=(
            f"{_COMMON_CAUTION} {_TIMING_CAUTION} No completion observed is "
            "not a final outcome because formal follow-up time is unavailable."
        ),
        priority_tier="CORE",
        analysis_status="DESCRIPTIVE_READY",
    ),
    CandidateResearchQuestion(
        research_question_id="RQ-016",
        research_question=(
            "Among same-author studies with returned-result AI attempts "
            "followed by manual completion, how often do source "
            "characteristics change and how often is feedback recorded?"
        ),
        primary_analytical_unit="study",
        comparison_or_grouping=(
            "AI-to-manual completion pathway, author continuity, and "
            "source-comparison eligibility"
        ),
        outcome_or_measure=("source-signature change and count-only feedback presence"),
        supporting_output_files=(
            "overview/study_retry_pathway_summary.csv; "
            "overview/repeated_attempt_source_consistency_summary.csv"
        ),
        interpretation_cautions=(
            f"{_COMMON_CAUTION} Source-signature equality does not prove "
            "identical text. Feedback presence does not establish satisfaction."
        ),
        priority_tier="SECONDARY",
        analysis_status="DESCRIPTIVE_READY",
    ),
)


def build_candidate_research_questions() -> pd.DataFrame:
    """Return the stable identifier-free candidate-question catalog."""
    return pd.DataFrame.from_records(
        [asdict(question) for question in _QUESTIONS],
        columns=list(CANDIDATE_RESEARCH_QUESTION_COLUMNS),
    )
