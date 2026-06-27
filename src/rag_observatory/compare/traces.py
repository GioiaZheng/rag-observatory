from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rag_observatory.taxonomy.failure_modes import classify_trace
from rag_observatory.trace.schema import ContextChunk, Metric, RagTrace


@dataclass(frozen=True)
class ItemRankChange:
    item_id: str
    before_rank: int | None
    after_rank: int | None


@dataclass(frozen=True)
class IdChange:
    before_ids: list[str]
    after_ids: list[str]
    added_ids: list[str]
    removed_ids: list[str]
    kept_ids: list[str]
    rank_changes: list[ItemRankChange]


@dataclass(frozen=True)
class MetricChange:
    name: str
    status: str
    before_value: Any | None
    after_value: Any | None
    before_passed: bool | None
    after_passed: bool | None


@dataclass(frozen=True)
class TraceComparison:
    before_run_id: str
    after_run_id: str
    same_query_id: bool
    same_query_text: bool
    retrieved_documents: IdChange
    selected_context_documents: IdChange
    answer_changed: bool
    metric_changes: list[MetricChange]
    failure_labels: IdChange


def compare_traces(before: RagTrace, after: RagTrace) -> TraceComparison:
    return TraceComparison(
        before_run_id=before.metadata.run_id,
        after_run_id=after.metadata.run_id,
        same_query_id=before.query.query_id == after.query.query_id,
        same_query_text=before.query.text == after.query.text,
        retrieved_documents=_compare_ranked_ids(
            [(doc.doc_id, doc.rank) for doc in before.retrieved_documents],
            [(doc.doc_id, doc.rank) for doc in after.retrieved_documents],
        ),
        selected_context_documents=_compare_ranked_ids(
            _context_doc_ranks(before.selected_context),
            _context_doc_ranks(after.selected_context),
        ),
        answer_changed=before.answer.text != after.answer.text,
        metric_changes=_compare_metrics(before.metrics, after.metrics),
        failure_labels=_compare_unranked_ids(
            [label.mode for label in classify_trace(before)],
            [label.mode for label in classify_trace(after)],
        ),
    )


def _compare_unranked_ids(before_ids: list[str], after_ids: list[str]) -> IdChange:
    return _compare_ranked_ids(
        [(item_id, None) for item_id in _ordered_unique(before_ids)],
        [(item_id, None) for item_id in _ordered_unique(after_ids)],
    )


def _compare_ranked_ids(
    before_items: list[tuple[str, int | None]],
    after_items: list[tuple[str, int | None]],
) -> IdChange:
    before_ranks = _first_rank_by_id(before_items)
    after_ranks = _first_rank_by_id(after_items)
    before_ids = list(before_ranks)
    after_ids = list(after_ranks)
    before_set = set(before_ids)
    after_set = set(after_ids)
    kept_ids = [item_id for item_id in before_ids if item_id in after_set]

    rank_changes = [
        ItemRankChange(item_id, before_ranks[item_id], after_ranks[item_id])
        for item_id in kept_ids
        if before_ranks[item_id] != after_ranks[item_id]
    ]

    return IdChange(
        before_ids=before_ids,
        after_ids=after_ids,
        added_ids=[item_id for item_id in after_ids if item_id not in before_set],
        removed_ids=[item_id for item_id in before_ids if item_id not in after_set],
        kept_ids=kept_ids,
        rank_changes=rank_changes,
    )


def _compare_metrics(
    before_metrics: list[Metric],
    after_metrics: list[Metric],
) -> list[MetricChange]:
    before_by_name = {metric.name: metric for metric in before_metrics}
    after_by_name = {metric.name: metric for metric in after_metrics}
    names = _ordered_unique([metric.name for metric in before_metrics + after_metrics])
    changes: list[MetricChange] = []

    for name in names:
        before_metric = before_by_name.get(name)
        after_metric = after_by_name.get(name)
        if before_metric is None:
            status = "added"
        elif after_metric is None:
            status = "removed"
        elif (
            before_metric.value != after_metric.value or before_metric.passed != after_metric.passed
        ):
            status = "changed"
        else:
            status = "unchanged"

        changes.append(
            MetricChange(
                name=name,
                status=status,
                before_value=before_metric.value if before_metric is not None else None,
                after_value=after_metric.value if after_metric is not None else None,
                before_passed=before_metric.passed if before_metric is not None else None,
                after_passed=after_metric.passed if after_metric is not None else None,
            )
        )

    return changes


def _context_doc_ranks(chunks: list[ContextChunk]) -> list[tuple[str, int | None]]:
    return [(chunk.doc_id, chunk.rank) for chunk in chunks]


def _first_rank_by_id(items: list[tuple[str, int | None]]) -> dict[str, int | None]:
    ranks: dict[str, int | None] = {}
    for item_id, rank in items:
        if item_id not in ranks:
            ranks[item_id] = rank
    return ranks


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
