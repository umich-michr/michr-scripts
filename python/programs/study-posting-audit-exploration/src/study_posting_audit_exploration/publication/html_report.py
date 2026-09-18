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
    .quality-summary {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 1rem;
      margin: 1rem 0;
    }
    .quality-card {
      padding: 1rem;
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      background: var(--panel);
    }
    .quality-card p { margin: 0.25rem 0; }
    .quality-value {
      font-size: 1.5rem;
      font-weight: 700;
    }
    .quality-warning-list {
      padding-left: 1.25rem;
    }
    .quality-warning-list li {
      margin-bottom: 1rem;
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

  <section aria-labelledby="data-quality-heading">
    <h2 id="data-quality-heading">Data quality</h2>
    <p>
      This successful publication passed every fatal validation check.
      Fatal conditions stop publication, so affected fatal counts are zero
      in a generated report.
    </p>
    <div class="quality-summary">
      <article class="quality-card">
        <p>Fatal validation checks passed</p>
        <p class="quality-value">
          {{ quality_fatal_passed }} of {{ quality_fatal_total }}
        </p>
      </article>
      <article class="quality-card">
        <p>Warning categories detected</p>
        <p class="quality-value">
          {{ quality_affected_warning_count }} of {{ quality_warning_total }}
        </p>
      </article>
      <article class="quality-card">
        <p>Warning occurrences</p>
        <p class="quality-value">{{ quality_warning_occurrences }}</p>
      </article>
    </div>

    {% if quality_warning_rows %}
    <h3>Warnings requiring review</h3>
    <ul class="quality-warning-list">
      {% for warning in quality_warning_rows %}
      <li>
        <strong>{{ warning.label }}</strong><br>
        Affected attempts: {{ warning.affected_attempt_count }} of
        {{ warning.eligible_attempt_count }}
        ({{ warning.percentage_text }}). Affected studies:
        {{ warning.affected_study_count }}. Affected authors:
        {{ warning.affected_author_count }}.<br>
        Consequence: {{ warning.consequence }}
      </li>
      {% endfor %}
    </ul>
    {% else %}
    <p>No warning checks affected attempts in this run.</p>
    {% endif %}

    <h3>Warning categories not detected</h3>
    <ul>
      {% for message in quality_zero_warning_messages %}
      <li>{{ message }}</li>
      {% endfor %}
    </ul>

    <p class="caution">
      Warning occurrences are summed across warning checks and are not a
      distinct-attempt count. One attempt can contribute to more than one
      warning. Warnings identify conditions to review; they do not establish
      a cause, an individual error, or that every analysis result is invalid.
      See <code>quality/data_quality_summary.csv</code> for the complete
      checklist, definitions, denominators, and consequences.
    </p>
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
  <p>
    These charts describe attempt authors, not experience measures for
    named study principal investigators unless that principal investigator
    was also the attempt author.
  </p>

  <h3>Experience at the start of an attempt</h3>
  <p>
    The first chart uses an author-attempt grain. Each attempt contributes
    one observation: the number of other studies its author had created
    before that attempt's start time. One author can therefore contribute
    multiple observations, including observations to both AI and manual
    bars.
  </p>
  <p class="caution">
    Hover over a bar to see its attempt authoring mode, median prior-study
    count, number of author-attempt observations with a value, unit, and
    metric definition.
  </p>
  <div class="chart">
    {{ author_attempt_start_experience_html | safe }}
  </div>

  <h3>Experience and activity when the report query ran</h3>
  <p>
    The next two charts use a unique-author grain. Each distinct attempt
    author contributes at most once to each metric and adoption group.
    Values include total studies created, other-study memberships,
    distinct calendar login days, and elapsed days between the earliest and
    latest available login timestamps when the report query ran. These are
    not historical snapshots of individual attempts.
  </p>
  <p class="caution">
    Counts may differ because the attempt-start chart counts author-attempt
    observations, while query-time charts count distinct authors once per
    metric; missing values can further reduce either count. Hover over a
    bar to see the adoption group, median, distinct authors with a value,
    unit, and metric definition.
  </p>
  <div class="chart">{{ author_experience_studies_html | safe }}</div>
  <div class="chart">{{ author_experience_days_html | safe }}</div>

  <p class="caution">
    These descriptive medians must not be interpreted as causes of
    authoring-mode choice or study outcomes.
  </p>
</section>

  <section aria-labelledby="completed-study-author-context-heading">
    <h2 id="completed-study-author-context-heading">
      Completed studies by authoring mode and completion-author context
    </h2>
    <p>
      Each completed study contributes exactly once through its unique
      completed attempt. AI or manual mode is the final authoring mode on that
      attempt. The role and principal-investigator status shown here are also
      taken from that completed attempt and are specific to that study.
    </p>
    <p class="caution">
      Chart values measure completed studies, not distinct people. The same
      person can complete several studies and can have different roles or be a
      principal investigator for one study and a non-principal investigator for
      another. Distinct completion authors appear only as aggregate hover
      context; no identities are displayed.
    </p>
    <div class="chart">
      {{ completed_studies_by_completion_author_role_html | safe }}
    </div>
    <div class="chart">
      {{ completed_studies_by_completion_author_pi_status_html | safe }}
    </div>
  </section>

  <section aria-labelledby="author-context-heading">
    <h2 id="author-context-heading">
      Author and principal-investigator appointment context
    </h2>
    <p>
      Appointment values are parsed from comma-separated
      <code>Title:Department:School</code> entries. The charts summarize
      schools, departments, and titles separately.
    </p>
    <p class="caution">
      Appointment groups may overlap because an author or principal
      investigator can have more than one appointment; these charts are not
      intended to sum to 100 percent. Each chart counts distinct attempt
      authors represented in the displayed appointment group.
    </p>
    <div class="chart">{{ author_appointment_schools_html | safe }}</div>
    <div class="chart">{{ pi_appointment_schools_html | safe }}</div>
    <div class="chart">{{ author_appointment_departments_html | safe }}</div>
    <div class="chart">{{ pi_appointment_departments_html | safe }}</div>
    <div class="chart">{{ author_appointment_titles_html | safe }}</div>
    <div class="chart">{{ pi_appointment_titles_html | safe }}</div>
  </section>

  <section aria-labelledby="study-mix-heading">
    <h2 id="study-mix-heading">Participant and department mix</h2>
    <p class="caution">
      These charts describe mutually exclusive categories among completed
      studies. Other and missing categories are retained rather than silently
      removed.
    </p>
    <div class="chart">{{ participant_mix_html | safe }}</div>
    <div class="chart">{{ department_mix_html | safe }}</div>
  </section>

  <section aria-labelledby="field-adoption-heading">
  <h2 id="field-adoption-heading">AI field adoption and editing</h2>
  <p>
    These charts summarize completed AI attempts at the field level. An
    offer means at least one suggestion was available for the field; a
    selection means the author selected one offered suggestion.
  </p>
  <p class="caution">
    Field populations and denominators can differ. Selection percentages use
    attempts with an offer as the denominator. Editing outcomes use selected
    attempts for that field. Edited-unclassified is kept separate from
    replaced because no usable character ratio was available. These
    descriptive outcomes do not establish writing quality, correctness,
    usefulness, accessibility, or causal benefit.
  </p>
  <div class="chart">{{ field_suggestion_adoption_html | safe }}</div>
  <div class="chart">{{ field_selected_outcomes_html | safe }}</div>
</section>

<section aria-labelledby="suggestion-choice-heading">
  <h2 id="suggestion-choice-heading">Suggestion choice</h2>
  <p>
    These charts summarize completed AI attempts without displaying
    suggestion text. Attempt-level selection is the percentage of eligible
    attempts with at least one selected suggestion. Suggestion-level
    selection is the percentage of all offered suggestion instances that
    were selected.
  </p>
  <p class="caution">
    Suggestion index is zero-based, so index 0 is the first offered
    suggestion. Fields and suggestion kinds can have different numbers of
    offers and eligible attempts. Selection does not establish that a
    suggestion was better, correct, accessible, useful, or causally
    beneficial.
  </p>
  <div class="chart">{{ suggestion_selection_by_kind_html | safe }}</div>
  <div class="chart">{{ suggestion_selection_by_index_html | safe }}</div>
</section>

<section aria-labelledby="readability-heading">
  <h2 id="readability-heading">Readability indicators</h2>
  <p>
    These charts use Flesch-Kincaid grade as one descriptive indicator.
    Selected-to-final change is calculated as final minus selected.
    Negative values indicate a lower final formula value; positive values
    indicate a higher final formula value.
  </p>
  <p class="caution">
    Lower or higher formula values are not automatically better or worse.
    Titles are short text and have limited readability reliability.
    Grade-level formulas do not establish comprehension, accuracy,
    cultural appropriateness, layout quality, accessibility, usefulness,
    or ethical adequacy. Sample counts and tolerances appear in hover text.
  </p>
  <div class="chart">{{ readability_change_direction_html | safe }}</div>
  <div class="chart">{{ final_grade_bands_html | safe }}</div>
  <h3>Selected versus unselected suggestions</h3>
  <p>
    This comparison uses completed AI attempts only. A field appears only when
    at least one attempt has exactly one selected suggestion, at least one
    unselected suggestion, and usable readability values for both. For each
    eligible attempt, the selected suggestion is compared with the mean of its
    unselected suggestions.
  </p>
  <p class="caution">
    An omitted field means no observations met all comparison requirements. It
    does not mean the field was absent from the audit, lacked final text, lacked
    AI suggestions, or was excluded from other readability analyses. Always
    check the comparable-attempt count in hover text; different fields can have
    different eligible sample sizes.
  </p>
  <div class="chart">
    {{ selected_vs_unselected_readability_html | safe }}
  </div>
  <h3>Edit intensity and readability direction</h3>
  <p>
    This chart explores whether the size of a selected-suggestion edit is
    associated with the direction of grade-level formula changes. It is
    descriptive and does not establish whether an edit improved the text.
  </p>

  <h4>How edit size is classified</h4>
  <p>
    The character edit ratio is the character edit distance divided by the
    longer character count of the selected suggestion or final text. Character
    edit distance counts the minimum insertions, deletions, and substitutions
    needed to transform the selected suggestion into the final text.
  </p>
  <ul>
    <li><strong>Exact:</strong> final text exactly matched the selected
      suggestion.</li>
    <li><strong>Cosmetic:</strong> only cosmetic normalization changed.</li>
    <li><strong>Light edit:</strong> character edit ratio at or below 10%.</li>
    <li><strong>Moderate edit:</strong> ratio above 10% and at or below
      30%.</li>
    <li><strong>Heavy edit:</strong> ratio above 30%.</li>
    <li><strong>Edited, unclassified:</strong> edited, but usable character
      measurements were unavailable.</li>
    <li><strong>Replaced:</strong> final text replaced the selected
      suggestion.</li>
    <li><strong>Cleared:</strong> selected suggestion was removed and final
      text was blank.</li>
    <li><strong>Unassisted:</strong> no AI suggestion was selected.</li>
  </ul>
  <p class="caution">
    These are project-specific exploratory character-edit bands using 10% and
    30% thresholds. The technical scheme ID is
    <code>EXPLORATORY_CHARACTER_RATIO_10_30</code>. The bands describe edit
    size, not writing quality.
  </p>

  <h4>How readability direction is classified</h4>
  <p>
    Consensus uses Flesch-Kincaid grade, Automated Readability Index,
    Coleman-Liau Index, and Gunning Fog.
  </p>
  <ul>
    <li><strong>Consensus decrease:</strong> the grade-level formulas agreed on
      a downward direction for material change.</li>
    <li><strong>No material change:</strong> formula changes stayed within the
      configured tolerance.</li>
    <li><strong>Consensus increase:</strong> the grade-level formulas agreed on
      an upward direction for material change.</li>
    <li><strong>Mixed formula direction:</strong> the formulas did not agree on
      direction. Mixed direction is not the same as no material change.</li>
  </ul>

  <h4>How to read a bar</h4>
  <p>
    Each bar represents one study-posting field and one edit category. The
    label includes the total group size as <strong>N</strong>. Colored sections
    show the share assigned to each readability result. Only fields with usable
    selected-and-final readability pairs receive a direction. If the colored
    sections total less than 100%, the unfilled remainder represents fields
    without a usable pair. Always inspect the counts in hover text: a 100%
    section based on one field is less stable than one based on many fields.
  </p>
  <p>
    <strong>Worked example:</strong> if a group contains five light-edited
    descriptions and one is classified as consensus decrease, that section is
    20% (1 of 5). A median Flesch-Kincaid change of -0.59 means the middle
    final-minus-selected indicator in that result group was 0.59 grade levels
    lower. It does not show that the final text was better or easier to
    understand.
  </p>
  <p class="caution">
    Lower is not automatically better, and higher is not automatically worse.
    Grade-level formulas do not establish comprehension, accuracy,
    accessibility, usefulness, cultural appropriateness, writing quality, or
    causal benefit.
  </p>
  <div class="chart">
    {{ edit_readability_relationship_html | safe }}
  </div>
</section>

  <section aria-labelledby="attempts-heading">
    <h2 id="attempts-heading">Attempts and workflow timing</h2>
    <p>
      Attempt-level timing separates time on the study-information page from
      total elapsed attempt time. Bars show medians and the error bars show the
      25th through 75th percentiles.
    </p>
    <p class="caution">
      Missing timing values are excluded from timing distributions and are
      reported in hover text where available. These descriptive attempt
      timings do not establish author effort, efficiency, quality, or a causal
      effect of authoring mode.
    </p>
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
class QualityWarningView:
    """One aggregate warning shown in the faculty-facing report."""

    label: str
    affected_attempt_count: int
    affected_study_count: int
    affected_author_count: int
    eligible_attempt_count: int
    percentage_text: str
    consequence: str


@dataclass(frozen=True, slots=True)
class QualityHtmlContext:
    """Aggregate quality values rendered into the HTML report."""

    fatal_passed: int
    fatal_total: int
    affected_warning_count: int
    warning_total: int
    warning_occurrences: int
    warning_rows: tuple[QualityWarningView, ...]
    zero_warning_messages: tuple[str, ...]


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


_QUALITY_REQUIRED_COLUMNS: tuple[str, ...] = (
    "data_quality_check_name",
    "severity_level",
    "affected_attempt_count",
    "affected_distinct_study_count",
    "affected_distinct_author_count",
    "eligible_attempt_count",
    "affected_attempt_percentage",
    "analysis_consequence",
)

_ZERO_WARNING_MESSAGES: dict[str, str] = {
    "ATTEMPT_AFTER_COMPLETION": "No attempts occurred after completion.",
    "CREATED_BY_ID_VARIES_WITHIN_STUDY": (
        "No studies had varying CREATED_BY_ID values."
    ),
    "MALFORMED_APPOINTMENT": ("No malformed appointment entries affected attempts."),
}


def _quality_html_context(
    data_quality_summary: pd.DataFrame,
) -> QualityHtmlContext:
    """Return validated aggregate quality values for HTML rendering."""
    missing = tuple(
        column
        for column in _QUALITY_REQUIRED_COLUMNS
        if column not in data_quality_summary.columns
    )

    if missing:
        raise ExplorationValidationError(
            f"data_quality_summary lacks required HTML columns: {missing!r}"
        )

    rows = cast(
        "list[dict[str, object]]",
        data_quality_summary.to_dict(orient="records"),
    )
    fatal_rows = [row for row in rows if row["severity_level"] == "FATAL"]
    warning_rows = [row for row in rows if row["severity_level"] == "WARNING"]

    if len(fatal_rows) + len(warning_rows) != len(rows):
        raise ExplorationValidationError(
            "data_quality_summary contains unsupported severity values"
        )

    fatal_passed = sum(
        int(
            _finite_number(
                row["affected_attempt_count"],
                value_name="affected_attempt_count",
            )
        )
        == 0
        for row in fatal_rows
    )
    warning_views: list[QualityWarningView] = []
    zero_messages: list[str] = []

    for row in warning_rows:
        name = str(row["data_quality_check_name"])
        affected_count = int(
            _finite_number(
                row["affected_attempt_count"],
                value_name="affected_attempt_count",
            )
        )

        if affected_count == 0:
            zero_messages.append(
                _ZERO_WARNING_MESSAGES.get(
                    name,
                    f"{name}: no affected attempts.",
                )
            )
            continue

        percentage = _percentage_text(row["affected_attempt_percentage"])

        if percentage is None:
            percentage = "percentage unavailable"

        warning_views.append(
            QualityWarningView(
                label=name.replace("_", " ").title(),
                affected_attempt_count=affected_count,
                affected_study_count=int(
                    _finite_number(
                        row["affected_distinct_study_count"],
                        value_name="affected_distinct_study_count",
                    )
                ),
                affected_author_count=int(
                    _finite_number(
                        row["affected_distinct_author_count"],
                        value_name="affected_distinct_author_count",
                    )
                ),
                eligible_attempt_count=int(
                    _finite_number(
                        row["eligible_attempt_count"],
                        value_name="eligible_attempt_count",
                    )
                ),
                percentage_text=percentage,
                consequence=escape(str(row["analysis_consequence"])),
            )
        )

    warning_occurrences = sum(
        int(
            _finite_number(
                row["affected_attempt_count"],
                value_name="affected_attempt_count",
            )
        )
        for row in warning_rows
    )

    return QualityHtmlContext(
        fatal_passed=fatal_passed,
        fatal_total=len(fatal_rows),
        affected_warning_count=len(warning_views),
        warning_total=len(warning_rows),
        warning_occurrences=warning_occurrences,
        warning_rows=tuple(warning_views),
        zero_warning_messages=tuple(zero_messages),
    )


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
    data_quality_summary: pd.DataFrame,
    charts: ExplorationCharts,
) -> str:
    """Return one self-contained faculty-facing HTML report."""
    environment = Environment(
        loader=BaseLoader(),
        autoescape=True,
        undefined=StrictUndefined,
    )
    template = environment.from_string(_TEMPLATE)
    quality = _quality_html_context(data_quality_summary)

    return template.render(
        title=_REPORT_TITLE,
        kpi_cards=_kpi_cards(overview_summary),
        quality_fatal_passed=quality.fatal_passed,
        quality_fatal_total=quality.fatal_total,
        quality_affected_warning_count=quality.affected_warning_count,
        quality_warning_total=quality.warning_total,
        quality_warning_occurrences=quality.warning_occurrences,
        quality_warning_rows=quality.warning_rows,
        quality_zero_warning_messages=quality.zero_warning_messages,
        study_pathways_html=_figure_html(
            charts.study_completion_pathways,
            include_plotlyjs=True,
        ),
        author_handoffs_html=_figure_html(
            charts.author_handoff_categories,
            include_plotlyjs=False,
        ),
        author_attempt_start_experience_html=_figure_html(
            charts.author_attempt_start_experience,
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
        field_suggestion_adoption_html=_figure_html(
            charts.field_suggestion_adoption,
            include_plotlyjs=False,
        ),
        field_selected_outcomes_html=_figure_html(
            charts.field_selected_outcomes,
            include_plotlyjs=False,
        ),
        suggestion_selection_by_kind_html=_figure_html(
            charts.suggestion_selection_by_kind,
            include_plotlyjs=False,
        ),
        suggestion_selection_by_index_html=_figure_html(
            charts.suggestion_selection_by_index,
            include_plotlyjs=False,
        ),
        readability_change_direction_html=_figure_html(
            charts.readability_change_direction,
            include_plotlyjs=False,
        ),
        final_grade_bands_html=_figure_html(
            charts.final_grade_bands,
            include_plotlyjs=False,
        ),
        selected_vs_unselected_readability_html=_figure_html(
            charts.selected_vs_unselected_readability,
            include_plotlyjs=False,
        ),
        edit_readability_relationship_html=_figure_html(
            charts.edit_readability_relationship,
            include_plotlyjs=False,
        ),
        attempt_outcomes_html=_figure_html(
            charts.attempt_outcomes_by_mode,
            include_plotlyjs=False,
        ),
        attempt_timing_html=_figure_html(
            charts.attempt_timing_distribution_by_mode,
            include_plotlyjs=False,
        ),
        completed_studies_by_completion_author_role_html=_figure_html(
            charts.completed_studies_by_completion_author_role,
            include_plotlyjs=False,
        ),
        completed_studies_by_completion_author_pi_status_html=_figure_html(
            charts.completed_studies_by_completion_author_pi_status,
            include_plotlyjs=False,
        ),
        author_appointment_schools_html=_figure_html(
            charts.author_appointment_schools,
            include_plotlyjs=False,
        ),
        pi_appointment_schools_html=_figure_html(
            charts.pi_appointment_schools,
            include_plotlyjs=False,
        ),
        author_appointment_departments_html=_figure_html(
            charts.author_appointment_departments,
            include_plotlyjs=False,
        ),
        pi_appointment_departments_html=_figure_html(
            charts.pi_appointment_departments,
            include_plotlyjs=False,
        ),
        author_appointment_titles_html=_figure_html(
            charts.author_appointment_titles,
            include_plotlyjs=False,
        ),
        pi_appointment_titles_html=_figure_html(
            charts.pi_appointment_titles,
            include_plotlyjs=False,
        ),
        participant_mix_html=_figure_html(
            charts.completed_study_participant_mix,
            include_plotlyjs=False,
        ),
        department_mix_html=_figure_html(
            charts.completed_study_department_mix,
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
    data_quality_summary: pd.DataFrame,
    charts: ExplorationCharts,
) -> None:
    """Write one self-contained HTML report."""
    try:
        path.write_text(
            render_html_report(
                overview_summary=overview_summary,
                data_quality_summary=data_quality_summary,
                charts=charts,
            ),
            encoding="utf-8",
        )
    except OSError as error:
        raise ExplorationInputError(
            f"Could not write exploration HTML report: {error}"
        ) from error
