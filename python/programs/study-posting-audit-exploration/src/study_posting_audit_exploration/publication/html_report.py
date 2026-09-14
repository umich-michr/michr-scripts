"""Self-contained faculty-facing HTML report rendering."""

from dataclasses import dataclass
from html import escape
import math
from numbers import Real
from pathlib import Path
from typing import cast

from jinja2 import BaseLoader, Environment, StrictUndefined
import pandas as pd
from plotly.io import to_html

from study_posting_audit_exploration.errors import (
    ExplorationInputError,
    ExplorationValidationError,
)
from study_posting_audit_exploration.publication.charts import (
    ExplorationCharts,
)

_REPORT_TITLE = "Study Posting Audit Exploration"

_KPI_METRICS: tuple[str, ...] = (
    "distinct_study_count_with_any_attempt",
    "distinct_completed_study_count",
    "distinct_completed_study_count_final_mode_ai",
    "distinct_completed_study_count_final_mode_manual",
    "distinct_author_count_with_any_ai_attempt",
    "distinct_author_count_with_any_manual_attempt",
    "distinct_author_count_with_both_ai_and_manual_attempts",
    "distinct_completed_study_count_with_preceding_incomplete_attempts",
)

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #1f2933;
      --muted: #52606d;
      --surface: #ffffff;
      --panel: #f5f7fa;
      --border: #cbd5e1;
      --accent: #1f5a94;
      --focus: #b45309;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--panel);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.5;
    }
    main {
      width: min(1200px, 100%);
      margin: 0 auto;
      padding: 1rem;
    }
    header, section {
      margin-bottom: 1.5rem;
      padding: 1.25rem;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.5rem;
    }
    h1, h2 { line-height: 1.2; }
    h1 { margin-top: 0; }
    .lede, .caution { color: var(--muted); }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 1rem;
    }
    .kpi-card {
      padding: 1rem;
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      background: var(--surface);
    }
    .kpi-label {
      margin: 0;
      color: var(--muted);
      font-size: 0.95rem;
    }
    .kpi-value {
      margin: 0.25rem 0;
      font-size: 1.75rem;
      font-weight: 700;
    }
    .kpi-detail {
      margin: 0;
      color: var(--muted);
      font-size: 0.85rem;
    }
    .chart {
      min-height: 360px;
      margin-top: 1rem;
    }
    .chart + .chart { margin-top: 2rem; }
    a:focus, button:focus, [tabindex]:focus {
      outline: 3px solid var(--focus);
      outline-offset: 2px;
    }
    @media print {
      body { background: #ffffff; }
      header, section {
        break-inside: avoid;
        border-color: #999999;
      }
    }
  </style>
</head>
<body>
<main>
  <header>
    <h1>{{ title }}</h1>
    <p class="lede">
      Aggregate exploratory analysis of normalized study-posting audit data.
    </p>
    <p class="caution">
      These descriptive results do not establish causality and must not be
      interpreted as evaluations of individual authors.
    </p>
  </header>

  <section aria-labelledby="executive-overview-heading">
    <h2 id="executive-overview-heading">Executive overview</h2>
    <div class="kpi-grid">
      {% for card in kpi_cards %}
      <article class="kpi-card">
        <p class="kpi-label">{{ card.label }}</p>
        <p class="kpi-value">{{ card.value }}</p>
        <p class="kpi-detail">{{ card.detail }}</p>
      </article>
      {% endfor %}
    </div>
  </section>

  <section aria-labelledby="study-pathways-heading">
    <h2 id="study-pathways-heading">Study pathways and author handoffs</h2>
    <p class="caution">
      A preceding attempt is an incomplete attempt ordered before the unique
      completed attempt for the same study. Author comparisons are made only
      within a study.
    </p>
    <div class="chart">{{ study_pathways_html | safe }}</div>
    <div class="chart">{{ author_handoffs_html | safe }}</div>
  </section>

  <section aria-labelledby="author-experience-heading">
    <h2 id="author-experience-heading">Author experience and activity</h2>
    <p class="caution">
      These author-grain medians describe values available when the report
      query ran. They are not attempt-time snapshots and must not be
      interpreted as causes of authoring-mode choice or study outcomes.
    </p>
    <div class="chart">{{ author_experience_studies_html | safe }}</div>
    <div class="chart">{{ author_experience_days_html | safe }}</div>
  </section>

  <section aria-labelledby="attempts-heading">
    <h2 id="attempts-heading">Attempts and workflow timing</h2>
    <div class="chart">{{ attempt_outcomes_html | safe }}</div>
    <div class="chart">{{ attempt_timing_html | safe }}</div>
  </section>

  <section aria-labelledby="content-source-heading">
    <h2 id="content-source-heading">Content-source concordance</h2>
    <p class="caution">
      Agreement is descriptive and uses normalized aggregate source labels.
    </p>
    <div class="chart">{{ content_source_html | safe }}</div>
  </section>

  <section aria-labelledby="interpretation-heading">
    <h2 id="interpretation-heading">Interpretation and privacy</h2>
    <p>
      The HTML report is generated only from aggregate analysis tables. It does
      not include usernames, audit identifiers, study numbers, source payloads,
      selected text, or final text.
    </p>
    <p>
      Readability formulas are indicators only. They do not establish
      comprehension, accuracy, cultural appropriateness, layout quality,
      accessibility, usefulness, or ethical adequacy.
    </p>
  </section>
</main>
</body>
</html>
"""


@dataclass(frozen=True, slots=True)
class KpiCard:
    """One executive-overview card."""

    label: str
    value: str
    detail: str


def _finite_number(
    value: object,
    *,
    value_name: str,
) -> float:
    """Return one finite numeric aggregate value."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ExplorationValidationError(
            f"HTML aggregate value {value_name!r} must be numeric"
        )

    converted = float(value)

    if not math.isfinite(converted):
        raise ExplorationValidationError(
            f"HTML aggregate value {value_name!r} must be finite"
        )

    return converted


def _percentage_text(value: object) -> str | None:
    """Return a formatted percentage when present."""
    if value is None or value is pd.NA or value is pd.NaT:
        return None

    if isinstance(value, float) and math.isnan(value):
        return None

    return f"{_finite_number(value, value_name='metric_percentage'):.1f}%"


def _kpi_cards(overview_summary: pd.DataFrame) -> tuple[KpiCard, ...]:
    """Return ordered KPI cards from the aggregate overview table."""
    rows = cast(
        "list[dict[str, object]]",
        overview_summary.to_dict(orient="records"),
    )
    rows_by_name = {str(row["overview_metric_name"]): row for row in rows}
    cards: list[KpiCard] = []

    for metric_name in _KPI_METRICS:
        row = rows_by_name.get(metric_name)

        if row is None:
            continue

        count = int(
            _finite_number(
                row["metric_count"],
                value_name="metric_count",
            )
        )
        denominator = int(
            _finite_number(
                row["metric_denominator_count"],
                value_name="metric_denominator_count",
            )
        )
        percentage = _percentage_text(row["metric_percentage"])
        detail_parts = [f"Denominator: {denominator}"]

        if percentage is not None:
            detail_parts.insert(0, percentage)

        cards.append(
            KpiCard(
                label=escape(str(row["overview_metric_label"])),
                value=f"{count:,}",
                detail="; ".join(detail_parts),
            )
        )

    return tuple(cards)


def _figure_html(
    figure: object,
    *,
    include_plotlyjs: bool,
) -> str:
    """Return one responsive Plotly fragment."""
    return str(
        to_html(
            figure,
            full_html=False,
            include_plotlyjs=include_plotlyjs,
            config={
                "displaylogo": False,
                "responsive": True,
            },
        )
    )


def render_html_report(
    *,
    overview_summary: pd.DataFrame,
    charts: ExplorationCharts,
) -> str:
    """Return one self-contained faculty-facing HTML report."""
    environment = Environment(
        loader=BaseLoader(),
        autoescape=True,
        undefined=StrictUndefined,
    )
    template = environment.from_string(_TEMPLATE)

    return template.render(
        title=_REPORT_TITLE,
        kpi_cards=_kpi_cards(overview_summary),
        study_pathways_html=_figure_html(
            charts.study_completion_pathways,
            include_plotlyjs=True,
        ),
        author_handoffs_html=_figure_html(
            charts.author_handoff_categories,
            include_plotlyjs=False,
        ),
        author_experience_studies_html=_figure_html(
            charts.author_experience_studies,
            include_plotlyjs=False,
        ),
        author_experience_days_html=_figure_html(
            charts.author_experience_days,
            include_plotlyjs=False,
        ),
        attempt_outcomes_html=_figure_html(
            charts.attempt_outcomes_by_mode,
            include_plotlyjs=False,
        ),
        attempt_timing_html=_figure_html(
            charts.median_attempt_time_by_mode,
            include_plotlyjs=False,
        ),
        content_source_html=_figure_html(
            charts.content_source_concordance,
            include_plotlyjs=False,
        ),
    )


def write_html_report(
    path: Path,
    *,
    overview_summary: pd.DataFrame,
    charts: ExplorationCharts,
) -> None:
    """Write one self-contained HTML report."""
    try:
        path.write_text(
            render_html_report(
                overview_summary=overview_summary,
                charts=charts,
            ),
            encoding="utf-8",
        )
    except OSError as error:
        raise ExplorationInputError(
            f"Could not write exploration HTML report: {error}"
        ) from error
