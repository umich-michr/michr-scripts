"""Tests for the safe repository-level audit workflow helper."""

from collections.abc import Sequence
import importlib.util
from io import StringIO
from pathlib import Path
import subprocess
from types import ModuleType

import pytest


def _load_tool() -> ModuleType:
    """Load the repository tool without making tools a package."""
    repository_root = Path(__file__).resolve().parents[4]
    tool_path = repository_root / "tools/run_study_posting_audit_exploration.py"
    spec = importlib.util.spec_from_file_location(
        "run_study_posting_audit_exploration",
        tool_path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load workflow tool")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


tool = _load_tool()


def _repository(tmp_path: Path) -> Path:
    """Create a minimal synthetic repository root."""
    root = tmp_path / "repository"
    root.mkdir()
    (root / "output").mkdir()
    (root / "Makefile").write_text("help:\n\t@true\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        "[project]\nname='synthetic'\nversion='0.0.0'\n",
        encoding="utf-8",
    )

    return root


@pytest.mark.parametrize(
    "unsafe_value",
    [
        ".",
        "output",
        "/",
    ],
)
def test_rejects_dangerous_report_cleanup_paths(
    tmp_path: Path,
    unsafe_value: str,
) -> None:
    """Never allow broad or repository-root deletion."""
    root = _repository(tmp_path)

    with pytest.raises(ValueError, match=r"unsafe|must be inside"):
        tool.resolve_workflow_config(
            repository_root=root,
            source_mode="database",
            report_output=unsafe_value,
        )


def test_rejects_output_outside_repository_output(tmp_path: Path) -> None:
    """Keep deletion within the repository output directory."""
    root = _repository(tmp_path)

    with pytest.raises(ValueError, match="inside the repository output"):
        tool.resolve_workflow_config(
            repository_root=root,
            source_mode="database",
            report_output=root.parent / "outside",
        )


def test_rejects_overlapping_output_paths(tmp_path: Path) -> None:
    """Require independent normalized and exploration destinations."""
    root = _repository(tmp_path)

    with pytest.raises(ValueError, match="must not overlap"):
        tool.resolve_workflow_config(
            repository_root=root,
            source_mode="database",
            report_output="output/workflow",
            exploration_output="output/workflow/exploration",
        )


def test_rejects_csv_input_inside_generated_output(tmp_path: Path) -> None:
    """Never remove an explicitly supplied source CSV during cleanup."""
    root = _repository(tmp_path)

    with pytest.raises(ValueError, match="CSV input must not be inside"):
        tool.resolve_workflow_config(
            repository_root=root,
            source_mode="csv",
            report_output="output/report",
            exploration_output="output/exploration",
            csv_input="output/report/source.csv",
        )


def test_database_workflow_runs_in_order_and_opens_report(
    tmp_path: Path,
) -> None:
    """Clean only destinations, run all stages, and open the final HTML."""
    root = _repository(tmp_path)
    report_output = root / "output/report"
    exploration_output = root / "output/exploration"
    report_output.mkdir()
    exploration_output.mkdir()
    config = tool.resolve_workflow_config(
        repository_root=root,
        source_mode="database",
        report_output=report_output,
        exploration_output=exploration_output,
    )
    cleaned: list[Path] = []
    commands: list[tuple[str, ...]] = []
    opened: list[Path] = []
    output = StringIO()

    def clean(path: Path) -> None:
        cleaned.append(path)

    def run(command: Sequence[str]) -> None:
        commands.append(tuple(command))

    def open_report(path: Path) -> bool:
        opened.append(path)
        return True

    tool.run_workflow(
        config,
        command_runner=run,
        path_cleaner=clean,
        report_opener=open_report,
        output=output,
    )

    assert cleaned == [
        exploration_output.resolve(),
        report_output.resolve(),
    ]
    assert commands == [
        (
            "uv",
            "run",
            "study-posting-audit-report",
            "database",
            "--output",
            str(report_output.resolve()),
        ),
        (
            "uv",
            "run",
            "study-posting-audit-exploration",
            "analyze",
            "--input-report",
            str(report_output.resolve()),
            "--output",
            str(exploration_output.resolve()),
        ),
        (
            "uv",
            "run",
            "study-posting-audit-exploration",
            "summarize-quality",
            "--exploration",
            str(exploration_output.resolve()),
        ),
    ]
    assert opened == [exploration_output.resolve() / "report.html"]
    assert "Generating normalized report from database source." in output.getvalue()
    assert "Summarizing data quality." in output.getvalue()


def test_csv_workflow_passes_optional_input_and_warning_flag(
    tmp_path: Path,
) -> None:
    """Build CSV and warning-sensitive commands without exposing source data."""
    root = _repository(tmp_path)
    csv_input = root / "input data/audit.csv"
    config = tool.resolve_workflow_config(
        repository_root=root,
        source_mode="csv",
        csv_input=csv_input,
        open_report=False,
        fail_on_warning=True,
    )
    commands: list[tuple[str, ...]] = []

    tool.run_workflow(
        config,
        command_runner=lambda command: commands.append(tuple(command)),
        output=StringIO(),
    )

    assert commands[0][-2:] == (
        "--input",
        str(csv_input.resolve()),
    )
    assert commands[2][-1] == "--fail-on-warning"


def test_csv_mode_may_use_existing_configuration_resolution(
    tmp_path: Path,
) -> None:
    """Omit --input so environment, dotenv, or prompting can resolve it."""
    root = _repository(tmp_path)
    config = tool.resolve_workflow_config(
        repository_root=root,
        source_mode="csv",
        csv_input=None,
        open_report=False,
    )
    commands: list[tuple[str, ...]] = []

    tool.run_workflow(
        config,
        command_runner=lambda command: commands.append(tuple(command)),
        output=StringIO(),
    )

    assert "--input" not in commands[0]


def test_workflow_stops_after_upstream_failure(tmp_path: Path) -> None:
    """Do not analyze, summarize, or open after report generation fails."""
    root = _repository(tmp_path)
    config = tool.resolve_workflow_config(
        repository_root=root,
        source_mode="database",
    )
    commands: list[tuple[str, ...]] = []
    opened: list[Path] = []

    def fail_report(command: Sequence[str]) -> None:
        commands.append(tuple(command))
        raise subprocess.CalledProcessError(2, command)

    def record_open(path: Path) -> bool:
        opened.append(path)
        return True

    with pytest.raises(subprocess.CalledProcessError):
        tool.run_workflow(
            config,
            command_runner=fail_report,
            report_opener=record_open,
            output=StringIO(),
        )

    assert len(commands) == 1
    assert opened == []


def test_opener_failure_does_not_fail_successful_workflow(
    tmp_path: Path,
) -> None:
    """Preserve success when no browser accepts the report."""
    root = _repository(tmp_path)
    config = tool.resolve_workflow_config(
        repository_root=root,
        source_mode="database",
    )
    output = StringIO()

    tool.run_workflow(
        config,
        command_runner=lambda _command: None,
        report_opener=lambda _path: False,
        output=output,
    )

    assert "no browser accepted" in output.getvalue()


def test_no_open_report_skips_browser(tmp_path: Path) -> None:
    """Support headless and continuous-integration workflows."""
    root = _repository(tmp_path)
    config = tool.resolve_workflow_config(
        repository_root=root,
        source_mode="database",
        open_report=False,
    )
    opened: list[Path] = []

    def record_open(path: Path) -> bool:
        opened.append(path)
        return True

    tool.run_workflow(
        config,
        command_runner=lambda _command: None,
        report_opener=record_open,
        output=StringIO(),
    )

    assert opened == []


def test_root_makefile_exposes_thin_workflow_targets() -> None:
    """Keep Make targets as a thin interface over the tested helper."""
    repository_root = Path(__file__).resolve().parents[4]
    makefile = (repository_root / "Makefile").read_text(encoding="utf-8")

    assert "audit-explore-database:" in makefile
    assert "audit-explore-csv:" in makefile
    assert "tools/run_study_posting_audit_exploration.py" in makefile
    assert "\t  database" in makefile
    assert "\t  csv" in makefile
    assert "AUDIT_REPORT_OUTPUT ?=" in makefile
    assert "AUDIT_EXPLORATION_OUTPUT ?=" in makefile
    assert "OPEN_REPORT ?= 1" in makefile
    assert "FAIL_ON_QUALITY_WARNING ?= 0" in makefile

    database_recipe = makefile.split(
        "audit-explore-database:",
        maxsplit=1,
    )[1].split(
        "audit-explore-csv:",
        maxsplit=1,
    )[0]
    csv_recipe = makefile.split(
        "audit-explore-csv:",
        maxsplit=1,
    )[1].split(
        "# ---------------------------------------------------------------------------",
        maxsplit=1,
    )[0]

    assert "rm -rf" not in database_recipe
    assert "rm -rf" not in csv_recipe
    assert "clean-output" not in database_recipe
    assert "clean-output" not in csv_recipe
