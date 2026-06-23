from __future__ import annotations

from rag_observatory.compare.traces import IdChange, TraceComparison, compare_traces
from rag_observatory.trace.schema import RagTrace


def render_markdown_comparison(before: RagTrace, after: RagTrace) -> str:
    comparison = compare_traces(before, after)
    lines: list[str] = ["# RAG Trace Comparison", ""]

    lines.extend(_run_pair_section(comparison, before, after))
    lines.extend(_query_section(comparison, before, after))
    lines.extend(_id_change_section("Retrieved Documents", comparison.retrieved_documents))
    lines.extend(
        _id_change_section(
            "Selected Context Documents",
            comparison.selected_context_documents,
        )
    )
    lines.extend(_answer_section(comparison, before, after))
    lines.extend(_metrics_section(comparison))
    lines.extend(_id_change_section("Failure Labels", comparison.failure_labels))

    return "\n".join(lines).rstrip() + "\n"


def _run_pair_section(
    comparison: TraceComparison,
    before: RagTrace,
    after: RagTrace,
) -> list[str]:
    rows = [
        ("Run ID", comparison.before_run_id, comparison.after_run_id),
        ("Timestamp", before.metadata.timestamp, after.metadata.timestamp),
        (
            "Retriever",
            before.metadata.retriever or "not recorded",
            after.metadata.retriever or "not recorded",
        ),
        (
            "Reranker",
            before.metadata.reranker or "not used",
            after.metadata.reranker or "not used",
        ),
        (
            "Generator",
            before.metadata.generator or "not recorded",
            after.metadata.generator or "not recorded",
        ),
        (
            "Evaluator",
            before.metadata.evaluator or "not recorded",
            after.metadata.evaluator or "not recorded",
        ),
    ]
    lines = ["## Run Pair", "", "| Field | Before | After |", "| --- | --- | --- |"]
    for field, before_value, after_value in rows:
        lines.append(f"| {field} | {_clean(before_value)} | {_clean(after_value)} |")
    lines.append("")
    return lines


def _query_section(
    comparison: TraceComparison,
    before: RagTrace,
    after: RagTrace,
) -> list[str]:
    lines = ["## Query", "", "| Field | Before | After | Status |", "| --- | --- | --- | --- |"]
    lines.append(
        f"| Query ID | {_clean(before.query.query_id)} | {_clean(after.query.query_id)} | {_status(comparison.same_query_id)} |"
    )
    lines.append(
        f"| Text | {_clean(before.query.text)} | {_clean(after.query.text)} | {_status(comparison.same_query_text)} |"
    )
    lines.append("")
    return lines


def _id_change_section(title: str, change: IdChange) -> list[str]:
    lines = [f"## {title}", ""]
    lines.append(f"- **Before:** {_format_ids(change.before_ids)}")
    lines.append(f"- **After:** {_format_ids(change.after_ids)}")
    lines.append(f"- **Added:** {_format_ids(change.added_ids)}")
    lines.append(f"- **Removed:** {_format_ids(change.removed_ids)}")
    lines.append(f"- **Kept:** {_format_ids(change.kept_ids)}")

    if change.rank_changes:
        lines.append("")
        lines.append("| Item | Before Rank | After Rank |")
        lines.append("| --- | ---: | ---: |")
        for rank_change in change.rank_changes:
            before_rank = _format_rank(rank_change.before_rank)
            after_rank = _format_rank(rank_change.after_rank)
            lines.append(f"| `{_clean(rank_change.item_id)}` | {before_rank} | {after_rank} |")

    lines.append("")
    return lines


def _answer_section(comparison: TraceComparison, before: RagTrace, after: RagTrace) -> list[str]:
    lines = [
        "## Generated Answer",
        "",
        f"- **Status:** {_status(not comparison.answer_changed)}",
    ]
    if comparison.answer_changed:
        lines.extend(
            [
                "",
                "| Before | After |",
                "| --- | --- |",
                f"| {_clean(before.answer.text)} | {_clean(after.answer.text)} |",
            ]
        )
    lines.append("")
    return lines


def _metrics_section(comparison: TraceComparison) -> list[str]:
    lines = ["## Evaluation Signals", ""]
    if not comparison.metric_changes:
        lines.append("No metric outputs recorded in either trace.")
        lines.append("")
        return lines

    lines.append("| Metric | Status | Before Value | Before Passed | After Value | After Passed |")
    lines.append("| --- | --- | ---: | --- | ---: | --- |")
    for metric in comparison.metric_changes:
        lines.append(
            "| "
            f"`{_clean(metric.name)}` | "
            f"{metric.status} | "
            f"{_format_value(metric.before_value)} | "
            f"{_format_bool(metric.before_passed)} | "
            f"{_format_value(metric.after_value)} | "
            f"{_format_bool(metric.after_passed)} |"
        )
    lines.append("")
    return lines


def _format_ids(values: list[str]) -> str:
    if not values:
        return "none"
    return ", ".join(f"`{_clean(value)}`" for value in values)


def _format_rank(value: int | None) -> str:
    return str(value) if value is not None else "not recorded"


def _format_value(value: object) -> str:
    if value is None:
        return "not recorded"
    return _clean(str(value))


def _format_bool(value: bool | None) -> str:
    if value is None:
        return "not recorded"
    return "yes" if value else "no"


def _status(unchanged: bool) -> str:
    return "unchanged" if unchanged else "changed"


def _clean(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
