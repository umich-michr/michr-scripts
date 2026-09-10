"""Require documentation updates alongside behavior-affecting source changes.

Run automatically by pre-commit. Changes that can alter analytical results or
published output require their governing documentation in the same commit.
Other changes produce advisory reminders.

Update the requirement mappings when package boundaries or public contracts
change.
"""

import shutil

# This repository-maintenance tool intentionally invokes the local Git
# executable. The executable is resolved to an absolute path with shutil.which,
# arguments are fixed, and no shell is used.
import subprocess  # nosec B404
import sys

TEXT_PACKAGE = "python/packages/text-post-edit-metrics"
STUDY_PACKAGE = "python/packages/study-posting-ai-analysis"
ROW_SOURCE_PACKAGE = "python/packages/tabular-row-sources"

REPORT_PROGRAM = "python/programs/study-posting-audit-report"

TEXT_README = f"{TEXT_PACKAGE}/README.md"
STUDY_README = f"{STUDY_PACKAGE}/README.md"
STUDY_SPECIFICATION = f"{STUDY_PACKAGE}/docs/analysis-specification.md"
STUDY_FLOW = f"{STUDY_PACKAGE}/docs/program-flow.md"
ROW_SOURCE_README = f"{ROW_SOURCE_PACKAGE}/README.md"
ROW_SOURCE_SCHEMA_DOC = f"{ROW_SOURCE_PACKAGE}/docs/schema-format.md"

REPORT_README = f"{REPORT_PROGRAM}/README.md"

type DocumentationRequirement = tuple[str, str]

# Blocking requirements for source that determines reported values, policy, or
# published flattened output.
REQUIRED_DOCUMENTS: dict[str, tuple[DocumentationRequirement, ...]] = {
    f"{TEXT_PACKAGE}/src/text_post_edit_metrics/metrics.py": (
        (
            f"{TEXT_PACKAGE}/docs/methodology.md",
            "the canonical methodology documents formulas and behavior",
        ),
        (
            f"{TEXT_PACKAGE}/docs/verification.md",
            "metric changes require verification documentation review",
        ),
    ),
    f"{TEXT_PACKAGE}/src/text_post_edit_metrics/normalization.py": (
        (
            f"{TEXT_PACKAGE}/docs/methodology.md",
            "the canonical methodology documents metric preprocessing",
        ),
        (
            f"{TEXT_PACKAGE}/docs/verification.md",
            "normalization changes require verification documentation review",
        ),
    ),
    f"{TEXT_PACKAGE}/src/text_post_edit_metrics/models.py": (
        (
            f"{TEXT_PACKAGE}/docs/methodology.md",
            "the canonical methodology documents PostEditingResult fields",
        ),
    ),
    f"{TEXT_PACKAGE}/tests/test_metrics_differential.py": (
        (
            f"{TEXT_PACKAGE}/docs/verification.md",
            "the canonical verification document records cases and seeds",
        ),
    ),
    f"{STUDY_PACKAGE}/src/study_posting_ai_analysis/text_normalization.py": (
        (
            STUDY_SPECIFICATION,
            "cosmetic equivalence is specified in sections 6 and 9",
        ),
    ),
    f"{STUDY_PACKAGE}/src/study_posting_ai_analysis/field_specs.py": (
        (
            STUDY_SPECIFICATION,
            "field requiredness is specified in section 4",
        ),
    ),
    f"{STUDY_PACKAGE}/src/study_posting_ai_analysis/field_analysis.py": (
        (
            STUDY_SPECIFICATION,
            "field outcomes are specified in sections 5, 10, and 11",
        ),
        (
            STUDY_FLOW,
            "the field dispatch and classification flow is diagrammed here",
        ),
    ),
    f"{STUDY_PACKAGE}/src/study_posting_ai_analysis/flattening.py": (
        (
            STUDY_README,
            "flattened output is part of the package's published contract",
        ),
        (
            STUDY_SPECIFICATION,
            "the analysis pipeline and reporting fields are specified here",
        ),
    ),
    f"{ROW_SOURCE_PACKAGE}/src/tabular_row_sources/__init__.py": (
        (
            ROW_SOURCE_README,
            "the package README documents the public source contract",
        ),
    ),
    f"{ROW_SOURCE_PACKAGE}/pyproject.toml": (
        (
            ROW_SOURCE_README,
            "the package README documents dependencies and scope",
        ),
    ),
    f"{ROW_SOURCE_PACKAGE}/docs/schema-format.md": (
        (
            ROW_SOURCE_SCHEMA_DOC,
            "the schema format document specifies the expected structure",
        ),
    ),
    f"{ROW_SOURCE_PACKAGE}/src/tabular_row_sources/models.py": (
        (
            ROW_SOURCE_SCHEMA_DOC,
            "the canonical schema documentation defines types and nullability",
        ),
    ),
    f"{ROW_SOURCE_PACKAGE}/src/tabular_row_sources/schema.py": (
        (
            ROW_SOURCE_SCHEMA_DOC,
            "the canonical schema documentation defines the JSON format",
        ),
    ),
    f"{ROW_SOURCE_PACKAGE}/src/tabular_row_sources/dbapi_source.py": (
        (
            ROW_SOURCE_README,
            "the package README documents the DB-API source contract",
        ),
    ),
    f"{REPORT_PROGRAM}/src/study_posting_audit_report/processing.py": (
        (
            REPORT_README,
            "the program README documents row processing and analysis-selection policy",
        ),
    ),
}

# Advisory pairings: these changes often require documentation, but not every
# internal edit changes the documented contract.
ADVISORY_DOCUMENTS: dict[str, tuple[DocumentationRequirement, ...]] = {
    f"{TEXT_PACKAGE}/src/text_post_edit_metrics/__init__.py": (
        (TEXT_README, "the README documents the package's public API"),
    ),
    f"{TEXT_PACKAGE}/pyproject.toml": (
        (TEXT_README, "the README documents runtime dependencies"),
    ),
    f"{STUDY_PACKAGE}/src/study_posting_ai_analysis/__init__.py": (
        (STUDY_README, "the README documents the package's public API"),
    ),
    f"{STUDY_PACKAGE}/pyproject.toml": (
        (STUDY_README, "the README documents package dependencies"),
    ),
    f"{ROW_SOURCE_PACKAGE}/src/tabular_row_sources/__init__.py": (
        (
            ROW_SOURCE_README,
            "the package README documents the public API",
        ),
    ),
    f"{ROW_SOURCE_PACKAGE}/pyproject.toml": (
        (
            ROW_SOURCE_README,
            "the package README documents dependencies and scope",
        ),
    ),
    f"{ROW_SOURCE_PACKAGE}/src/tabular_row_sources/conversion.py": (
        (
            ROW_SOURCE_SCHEMA_DOC,
            "the canonical schema documentation defines value conversion",
        ),
    ),
    f"{ROW_SOURCE_PACKAGE}/src/tabular_row_sources/sql.py": (
        (
            ROW_SOURCE_README,
            "the package README documents SQL-file loading",
        ),
    ),
    f"{REPORT_PROGRAM}/src/study_posting_audit_report/__init__.py": (
        (
            REPORT_README,
            "the program README documents the public program contract",
        ),
    ),
    f"{REPORT_PROGRAM}/pyproject.toml": (
        (
            REPORT_README,
            "the program README documents dependencies and scope",
        ),
    ),
    "Makefile": (("README.md", "the root README documents development commands"),),
    "pyproject.toml": (
        ("README.md", "the root README documents workspace configuration"),
    ),
}


def staged_files() -> set[str]:
    """Return repository-relative paths staged for commit."""
    git = shutil.which("git")

    if git is None:
        raise RuntimeError("git executable not found on PATH")

    # The executable is an absolute path returned by shutil.which. Every
    # argument is a fixed literal, shell=False is the default, and no staged
    # filename is used as command input.
    completed = subprocess.run(  # noqa: S603  # nosec B603
        [git, "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True,
        check=True,
        text=True,
    )

    return {line.strip() for line in completed.stdout.splitlines() if line.strip()}


def missing_requirements(
    *,
    staged: set[str],
    requirements: dict[str, tuple[DocumentationRequirement, ...]],
) -> list[str]:
    """Return messages for source changes missing paired documentation."""
    messages: list[str] = []

    for source, documents in requirements.items():
        if source not in staged:
            continue

        for document, reason in documents:
            if document not in staged:
                messages.append(
                    f"  {source}\n    requires {document}\n    because {reason}"
                )

    return messages


def main() -> int:
    """Return zero when required documentation pairings are satisfied."""
    staged = staged_files()

    if not staged:
        return 0

    blocking = missing_requirements(
        staged=staged,
        requirements=REQUIRED_DOCUMENTS,
    )
    advisory = missing_requirements(
        staged=staged,
        requirements=ADVISORY_DOCUMENTS,
    )

    if advisory:
        print("\nDocumentation reminders:")
        print("\n\n".join(advisory))

    if not blocking:
        return 0

    print("\nDocumentation synchronization required:\n")
    print("\n\n".join(blocking))
    print(
        "\nThese files govern analytical results or published output."
        "\nUpdate the named documentation in the same commit."
        "\nIf a package boundary changed, update this checker as part of"
        "\nthe same architectural change."
    )

    return 1


if __name__ == "__main__":
    sys.exit(main())
