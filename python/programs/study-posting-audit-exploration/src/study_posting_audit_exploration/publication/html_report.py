"""Self-contained faculty-facing HTML report rendering."""

from dataclasses import dataclass
from html import escape
import json
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
    "all_attempt_count",
    "distinct_study_count_with_any_attempt",
    "distinct_completed_study_count",
    "distinct_author_count_with_any_attempt",
    "distinct_completed_study_count_final_mode_ai",
    "distinct_completed_study_count_final_mode_manual",
)

_REQUIRED_PATHWAY_METRICS: tuple[str, ...] = (
    "distinct_completed_study_count",
    "distinct_completed_study_count_with_preceding_incomplete_attempts",
    "distinct_completed_study_count_with_preceding_ai_error_attempts",
)

_HANDOFF_CATEGORIES: frozenset[str] = frozenset(
    {
        "ALL_PRECEDING_ATTEMPTS_BY_OTHER_AUTHORS",
        "MIXED_COMPLETION_AND_OTHER_AUTHORS",
    }
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
    header, section, nav, .faculty-summary, details.report-section {
      margin-bottom: 1.5rem;
      padding: 1.25rem;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 0.5rem;
    }
    nav h2, .faculty-summary h2 { margin-top: 0; }
    .report-toc {
      columns: 2;
      column-gap: 2rem;
      margin: 0;
      padding-left: 1.25rem;
    }
    .report-toc li {
      break-inside: avoid;
      margin-bottom: 0.4rem;
    }
    .report-toc a {
      color: var(--accent);
      text-decoration-thickness: 0.08em;
      text-underline-offset: 0.15em;
    }
    .faculty-summary-list {
      margin-bottom: 0;
      padding-left: 1.25rem;
    }
    .faculty-summary-list li { margin-bottom: 0.5rem; }
    details.report-section {
      padding: 0;
      overflow: visible;
    }
    details.report-section > summary {
      padding: 1.25rem;
      cursor: pointer;
      color: var(--ink);
      font-size: 1.5rem;
      font-weight: 700;
      line-height: 1.2;
    }
    details.report-section > summary:hover {
      background: var(--panel);
    }
    details.report-section > summary:focus {
      outline: 3px solid var(--focus);
      outline-offset: -3px;
    }
    details.report-section[open] > summary {
      border-bottom: 1px solid var(--border);
    }
    details.report-section > section {
      margin: 0;
      border: 0;
      border-radius: 0;
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
    .pathway-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 1rem;
      margin: 1rem 0;
    }
    .pathway-card {
      padding: 1rem;
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      background: var(--panel);
    }
    .pathway-card p { margin: 0.25rem 0; }
    .pathway-value {
      font-size: 1.35rem;
      font-weight: 700;
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
    .retry-table-wrapper,
    .feedback-table-wrapper {
      margin-top: 1rem;
      overflow-x: auto;
    }
    .retry-table {
      width: 100%;
      border-collapse: collapse;
      background: var(--surface);
    }
    .retry-table caption {
      padding-bottom: 0.75rem;
      color: var(--muted);
      text-align: left;
      font-weight: 700;
    }
    .retry-table th,
    .retry-table td {
      padding: 0.65rem;
      border: 1px solid var(--border);
      text-align: left;
      vertical-align: top;
    }
    .retry-table th {
      background: var(--panel);
    }
    .retry-table th:not(:first-child),
    .retry-table td:not(:first-child) {
      text-align: right;
    }
    .interpretation-table th:not(:first-child),
    .interpretation-table td:not(:first-child) {
      text-align: left;
    }
    .feedback-table {
      width: 100%;
      border-collapse: collapse;
      background: var(--surface);
    }
    .feedback-table caption {
      padding-bottom: 0.75rem;
      color: var(--muted);
      text-align: left;
      font-weight: 700;
    }
    .feedback-table th,
    .feedback-table td {
      padding: 0.75rem;
      border: 1px solid var(--border);
      text-align: left;
      vertical-align: top;
    }
    .feedback-table th {
      background: var(--panel);
    }
    .feedback-record-id {
      width: 10rem;
      white-space: nowrap;
    }
    .feedback-text {
      min-width: 28rem;
      overflow-wrap: anywhere;
      white-space: pre-wrap;
    }
    .chart {
      min-height: 360px;
      margin-top: 1rem;
    }
    .chart + .chart { margin-top: 2rem; }
    .explanation-panel {
      margin: 1.25rem 0;
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      background: var(--panel);
    }
    .explanation-panel > summary {
      padding: 0.9rem 1rem;
      cursor: pointer;
      font-weight: 700;
    }
    .explanation-panel > summary:hover {
      background: var(--surface);
    }
    .explanation-panel > summary:focus {
      outline: 3px solid var(--focus);
      outline-offset: -3px;
    }
    .explanation-panel-content {
      padding: 0 1rem 1rem;
    }
    .explanation-panel-content dt {
      margin-top: 0.8rem;
      font-weight: 700;
    }
    .explanation-panel-content dd {
      margin: 0.2rem 0 0 1.25rem;
    }
    a:focus, button:focus, [tabindex]:focus {
      outline: 3px solid var(--focus);
      outline-offset: 2px;
    }
    @media (max-width: 700px) {
      .report-toc { columns: 1; }
    }
    @media print {
      body { background: #ffffff; }
      header, section, nav, .faculty-summary, details.report-section {
        break-inside: avoid;
        border-color: #999999;
      }
      details.report-section > summary {
        display: none;
      }
      details.report-section:not([open]) > section {
        display: block;
      }
      details.explanation-panel > summary {
        display: none;
      }
      details.explanation-panel:not([open])
        > .explanation-panel-content {
        display: block;
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

  <nav aria-labelledby="report-contents-heading">
    <h2 id="report-contents-heading">Report contents</h2>
    <ol class="report-toc">
      <li><a href="#executive-overview-heading">Captured data at a glance</a></li>
      <li><a href="#data-quality-heading">Data quality</a></li>
      <li><a href="#study-pathways-heading">Study pathways and author handoffs</a></li>
      <li>
        <a href="#retry-pathways-heading">
          Retry pathways and observed workflow patterns
        </a>
      </li>
      <li><a href="#author-experience-heading">Author experience and activity</a></li>
      <li>
        <a href="#completed-study-author-context-heading">
          Completed-study author context
        </a>
      </li>
      <li><a href="#author-context-heading">Appointment context</a></li>
      <li><a href="#study-mix-heading">Participant and department mix</a></li>
      <li><a href="#field-adoption-heading">AI field adoption and editing</a></li>
      <li><a href="#suggestion-choice-heading">Suggestion choice</a></li>
      <li>
        <a href="#compensation-heading">
          Compensation choices and text suggestions
        </a>
      </li>
      <li><a href="#readability-heading">Readability indicators</a></li>
      <li>
        <a href="#content-source-heading">
          Source context, repeated attempts, and latency
        </a>
      </li>
      <li><a href="#user-feedback-heading">User feedback on AI assistance</a></li>
    </ol>
  </nav>

  <aside class="faculty-summary" aria-labelledby="faculty-summary-heading">
    <h2 id="faculty-summary-heading">Faculty summary</h2>
    <ul class="faculty-summary-list">
      <li>
        The report contains {{ faculty_summary.all_attempt_count }} attempts
        representing {{ faculty_summary.distinct_study_count }} studies and
        {{ faculty_summary.completed_study_count }} completed studies
        ({{ faculty_summary.completion_percentage_text }}).
      </li>
      <li>
        Among completed studies, {{ faculty_summary.completed_ai_count }} used
        AI as the final authoring mode and
        {{ faculty_summary.completed_manual_count }} were authored manually.
      </li>
      <li>
        {{ faculty_summary.preceding_incomplete_count }} completed studies had
        at least one preceding incomplete attempt.
      </li>
      <li>
        {{ faculty_summary.warning_category_count }} of
        {{ faculty_summary.warning_category_total }} reportable warning
        categories affected attempts.
      </li>
      <li>
        {{ faculty_summary.feedback_count }} AI-usefulness feedback
        responses are available in the final section.
      </li>
    </ul>
    <p class="caution">
      Detailed sections below provide workflow, author, field, readability,
      source-concordance, quality, and feedback context. These descriptive
      results do not establish causal benefit or evaluate individuals.
    </p>
  </aside>

    <details class="report-section" open>
    <summary id="executive-overview-heading">
      Captured data at a glance
    </summary>
    <section aria-labelledby="executive-overview-heading">
    <div class="kpi-grid">
      {% for card in kpi_cards %}
      <article class="kpi-card">
        <p class="kpi-label">{{ card.label }}</p>
        <p class="kpi-value">{{ card.value }}</p>
        <p class="kpi-detail">{{ card.detail }}</p>
      </article>
      {% endfor %}
    </div>
    <p class="caution">
      Authors are counted as distinct attempt authors. Completed-study
      authoring mode is taken from each study's unique completed attempt.
    </p>

    <p>
      This chart counts audit attempts, not studies. A study can contribute
      more than one attempt. Each colored segment shows how many attempts used
      AI or manual authoring and whether that attempt completed the posting.
    </p>
    <p class="caution">
      A completed attempt created the posting. An incomplete attempt did not
      create it during that recorded attempt; the chart does not explain why.
    </p>
    <div class="chart">{{ attempt_outcomes_html | safe }}</div>

    <h3>Completion pathways</h3>
    <div class="pathway-grid">
      {% for callout in pathway_callouts %}
      <article class="pathway-card">
        <p class="kpi-label">{{ callout.label }}</p>
        <p class="pathway-value">
          {{ callout.affected_count }} of {{ callout.completed_study_count }}
          ({{ callout.percentage_text }})
        </p>
        <p class="kpi-detail">{{ callout.detail }}</p>
      </article>
      {% endfor %}
    </div>

    <h3>Recorded time for completed attempts</h3>
    <p>
      Attempt-level timing separates time on the study-information page from
      total elapsed attempt time. Bars show medians and error bars show the
      25th through 75th percentiles. Sample sizes, missing counts, and 90th
      percentiles are available in hover text.
    </p>
    <p class="caution">
      Recorded and elapsed times may include pauses or work outside the
      application. They do not establish author effort, efficiency, quality,
      or a causal effect of authoring mode.
    </p>
    <div class="chart">{{ attempt_timing_html | safe }}</div>

    <details class="explanation-panel">
      <summary>How to read the overview charts</summary>
      <div class="explanation-panel-content">
        <h4>Attempt outcomes</h4>
        <p>
          Read the stacked bar from left to right. Its full length is all
          recorded attempts. Each colored segment is one outcome and authoring
          mode, such as completed AI attempts or incomplete manual attempts.
          The segment count is an attempt count, so several segments can come
          from attempts for the same study.
        </p>
        <p>
          <strong>Synthetic example:</strong> if a report contains 40 attempts
          and the completed-AI segment contains 10, then 10 of the 40 attempts
          were completed AI attempts. This does not mean 10 different studies
          used AI, because one study can have several attempts.
        </p>

        <h4>Completion-pathway cards</h4>
        <p>
          These cards switch to a study-level view. Each completed study
          contributes once. A card showing preceding incomplete attempts means
          that the same study had at least one earlier recorded attempt before
          its unique completed attempt.
        </p>
        <p>
          <strong>Synthetic example:</strong> if 5 of 20 completed studies had
          a preceding incomplete attempt, the card reports 25%. It does not
          explain why those earlier attempts ended.
        </p>

        <h4>Completed-attempt timing</h4>
        <p>
          Each bar is the median recorded time among completed attempts in one
          authoring mode. The thin error line spans the 25th to 75th
          percentiles: the middle half of recorded values. Hover text provides
          the number of attempts with a timing value, missing counts, and the
          90th percentile.
        </p>
        <p>
          <strong>Synthetic example:</strong> a median of 8 minutes with an
          error line from 4 to 12 minutes means half of the recorded values
          were at or below 8 minutes, and the middle half fell between 4 and
          12 minutes. It does not show that the mode caused faster or slower
          work.
        </p>

        <p class="caution">
          Attempts, completed studies, and authors are different counting
          units. Compare values only when the chart or card uses the same unit
          and denominator.
        </p>
      </div>
    </details>

    <p class="caution">
      These figures describe the audit records captured in this report. They
      do not estimate causal effects of AI, measure writing quality, or
      establish author productivity. Attempts and studies are different
      analytical units: a study may have multiple attempts, while each
      completed study contributes one unique completed attempt.
    </p>
  </section>
  </details>

    <details class="report-section" open>
    <summary id="data-quality-heading">
      Data quality
    </summary>
    <section aria-labelledby="data-quality-heading">
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
  </details>

    <details class="report-section" open>
    <summary id="study-pathways-heading">
      Study pathways and author handoffs
    </summary>
    <section aria-labelledby="study-pathways-heading">
    <p>
      These charts count completed studies. Each completed study contributes
      once, using the AI or manual mode recorded on its unique completed
      attempt. The first chart separates studies completed on their first
      recorded attempt from studies with one or more earlier incomplete
      attempts.
    </p>
    <p class="caution">
      A preceding attempt is an incomplete attempt ordered before the unique
      completed attempt for the same study. The chart describes the recorded
      sequence; it does not explain why an earlier attempt ended.
    </p>
    <div class="chart">{{ study_pathways_html | safe }}</div>

    <details class="explanation-panel">
      <summary>How to read the author-handoff categories</summary>
      <div class="explanation-panel-content">
        <p>
          Each completed study appears in exactly one category. The
          <strong>completion author</strong> is the person who made the final
          attempt that created the study posting.
        </p>
        <dl>
          <dt>No preceding attempt</dt>
          <dd>
            The study posting was created on its first recorded attempt.
          </dd>

          <dt>All preceding attempts by completion author</dt>
          <dd>
            The study had one or more earlier incomplete attempts, and every
            earlier attempt was made by the same person who ultimately created
            the posting. No author handoff occurred.
          </dd>

          <dt>All preceding attempts by other authors</dt>
          <dd>
            The study had one or more earlier incomplete attempts, and every
            earlier attempt was made by someone other than the person who
            ultimately created the posting.
          </dd>

          <dt>Mixed completion and other authors</dt>
          <dd>
            Earlier incomplete attempts included both the person who
            ultimately created the posting and at least one other author.
          </dd>
        </dl>

        <h4>How to read the stacked bars</h4>
        <p>
          Each full bar is all completed studies for one final authoring mode.
          The colored segments divide that bar into author-handoff categories.
          Segment heights are completed-study counts, not author counts.
        </p>
        <p>
          <strong>Synthetic chart example:</strong> if an AI bar contains 20
          completed studies and 4 are in an “all preceding attempts by other
          authors” segment, then 4 of those 20 completed AI studies had earlier
          attempts made only by people other than the completion author. It
          does not show why responsibility changed.
        </p>

        <h4>Brief category example</h4>
        <p>
          Suppose Alex made the completed attempt:
        </p>
        <ul>
          <li>
            No earlier attempt means <strong>No preceding attempt</strong>.
          </li>
          <li>
            Only Alex made earlier attempts means
            <strong>All preceding attempts by completion author</strong>.
          </li>
          <li>
            Only people other than Alex made earlier attempts means
            <strong>All preceding attempts by other authors</strong>.
          </li>
          <li>
            Alex and at least one other person made earlier attempts means
            <strong>Mixed completion and other authors</strong>.
          </li>
        </ul>

        <p class="caution">
          These categories describe the recorded sequence of attempt authors.
          They do not explain why an author changed, how responsibility was
          assigned, or whether collaboration occurred outside the application.
        </p>
      </div>
    </details>

    <div class="chart">{{ author_handoffs_html | safe }}</div>
  </section>
  </details>


    <details class="report-section">
    <summary id="retry-pathways-heading">
      Retry pathways and observed workflow patterns
    </summary>
    <section aria-labelledby="retry-pathways-heading">
      <p>
        Each study appears once in the cards and pathway chart. The patterns
        summarize recorded completion state, authoring modes, author changes,
        AI errors, returned-result AI attempts, source comparisons, feedback
        presence, and timing.
      </p>
      <p class="caution">
        “No completion observed” means no completed attempt appears in the
        captured report. Completion may occur outside the observation window.
        These results do not measure drop-off or a final unresolved outcome.
      </p>

      <div class="pathway-grid">
        {% for card in retry_cards %}
        <article class="pathway-card">
          <h3>{{ card.label }}</h3>
          <p class="pathway-value">
            {{ card.study_count }} studies ({{ card.percentage_text }})
          </p>
          <p>Median attempts: {{ card.median_attempts_text }}</p>
          <p>{{ card.mode_mix_text }}</p>
        </article>
        {% endfor %}
      </div>

      <div class="chart">{{ retry_pathways_html | safe }}</div>
      <p>
        <strong>Synthetic example:</strong> AI → AI → manual completion belongs
        to <strong>AI to manual → manual completion</strong>. This records the
        observed sequence and does not explain why the team changed modes.
      </p>

      <div class="retry-table-wrapper" role="region"
           aria-label="Observed retry characteristics table" tabindex="0">
        <table class="retry-table">
          <caption>
            Observed retry characteristics. General percentages use all studies
            in the row; source-change percentages use source-comparison-eligible
            studies; feedback percentages use AI-exposed studies.
          </caption>
          <thead>
            <tr>
              <th scope="col">Study group</th>
              <th scope="col">Studies</th>
              <th scope="col">Median attempts</th>
              <th scope="col">Both modes</th>
              <th scope="col">Author change</th>
              <th scope="col">AI error</th>
              <th scope="col">Returned-result AI</th>
              <th scope="col">Source change among eligible</th>
              <th scope="col">Feedback among AI-exposed</th>
              <th scope="col">First attempt to completion end</th>
              <th scope="col">First to latest observed attempt</th>
              <th scope="col">Latest attempt to report-run cutoff</th>
              <th scope="col">First attempt to report-run cutoff</th>
            </tr>
          </thead>
          <tbody>
            {% for row in retry_characteristics %}
            <tr>
              <th scope="row">{{ row.label }}</th>
              <td>{{ row.study_count }}</td>
              <td>{{ row.median_attempts_text }}</td>
              <td>{{ row.both_modes_text }}</td>
              <td>{{ row.author_change_text }}</td>
              <td>{{ row.ai_error_text }}</td>
              <td>{{ row.returned_result_ai_text }}</td>
              <td>{{ row.source_change_text }}</td>
              <td>{{ row.feedback_text }}</td>
              <td>{{ row.completion_timing_text }}</td>
              <td>{{ row.observed_activity_span_text }}</td>
              <td>{{ row.latest_attempt_to_cutoff_text }}</td>
              <td>{{ row.first_attempt_to_cutoff_text }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>

      <details class="explanation-panel">
        <summary>How to read the retry summary</summary>
        <div class="explanation-panel-content">
          <h4>Cards</h4>
          <p>
            The four cards divide all studies into completed versus no
            completion observed and one versus multiple recorded attempts.
            Each study appears in exactly one card. The percentage uses all
            studies with at least one captured attempt as its denominator.
          </p>
          <p>
            <strong>Synthetic example:</strong> if 12 of 50 studies had
            multiple attempts and then completed, that card reports 24%.
            This identifies a repeated-attempt pattern but does not explain
            why another attempt was needed.
          </p>

          <h4>Horizontal pathway chart</h4>
          <p>
            Each horizontal bar is one mutually exclusive sequence category.
            Bar length is the number of studies in that category. A study
            appears in only one bar, based on its complete recorded mode
            sequence and whether completion was observed.
          </p>
          <p>
            <strong>Synthetic example:</strong> AI → AI → manual completion is
            counted once in <strong>AI to manual → manual completion</strong>,
            not once for every arrow or attempt.
          </p>

          <h4>Characteristics table</h4>
          <p>
            Each row groups studies by observed result: completed with AI,
            completed manually, or no completion observed. General
            percentages use all studies in that row. Source-change
            percentages use only studies with comparable returned-result AI
            attempts. Feedback percentages use only studies with at least one
            AI attempt.
          </p>
          <p>
            A value shown as <code>\\N</code> means the measure was
            unavailable, usually because its denominator was zero. It does
            not mean zero percent.
          </p>

          <h4>Timing columns</h4>
          <ul>
            <li>
              <strong>First attempt to completion end</strong> applies to
              completed studies.
            </li>
            <li>
              <strong>First to latest observed attempt</strong> describes the
              period containing recorded activity for studies with no
              completion observed.
            </li>
            <li>
              <strong>Latest attempt to report-run cutoff</strong> describes
              how long the report continued observing after the latest
              attempt.
            </li>
            <li>
              <strong>First attempt to report-run cutoff</strong> is the total
              captured observation window.
            </li>
          </ul>
          <p>
            <strong>Synthetic timing example:</strong> if a study's first
            attempt was on day 1, its latest attempt was on day 3, and the
            report ran on day 10, then its observed activity span is 2 days,
            follow-up after the latest attempt is 7 days, and total
            observation window is 9 days.
          </p>
          <p class="caution">
            These durations are descriptive. They do not classify studies as
            abandoned, measure satisfaction, or establish a causal effect of
            AI or manual authoring.
          </p>
        </div>
      </details>

      <details class="explanation-panel">
        <summary>How to interpret observed retry patterns</summary>
        <div class="explanation-panel-content">
          <div class="retry-table-wrapper" role="region"
               aria-label="Observed retry pattern interpretation table"
               tabindex="0">
            <table class="retry-table interpretation-table">
              <thead>
                <tr>
                  <th scope="col">Observed pattern</th>
                  <th scope="col">May motivate investigating</th>
                  <th scope="col">Does not prove</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th scope="row">AI attempts followed by manual completion</th>
                  <td>Whether AI output fit the team's needs</td>
                  <td>That the team disliked or rejected AI</td>
                </tr>
                <tr>
                  <th scope="row">
                    Source size, type, or category changed across AI retries
                  </th>
                  <td>Whether teams explored different source inputs</td>
                  <td>That changes were intentional tests</td>
                </tr>
                <tr>
                  <th scope="row">Same author retried several times</th>
                  <td>Whether one person iterated through the workflow</td>
                  <td>What they thought about suggestion quality</td>
                </tr>
                <tr>
                  <th scope="row">Multiple authors participated</th>
                  <td>
                    Whether responsibility shifted or collaboration occurred
                  </td>
                  <td>Why a handoff occurred</td>
                </tr>
                <tr>
                  <th scope="row">No completion observed</th>
                  <td>Whether completion occurred after the extract</td>
                  <td>That the study was abandoned</td>
                </tr>
                <tr>
                  <th scope="row">Feedback not recorded</th>
                  <td>Whether feedback capture was optional or skipped</td>
                  <td>Satisfaction or dissatisfaction</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="caution">
            Patterns support targeted qualitative follow-up, not causal or
            motivational conclusions.
          </p>
        </div>
      </details>
    </section>
    </details>

    <details class="report-section">
    <summary id="author-experience-heading">
      Author experience and activity
    </summary>
    <section aria-labelledby="author-experience-heading">
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

  <details class="explanation-panel">
    <summary>How to compare attempt-time and query-time experience</summary>
    <div class="explanation-panel-content">
      <h4>Attempt-time chart</h4>
      <p>
        Each bar shows the median number of prior studies across attempts in
        one authoring mode. Because attempts are counted, an author with three
        attempts contributes three observations.
      </p>
      <p>
        <strong>Synthetic example:</strong> if five AI attempts have prior-study
        counts of 0, 1, 2, 4, and 8, the AI bar is 2 studies, the middle value.
      </p>

      <h4>Query-time charts</h4>
      <p>
        Each cluster is an author adoption group, and each colored bar is one
        experience or activity metric. Bar height is the median among distinct
        authors who had a value for that metric when the report query ran.
      </p>
      <p>
        <strong>Synthetic example:</strong> if the “authors with any AI
        attempt” group has a 6-day bar for distinct login days, the median
        author in that group had 6 distinct calendar days with a recorded
        login. It does not mean each author had 6 login days.
      </p>
      <p class="caution">
        Attempt-time and query-time bars use different observation units and
        time points, so their heights should not be compared as if they
        measured the same population. Larger medians do not establish that
        experience caused authoring-mode choice or completion.
      </p>
    </div>
  </details>

  <p class="caution">
    These descriptive medians must not be interpreted as causes of
    authoring-mode choice or study outcomes.
  </p>
</section>
  </details>

    <details class="report-section">
    <summary id="completed-study-author-context-heading">
      Completed studies by authoring mode and completion-author context
    </summary>
    <section aria-labelledby="completed-study-author-context-heading">
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

    <details class="explanation-panel">
      <summary>How to read completion-author context</summary>
      <div class="explanation-panel-content">
        <p>
          Each horizontal bar is one final authoring mode. Its stacked
          segments divide completed studies by the completion author's role or
          by whether that author was the principal investigator for that
          specific study. Segment length is a completed-study count.
        </p>
        <p>
          <strong>Synthetic example:</strong> if the manual bar contains 15
          completed studies and its “PI for this study” segment contains 6,
          then the completion author was the study's principal investigator
          for 6 of those 15 studies. This counts studies, not six necessarily
          different people.
        </p>
        <p class="caution">
          These charts describe who made the recorded completed attempt. They
          do not measure effort by other team members or explain why AI or
          manual authoring was used.
        </p>
      </div>
    </details>
  </section>
  </details>

    <details class="report-section">
    <summary id="author-context-heading">
      Author and principal-investigator appointment context
    </summary>
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

    <details class="explanation-panel">
      <summary>How to interpret overlapping appointment groups</summary>
      <div class="explanation-panel-content">
        <p>
          Each horizontal bar counts distinct attempt authors represented in
          one school, department, or title group. “Author appointment” charts
          use appointments recorded for attempt authors. “Principal-
          investigator appointment” charts count attempt authors according to
          the appointment groups of their studies' named principal
          investigators.
        </p>
        <p>
          <strong>Synthetic example:</strong> among 10 distinct attempt authors,
          6 might be represented in one school and 5 in another. The total can
          exceed 10 because an author or a study's principal investigator may
          have appointments in both schools; the chart does not count 11
          different people.
        </p>
        <p class="caution">
          Larger bars show broader representation in the captured attempts,
          not greater feature use per person, influence, or effectiveness.
        </p>
      </div>
    </details>
  </section>
  </details>

    <details class="report-section">
    <summary id="study-mix-heading">
      Participant and department mix
    </summary>
    <section aria-labelledby="study-mix-heading">
    <p>
      These horizontal bars count completed studies by participant type and
      study department. One bar represents one category, and its length is the
      number of completed studies in that category.
    </p>
    <p class="caution">
      Categories within each chart are mutually exclusive, so each completed
      study contributes once per chart. Other and missing categories are
      retained rather than silently removed. The charts describe the completed
      study mix; they do not compare completion rates between categories.
    </p>
    <div class="chart">{{ participant_mix_html | safe }}</div>
    <div class="chart">{{ department_mix_html | safe }}</div>
  </section>
  </details>

    <details class="report-section">
    <summary id="field-adoption-heading">
      AI field adoption and editing
    </summary>
    <section aria-labelledby="field-adoption-heading">
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

  <details class="explanation-panel">
    <summary>How to read field adoption and editing</summary>
    <div class="explanation-panel-content">
      <h4>Offers and selections</h4>
      <p>
        Each field has side-by-side bars. One bar counts completed AI attempts
        with at least one suggestion offered for that field; the other counts
        completed AI attempts where an offered suggestion was selected.
      </p>
      <p>
        <strong>Synthetic example:</strong> if 20 completed AI attempts had a
        description suggestion and 8 selected one, the bars are 20 and 8. The
        selection percentage is 40% of attempts with an offer, not 8 divided
        by every completed AI attempt.
      </p>

      <h4>What happened after selection</h4>
      <p>
        Each stacked bar contains completed AI attempts that selected a
        suggestion for one field. Colored segments count how the selected
        suggestion compared with the final field text, such as exact, lightly
        edited, heavily edited, replaced, or cleared.
      </p>
      <p>
        <strong>Synthetic example:</strong> if 10 attempts selected a title
        suggestion and 3 are in the light-edit segment, 3 of those 10 selected
        attempts ended with a light edit. It does not show that the edit
        improved or harmed the title.
      </p>
    </div>
  </details>
</section>
  </details>

  <details class="report-section">
    <summary id="suggestion-choice-heading">
    Suggestion choice
  </summary>
  <section aria-labelledby="suggestion-choice-heading">
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

  <details class="explanation-panel">
    <summary>How to read the suggestion-choice charts</summary>
    <div class="explanation-panel-content">
      <h4>Selection by field and kind</h4>
      <p>
        Each bar is one field and suggestion-kind combination. Bar height is
        the percentage of completed AI attempts with at least one offered
        suggestion in that combination that selected a suggestion.
      </p>
      <p>
        <strong>Synthetic example:</strong> if 12 eligible attempts received
        one or more suggestions of a kind and 9 selected one, the bar is 75%.
        This is an attempt-level percentage even if those attempts received
        more than 12 individual suggestions.
      </p>

      <h4>Selection by offered position</h4>
      <p>
        Each point shows the percentage of suggestion instances offered at one
        zero-based position that were selected. Index 0 means first, index 1
        means second, and so on. Lines separate field and suggestion-kind
        combinations.
      </p>
      <p>
        <strong>Synthetic example:</strong> if a group offered 10 suggestions
        at index 0 and 4 were selected, its index-0 point is 40%.
      </p>
      <p class="caution">
        Later positions may have fewer opportunities because not every attempt
        offers the same number of suggestions. Compare positions with their
        offered counts; a higher point does not by itself show that position or
        suggestion quality caused selection.
      </p>
    </div>
  </details>
</section>
  </details>

  <details class="report-section">
    <summary id="compensation-heading">
      Compensation choices and text suggestions
    </summary>
    <section aria-labelledby="compensation-heading">
      <p>
        This section includes completed AI attempts only. It first compares
        the compensation Yes/No value supplied by AI with the final saved
        value. It then summarizes generic and specific compensation text
        suggestions.
      </p>
      <p class="caution">
        A matching final Yes/No value means the saved value matched the value
        supplied by AI. The audit data do not show whether the user actively
        clicked or affirmatively accepted that value.
      </p>

      <h3>AI-supplied Yes/No value and final saved value</h3>
      {% if compensation_flag %}
      <div class="retry-table-wrapper" role="region"
           aria-label="Compensation Yes or No comparison table" tabindex="0">
        <table class="retry-table">
          <caption>
            Compensation Yes/No comparison among completed AI attempts
          </caption>
          <thead>
            <tr>
              <th scope="col">Completed AI attempts</th>
              <th scope="col">With AI-supplied value</th>
              <th scope="col">Final matched AI value</th>
              <th scope="col">Final differed from AI value</th>
              <th scope="col">Final value unavailable</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{{ compensation_flag.completed_attempt_count }}</td>
              <td>{{ compensation_flag.ai_value_count }}</td>
              <td>{{ compensation_flag.matched_count }}</td>
              <td>{{ compensation_flag.differed_count }}</td>
              <td>{{ compensation_flag.final_unavailable_count }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p>
        Among attempts with an AI-supplied value,
        {{ compensation_flag.matched_percentage_text }} had a matching final
        value and {{ compensation_flag.differed_percentage_text }} had a
        different final value. These percentages can sum to less than 100%
        when a final value was unavailable.
      </p>
      {% else %}
      <p>No compensation Yes/No aggregate was available.</p>
      {% endif %}

      <h3>Generic and specific compensation text suggestions</h3>
      <p>
        The chart compares completed AI attempts offered each kind with
        completed AI attempts selecting that kind.
      </p>
      <div class="chart">
        {{ compensation_suggestion_use_html | safe }}
      </div>
      {% if compensation_text_rows %}
      <div class="retry-table-wrapper" role="region"
           aria-label="Compensation text suggestion table" tabindex="0">
        <table class="retry-table">
          <caption>
            Compensation text offers and selections among completed AI attempts
          </caption>
          <thead>
            <tr>
              <th scope="col">Suggestion kind</th>
              <th scope="col">Attempts with one or more offers</th>
              <th scope="col">Text suggestions offered</th>
              <th scope="col">Attempts selecting this kind</th>
              <th scope="col">
                Attempts selecting among attempts offered this kind
              </th>
            </tr>
          </thead>
          <tbody>
            {% for row in compensation_text_rows %}
            <tr>
              <th scope="row">{{ row.label }}</th>
              <td>{{ row.attempt_count_with_suggestion }}</td>
              <td>{{ row.offered_count }}</td>
              <td>{{ row.selected_count }}</td>
              <td>{{ row.attempt_selection_percentage_text }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <p>No compensation text-suggestion aggregate was available.</p>
      {% endif %}

      <h3>Which kinds and how many suggestions were offered?</h3>
      <p>
        The next charts separate all completed AI attempts from the subset
        whose final saved compensation value was Yes. Each attempt appears in
        exactly one category per chart: both kinds, generic only, specific
        only, or neither.
      </p>
      <div class="chart">
        {{ compensation_offer_composition_all_html | safe }}
      </div>
      <div class="chart">
        {{ compensation_offer_composition_final_yes_html | safe }}
      </div>

      {% if compensation_count_pair_rows %}
      <div class="retry-table-wrapper" role="region"
           aria-label="Compensation suggestion count combinations" tabindex="0">
        <table class="retry-table">
          <caption>
            Observed generic and specific suggestion-count combinations
          </caption>
          <thead>
            <tr>
              <th scope="col">Population</th>
              <th scope="col">Offer composition</th>
              <th scope="col">Generic suggestions</th>
              <th scope="col">Specific suggestions</th>
              <th scope="col">Completed AI attempts</th>
              <th scope="col">Share of population</th>
              <th scope="col">Exactly 3 generic + 3 specific</th>
            </tr>
          </thead>
          <tbody>
            {% for row in compensation_count_pair_rows %}
            <tr>
              <td>{{ row.population_label }}</td>
              <td>{{ row.composition_label }}</td>
              <td>{{ row.generic_count }}</td>
              <td>{{ row.specific_count }}</td>
              <td>{{ row.attempt_count }}</td>
              <td>{{ row.percentage_text }}</td>
              <td>{{ row.exact_three_plus_three_text }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <p>No exact compensation suggestion-count combinations were available.</p>
      {% endif %}

      <h3>Workflow consistency checks</h3>
      <p>
        These checks identify combinations that may merit follow-up, such as
        AI supplying No while text suggestions were still offered or a final
        Yes value without the expected suggestion set.
      </p>
      {% if compensation_consistency_rows %}
      <div class="retry-table-wrapper" role="region"
           aria-label="Compensation workflow consistency checks" tabindex="0">
        <table class="retry-table">
          <caption>
            Descriptive compensation workflow-consistency checks
          </caption>
          <thead>
            <tr>
              <th scope="col">Observed condition</th>
              <th scope="col">Completed AI attempts</th>
              <th scope="col">Denominator population</th>
              <th scope="col">Denominator attempts</th>
              <th scope="col">Percentage</th>
            </tr>
          </thead>
          <tbody>
            {% for row in compensation_consistency_rows %}
            <tr>
              <th scope="row">{{ row.label }}</th>
              <td>{{ row.attempt_count }}</td>
              <td>{{ row.population_label }}</td>
              <td>{{ row.population_count }}</td>
              <td>{{ row.percentage_text }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <p>No compensation workflow-consistency aggregates were available.</p>
      {% endif %}
      <p class="caution">
        Consistency checks can overlap, so do not add their counts or
        percentages as though they divide attempts into exclusive groups.
        They are descriptive flags, not proof of model malfunction or user
        intent.
      </p>

      <p>
        Compensation edit and retention outcomes also appear in
        <a href="#field-adoption-heading">AI field adoption and editing</a>.
        Suggestion-position patterns appear in
        <a href="#suggestion-choice-heading">Suggestion choice</a>, and
        eligible formula-based text indicators appear in
        <a href="#readability-heading">Readability indicators</a>.
      </p>

      <details class="explanation-panel">
        <summary>How to interpret compensation choices</summary>
        <div class="explanation-panel-content">
          <p>
            The Yes/No table counts completed AI attempts. “Matched” means the
            AI-supplied Boolean and final saved Boolean were equal; “differed”
            means they were unequal. It does not identify an active click.
          </p>
          <p>
            The text table uses two units. “Attempts with one or more
            offers” and “attempts selecting” count completed AI attempts.
            “Text suggestions offered” counts individual suggestion instances.
            At most one compensation text suggestion can be selected per
            attempt.
          </p>
          <p>
            <strong>Synthetic example:</strong> if 10 completed AI attempts
            received generic suggestions and 4 selected a generic suggestion,
            the attempt-level selection percentage is 40%. If those attempts
            received 30 individual generic suggestions, 30 remains useful offer
            context but is not the percentage denominator.
          </p>
          <p>
            <strong>Synthetic offer-composition example:</strong> suppose 10
            final-Yes attempts include 6 with both kinds at 3 generic and 3
            specific, 2 with generic only at counts of 1 and 2, and 2 with
            specific only. The composition chart shows 6, 2, 2, and 0 across
            the four categories; the exact-count table preserves the 3+3,
            1+0, 2+0, and 0+specific-count combinations.
          </p>
          <p class="caution">
            These summaries describe what was captured as offered and selected.
            They do not establish preference, suggestion quality, causal
            benefit, model malfunction, or user intent.
          </p>
        </div>
      </details>
    </section>
  </details>

  <details class="report-section">
    <summary id="readability-heading">
    Readability indicators
  </summary>
  <section aria-labelledby="readability-heading">
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

  <details class="explanation-panel">
    <summary>How to read direction and final grade bands</summary>
    <div class="explanation-panel-content">
      <h4>Selected-to-final direction</h4>
      <p>
        Each stacked bar is one field and counts attempts with usable selected
        and final Flesch-Kincaid values. Its segments show whether the final
        value was lower, within the no-material-change tolerance, or higher
        than the selected suggestion's value.
      </p>
      <p>
        <strong>Synthetic example:</strong> if 12 paired descriptions include
        5 lower, 4 within tolerance, and 3 higher final values, the stacked bar
        has segments of 5, 4, and 3.
      </p>

      <h4>Observed final grade bands</h4>
      <p>
        Each stacked bar is one field and final authoring mode. Its full height
        is the number of observed nonblank final texts with a usable
        Flesch-Kincaid value; colored segments divide those texts into formula
        grade bands.
      </p>
      <p>
        <strong>Synthetic example:</strong> if an AI-description bar contains
        20 final texts and 6 are in the above-grade-8-through-grade-10 segment,
        6 of those 20 formula values fell in that band. The band is not a
        reading-age assignment or a quality rating.
      </p>
    </div>
  </details>

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

  <details class="explanation-panel">
    <summary>How to read selected versus unselected differences</summary>
    <div class="explanation-panel-content">
      <p>
        Each field has one bar. For every comparable attempt, the calculation
        is the selected suggestion's Flesch-Kincaid value minus the mean value
        of that attempt's unselected suggestions. The chart shows the median
        of those attempt-level differences.
      </p>
      <p>
        <strong>Synthetic example:</strong> a bar at -0.5 means the middle
        selected-minus-mean-unselected difference was 0.5 grade levels below
        zero. A bar at +0.5 means the selected suggestion's formula value was
        0.5 grade levels higher at the median.
      </p>
      <p class="caution">
        Positive or negative values describe formula-score differences only.
        Selection does not prove that the chosen suggestion was clearer,
        better, more accurate, or more accessible.
      </p>
    </div>
  </details>

  <h3>Edit intensity and readability direction</h3>
  <p>
    This chart explores whether the size of a selected-suggestion edit is
    associated with the direction of grade-level formula changes. It is
    descriptive and does not establish whether an edit improved the text.
  </p>

  <details class="explanation-panel">
    <summary>Definitions and how to read edit-intensity results</summary>
    <div class="explanation-panel-content">
      <h4>How edit size is classified</h4>
      <p>
        The character edit ratio is the character edit distance divided by the
        longer character count of the selected suggestion or final text.
        Character edit distance counts the minimum insertions, deletions, and
        substitutions needed to transform the selected suggestion into the
        final text.
      </p>
      <ul>
        <li><strong>Exact:</strong> final text exactly matched the selected
          suggestion.</li>
        <li><strong>Cosmetic:</strong> only cosmetic normalization changed.</li>
        <li><strong>Light edit:</strong> character edit ratio at or below
          10%.</li>
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
        These are project-specific exploratory character-edit bands using 10%
        and 30% thresholds. The technical scheme ID is
        <code>EXPLORATORY_CHARACTER_RATIO_10_30</code>. The bands describe edit
        size, not writing quality.
      </p>

      <h4>How readability direction is classified</h4>
      <p>
        Consensus uses Flesch-Kincaid grade, Automated Readability Index,
        Coleman-Liau Index, and Gunning Fog.
      </p>
      <ul>
        <li><strong>Consensus decrease:</strong> the grade-level formulas agreed
          on a downward direction for material change.</li>
        <li><strong>No material change:</strong> formula changes stayed within
          the configured tolerance.</li>
        <li><strong>Consensus increase:</strong> the grade-level formulas agreed
          on an upward direction for material change.</li>
        <li><strong>Mixed formula direction:</strong> the formulas did not agree
          on direction. Mixed direction is not the same as no material
          change.</li>
      </ul>

      <h4>How to read a bar</h4>
      <p>
        Each bar represents one study-posting field and one edit category. The
        label includes the total group size as <strong>N</strong>. Colored
        sections show the share assigned to each readability result. Only
        fields with usable selected-and-final readability pairs receive a
        direction. If the colored sections total less than 100%, the unfilled
        remainder represents fields without a usable pair. Always inspect the
        counts in hover text: a 100% section based on one field is less stable
        than one based on many fields.
      </p>
      <p>
        <strong>Worked example:</strong> if a group contains five light-edited
        descriptions and one is classified as consensus decrease, that section
        is 20% (1 of 5). A median Flesch-Kincaid change of -0.59 means the
        middle final-minus-selected indicator in that result group was 0.59
        grade levels lower. It does not show that the final text was better or
        easier to understand.
      </p>
      <p class="caution">
        Lower is not automatically better, and higher is not automatically
        worse. Grade-level formulas do not establish comprehension, accuracy,
        accessibility, usefulness, cultural appropriateness, writing quality,
        or causal benefit.
      </p>
    </div>
  </details>

  <div class="chart">
    {{ edit_readability_relationship_html | safe }}
  </div>
</section>
  </details>

    <details class="report-section">
    <summary id="content-source-heading">
      Source context, repeated attempts, and latency
    </summary>
    <section aria-labelledby="content-source-heading">
    <p>
      This section separates generation activity from completed study
      creation. An <strong>AI generation that returned a result</strong> is an
      AI generation that did not end in either recorded AI-error category. It
      includes completed and user-dropped attempts. It does not mean that the
      study posting was created.
    </p>

    <h3>All AI generations that returned a result</h3>
    <p>
      One study can contribute more than one generation attempt to these
      charts. Input method describes how source material was supplied; it is
      workflow context, not the primary explanation for source size or
      latency.
    </p>
    <div class="chart">
      {{ returned_result_input_method_html | safe }}
    </div>
    <div class="chart">
      {{ returned_result_source_size_latency_html | safe }}
    </div>

    <h3>Completed AI-assisted attempts</h3>
    <p>
      Each completed study contributes its unique completed AI-assisted
      attempt once. These charts use the same source-size band boundaries as
      the all-generation charts so the populations remain comparable.
    </p>
    <div class="chart">
      {{ completed_ai_input_method_html | safe }}
    </div>
    <div class="chart">
      {{ completed_ai_source_size_latency_html | safe }}
    </div>

    <h3>How source-size bands and latency are summarized</h3>
    <p>
      Source size is the captured character count of text supplied to
      generation. Bands are ranked from source-size quartiles among all AI
      generations that returned a result. Error bars show the
      25th-to-75th-percentile latency range. Hover text includes the 90th
      percentile and missing or nonmissing latency counts. Faculty-facing
      latency is displayed in seconds.
    </p>
    <p class="caution">
      Bands improve descriptive comparability but do not remove every
      within-band difference. Latency may also reflect service conditions and
      other unmeasured factors. The results do not establish that source size,
      source category, or input method caused a latency difference.
    </p>

    <details class="explanation-panel">
      <summary>How to read input method and latency</summary>
      <div class="explanation-panel-content">
        <h4>Input-method charts</h4>
        <p>
          Each horizontal bar is one captured way of supplying source
          material. Bar length is the number of generation attempts in the
          population named by the chart. One study can contribute several bars'
          worth of activity across separate generations, but only once per
          generation.
        </p>
        <p>
          <strong>Synthetic example:</strong> if 30 returned-result generations
          used file upload and 20 used pasted text, their bars are 30 and 20.
          This counts generations, not necessarily 50 different studies or
          authors.
        </p>

        <h4>Latency charts</h4>
        <p>
          Each source-size band is defined by ranked quartile boundaries from
          all generations that returned a result. Bar height is median
          generation latency in seconds. The error line spans the 25th to 75th
          percentile, so a longer line means the middle half of observed
          latencies was more spread out.
        </p>
        <p>
          <strong>Synthetic example:</strong> a 6-second bar with an error line
          from 4 to 9 seconds means the median was 6 seconds and the middle half
          of captured latencies ranged from 4 through 9 seconds. It does not
          mean every generation took between 4 and 9 seconds.
        </p>
        <p class="caution">
          Compare the all-returned-result and completed-AI charts as different
          populations. A latency difference does not establish that source
          size or input method caused it.
        </p>
      </div>
    </details>

    <h3>Reported versus inferred content source</h3>
    <p>
      This heatmap compares the author-reported semantic source category with
      the model-inferred category for AI generations that returned a result
      and had both categories available. Counts use normalized aggregate
      labels.
    </p>
    <div class="chart">{{ content_source_html | safe }}</div>

    <details class="explanation-panel">
      <summary>How to read the reported-versus-inferred heatmap</summary>
      <div class="explanation-panel-content">
        <p>
          Each cell combines one author-reported category on the vertical axis
          with one model-inferred category on the horizontal axis. The cell
          value and color intensity show the number of comparable AI
          generations in that combination.
        </p>
        <p>
          <strong>Synthetic example:</strong> if the “Category A” row and
          “Category A” column cell contains 18, then 18 comparable generations
          were reported and inferred as Category A. If the same row's
          “Category B” column contains 5, then 5 were reported as A and inferred
          as B.
        </p>
        <p class="caution">
          Diagonal cells show matching normalized labels; off-diagonal cells
          show different labels. Neither pattern proves which label is correct
          or why the labels differ.
        </p>
      </div>
    </details>

    <p class="caution">
      Agreement is descriptive. It does not establish that either category is
      objectively correct, and a missing reported category is not silently
      replaced with an inferred category.
    </p>

    <h3>Source changes before completed AI-assisted attempts</h3>
    {% if source_context.has_repeated_pathways %}
    <p>
      <strong>{{ source_context.transition_count }}</strong>
      consecutive-generation transitions from
      <strong>{{ source_context.contributing_study_count }}</strong>
      completed AI studies are represented. Each transition compares two
      adjacent AI generations that returned a result within a pathway ending
      in a completed AI-assisted attempt. A study can contribute more than one
      transition.
    </p>
    {% else %}
    <p>
      No completed AI pathway contained two generation attempts that returned
      a result, so no consecutive-generation transition was available.
    </p>
    {% endif %}

    {% if source_context.has_repeated_pathways %}
    <div class="chart">
      {{ repeated_source_consistency_html | safe }}
    </div>
    {% endif %}

    <details class="explanation-panel">
      <summary>How to read adjacent-generation source changes</summary>
      <div class="explanation-panel-content">
        <h4>What is being compared?</h4>
        <p>
          Each comparison uses two adjacent AI generations for the same study.
          Manual attempts and AI-error attempts are not treated as source
          comparisons. The completed-path analysis stops at the completed
          AI-assisted attempt.
        </p>
        <p>
          If a study had three qualifying AI generations before completion, it
          contributes two transitions: generation 1 to generation 2, and
          generation 2 to the completed generation.
        </p>

        {% if source_context.has_repeated_pathways %}
        <h4>Available comparisons</h4>
        <ul>
          {% for comparison in source_context.comparisons %}
          <li>
            <strong>{{ comparison.label }}:</strong>
            {{ comparison.comparable_transition_count }} comparable and
            {{ comparison.unavailable_transition_count }} unavailable among
            {{ comparison.all_transition_count }} total completed-path
            transitions.
          </li>
          {% endfor %}
        </ul>
        {% endif %}

        <h4>Illustrative example</h4>
        <p>
          Suppose generation 1 used DOCX, reported informed consent, contained
          4,200 source characters, and took 12.0 seconds. Generation 2 used
          DOCX, reported informed consent, contained 5,100 characters, and took
          13.5 seconds. Source size changed; reported source and input method
          were unchanged; the source-signature proxy changed because source
          size changed; and captured latency increased by 1.5 seconds. This
          example does not show that the source-size change caused the latency
          increase.
        </p>
        <p class="caution">
          Equal source size and equal reported source category form an
          unchanged-source proxy, not proof that source text was identical.
          Different text can have the same character count and category.
          Positive latency change means the later generation took longer;
          negative means it took less time; zero means no captured latency
          change. These associations remain descriptive.
        </p>
      </div>
    </details>
  </section>
  </details>

    <details class="report-section" open>
    <summary id="user-feedback-heading">
      User feedback on AI assistance
    </summary>
    <section aria-labelledby="user-feedback-heading">
    <p>
      These comments are self-reported feedback about the perceived usefulness
      of AI assistance. They are descriptive and do not establish causal
      benefit, writing quality, correctness, accessibility, or effectiveness.
    </p>

    {% if user_feedback_rows %}
    <div class="feedback-table-wrapper" role="region"
         aria-label="User feedback table" tabindex="0">
      <table class="feedback-table">
        <caption>
          Available AI-usefulness feedback ordered by audit record ID
        </caption>
        <thead>
          <tr>
            <th scope="col">Audit record ID</th>
            <th scope="col">User feedback</th>
          </tr>
        </thead>
        <tbody>
          {% for feedback in user_feedback_rows %}
          <tr>
            <td class="feedback-record-id">{{ feedback.audit_record_id }}</td>
            <td class="feedback-text">{{ feedback.feedback_text }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
    <p>No user feedback about AI usefulness was available for this report.</p>
    {% endif %}
  </section>
  </details>

</main>
</body>
</html>
"""


@dataclass(frozen=True, slots=True)
class SourceComparisonView:
    """One faculty-facing completed-path comparison denominator."""

    label: str
    comparable_transition_count: int
    unavailable_transition_count: int
    all_transition_count: int


@dataclass(frozen=True, slots=True)
class SourceContextHtmlContext:
    """Aggregate completed-path counts for source-context explanation."""

    contributing_study_count: int
    transition_count: int
    comparisons: tuple[SourceComparisonView, ...]
    has_repeated_pathways: bool


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


def _source_context_html_context(
    repeated_summary: pd.DataFrame,
) -> SourceContextHtmlContext:
    """Return validated aggregate context for completed-path transitions."""
    required = (
        "summary_grain",
        "comparison_dimension_name",
        "comparison_category",
        "population_unit_count",
        "contributing_study_count",
        "eligible_unit_count",
        "category_unit_count",
    )
    missing_columns = tuple(
        column for column in required if column not in repeated_summary.columns
    )

    if missing_columns:
        raise ExplorationValidationError(
            "repeated_attempt_source_consistency_summary lacks required "
            f"HTML columns: {missing_columns!r}"
        )

    rows = repeated_summary.loc[
        repeated_summary["summary_grain"].eq(
            "COMPLETED_AI_PATH_CONSECUTIVE_SUCCESSFUL_AI_TRANSITION"
        )
    ]
    dimension_labels = (
        ("SOURCE_SIZE", "Source size"),
        ("REPORTED_CONTENT_SOURCE", "Reported content source"),
        ("INPUT_METHOD", "Input method"),
        ("SOURCE_SIGNATURE_PROXY", "Source-signature proxy"),
    )

    if rows.empty:
        return SourceContextHtmlContext(
            contributing_study_count=0,
            transition_count=0,
            comparisons=tuple(
                SourceComparisonView(
                    label=label,
                    comparable_transition_count=0,
                    unavailable_transition_count=0,
                    all_transition_count=0,
                )
                for _, label in dimension_labels
            ),
            has_repeated_pathways=False,
        )

    transition_counts = {int(value) for value in rows["population_unit_count"]}
    study_counts = {int(value) for value in rows["contributing_study_count"]}

    if len(transition_counts) != 1 or len(study_counts) != 1:
        raise ExplorationValidationError(
            "completed-path source summary has inconsistent population counts"
        )

    transition_count = transition_counts.pop()
    study_count = study_counts.pop()
    comparisons: list[SourceComparisonView] = []

    for dimension, label in dimension_labels:
        dimension_rows = rows.loc[rows["comparison_dimension_name"].eq(dimension)]
        categories = {
            str(row["comparison_category"]): row
            for row in dimension_rows.to_dict(orient="records")
        }

        if set(categories) != {
            "SAME",
            "CHANGED",
            "MISSING",
        }:
            raise ExplorationValidationError(
                "completed-path source summary requires SAME, CHANGED, "
                f"and MISSING rows for {dimension!r}"
            )

        same_eligible = int(categories["SAME"]["eligible_unit_count"])
        changed_eligible = int(categories["CHANGED"]["eligible_unit_count"])

        if same_eligible != changed_eligible:
            raise ExplorationValidationError(
                "completed-path source summary has inconsistent comparable "
                f"denominators for {dimension!r}"
            )

        unavailable = int(categories["MISSING"]["category_unit_count"])

        if same_eligible + unavailable != transition_count:
            raise ExplorationValidationError(
                "completed-path source summary comparison counts do not "
                f"reconcile for {dimension!r}"
            )

        comparisons.append(
            SourceComparisonView(
                label=label,
                comparable_transition_count=same_eligible,
                unavailable_transition_count=unavailable,
                all_transition_count=transition_count,
            )
        )

    return SourceContextHtmlContext(
        contributing_study_count=study_count,
        transition_count=transition_count,
        comparisons=tuple(comparisons),
        has_repeated_pathways=transition_count > 0,
    )


def _faculty_summary(
    *,
    overview_summary: pd.DataFrame,
    quality: QualityHtmlContext,
    feedback_rows: tuple[UserFeedbackView, ...],
) -> FacultySummaryView:
    """Return a concise summary from existing report values."""
    rows = _overview_rows_by_name(overview_summary)

    def count(metric_name: str) -> int:
        row = _required_overview_row(rows, metric_name)
        return int(
            _finite_number(
                row["metric_count"],
                value_name=metric_name,
            )
        )

    completed_row = _required_overview_row(
        rows,
        "distinct_completed_study_count",
    )
    completion_percentage = _percentage_text(completed_row["metric_percentage"])

    return FacultySummaryView(
        all_attempt_count=count("all_attempt_count"),
        distinct_study_count=count("distinct_study_count_with_any_attempt"),
        completed_study_count=count("distinct_completed_study_count"),
        completion_percentage_text=(
            completion_percentage
            if completion_percentage is not None
            else "percentage unavailable"
        ),
        completed_ai_count=count("distinct_completed_study_count_final_mode_ai"),
        completed_manual_count=count(
            "distinct_completed_study_count_final_mode_manual"
        ),
        preceding_incomplete_count=count(
            "distinct_completed_study_count_with_preceding_incomplete_attempts"
        ),
        warning_category_count=quality.affected_warning_count,
        warning_category_total=quality.warning_total,
        feedback_count=len(feedback_rows),
    )


@dataclass(frozen=True, slots=True)
class KpiCard:
    """One executive-overview card."""

    label: str
    value: str
    detail: str


@dataclass(frozen=True, slots=True)
class CompletionPathwayCallout:
    """One completed-study pathway callout."""

    label: str
    affected_count: int
    completed_study_count: int
    percentage_text: str
    detail: str


@dataclass(frozen=True, slots=True)
class RetryCardView:
    """One faculty-facing study retry card."""

    label: str
    study_count: int
    percentage_text: str
    median_attempts_text: str
    mode_mix_text: str


@dataclass(frozen=True, slots=True)
class RetryCharacteristicView:
    """One accessible retry-characteristics table row."""

    label: str
    study_count: int
    median_attempts_text: str
    both_modes_text: str
    author_change_text: str
    ai_error_text: str
    returned_result_ai_text: str
    source_change_text: str
    feedback_text: str
    completion_timing_text: str
    observed_activity_span_text: str
    latest_attempt_to_cutoff_text: str
    first_attempt_to_cutoff_text: str


@dataclass(frozen=True, slots=True)
class CompensationFlagView:
    """One completed-AI compensation Boolean comparison."""

    completed_attempt_count: int
    ai_value_count: int
    matched_count: int
    differed_count: int
    final_unavailable_count: int
    matched_percentage_text: str
    differed_percentage_text: str


@dataclass(frozen=True, slots=True)
class CompensationTextView:
    """One generic or specific compensation suggestion summary."""

    label: str
    attempt_count_with_suggestion: int
    offered_count: int
    selected_count: int
    attempt_selection_percentage_text: str


@dataclass(frozen=True, slots=True)
class CompensationCountPairView:
    """One exact generic/specific offer-count combination."""

    population_label: str
    composition_label: str
    generic_count: int
    specific_count: int
    attempt_count: int
    percentage_text: str
    exact_three_plus_three_text: str


@dataclass(frozen=True, slots=True)
class CompensationConsistencyView:
    """One descriptive compensation workflow-consistency check."""

    label: str
    population_label: str
    attempt_count: int
    population_count: int
    percentage_text: str


@dataclass(frozen=True, slots=True)
class UserFeedbackView:
    """One authorized faculty-facing feedback response."""

    audit_record_id: int
    feedback_text: str


@dataclass(frozen=True, slots=True)
class FacultySummaryView:
    """Concise existing metrics for faculty orientation."""

    all_attempt_count: int
    distinct_study_count: int
    completed_study_count: int
    completion_percentage_text: str
    completed_ai_count: int
    completed_manual_count: int
    preceding_incomplete_count: int
    warning_category_count: int
    warning_category_total: int
    feedback_count: int


def _user_feedback_rows(
    records: pd.DataFrame,
) -> tuple[UserFeedbackView, ...]:
    """Return authorized nonblank feedback ordered by audit record ID."""
    required_columns = (
        "ID",
        "USER_FEEDBACK_COMMENTS",
    )
    missing = tuple(
        column for column in required_columns if column not in records.columns
    )

    if missing:
        raise ExplorationValidationError(
            f"records lacks required feedback columns: {missing!r}"
        )

    projected = records.loc[
        :,
        list(required_columns),
    ].copy()
    feedback_text = projected["USER_FEEDBACK_COMMENTS"].astype("string")
    projected["_feedback_trimmed"] = feedback_text.str.strip()
    available = projected.loc[
        projected["USER_FEEDBACK_COMMENTS"].notna()
        & projected["_feedback_trimmed"].notna()
        & projected["_feedback_trimmed"].ne("")
    ].copy()

    if available.empty:
        return ()

    if available["ID"].isna().any():
        raise ExplorationValidationError(
            "feedback-bearing records require an audit record ID"
        )

    try:
        numeric_ids = pd.to_numeric(
            available["ID"],
            errors="raise",
        )
    except (TypeError, ValueError) as error:
        raise ExplorationValidationError(
            "feedback-bearing records require numeric audit record IDs"
        ) from error

    if not numeric_ids.map(lambda value: float(value).is_integer()).all():
        raise ExplorationValidationError(
            "feedback-bearing records require integer audit record IDs"
        )

    available["_audit_record_id"] = numeric_ids.astype("int64")
    available = available.sort_values(
        by=[
            "_audit_record_id",
        ],
        kind="stable",
    )

    return tuple(
        UserFeedbackView(
            audit_record_id=int(row["_audit_record_id"]),
            feedback_text=str(row["USER_FEEDBACK_COMMENTS"]),
        )
        for row in available.to_dict(orient="records")
    )


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


def _overview_rows_by_name(
    overview_summary: pd.DataFrame,
) -> dict[str, dict[str, object]]:
    """Return unique overview rows keyed by metric name."""
    required_columns = (
        "overview_metric_name",
        "overview_metric_label",
        "metric_count",
        "metric_denominator_count",
        "metric_percentage",
    )
    missing = tuple(
        column for column in required_columns if column not in overview_summary.columns
    )

    if missing:
        raise ExplorationValidationError(
            f"overview_summary lacks required HTML columns: {missing!r}"
        )

    rows = cast(
        "list[dict[str, object]]",
        overview_summary.to_dict(orient="records"),
    )
    rows_by_name: dict[str, dict[str, object]] = {}

    for row in rows:
        metric_name = str(row["overview_metric_name"])

        if metric_name in rows_by_name:
            raise ExplorationValidationError(
                f"overview_summary contains duplicate metric {metric_name!r}"
            )

        rows_by_name[metric_name] = row

    return rows_by_name


def _required_overview_row(
    rows_by_name: dict[str, dict[str, object]],
    metric_name: str,
) -> dict[str, object]:
    """Return one required overview row."""
    row = rows_by_name.get(metric_name)

    if row is None:
        raise ExplorationValidationError(
            f"overview_summary lacks required metric {metric_name!r}"
        )

    return row


def _kpi_cards(overview_summary: pd.DataFrame) -> tuple[KpiCard, ...]:
    """Return the six ordered faculty overview KPI cards."""
    rows_by_name = _overview_rows_by_name(overview_summary)
    cards: list[KpiCard] = []

    for metric_name in _KPI_METRICS:
        row = _required_overview_row(rows_by_name, metric_name)
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


def _completion_pathway_callouts(
    overview_summary: pd.DataFrame,
    author_handoff_summary: pd.DataFrame,
) -> tuple[CompletionPathwayCallout, ...]:
    """Return three faculty-facing completed-study pathway callouts."""
    rows_by_name = _overview_rows_by_name(overview_summary)

    for metric_name in _REQUIRED_PATHWAY_METRICS:
        _required_overview_row(rows_by_name, metric_name)

    completed_study_count = int(
        _finite_number(
            rows_by_name["distinct_completed_study_count"]["metric_count"],
            value_name="distinct_completed_study_count",
        )
    )
    preceding_incomplete_count = int(
        _finite_number(
            rows_by_name[
                "distinct_completed_study_count_with_preceding_incomplete_attempts"
            ]["metric_count"],
            value_name=(
                "distinct_completed_study_count_with_preceding_incomplete_attempts"
            ),
        )
    )
    preceding_ai_error_count = int(
        _finite_number(
            rows_by_name[
                "distinct_completed_study_count_with_preceding_ai_error_attempts"
            ]["metric_count"],
            value_name=(
                "distinct_completed_study_count_with_preceding_ai_error_attempts"
            ),
        )
    )
    required_handoff_columns = (
        "completed_attempt_authoring_mode",
        "author_handoff_category",
        "distinct_completed_study_count",
    )
    missing = tuple(
        column
        for column in required_handoff_columns
        if column not in author_handoff_summary.columns
    )

    if missing:
        raise ExplorationValidationError(
            f"author_handoff_summary lacks required HTML columns: {missing!r}"
        )

    handoff_rows = author_handoff_summary.loc[
        author_handoff_summary["completed_attempt_authoring_mode"].isin(
            ("AI", "MANUAL")
        )
        & author_handoff_summary["author_handoff_category"].isin(_HANDOFF_CATEGORIES)
    ]
    handoff_count = sum(
        int(
            _finite_number(
                value,
                value_name="distinct_completed_study_count",
            )
        )
        for value in handoff_rows["distinct_completed_study_count"].tolist()
    )

    def callout(
        *,
        label: str,
        affected_count: int,
        detail: str,
    ) -> CompletionPathwayCallout:
        if affected_count < 0 or affected_count > completed_study_count:
            raise ExplorationValidationError(
                f"{label} count is outside the completed-study population"
            )

        percentage = (
            100.0 * affected_count / completed_study_count
            if completed_study_count
            else 0.0
        )

        return CompletionPathwayCallout(
            label=label,
            affected_count=affected_count,
            completed_study_count=completed_study_count,
            percentage_text=f"{percentage:.1f}%",
            detail=detail,
        )

    return (
        callout(
            label="Completed studies with preceding incomplete attempts",
            affected_count=preceding_incomplete_count,
            detail=(
                "At least one incomplete attempt was ordered before the unique "
                "completed attempt for the same study."
            ),
        ),
        callout(
            label="Completed studies with an author handoff",
            affected_count=handoff_count,
            detail=(
                "At least one preceding attempt was authored by someone other "
                "than the completion author."
            ),
        ),
        callout(
            label="Completed studies with a preceding AI error",
            affected_count=preceding_ai_error_count,
            detail=(
                "At least one AI-error attempt was ordered before the unique "
                "completed attempt for the same study."
            ),
        ),
    )


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


def _aggregate_count(
    value: object,
    *,
    value_name: str,
) -> int:
    """Return one validated nonnegative aggregate count."""
    number = _finite_number(value, value_name=value_name)

    if number < 0 or not number.is_integer():
        raise ExplorationValidationError(
            f"HTML aggregate value {value_name!r} must be a nonnegative integer"
        )

    return int(number)


def _compensation_flag_view(
    summary: pd.DataFrame,
) -> CompensationFlagView | None:
    """Return the completed-AI compensation Boolean comparison."""
    required = (
        "field_name",
        "analysis_type",
        "completed_ai_attempt_count",
        "attempt_count_with_ai_value_selected",
        "attempt_count_final_equal_to_selected",
        "attempt_count_final_different_from_selected",
        "attempt_count_final_missing",
        "final_equal_to_selected_percentage_among_selected",
        "final_different_from_selected_percentage_among_selected",
    )
    missing = [column for column in required if column not in summary.columns]
    if missing:
        raise ExplorationValidationError(
            "nontext_field_adoption_summary lacks required HTML columns: "
            + ", ".join(missing)
        )

    rows = summary.loc[
        summary["field_name"].eq("offersCompensation")
        & summary["analysis_type"].eq("BOOLEAN")
    ]
    if rows.empty:
        return None
    if len(rows) != 1:
        raise ExplorationValidationError(
            "nontext_field_adoption_summary must contain at most one "
            "offersCompensation BOOLEAN row"
        )

    row = rows.iloc[0]
    count_names = (
        ("completed_ai_attempt_count", "completed_attempt_count"),
        ("attempt_count_with_ai_value_selected", "ai_value_count"),
        ("attempt_count_final_equal_to_selected", "matched_count"),
        ("attempt_count_final_different_from_selected", "differed_count"),
        ("attempt_count_final_missing", "final_unavailable_count"),
    )
    counts = {
        output_name: _aggregate_count(row[column], value_name=column)
        for column, output_name in count_names
    }

    return CompensationFlagView(
        **counts,
        matched_percentage_text=(
            _percentage_text(row["final_equal_to_selected_percentage_among_selected"])
            or "\\N"
        ),
        differed_percentage_text=(
            _percentage_text(
                row["final_different_from_selected_percentage_among_selected"]
            )
            or "\\N"
        ),
    )


def _compensation_text_views(
    summary: pd.DataFrame,
) -> tuple[CompensationTextView, ...]:
    """Return generic and specific completed-AI compensation summaries."""
    required = (
        "compensation_suggestion_kind",
        "completed_ai_attempt_count_with_suggestion",
        "offered_suggestion_count",
        "selected_suggestion_count",
        "suggestion_selection_percentage",
    )
    missing = [column for column in required if column not in summary.columns]
    if missing:
        raise ExplorationValidationError(
            "compensation_analysis_summary lacks required HTML columns: "
            + ", ".join(missing)
        )

    labels = {
        "genericCompensation": "Generic compensation",
        "specificCompensation": "Specific compensation",
    }
    kinds = summary["compensation_suggestion_kind"].astype("string")
    unknown = sorted(set(kinds.dropna().astype(str)) - set(labels))

    if unknown:
        raise ExplorationValidationError(
            "compensation_analysis_summary contains unsupported suggestion "
            "kinds: " + ", ".join(unknown)
        )

    if kinds.duplicated(keep=False).any():
        raise ExplorationValidationError(
            "compensation_analysis_summary must contain at most one row per "
            "suggestion kind"
        )

    rows_by_kind = {
        str(row["compensation_suggestion_kind"]): row
        for row in summary.to_dict(orient="records")
    }
    views: list[CompensationTextView] = []
    for kind, label in labels.items():
        row = rows_by_kind.get(kind)
        if row is None:
            continue

        offered_attempt_count = _aggregate_count(
            row["completed_ai_attempt_count_with_suggestion"],
            value_name="completed_ai_attempt_count_with_suggestion",
        )
        offered_instance_count = _aggregate_count(
            row["offered_suggestion_count"],
            value_name="offered_suggestion_count",
        )
        selected_attempt_count = _aggregate_count(
            row["selected_suggestion_count"],
            value_name="selected_suggestion_count",
        )
        attempt_selection_percentage_text = (
            f"{100.0 * selected_attempt_count / offered_attempt_count:.1f}%"
            if offered_attempt_count > 0
            else "\\N"
        )
        views.append(
            CompensationTextView(
                label=label,
                attempt_count_with_suggestion=offered_attempt_count,
                offered_count=offered_instance_count,
                selected_count=selected_attempt_count,
                attempt_selection_percentage_text=(attempt_selection_percentage_text),
            )
        )
    return tuple(views)


_COMPENSATION_POPULATION_LABELS = {
    "ALL_COMPLETED_AI_ATTEMPTS": "All completed AI attempts",
    "FINAL_COMPENSATION_YES": "Final compensation Yes",
    "AI_VALUE_AVAILABLE_COMPLETED_AI_ATTEMPTS": (
        "Completed AI attempts with an AI-supplied Yes/No value"
    ),
}
_COMPENSATION_COMPOSITION_LABELS = {
    "BOTH_KINDS": "Both generic and specific",
    "GENERIC_ONLY": "Generic only",
    "SPECIFIC_ONLY": "Specific only",
    "NEITHER": "Neither kind",
}
_COMPENSATION_CONSISTENCY_LABELS = {
    "AI_NO_WITH_TEXT_OFFERS": "AI supplied No but text suggestions were offered",
    "AI_YES_WITH_NO_TEXT_OFFERS": (
        "AI supplied Yes but no text suggestions were offered"
    ),
    "FINAL_YES_WITH_NO_TEXT_OFFERS": "Final Yes with no text suggestions offered",
    "FINAL_YES_WITH_ONE_KIND_ONLY": "Final Yes with only one suggestion kind offered",
    "FINAL_YES_WITH_NON_3_PLUS_3": "Final Yes without exactly 3 generic and 3 specific",
}


def _embedded_compensation_html_rows(
    summary: pd.DataFrame,
    *,
    column_name: str,
) -> list[dict[str, object]]:
    """Return one validated embedded aggregate copied across kind rows."""
    if column_name not in summary.columns:
        return []

    payloads = summary[column_name].dropna().astype(str).unique()

    if len(payloads) == 0:
        return []

    if len(payloads) != 1:
        raise ExplorationValidationError(
            f"compensation_analysis_summary must contain one consistent "
            f"{column_name} payload"
        )

    try:
        decoded = json.loads(str(payloads[0]))
    except json.JSONDecodeError as error:
        raise ExplorationValidationError(
            f"compensation_analysis_summary contains invalid {column_name}"
        ) from error

    if not isinstance(decoded, list) or any(
        not isinstance(row, dict) for row in decoded
    ):
        raise ExplorationValidationError(
            f"compensation_analysis_summary {column_name} must contain "
            "a JSON list of objects"
        )

    return decoded


def _boolean_yes_no(
    value: object,
    *,
    value_name: str,
) -> str:
    """Return Yes or No for a required Boolean aggregate."""
    if isinstance(value, bool):
        return "Yes" if value else "No"

    raise ExplorationValidationError(
        f"embedded compensation {value_name} must contain a Boolean"
    )


def _compensation_count_pair_views(
    summary: pd.DataFrame,
) -> tuple[CompensationCountPairView, ...]:
    """Return exact offer-count combinations for both populations."""
    rows = _embedded_compensation_html_rows(
        summary,
        column_name="offer_count_pair_summary_json",
    )
    views: list[CompensationCountPairView] = []

    for row in rows:
        population = str(row.get("population_name"))
        composition = str(row.get("offer_composition_category"))

        if population not in _COMPENSATION_POPULATION_LABELS:
            raise ExplorationValidationError(
                "embedded compensation count pairs contain an unsupported population"
            )

        if composition not in _COMPENSATION_COMPOSITION_LABELS:
            raise ExplorationValidationError(
                "embedded compensation count pairs contain an unsupported category"
            )

        views.append(
            CompensationCountPairView(
                population_label=_COMPENSATION_POPULATION_LABELS[population],
                composition_label=_COMPENSATION_COMPOSITION_LABELS[composition],
                generic_count=_aggregate_count(
                    row.get("generic_suggestion_count"),
                    value_name="generic_suggestion_count",
                ),
                specific_count=_aggregate_count(
                    row.get("specific_suggestion_count"),
                    value_name="specific_suggestion_count",
                ),
                attempt_count=_aggregate_count(
                    row.get("attempt_count"),
                    value_name="attempt_count",
                ),
                percentage_text=(
                    _percentage_text(row.get("attempt_percentage")) or "\\N"
                ),
                exact_three_plus_three_text=_boolean_yes_no(
                    row.get("is_exact_three_plus_three"),
                    value_name="is_exact_three_plus_three",
                ),
            )
        )

    return tuple(views)


def _compensation_consistency_views(
    summary: pd.DataFrame,
) -> tuple[CompensationConsistencyView, ...]:
    """Return descriptive workflow-consistency checks with denominators."""
    rows = _embedded_compensation_html_rows(
        summary,
        column_name="workflow_consistency_summary_json",
    )
    views: list[CompensationConsistencyView] = []

    for row in rows:
        population = str(row.get("population_name"))
        category = str(row.get("consistency_category"))

        if population not in _COMPENSATION_POPULATION_LABELS:
            raise ExplorationValidationError(
                "embedded compensation consistency contains an unsupported population"
            )

        if category not in _COMPENSATION_CONSISTENCY_LABELS:
            raise ExplorationValidationError(
                "embedded compensation consistency contains an unsupported category"
            )

        views.append(
            CompensationConsistencyView(
                label=_COMPENSATION_CONSISTENCY_LABELS[category],
                population_label=_COMPENSATION_POPULATION_LABELS[population],
                attempt_count=_aggregate_count(
                    row.get("attempt_count"),
                    value_name="attempt_count",
                ),
                population_count=_aggregate_count(
                    row.get("population_attempt_count"),
                    value_name="population_attempt_count",
                ),
                percentage_text=(
                    _percentage_text(row.get("attempt_percentage")) or "\\N"
                ),
            )
        )

    return tuple(views)


def _empty_nontext_summary() -> pd.DataFrame:
    """Return canonical columns consumed by compensation HTML."""
    return pd.DataFrame(
        columns=[
            "field_name",
            "analysis_type",
            "completed_ai_attempt_count",
            "attempt_count_with_ai_value_selected",
            "attempt_count_final_equal_to_selected",
            "attempt_count_final_different_from_selected",
            "attempt_count_final_missing",
            "final_equal_to_selected_percentage_among_selected",
            "final_different_from_selected_percentage_among_selected",
        ]
    )


def _empty_compensation_summary() -> pd.DataFrame:
    """Return canonical compensation text-summary columns."""
    return pd.DataFrame(
        columns=[
            "compensation_suggestion_kind",
            "completed_ai_attempt_count_with_suggestion",
            "offered_suggestion_count",
            "selected_suggestion_count",
            "suggestion_selection_percentage",
            "offer_composition_summary_json",
            "offer_count_pair_summary_json",
            "workflow_consistency_summary_json",
        ]
    )


def _nullable_number_text(
    value: object,
    *,
    suffix: str = "",
) -> str:
    """Return one faculty-facing number or unavailable marker."""
    if value is None or value is pd.NA or value is pd.NaT:
        return "\\N"

    if isinstance(value, float) and math.isnan(value):
        return "\\N"

    number = _finite_number(value, value_name="retry aggregate")
    rendered = f"{number:,.1f}" if not number.is_integer() else f"{int(number):,}"

    return f"{rendered}{suffix}"


def _retry_cards(
    summary: pd.DataFrame,
) -> tuple[RetryCardView, ...]:
    """Return four cards from identifier-free study-level aggregates."""
    required = (
        "retry_card_group",
        "study_count",
        "population_study_count",
        "study_percentage",
        "median_attempt_count",
        "ai_only_study_count",
        "manual_only_study_count",
        "both_modes_study_count",
    )
    missing = tuple(column for column in required if column not in summary.columns)

    if missing:
        raise ExplorationValidationError(
            f"retry_card_summary lacks required HTML columns: {missing!r}"
        )

    labels = {
        "SINGLE_ATTEMPT_COMPLETED": "One recorded attempt, completed",
        "MULTIPLE_ATTEMPTS_COMPLETED": ("Multiple recorded attempts, completed"),
        "SINGLE_ATTEMPT_NO_COMPLETION_OBSERVED": (
            "One recorded attempt, no completion observed"
        ),
        "MULTIPLE_ATTEMPTS_NO_COMPLETION_OBSERVED": (
            "Multiple recorded attempts, no completion observed"
        ),
    }
    cards: list[RetryCardView] = []

    for row in summary.to_dict(orient="records"):
        group_name = str(row["retry_card_group"])
        mode_mix = (
            f"AI-only: {_nullable_number_text(row['ai_only_study_count'])}; "
            f"manual-only: "
            f"{_nullable_number_text(row['manual_only_study_count'])}; "
            f"both modes: "
            f"{_nullable_number_text(row['both_modes_study_count'])}."
        )
        cards.append(
            RetryCardView(
                label=labels.get(group_name, group_name),
                study_count=int(
                    _finite_number(
                        row["study_count"],
                        value_name="study_count",
                    )
                ),
                percentage_text=_nullable_number_text(
                    row["study_percentage"],
                    suffix="%",
                ),
                median_attempts_text=_nullable_number_text(row["median_attempt_count"]),
                mode_mix_text=mode_mix,
            )
        )

    return tuple(cards)


def _percentage_with_denominator(
    percentage: object,
    denominator: object,
) -> str:
    """Return percentage plus its explicit denominator."""
    return (
        f"{_nullable_number_text(percentage, suffix='%')} "
        f"(n={_nullable_number_text(denominator)})"
    )


def _retry_characteristic_views(
    summary: pd.DataFrame,
) -> tuple[RetryCharacteristicView, ...]:
    """Return validated rows for the accessible retry table."""
    required = (
        "study_outcome_group",
        "study_count",
        "median_attempt_count",
        "percentage_with_both_modes",
        "percentage_with_author_change",
        "percentage_with_ai_error",
        "percentage_with_returned_result_ai",
        "source_comparison_eligible_study_count",
        "percentage_with_source_signature_change_among_eligible",
        "ai_exposed_study_count",
        "percentage_with_feedback_recorded_among_ai_exposed",
        "median_minutes_first_to_completion",
        "median_minutes_first_to_last_observed_attempt",
        "study_count_with_report_run_cutoff",
        "median_minutes_latest_attempt_to_report_run_cutoff",
        "median_minutes_first_attempt_to_report_run_cutoff",
    )
    missing = tuple(column for column in required if column not in summary.columns)

    if missing:
        raise ExplorationValidationError(
            f"retry_characteristics_summary lacks required HTML columns: {missing!r}"
        )

    labels = {
        "COMPLETED_AI": "Completed with AI",
        "COMPLETED_MANUAL": "Completed manually",
        "NO_COMPLETION_OBSERVED": "No completion observed",
    }
    views: list[RetryCharacteristicView] = []

    for row in summary.to_dict(orient="records"):
        group = str(row["study_outcome_group"])
        study_count = int(_finite_number(row["study_count"], value_name="study_count"))
        is_unresolved = group == "NO_COMPLETION_OBSERVED"
        completion_timing = (
            None if is_unresolved else row["median_minutes_first_to_completion"]
        )
        observed_activity_span = (
            row["median_minutes_first_to_last_observed_attempt"]
            if is_unresolved
            else None
        )
        latest_to_cutoff = (
            row["median_minutes_latest_attempt_to_report_run_cutoff"]
            if is_unresolved
            else None
        )
        first_to_cutoff = (
            row["median_minutes_first_attempt_to_report_run_cutoff"]
            if is_unresolved
            else None
        )
        cutoff_count = row["study_count_with_report_run_cutoff"]

        views.append(
            RetryCharacteristicView(
                label=labels.get(group, group),
                study_count=study_count,
                median_attempts_text=_nullable_number_text(row["median_attempt_count"]),
                both_modes_text=_percentage_with_denominator(
                    row["percentage_with_both_modes"],
                    study_count,
                ),
                author_change_text=_percentage_with_denominator(
                    row["percentage_with_author_change"],
                    study_count,
                ),
                ai_error_text=_percentage_with_denominator(
                    row["percentage_with_ai_error"],
                    study_count,
                ),
                returned_result_ai_text=_percentage_with_denominator(
                    row["percentage_with_returned_result_ai"],
                    study_count,
                ),
                source_change_text=_percentage_with_denominator(
                    row["percentage_with_source_signature_change_among_eligible"],
                    row["source_comparison_eligible_study_count"],
                ),
                feedback_text=_percentage_with_denominator(
                    row["percentage_with_feedback_recorded_among_ai_exposed"],
                    row["ai_exposed_study_count"],
                ),
                completion_timing_text=_nullable_number_text(
                    completion_timing,
                    suffix=" minutes",
                ),
                observed_activity_span_text=_nullable_number_text(
                    observed_activity_span,
                    suffix=" minutes",
                ),
                latest_attempt_to_cutoff_text=(
                    _nullable_number_text(
                        latest_to_cutoff,
                        suffix=" minutes",
                    )
                    + " (n="
                    + _nullable_number_text(cutoff_count)
                    + ")"
                ),
                first_attempt_to_cutoff_text=(
                    _nullable_number_text(
                        first_to_cutoff,
                        suffix=" minutes",
                    )
                    + " (n="
                    + _nullable_number_text(cutoff_count)
                    + ")"
                ),
            )
        )

    return tuple(views)


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


def render_html_report(  # noqa: PLR0913
    *,
    records: pd.DataFrame,
    overview_summary: pd.DataFrame,
    author_handoff_summary: pd.DataFrame,
    retry_card_summary: pd.DataFrame,
    retry_characteristics_summary: pd.DataFrame,
    data_quality_summary: pd.DataFrame,
    repeated_attempt_source_consistency_summary: pd.DataFrame,
    charts: ExplorationCharts,
    nontext_field_adoption_summary: pd.DataFrame | None = None,
    compensation_analysis_summary: pd.DataFrame | None = None,
) -> str:
    """Return one self-contained faculty-facing HTML report."""
    environment = Environment(
        loader=BaseLoader(),
        autoescape=True,
        undefined=StrictUndefined,
    )
    template = environment.from_string(_TEMPLATE)
    quality = _quality_html_context(data_quality_summary)
    feedback_rows = _user_feedback_rows(records)
    source_context = _source_context_html_context(
        repeated_attempt_source_consistency_summary
    )
    compensation_flag = _compensation_flag_view(
        _empty_nontext_summary()
        if nontext_field_adoption_summary is None
        else nontext_field_adoption_summary
    )
    compensation_text_rows = _compensation_text_views(
        _empty_compensation_summary()
        if compensation_analysis_summary is None
        else compensation_analysis_summary
    )

    return template.render(
        title=_REPORT_TITLE,
        compensation_flag=compensation_flag,
        compensation_text_rows=compensation_text_rows,
        compensation_count_pair_rows=_compensation_count_pair_views(
            _empty_compensation_summary()
            if compensation_analysis_summary is None
            else compensation_analysis_summary
        ),
        compensation_consistency_rows=_compensation_consistency_views(
            _empty_compensation_summary()
            if compensation_analysis_summary is None
            else compensation_analysis_summary
        ),
        user_feedback_rows=feedback_rows,
        source_context=source_context,
        faculty_summary=_faculty_summary(
            overview_summary=overview_summary,
            quality=quality,
            feedback_rows=feedback_rows,
        ),
        kpi_cards=_kpi_cards(overview_summary),
        pathway_callouts=_completion_pathway_callouts(
            overview_summary,
            author_handoff_summary,
        ),
        retry_cards=_retry_cards(retry_card_summary),
        retry_characteristics=_retry_characteristic_views(
            retry_characteristics_summary
        ),
        retry_pathways_html=_figure_html(
            charts.retry_pathways,
            include_plotlyjs=False,
        ),
        quality_fatal_passed=quality.fatal_passed,
        quality_fatal_total=quality.fatal_total,
        quality_affected_warning_count=quality.affected_warning_count,
        quality_warning_total=quality.warning_total,
        quality_warning_occurrences=quality.warning_occurrences,
        quality_warning_rows=quality.warning_rows,
        quality_zero_warning_messages=quality.zero_warning_messages,
        study_pathways_html=_figure_html(
            charts.study_completion_pathways,
            include_plotlyjs=False,
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
        compensation_suggestion_use_html=_figure_html(
            charts.compensation_suggestion_use,
            include_plotlyjs=False,
        ),
        compensation_offer_composition_all_html=_figure_html(
            charts.compensation_offer_composition_all,
            include_plotlyjs=False,
        ),
        compensation_offer_composition_final_yes_html=_figure_html(
            charts.compensation_offer_composition_final_yes,
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
            include_plotlyjs=True,
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
        returned_result_input_method_html=_figure_html(
            charts.returned_result_input_method_preference,
            include_plotlyjs=False,
        ),
        returned_result_source_size_latency_html=_figure_html(
            charts.returned_result_source_size_latency,
            include_plotlyjs=False,
        ),
        completed_ai_input_method_html=_figure_html(
            charts.completed_ai_input_method_preference,
            include_plotlyjs=False,
        ),
        completed_ai_source_size_latency_html=_figure_html(
            charts.completed_ai_source_size_latency,
            include_plotlyjs=False,
        ),
        repeated_source_consistency_html=_figure_html(
            charts.repeated_attempt_source_consistency,
            include_plotlyjs=False,
        ),
    )


def write_html_report(  # noqa: PLR0913
    path: Path,
    *,
    records: pd.DataFrame,
    overview_summary: pd.DataFrame,
    author_handoff_summary: pd.DataFrame,
    retry_card_summary: pd.DataFrame,
    retry_characteristics_summary: pd.DataFrame,
    data_quality_summary: pd.DataFrame,
    repeated_attempt_source_consistency_summary: pd.DataFrame,
    charts: ExplorationCharts,
    nontext_field_adoption_summary: pd.DataFrame | None = None,
    compensation_analysis_summary: pd.DataFrame | None = None,
) -> None:
    """Write one self-contained HTML report."""
    try:
        path.write_text(
            render_html_report(
                records=records,
                overview_summary=overview_summary,
                author_handoff_summary=author_handoff_summary,
                retry_card_summary=retry_card_summary,
                retry_characteristics_summary=(retry_characteristics_summary),
                data_quality_summary=data_quality_summary,
                repeated_attempt_source_consistency_summary=(
                    repeated_attempt_source_consistency_summary
                ),
                charts=charts,
                nontext_field_adoption_summary=nontext_field_adoption_summary,
                compensation_analysis_summary=compensation_analysis_summary,
            ),
            encoding="utf-8",
        )
    except OSError as error:
        raise ExplorationInputError(
            f"Could not write exploration HTML report: {error}"
        ) from error
