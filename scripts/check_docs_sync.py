"""Require documentation updates alongside changes that affect reported results.

Run automatically by pre-commit. Blocks a commit when a metric or rule module
changed without its governing specification section. Other pairings produce an
advisory reminder only, so the blocking signal stays credible.

Amend REQUIRED_PAIRS or ADVISORY_PAIRS when the module layout changes.
"""

import subprocess
import sys

# Blocking: these modules determine published numbers. A silent change here
# would invalidate the specification.
REQUIRED_PAIRS: dict[str, tuple[str, str]] = {
    "src/study_posting_ai_analysis/metrics.py": (
        "docs/analysis-specification.md",
        "metric formulas are specified in section 7",
    ),
    "src/study_posting_ai_analysis/text_normalization.py": (
        "docs/analysis-specification.md",
        "preprocessing is specified in section 9",
    ),
    "src/study_posting_ai_analysis/field_specs.py": (
        "docs/analysis-specification.md",
        "requiredness rules are specified in section 4",
    ),
    "src/study_posting_ai_analysis/field_analysis.py": (
        "docs/analysis-specification.md",
        "outcome rules are specified in sections 5, 10, and 11",
    ),
}

# Advisory: usually implies a documentation update, but not always.
ADVISORY_PAIRS: dict[str, tuple[str, str]] = {
    "src/study_posting_ai_analysis/reporting.py": (
        "README.md",
        "output columns are listed under 'What the analysis produces'",
    ),
    "src/study_posting_ai_analysis/cli.py": (
        "README.md",
        "commands and named arguments are documented in the README",
    ),
    "Makefile": (
        "README.md",
        "the commands table lists Make targets",
    ),
    "pyproject.toml": (
        "README.md",
        "the reproducibility table lists pinned versions",
    ),
}


def staged_files() -> set[str]:
    """Return repository-relative paths staged for commit."""
    completed = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    )

    return {line.strip() for line in completed.stdout.splitlines() if line.strip()}


def main() -> int:
    """Return 0 when documentation pairing is satisfied, 1 otherwise."""
    staged = staged_files()

    if not staged:
        return 0

    blocking: list[str] = []
    advisory: list[str] = []

    for source, (document, reason) in REQUIRED_PAIRS.items():
        if source in staged and document not in staged:
            blocking.append(
                f"  {source}\n    requires a change to {document}\n    because {reason}"
            )

    for source, (document, reason) in ADVISORY_PAIRS.items():
        if source in staged and document not in staged:
            advisory.append(f"  {source} -> consider {document} ({reason})")

    if advisory:
        print("\nDocumentation reminders:")
        print("\n".join(advisory))

    if blocking:
        print("\nDocumentation sync required:\n")
        print("\n\n".join(blocking))
        print(
            "\nThese modules govern reported results. Update the specification in"
            "\nthe same commit, or amend the pairing in scripts/check_docs_sync.py"
            "\nif it no longer applies."
            "\n\nTo override deliberately: git commit --no-verify\n"
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
