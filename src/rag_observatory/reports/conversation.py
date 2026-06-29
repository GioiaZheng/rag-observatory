from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from rag_observatory.taxonomy.failure_modes import classify_trace
from rag_observatory.trace.schema import RagTrace


def render_markdown_conversation_report(traces: Sequence[RagTrace]) -> str:
    if not traces:
        return "# Conversational RAG Diagnostic Report\n\nNo traces provided.\n"

    ordered = sorted(
        traces,
        key=lambda trace: (
            trace.conversation.turn_index
            if trace.conversation is not None and trace.conversation.turn_index is not None
            else 10**9,
            trace.conversation.turn_id if trace.conversation is not None else trace.query.query_id,
        ),
    )
    conversation_id = _conversation_id(ordered)
    lines = ["# Conversational RAG Diagnostic Report", ""]
    lines.extend(_summary_section(ordered, conversation_id))
    lines.extend(_turn_overview_section(ordered))
    lines.extend(_failure_summary_section(ordered))
    lines.extend(_turn_details_section(ordered))
    return "\n".join(lines).rstrip() + "\n"


def _summary_section(traces: Sequence[RagTrace], conversation_id: str) -> list[str]:
    unanswerable_count = sum(
        1
        for trace in traces
        if trace.conversation is not None and trace.conversation.answerability == "unanswerable"
    )
    return [
        "## Summary",
        "",
        f"- **Conversation:** `{_clean(conversation_id)}`",
        f"- **Turns:** {len(traces)}",
        f"- **Unanswerable turns:** {unanswerable_count}",
        "",
    ]


def _turn_overview_section(traces: Sequence[RagTrace]) -> list[str]:
    lines = [
        "## Turn Overview",
        "",
        "| Turn | Original Text | Standalone Query | Answerability | Failure Modes | Retrieval Diagnosis |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for trace in traces:
        modes = _failure_modes(trace)
        lines.append(
            "| "
            f"{_turn_label(trace)} | "
            f"{_original_text(trace)} | "
            f"{_standalone_query(trace)} | "
            f"{_answerability(trace)} | "
            f"{_format_modes(modes)} | "
            f"{_retrieval_diagnosis(trace, modes)} |"
        )
    lines.append("")
    return lines


def _failure_summary_section(traces: Sequence[RagTrace]) -> list[str]:
    counter: Counter[str] = Counter()
    for trace in traces:
        counter.update(_failure_modes(trace))

    lines = [
        "## Failure Summary",
        "",
        "| Failure Mode | Turns |",
        "| --- | ---: |",
    ]
    if not counter:
        lines.append("| none | 0 |")
        lines.append("")
        return lines

    for mode, count in sorted(counter.items()):
        lines.append(f"| `{_clean(mode)}` | {count} |")
    lines.append("")
    return lines


def _turn_details_section(traces: Sequence[RagTrace]) -> list[str]:
    lines = ["## Turn Details", ""]
    for trace in traces:
        modes = _failure_modes(trace)
        lines.extend(
            [
                f"### Turn {_turn_label(trace)}",
                "",
                f"- **Query ID:** `{_clean(trace.query.query_id)}`",
                f"- **Original text:** {_original_text(trace)}",
                f"- **Standalone query:** {_standalone_query(trace)}",
                f"- **Answerability:** {_answerability(trace)}",
                f"- **Retrieved documents:** {len(trace.retrieved_documents)}",
                f"- **Selected context chunks:** {len(trace.selected_context)}",
                f"- **Failure modes:** {_format_modes(modes)}",
                f"- **Retrieval diagnosis:** {_retrieval_diagnosis(trace, modes)}",
                "",
            ]
        )
    return lines


def _retrieval_diagnosis(trace: RagTrace, modes: tuple[str, ...]) -> str:
    if "retrieval_miss" not in modes:
        return "none"
    if _has_failed_rewrite_metric(trace):
        return "query rewriting"
    if trace.conversation is not None and trace.conversation.answerability == "unanswerable":
        return "insufficient evidence for unanswerable turn"
    return "retrieved evidence missing"


def _has_failed_rewrite_metric(trace: RagTrace) -> bool:
    for metric in trace.metrics:
        metric_name = metric.name.lower()
        if ("rewrite" in metric_name or "standalone_query" in metric_name) and (
            metric.passed is False
        ):
            return True
    return False


def _conversation_id(traces: Sequence[RagTrace]) -> str:
    ids = {trace.conversation.conversation_id for trace in traces if trace.conversation is not None}
    if len(ids) == 1:
        return next(iter(ids))
    if not ids:
        return "single-turn"
    return "mixed"


def _failure_modes(trace: RagTrace) -> tuple[str, ...]:
    return tuple(label.mode for label in classify_trace(trace))


def _turn_label(trace: RagTrace) -> str:
    if trace.conversation is None:
        return _clean(trace.query.query_id)
    if trace.conversation.turn_index is not None:
        return str(trace.conversation.turn_index)
    return _clean(trace.conversation.turn_id)


def _original_text(trace: RagTrace) -> str:
    if trace.conversation is None:
        return _clean(trace.query.text)
    return _clean(trace.conversation.original_turn_text)


def _standalone_query(trace: RagTrace) -> str:
    if trace.conversation is None or trace.conversation.standalone_query is None:
        return "none"
    return _clean(trace.conversation.standalone_query)


def _answerability(trace: RagTrace) -> str:
    if trace.conversation is None:
        return "unknown"
    return _clean(trace.conversation.answerability)


def _format_modes(modes: tuple[str, ...]) -> str:
    if not modes:
        return "none"
    return ", ".join(f"`{_clean(mode)}`" for mode in modes)


def _clean(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
