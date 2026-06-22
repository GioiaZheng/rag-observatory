from __future__ import annotations

from rag_observatory.taxonomy.failure_modes import (
    FailureModeDefinition,
    classify_trace,
    get_failure_mode_definition,
)
from rag_observatory.trace.schema import Document, FailureLabel, RagTrace


def render_markdown_report(
    trace: RagTrace,
    failure_labels: list[FailureLabel] | None = None,
) -> str:
    labels = failure_labels if failure_labels is not None else classify_trace(trace)
    lines: list[str] = []

    lines.append("# RAG Diagnostic Report")
    lines.append("")
    lines.extend(_run_section(trace))
    lines.extend(_query_section(trace))
    lines.extend(_answer_section(trace))
    lines.extend(_documents_section("Retrieved Documents", trace.retrieved_documents))
    if trace.reranked_documents:
        lines.extend(_documents_section("Reranked Documents", trace.reranked_documents))
    lines.extend(_context_section(trace))
    lines.extend(_citations_section(trace))
    lines.extend(_metrics_section(trace))
    lines.extend(_failures_section(labels))
    lines.extend(_likely_source_section(labels))
    lines.extend(_inspect_next_section(labels))
    if trace.diagnostic_notes:
        lines.extend(_notes_section(trace))

    return "\n".join(lines).rstrip() + "\n"


def _run_section(trace: RagTrace) -> list[str]:
    metadata = trace.metadata
    rows = [
        ("Run ID", metadata.run_id),
        ("Timestamp", metadata.timestamp),
        ("Dataset", metadata.dataset or "not recorded"),
        ("Retriever", metadata.retriever or "not recorded"),
        ("Reranker", metadata.reranker or "not used"),
        ("Generator", metadata.generator or "not recorded"),
        ("Evaluator", metadata.evaluator or "not recorded"),
    ]
    lines = ["## Run", ""]
    for key, value in rows:
        lines.append(f"- **{key}:** {_clean(value)}")
    lines.append("")
    return lines


def _query_section(trace: RagTrace) -> list[str]:
    lines = [
        "## Query",
        "",
        f"- **Query ID:** {_clean(trace.query.query_id)}",
        f"- **Text:** {_clean(trace.query.text)}",
    ]
    if trace.query.gold_answer:
        lines.append(f"- **Gold answer:** {_clean(trace.query.gold_answer)}")
    lines.append("")
    return lines


def _answer_section(trace: RagTrace) -> list[str]:
    return ["## Generated Answer", "", _clean(trace.answer.text), ""]


def _documents_section(title: str, documents: list[Document]) -> list[str]:
    lines = [f"## {title}", ""]
    if not documents:
        lines.append("No documents recorded.")
        lines.append("")
        return lines

    lines.append("| Rank | Document | Score | Relevant | Snippet |")
    lines.append("| --- | --- | ---: | --- | --- |")
    for index, doc in enumerate(documents, start=1):
        rank = doc.rank if doc.rank is not None else index
        title_text = doc.title or doc.doc_id
        score = f"{doc.score:.4f}" if doc.score is not None else ""
        relevance = _format_bool(doc.is_relevant)
        lines.append(
            f"| {rank} | `{_clean(title_text)}` | {score} | {relevance} | {_snippet(doc.text)} |"
        )
    lines.append("")
    return lines


def _context_section(trace: RagTrace) -> list[str]:
    lines = ["## Selected Context", ""]
    if not trace.selected_context:
        lines.append("No context chunks selected.")
        lines.append("")
        return lines

    for chunk in sorted(
        trace.selected_context,
        key=lambda item: item.rank if item.rank is not None else 10**9,
    ):
        rank = chunk.rank if chunk.rank is not None else "unranked"
        token_text = f", {chunk.token_count} tokens" if chunk.token_count is not None else ""
        lines.append(f"- **{_clean(chunk.context_id)}** from `{_clean(chunk.doc_id)}` (rank {rank}{token_text})")
        lines.append(f"  {_snippet(chunk.text, limit=220)}")
    lines.append("")
    return lines


def _citations_section(trace: RagTrace) -> list[str]:
    lines = ["## Evidence and Citations", ""]
    if not trace.answer.citations:
        lines.append("No answer citations recorded.")
        lines.append("")
        return lines

    for citation in trace.answer.citations:
        quote = f": {_snippet(citation.quote)}" if citation.quote else ""
        lines.append(f"- `{_clean(citation.doc_id)}`{quote}")
    lines.append("")
    return lines


def _metrics_section(trace: RagTrace) -> list[str]:
    lines = ["## Evaluation Signals", ""]
    if not trace.metrics:
        lines.append("No metric outputs recorded.")
        lines.append("")
        return lines

    lines.append("| Metric | Value | Passed | Notes |")
    lines.append("| --- | ---: | --- | --- |")
    for metric in trace.metrics:
        passed = _format_bool(metric.passed)
        value = _clean(str(metric.value))
        notes = _clean(metric.notes or "")
        lines.append(f"| `{_clean(metric.name)}` | {value} | {passed} | {notes} |")
    lines.append("")
    return lines


def _failures_section(labels: list[FailureLabel]) -> list[str]:
    lines = ["## Failure Modes", ""]
    if not labels:
        lines.append("No failure labels assigned.")
        lines.append("")
        return lines

    lines.append("| Mode | Severity | Method | Rationale |")
    lines.append("| --- | --- | --- | --- |")
    for label in labels:
        rationale = label.rationale or label.evidence or ""
        lines.append(
            f"| `{_clean(label.mode)}` | {_clean(label.severity)} | {_clean(label.detection_method)} | {_clean(rationale)} |"
        )
    lines.append("")
    return lines


def _likely_source_section(labels: list[FailureLabel]) -> list[str]:
    lines = ["## Likely Failure Source", ""]
    if not labels:
        lines.append("No likely failure source identified from the current trace.")
        lines.append("")
        return lines

    priority = [
        ("retrieval_miss", "Retrieval failed to surface necessary evidence."),
        ("reranking_error", "Reranking likely promoted weaker evidence."),
        ("context_truncation", "Context selection likely dropped necessary evidence."),
        ("context_pollution", "Context selection introduced distracting evidence."),
        ("unsupported_answer", "Generation produced claims not supported by selected context."),
        ("contradicted_by_context", "Generation contradicted available context."),
        ("wrong_citation", "Evidence attribution appears incorrect."),
        ("missing_citation", "Evidence attribution is incomplete."),
        ("metric_disagreement", "Evaluation signals need calibration review."),
        ("retrieval_noise", "Retrieval introduced distracting evidence."),
        ("ambiguous_question", "The query may be under-specified."),
        ("unknown", "The failure cannot yet be localized."),
    ]
    modes = {label.mode for label in labels}
    for mode, explanation in priority:
        if mode in modes:
            definition = get_failure_mode_definition(mode)
            lines.append(f"{explanation} {_clean(definition.definition)}")
            lines.append("")
            return lines

    lines.append("Failure labels are present, but no source mapping is available.")
    lines.append("")
    return lines


def _inspect_next_section(labels: list[FailureLabel]) -> list[str]:
    lines = ["## Inspect Next", ""]
    if not labels:
        lines.append("- Confirm whether the trace has complete metric and citation outputs.")
        lines.append("")
        return lines

    for label in labels:
        definition = get_failure_mode_definition(label.mode)
        lines.append(f"- `{_clean(label.mode)}`: {_inspect_hint(definition)}")
    lines.append("")
    return lines


def _notes_section(trace: RagTrace) -> list[str]:
    lines = ["## Diagnostic Notes", ""]
    for note in trace.diagnostic_notes:
        lines.append(f"- **{_clean(note.stage)}:** {_clean(note.note)}")
    lines.append("")
    return lines


def _inspect_hint(definition: FailureModeDefinition) -> str:
    hints = {
        "retrieval_miss": "inspect retrieval candidates and query formulation.",
        "retrieval_noise": "inspect irrelevant retrieved documents and ranking scores.",
        "reranking_error": "compare retrieved order with reranked order.",
        "context_truncation": "inspect context selection rules and token limits.",
        "context_pollution": "inspect selected chunks for irrelevant evidence.",
        "unsupported_answer": "compare answer claims against selected context.",
        "contradicted_by_context": "mark the exact contradictory spans.",
        "missing_citation": "check whether citation capture was expected and enabled.",
        "wrong_citation": "compare cited documents with answer claims.",
        "ambiguous_question": "review whether the query needs clarification.",
        "metric_disagreement": "inspect metric definitions, thresholds, and examples.",
        "unknown": "collect a human diagnostic note and refine the taxonomy.",
    }
    return hints.get(definition.mode, definition.limitations)


def _format_bool(value: bool | None) -> str:
    if value is None:
        return "not recorded"
    return "yes" if value else "no"


def _snippet(value: str | None, *, limit: int = 160) -> str:
    if not value:
        return ""
    cleaned = _clean(value).replace("\n", " ")
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _clean(value: str) -> str:
    return value.replace("|", "\\|").strip()
