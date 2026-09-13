from pathlib import Path

import study_posting_audit_exploration as package
from study_posting_audit_exploration import (
    AttemptAnalysisTables,
    AttemptHistoryTables,
    AuditExplorationError,
    ExplorationConfigurationError,
    ExplorationInputConfig,
    ExplorationInputError,
    ExplorationPublication,
    ExplorationRunConfig,
    ExplorationValidationError,
    LoadedAuditReport,
    OverviewTables,
    ValidationSummary,
    build_attempt_analysis_tables,
    build_overview_tables,
    derive_attempt_histories,
    load_audit_report,
    publish_exploration,
    validate_audit_report,
)


def test_package_is_not_an_implicit_namespace() -> None:
    assert package.__file__ is not None


def test_package_exposes_version_and_typing_marker() -> None:
    assert package.__version__ == "0.1.0"
    assert "__version__" in package.__all__
    assert package.__file__ is not None

    package_directory = Path(package.__file__).parent

    assert (package_directory / "py.typed").is_file()


def test_public_api_exports_batch_one_contract() -> None:
    assert package.ExplorationInputConfig is ExplorationInputConfig
    assert package.LoadedAuditReport is LoadedAuditReport
    assert package.ValidationSummary is ValidationSummary
    assert package.load_audit_report is load_audit_report
    assert package.validate_audit_report is validate_audit_report


def test_exceptions_share_one_base_class() -> None:
    assert issubclass(ExplorationConfigurationError, AuditExplorationError)
    assert issubclass(ExplorationInputError, AuditExplorationError)
    assert issubclass(ExplorationValidationError, AuditExplorationError)


def test_public_api_exports_batch_three_contract() -> None:
    assert package.ExplorationRunConfig is ExplorationRunConfig
    assert package.AttemptHistoryTables is AttemptHistoryTables
    assert package.ExplorationPublication is ExplorationPublication
    assert package.derive_attempt_histories is derive_attempt_histories
    assert package.publish_exploration is publish_exploration


def test_public_api_exports_batch_four_overview_contract() -> None:
    assert package.OverviewTables is OverviewTables
    assert package.build_overview_tables is build_overview_tables


def test_public_api_exports_attempt_analysis_contract() -> None:
    assert package.AttemptAnalysisTables is AttemptAnalysisTables
    assert package.build_attempt_analysis_tables is (build_attempt_analysis_tables)
