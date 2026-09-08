"""Require documentation updates alongside changes that affect reported results.

Run automatically by pre-commit. Blocks a commit when a metric or rule module
changed without its governing specification section. Other pairings produce an
advisory reminder only, so the blocking signal stays credible.

Amend REQUIRED_PAIRS or ADVISORY_PAIRS when the module layout changes.
"""

import shutil
import subprocess
import sys

PACKAGE = "packages/study-posting-ai-analysis"

# Blocking: these modules determine published numbers.
REQUIRED_PAIRS: dict[str, tuple[str, str]] = {
    f"{PACKAGE}/src/study_posting_ai_analysis/metrics.py": (
        f"{PACKAGE}/docs/analysis-specification.md",
        "metric formulas are specified in section 7",
    ),
    f"{PACKAGE}/src/study_posting_ai_analysis/text_normalization.py": (
        f"{PACKAGE}/docs/analysis-specification.md",
        "preprocessing is specified in section 9",
    ),
    f"{PACKAGE}/src/study_posting_ai_analysis/field_specs.py": (
        f"{PACKAGE}/docs/analysis-specification.md",
        "requiredness rules are specified in section 4",
    ),
    f"{PACKAGE}/src/study_posting_ai_analysis/field_analysis.py": (
        f"{PACKAGE}/docs/analysis-specification.md",
        "outcome rules are specified in sections 5, 10, and 11",
    ),
}

# Advisory: usually implies a documentation update, but not always.
ADVISORY_PAIRS: dict[str, tuple[str, str]] = {
    f"{PACKAGE}/src/study_posting_ai_analysis/flattening.py": (
        f"{PACKAGE}/README.md",
        "FLATTENED_COLUMNS is described under 'What it reports'",
    ),
    f"{PACKAGE}/src/study_posting_ai_analysis/__init__.py": (
        f"{PACKAGE}/README.md",
        "the public API table lists the exported names",
    ),
    f"{PACKAGE}/pyproject.toml": (
        f"{PACKAGE}/README.md",
        "the reproducibility table lists pinned versions",
    ),
    "Makefile": ("README.md", "the commands table lists Make targets"),
}


def staged_files() -> set[str]:
    """Return repository-relative paths staged for commit."""
    git = shutil.which("git")

    if git is None:
        message = "git executable not found on PATH"
        raise RuntimeError(message)

    completed = subprocess.run(  # noqa: S603
        [git, "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
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
