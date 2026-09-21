import pandas as pd

from study_posting_audit_exploration import (
    AGGREGATE_FILE_ORDER,
    AGGREGATE_OUTPUT_COLUMNS,
    METRIC_DEFINITION_COLUMNS,
    MetricDefinition,
    build_metric_definitions,
)


def test_metric_definition_model_is_immutable() -> None:
    definition = MetricDefinition(
        metric_name="attempt_count",
        plain_language_label="Attempt count",
        analytical_unit="attempt",
        calculation_definition="Count of attempts.",
        numerator_definition="Not applicable.",
        denominator_definition="Not applicable.",
        measurement_unit="count",
        value_selection_rule="Use the aggregate row.",
        missing_value_treatment="No missing value.",
        source_file_names="attempts/grouped_attempt_summary.csv",
        source_column_names="attempt_count",
        interpretation_notes="",
    )

    assert definition.metric_name == "attempt_count"
    assert definition.measurement_unit == "count"


def test_metric_definitions_cover_every_aggregate_column_in_order() -> None:
    definitions = build_metric_definitions(AGGREGATE_OUTPUT_COLUMNS)
    expected_pairs = [
        (
            file_name,
            column_name,
        )
        for file_name in AGGREGATE_FILE_ORDER
        for column_name in AGGREGATE_OUTPUT_COLUMNS[file_name]
    ]
    actual_pairs = list(
        definitions[
            [
                "source_file_names",
                "source_column_names",
            ]
        ].itertuples(
            index=False,
            name=None,
        )
    )

    assert tuple(definitions.columns) == METRIC_DEFINITION_COLUMNS
    assert actual_pairs == expected_pairs
    assert len(definitions) == sum(
        len(columns) for columns in AGGREGATE_OUTPUT_COLUMNS.values()
    )


def test_metric_definitions_are_nonblank_and_identifier_free() -> None:
    definitions = build_metric_definitions(AGGREGATE_OUTPUT_COLUMNS)

    assert not definitions.empty
    assert not definitions.isna().any().any()

    for column_name in METRIC_DEFINITION_COLUMNS:
        values = definitions[column_name].astype("string")
        assert values.str.strip().ne("").all() or (
            column_name == "interpretation_notes"
        )

    published_text = definitions.to_csv(
        index=False,
        lineterminator="\n",
    )

    for forbidden_value in (
        "audit_record_id",
        "study_num",
        "author_user_name",
        "selected_text",
        "final_source_text",
    ):
        assert forbidden_value not in published_text


def test_metric_definitions_describe_special_policies() -> None:
    definitions = build_metric_definitions(AGGREGATE_OUTPUT_COLUMNS)

    percentage_rows = definitions.loc[
        definitions["metric_name"].str.contains("percentage")
    ]
    readability_rows = definitions.loc[
        definitions["metric_name"].str.contains("readability|grade")
    ]
    edit_rows = definitions.loc[
        definitions["metric_name"].str.contains("edit_intensity|edit_ratio")
    ]
    missing_final = definitions.loc[
        definitions["metric_name"].eq("final_text_attempt_count_missing_or_blank")
    ]
    source_signature_rows = definitions.loc[
        definitions["metric_name"].str.contains("source_signature")
    ]
    latency_rows = definitions.loc[definitions["metric_name"].str.contains("latency")]

    assert percentage_rows["denominator_definition"].ne("Not applicable.").all()
    assert percentage_rows["interpretation_notes"].str.contains("descriptive").all()
    assert (
        readability_rows["interpretation_notes"].str.contains("indicators only").all()
    )
    assert edit_rows["interpretation_notes"].str.contains("exploratory").all()
    assert (
        missing_final["missing_value_treatment"]
        .str.contains("always published as missing")
        .all()
    )
    assert source_signature_rows["interpretation_notes"].str.contains("proxy").all()
    assert latency_rows["interpretation_notes"].str.contains("descriptive").all()


def test_metric_definitions_accept_stable_schema_mapping() -> None:
    definitions = build_metric_definitions(
        {
            file_name: tuple(columns)
            for file_name, columns in AGGREGATE_OUTPUT_COLUMNS.items()
        }
    )

    assert isinstance(definitions, pd.DataFrame)
