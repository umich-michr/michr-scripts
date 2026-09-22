"""Static filenames and column contracts for normalized report inputs."""

RECORDS_FILENAME = "records.csv"
AI_ASSISTANCE_METRICS_FILENAME = "ai_assistance_metrics.csv"
READABILITY_METRICS_FILENAME = "readability_metrics.csv"
REPORT_METADATA_FILENAME = "report_metadata.json"
REPORT_METADATA_SCHEMA_VERSION = 1
SOURCE_TIMESTAMP_TIME_ZONE = "America/Detroit"
SOURCE_SNAPSHOT_PROVENANCE_UNAVAILABLE = "UNAVAILABLE"
SOURCE_SNAPSHOT_PROVENANCE_SOURCE_PROVIDED = "SOURCE_PROVIDED"
SOURCE_SNAPSHOT_PROVENANCE_REPORT_RUN_CUTOFF = "REPORT_RUN_CUTOFF"

REPORT_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "report_generated_at_utc",
        "source_snapshot_as_of_utc",
        "source_snapshot_provenance",
    }
)

RECORD_COLUMNS: tuple[str, ...] = (
    "ID",
    "START_TIME",
    "END_TIME",
    "ATTEMPT_TYPE",
    "ATTEMPT_RESULT",
    "USER_TYPE",
    "STUDY_NUM",
    "CREATED_DATE",
    "CREATED_BY_ID",
    "PUBLISHABLE",
    "STUDY_DEPARTMENT",
    "STUDY_PARTICIPANT_TYPE",
    "USER_ID",
    "AUTHOR_USER_NAME",
    "AUTHOR_STUDY_TEAM_ROLE",
    "AUTHOR_ERESEARCH_ROLE",
    "AUTHOR_APPOINTMENTS",
    "PI_USER_NAME",
    "PI_APPOINTMENTS",
    "PRIOR_CREATED_COUNT",
    "TOTAL_CREATED_COUNT",
    "MEMBER_OF_OTHER_STUDIES_COUNT",
    "LOGIN_DAYS",
    "MIN_LOGIN_TIME",
    "MAX_LOGIN_TIME",
    "TIME_SPENT_ON_STUDY_INFO_PAGE_MS",
    "TIME_TO_FINISH_ADDING_STUDY_MS",
    "LATENCY_MS",
    "SOURCE_SIZE_CHARS",
    "SOURCE_TYPE",
    "STUDY_CONTENT_SOURCE",
    "LLM_INFERRED_STUDY_CONTENT_SOURCE",
    "STUDY_CONTENT_SOURCE_OTHER_VALUE",
    "LLM_INFERRED_STUDY_CONTENT_SOURCE_OTHER_VALUE",
    "USER_FEEDBACK_COMMENTS",
    "LLM_SUGGESTIONS",
    "SELECTED_SUGGESTIONS",
    "FINAL_SUBMISSION",
    "LLM_METADATA",
)

AI_ASSISTANCE_COLUMNS: tuple[str, ...] = (
    "record_id",
    "field_name",
    "analysis_type",
    "match_type",
    "suggestion_count_total",
    "suggestion_counts_json",
    "picked_kind",
    "picked_index",
    "selected_text",
    "final_text",
    "ter_rate",
    "ter_effort_saved_raw",
    "ter_effort_saved",
    "policy_adjusted_effort_saved",
    "character_edit_distance",
    "character_effort_saved_raw",
    "character_effort_saved",
    "soft_word_edit_distance",
    "soft_word_effort_saved_raw",
    "soft_word_effort_saved",
    "estimated_characters_saved",
    "suggestion_character_count",
    "final_character_count",
    "suggestion_word_count",
    "final_word_count",
    "flag_suggested",
    "flag_saved",
    "flag_accepted",
    "flag_changed",
    "compensation_text_required",
    "lookup_similarity",
    "offered_ids",
    "picked_ids",
    "saved_ids",
    "kept_ids",
    "dropped_ids",
    "added_ids",
    "saved_not_offered_ids",
)

READABILITY_COLUMNS: tuple[str, ...] = (
    "record_id",
    "attempt_type",
    "field_name",
    "text_role",
    "suggestion_kind",
    "suggestion_index",
    "selected",
    "flesch_kincaid_grade",
    "automated_readability_index",
    "coleman_liau_index",
    "gunning_fog",
    "dale_chall_readability_score",
    "estimated_reading_time_seconds",
    "sentence_count",
    "word_count",
    "syllable_count",
    "letter_count",
    "polysyllable_count",
)

RECORD_DATETIME_COLUMNS: tuple[str, ...] = (
    "START_TIME",
    "END_TIME",
    "CREATED_DATE",
    "MIN_LOGIN_TIME",
    "MAX_LOGIN_TIME",
)

RECORD_INTEGER_COLUMNS: tuple[str, ...] = (
    "ID",
    "CREATED_BY_ID",
    "USER_ID",
    "PRIOR_CREATED_COUNT",
    "TOTAL_CREATED_COUNT",
    "MEMBER_OF_OTHER_STUDIES_COUNT",
    "LOGIN_DAYS",
    "TIME_SPENT_ON_STUDY_INFO_PAGE_MS",
    "TIME_TO_FINISH_ADDING_STUDY_MS",
    "LATENCY_MS",
    "SOURCE_SIZE_CHARS",
)

AI_ASSISTANCE_INTEGER_COLUMNS: tuple[str, ...] = (
    "record_id",
    "suggestion_count_total",
    "picked_index",
    "character_edit_distance",
    "suggestion_character_count",
    "final_character_count",
    "suggestion_word_count",
    "final_word_count",
)

AI_ASSISTANCE_FLOAT_COLUMNS: tuple[str, ...] = (
    "ter_rate",
    "ter_effort_saved_raw",
    "ter_effort_saved",
    "policy_adjusted_effort_saved",
    "character_effort_saved_raw",
    "character_effort_saved",
    "soft_word_edit_distance",
    "soft_word_effort_saved_raw",
    "soft_word_effort_saved",
    "estimated_characters_saved",
    "lookup_similarity",
)

READABILITY_INTEGER_COLUMNS: tuple[str, ...] = (
    "record_id",
    "suggestion_index",
    "sentence_count",
    "word_count",
    "syllable_count",
    "letter_count",
    "polysyllable_count",
)

READABILITY_FLOAT_COLUMNS: tuple[str, ...] = (
    "flesch_kincaid_grade",
    "automated_readability_index",
    "coleman_liau_index",
    "gunning_fog",
    "dale_chall_readability_score",
    "estimated_reading_time_seconds",
)
