from __future__ import annotations

import html

from rag_observatory.taxonomy.failure_modes import classify_trace, get_failure_mode_definition
from rag_observatory.trace.schema import ContextChunk, Document, FailureLabel, Metric, RagTrace


def render_html_report(
    trace: RagTrace,
    failure_labels: list[FailureLabel] | None = None,
) -> str:
    labels = failure_labels if failure_labels is not None else classify_trace(trace)
    title = "RAG Diagnostic Report"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_escape(title)} - {_escape(trace.metadata.run_id)}</title>
  <style>
{_style_sheet()}
  </style>
</head>
<body>
  <main class="report">
    <header class="hero">
      <p class="eyebrow">Trace-based RAG failure analysis</p>
      <h1>{_escape(title)}</h1>
      <p class="lede">{_escape(_likely_failure_source(labels))}</p>
      {_summary_grid(trace, labels)}
    </header>
    {_run_section(trace)}
    {_query_section(trace)}
    {_answer_section(trace)}
    {_documents_section("Retrieved Documents", trace.retrieved_documents)}
    {_documents_section("Reranked Documents", trace.reranked_documents) if trace.reranked_documents else ""}
    {_context_section(trace.selected_context)}
    {_metrics_section(trace.metrics)}
    {_failure_section(labels)}
    {_inspect_next_section(labels)}
  </main>
</body>
</html>
"""


def render_report_screenshot_svg(
    trace: RagTrace,
    failure_labels: list[FailureLabel] | None = None,
) -> str:
    labels = failure_labels if failure_labels is not None else classify_trace(trace)
    modes = [label.mode for label in labels] or ["no_failure_labels"]
    mode_lines = [_truncate(mode.replace("_", " "), 28) for mode in modes[:6]]
    mode_text = "\n".join(
        f'<text x="88" y="{370 + index * 34}" class="mode">{_escape(mode)}</text>'
        for index, mode in enumerate(mode_lines)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="780" viewBox="0 0 1200 780" role="img" aria-labelledby="title desc">
  <title id="title">RAG diagnostic report preview</title>
  <desc id="desc">Deterministic SVG preview for a trace-based RAG diagnostic report.</desc>
  <style>
    .bg {{ fill: #f7f5ef; }}
    .panel {{ fill: #fffdf8; stroke: #d8d1c2; stroke-width: 2; }}
    .title {{ fill: #14231f; font: 700 44px system-ui, sans-serif; }}
    .label {{ fill: #6d5f4c; font: 600 18px system-ui, sans-serif; }}
    .text {{ fill: #26332f; font: 22px system-ui, sans-serif; }}
    .small {{ fill: #46544e; font: 18px system-ui, sans-serif; }}
    .mode {{ fill: #682c22; font: 700 24px system-ui, sans-serif; }}
    .chip {{ fill: #f5ded8; stroke: #d6a398; }}
    .stage {{ fill: #18473b; font: 700 19px system-ui, sans-serif; }}
  </style>
  <rect width="1200" height="780" class="bg"/>
  <rect x="44" y="44" width="1112" height="692" rx="18" class="panel"/>
  <text x="88" y="122" class="label">Trace-based RAG failure analysis</text>
  <text x="88" y="182" class="title">RAG Diagnostic Report</text>
  <text x="88" y="238" class="text">{_escape(_truncate(trace.query.text, 82))}</text>
  <text x="88" y="292" class="label">Failure modes</text>
  <rect x="76" y="322" width="456" height="242" rx="14" class="chip"/>
  {mode_text}
  <text x="592" y="292" class="label">Pipeline stages</text>
  <text x="592" y="342" class="stage">retrieval</text>
  <text x="592" y="382" class="stage">reranking</text>
  <text x="592" y="422" class="stage">context selection</text>
  <text x="592" y="462" class="stage">generation</text>
  <text x="592" y="502" class="stage">evaluation</text>
  <text x="88" y="628" class="label">Likely source</text>
  <text x="88" y="668" class="small">{_escape(_truncate(_likely_failure_source(labels), 102))}</text>
  <text x="88" y="706" class="small">Run: {_escape(_truncate(trace.metadata.run_id, 74))}</text>
</svg>
"""


def _summary_grid(trace: RagTrace, labels: list[FailureLabel]) -> str:
    rows = [
        ("Run ID", trace.metadata.run_id),
        ("Dataset", trace.metadata.dataset or "not recorded"),
        ("Failure labels", str(len(labels))),
        ("Metrics", str(len(trace.metrics))),
    ]
    cards = "\n".join(
        f"""<div class="summary-card">
        <span>{_escape(label)}</span>
        <strong>{_escape(value)}</strong>
      </div>"""
        for label, value in rows
    )
    return f'<div class="summary-grid">{cards}</div>'


def _run_section(trace: RagTrace) -> str:
    metadata = trace.metadata
    rows = [
        ("Timestamp", metadata.timestamp),
        ("Retriever", metadata.retriever or "not recorded"),
        ("Reranker", metadata.reranker or "not used"),
        ("Generator", metadata.generator or "not recorded"),
        ("Evaluator", metadata.evaluator or "not recorded"),
    ]
    return _definition_section("Run", rows)


def _query_section(trace: RagTrace) -> str:
    rows = [
        ("Query ID", trace.query.query_id),
        ("Text", trace.query.text),
        ("Gold answer", trace.query.gold_answer or "not recorded"),
    ]
    return _definition_section("Query", rows)


def _answer_section(trace: RagTrace) -> str:
    citations = ", ".join(citation.doc_id for citation in trace.answer.citations) or "none"
    return f"""<section>
      <h2>Generated Answer</h2>
      <p class="answer">{_escape(trace.answer.text)}</p>
      <p class="meta"><strong>Citations:</strong> {_escape(citations)}</p>
    </section>"""


def _documents_section(title: str, documents: list[Document]) -> str:
    if not documents:
        return f"""<section>
      <h2>{_escape(title)}</h2>
      <p class="muted">No documents recorded.</p>
    </section>"""
    rows = "\n".join(_document_row(document) for document in documents)
    return f"""<section>
      <h2>{_escape(title)}</h2>
      <table>
        <thead><tr><th>Rank</th><th>Document</th><th>Score</th><th>Relevant</th><th>Snippet</th></tr></thead>
        <tbody>
{rows}
        </tbody>
      </table>
    </section>"""


def _document_row(document: Document) -> str:
    score = f"{document.score:.4f}" if document.score is not None else ""
    rank = "" if document.rank is None else str(document.rank)
    title = document.title or document.doc_id
    return f"""          <tr>
            <td>{_escape(rank)}</td>
            <td><code>{_escape(title)}</code></td>
            <td>{_escape(score)}</td>
            <td>{_format_bool(document.is_relevant)}</td>
            <td>{_escape(_truncate(document.text, 150))}</td>
          </tr>"""


def _context_section(chunks: list[ContextChunk]) -> str:
    if not chunks:
        return """<section>
      <h2>Selected Context</h2>
      <p class="muted">No context chunks selected.</p>
    </section>"""
    items = "\n".join(
        f"""        <li>
          <strong>{_escape(chunk.context_id)}</strong>
          <span>from <code>{_escape(chunk.doc_id)}</code></span>
          <p>{_escape(_truncate(chunk.text, 220))}</p>
        </li>"""
        for chunk in chunks
    )
    return f"""<section>
      <h2>Selected Context</h2>
      <ol class="context-list">
{items}
      </ol>
    </section>"""


def _metrics_section(metrics: list[Metric]) -> str:
    if not metrics:
        return """<section>
      <h2>Evaluation Signals</h2>
      <p class="muted">No metric outputs recorded.</p>
    </section>"""
    rows = "\n".join(
        f"""          <tr>
            <td><code>{_escape(metric.name)}</code></td>
            <td>{_escape(str(metric.value))}</td>
            <td>{_format_bool(metric.passed)}</td>
            <td>{_escape(metric.notes or "")}</td>
          </tr>"""
        for metric in metrics
    )
    return f"""<section>
      <h2>Evaluation Signals</h2>
      <table>
        <thead><tr><th>Metric</th><th>Value</th><th>Passed</th><th>Notes</th></tr></thead>
        <tbody>
{rows}
        </tbody>
      </table>
    </section>"""


def _failure_section(labels: list[FailureLabel]) -> str:
    if not labels:
        return """<section>
      <h2>Failure Modes</h2>
      <p class="muted">No failure labels assigned.</p>
    </section>"""
    chips = "\n".join(
        f"""        <li class="failure-chip">
          <strong>{_escape(label.mode)}</strong>
          <span>{_escape(label.severity)} - {_escape(label.detection_method)}</span>
          <p>{_escape(label.rationale or label.evidence or "")}</p>
        </li>"""
        for label in labels
    )
    return f"""<section>
      <h2>Failure Modes</h2>
      <ul class="failure-list">
{chips}
      </ul>
    </section>"""


def _inspect_next_section(labels: list[FailureLabel]) -> str:
    if not labels:
        hints = ["Confirm whether the trace has complete metric and citation outputs."]
    else:
        hints = [
            f"{label.mode}: {get_failure_mode_definition(label.mode).limitations}"
            for label in labels
        ]
    items = "\n".join(f"        <li>{_escape(hint)}</li>" for hint in hints)
    return f"""<section>
      <h2>Inspect Next</h2>
      <ul>
{items}
      </ul>
    </section>"""


def _definition_section(title: str, rows: list[tuple[str, str]]) -> str:
    items = "\n".join(
        f"""        <div>
          <dt>{_escape(label)}</dt>
          <dd>{_escape(value)}</dd>
        </div>"""
        for label, value in rows
    )
    return f"""<section>
      <h2>{_escape(title)}</h2>
      <dl class="definition-grid">
{items}
      </dl>
    </section>"""


def _likely_failure_source(labels: list[FailureLabel]) -> str:
    if not labels:
        return "No likely failure source identified from the current trace."
    priority = (
        ("retrieval_miss", "Retrieval failed to surface necessary evidence."),
        ("reranking_error", "Reranking likely promoted weaker evidence."),
        ("context_truncation", "Context selection likely dropped necessary evidence."),
        ("context_pollution", "Context selection introduced distracting evidence."),
        ("unsupported_answer", "Generation produced claims not supported by selected context."),
        ("wrong_citation", "Evidence attribution appears incorrect."),
        ("metric_disagreement", "Evaluation signals need calibration review."),
    )
    modes = {label.mode for label in labels}
    for mode, message in priority:
        if mode in modes:
            return message
    return "Failure labels are present, but no source mapping is available."


def _format_bool(value: bool | None) -> str:
    if value is None:
        return "not recorded"
    return "yes" if value else "no"


def _truncate(value: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _style_sheet() -> str:
    return """    :root {
      color-scheme: light;
      --bg: #f7f5ef;
      --panel: #fffdf8;
      --ink: #17231f;
      --muted: #5e6c66;
      --line: #d8d1c2;
      --green: #1d5b4c;
      --red: #7a3328;
      --red-bg: #f5ded8;
      --gold-bg: #f1e7c8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 16px;
      line-height: 1.5;
    }
    .report {
      margin: 0 auto;
      max-width: 1120px;
      padding: 32px;
    }
    .hero, section {
      background: var(--panel);
      border: 1px solid var(--line);
      margin: 0 0 18px;
      padding: 24px;
    }
    .eyebrow {
      color: var(--green);
      font-weight: 700;
      margin: 0 0 8px;
    }
    h1, h2 {
      line-height: 1.15;
      margin: 0 0 16px;
    }
    h1 { font-size: 40px; }
    h2 { font-size: 24px; }
    .lede {
      color: var(--muted);
      font-size: 19px;
      margin: 0 0 22px;
      max-width: 760px;
    }
    .summary-grid, .definition-grid {
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    }
    .summary-card {
      background: var(--gold-bg);
      border: 1px solid #d7c690;
      padding: 14px;
    }
    .summary-card span, dt {
      color: var(--muted);
      display: block;
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
    }
    .summary-card strong, dd {
      display: block;
      font-size: 18px;
      font-weight: 700;
      margin: 4px 0 0;
      overflow-wrap: anywhere;
    }
    table {
      border-collapse: collapse;
      width: 100%;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 10px;
      text-align: left;
      vertical-align: top;
    }
    th {
      color: var(--muted);
      font-size: 13px;
      text-transform: uppercase;
    }
    code {
      background: #edf2ef;
      padding: 2px 5px;
    }
    .answer {
      font-size: 19px;
    }
    .meta, .muted {
      color: var(--muted);
    }
    .context-list, .failure-list {
      display: grid;
      gap: 12px;
      list-style: none;
      margin: 0;
      padding: 0;
    }
    .context-list li, .failure-chip {
      border: 1px solid var(--line);
      padding: 14px;
    }
    .failure-chip {
      background: var(--red-bg);
      border-color: #d6a398;
    }
    .failure-chip strong {
      color: var(--red);
      display: block;
      margin-bottom: 4px;
    }
    @media (max-width: 720px) {
      .report { padding: 16px; }
      .hero, section { padding: 18px; }
      h1 { font-size: 32px; }
      table { display: block; overflow-x: auto; }
    }"""
