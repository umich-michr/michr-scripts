"""Safely regenerate normalized and exploration study-posting reports."""

import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess  # nosec B404
import sys
from typing import TextIO
import webbrowser

_DEFAULT_REPORT_OUTPUT = Path("output/study-posting-ai-audit-analysis/report")
_DEFAULT_EXPLORATION_OUTPUT = Path("output/study-posting-ai-audit-analysis/exploration")

CommandRunner = Callable[[Sequence[str]], None]
PathCleaner = Callable[[Path], None]
ReportOpener = Callable[[Path], bool]


@dataclass(frozen=True, slots=True)
class WorkflowConfig:
    """Resolved settings for one end-to-end audit workflow."""

    repository_root: Path
    source_mode: str
    report_output: Path
    exploration_output: Path
    csv_input: Path | None
    open_report: bool
    fail_on_warning: bool


def repository_root_from_script(script_path: Path) -> Path:
    """Return the repository root containing one tools script."""
    resolved = script_path.resolve()
    root = resolved.parent.parent

    if not (root / "pyproject.toml").is_file() or not (root / "Makefile").is_file():
        raise ValueError(
            "Could not identify the repository root from the workflow script"
        )

    return root


def _resolved_path(
    root: Path,
    value: str | Path,
) -> Path:
    """Resolve one path relative to the repository root."""
    path = Path(value)

    if not path.is_absolute():
        path = root / path

    return path.resolve()


def _is_relative_to(path: Path, parent: Path) -> bool:
    """Return whether path is inside parent."""
    try:
        path.relative_to(parent)
    except ValueError:
        return False

    return True


def _require_safe_output_path(
    path: Path,
    *,
    repository_root: Path,
    label: str,
) -> None:
    """Require one narrowly scoped generated-output destination."""
    approved_root = (repository_root / "output").resolve()
    forbidden = {
        Path("/").resolve(),
        repository_root.resolve(),
        approved_root,
        Path.home().resolve(),
    }

    if path in forbidden:
        raise ValueError(f"{label} is an unsafe cleanup destination: {path}")

    if not _is_relative_to(path, approved_root):
        raise ValueError(
            f"{label} must be inside the repository output directory: {path}"
        )


def _require_nonoverlapping_outputs(
    report_output: Path,
    exploration_output: Path,
) -> None:
    """Require independent report and exploration destinations."""
    if (
        report_output == exploration_output
        or _is_relative_to(report_output, exploration_output)
        or _is_relative_to(exploration_output, report_output)
    ):
        raise ValueError("Report and exploration output directories must not overlap")


def _require_csv_input_separate_from_outputs(
    csv_input: Path | None,
    *,
    report_output: Path,
    exploration_output: Path,
) -> None:
    """Prevent generated-output cleanup from removing an explicit CSV input."""
    if csv_input is None:
        return

    if (
        csv_input in (report_output, exploration_output)
        or _is_relative_to(csv_input, report_output)
        or _is_relative_to(csv_input, exploration_output)
    ):
        raise ValueError("CSV input must not be inside a generated-output directory")


def resolve_workflow_config(
    *,
    repository_root: Path,
    source_mode: str,
    report_output: str | Path = _DEFAULT_REPORT_OUTPUT,
    exploration_output: str | Path = _DEFAULT_EXPLORATION_OUTPUT,
    csv_input: str | Path | None = None,
    open_report: bool = True,
    fail_on_warning: bool = False,
) -> WorkflowConfig:
    """Resolve and validate one workflow configuration."""
    root = repository_root.resolve()

    if source_mode not in {"csv", "database"}:
        raise ValueError(f"Unsupported source mode: {source_mode}")

    resolved_report = _resolved_path(root, report_output)
    resolved_exploration = _resolved_path(root, exploration_output)
    resolved_csv = None if csv_input is None else _resolved_path(root, csv_input)

    if source_mode == "database" and resolved_csv is not None:
        raise ValueError("CSV input is supported only for CSV source mode")

    _require_safe_output_path(
        resolved_report,
        repository_root=root,
        label="Report output",
    )
    _require_safe_output_path(
        resolved_exploration,
        repository_root=root,
        label="Exploration output",
    )
    _require_nonoverlapping_outputs(
        resolved_report,
        resolved_exploration,
    )
    _require_csv_input_separate_from_outputs(
        resolved_csv,
        report_output=resolved_report,
        exploration_output=resolved_exploration,
    )

    return WorkflowConfig(
        repository_root=root,
        source_mode=source_mode,
        report_output=resolved_report,
        exploration_output=resolved_exploration,
        csv_input=resolved_csv,
        open_report=open_report,
        fail_on_warning=fail_on_warning,
    )


def _report_command(config: WorkflowConfig) -> tuple[str, ...]:
    """Return the normalized-report command without secret arguments."""
    command = [
        "uv",
        "run",
        "study-posting-audit-report",
        config.source_mode,
        "--output",
        str(config.report_output),
    ]

    if config.source_mode == "csv" and config.csv_input is not None:
        command.extend(
            [
                "--input",
                str(config.csv_input),
            ]
        )

    return tuple(command)


def _exploration_command(config: WorkflowConfig) -> tuple[str, ...]:
    """Return the exploration publication command."""
    return (
        "uv",
        "run",
        "study-posting-audit-exploration",
        "analyze",
        "--input-report",
        str(config.report_output),
        "--output",
        str(config.exploration_output),
    )


def _quality_command(config: WorkflowConfig) -> tuple[str, ...]:
    """Return the deterministic quality-summary command."""
    command = [
        "uv",
        "run",
        "study-posting-audit-exploration",
        "summarize-quality",
        "--exploration",
        str(config.exploration_output),
    ]

    if config.fail_on_warning:
        command.append("--fail-on-warning")

    return tuple(command)


def _run_command(command: Sequence[str]) -> None:
    """Run one subprocess and stop on nonzero status."""
    subprocess.run(  # noqa: S603  # nosec B603
        tuple(command),
        cwd=None,
        check=True,
    )


def _clean_path(path: Path) -> None:
    """Remove one validated generated destination when present."""
    if not path.exists():
        return

    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _open_report(path: Path) -> bool:
    """Open one local HTML report with the platform browser."""
    return bool(webbrowser.open(path.resolve().as_uri()))


def run_workflow(
    config: WorkflowConfig,
    *,
    command_runner: CommandRunner = _run_command,
    path_cleaner: PathCleaner = _clean_path,
    report_opener: ReportOpener = _open_report,
    output: TextIO = sys.stdout,
) -> None:
    """Regenerate normalized and exploration outputs in a safe sequence."""
    for label, path in (
        ("exploration output", config.exploration_output),
        ("normalized report output", config.report_output),
    ):
        if path.exists():
            print(f"Removing previous {label}: {path}", file=output)
            path_cleaner(path)

    print(
        f"Generating normalized report from {config.source_mode} source.",
        file=output,
    )
    command_runner(_report_command(config))

    print("Generating exploration output.", file=output)
    command_runner(_exploration_command(config))

    print("Summarizing data quality.", file=output)
    command_runner(_quality_command(config))

    report_path = config.exploration_output / "report.html"
    print(f"HTML report: {report_path}", file=output)

    if config.open_report:
        try:
            opened = report_opener(report_path)
        except (OSError, webbrowser.Error) as error:
            print(
                f"Warning: could not open HTML report: {error}",
                file=output,
            )
        else:
            if not opened:
                print(
                    "Warning: no browser accepted the HTML report.",
                    file=output,
                )


def build_parser() -> argparse.ArgumentParser:
    """Build the end-to-end workflow argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Safely regenerate a normalized study-posting audit report and "
            "its exploration."
        )
    )
    parser.add_argument(
        "source_mode",
        choices=("csv", "database"),
        help="Normalized-report source mode.",
    )
    parser.add_argument(
        "--report-output",
        default=str(_DEFAULT_REPORT_OUTPUT),
        metavar="PATH",
        help="Generated normalized-report directory.",
    )
    parser.add_argument(
        "--exploration-output",
        default=str(_DEFAULT_EXPLORATION_OUTPUT),
        metavar="PATH",
        help="Generated exploration directory.",
    )
    parser.add_argument(
        "--csv-input",
        metavar="PATH",
        help="Optional explicit CSV input path for CSV mode.",
    )
    parser.add_argument(
        "--open-report",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Open the generated HTML report when possible.",
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Propagate quality-summary warning status.",
    )

    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    output: TextIO | None = None,
) -> int:
    """Run the end-to-end workflow and return a process exit status."""
    parser = build_parser()
    namespace = parser.parse_args(argv)
    resolved_output = sys.stdout if output is None else output

    try:
        root = repository_root_from_script(Path(__file__))
        config = resolve_workflow_config(
            repository_root=root,
            source_mode=namespace.source_mode,
            report_output=namespace.report_output,
            exploration_output=namespace.exploration_output,
            csv_input=namespace.csv_input,
            open_report=namespace.open_report,
            fail_on_warning=namespace.fail_on_warning,
        )
        run_workflow(
            config,
            output=resolved_output,
        )
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: end-to-end audit workflow failed: {error}", file=sys.stderr)

        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
