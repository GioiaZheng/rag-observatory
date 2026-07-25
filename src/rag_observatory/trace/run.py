from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from rag_observatory.taxonomy.failure_modes import classify_trace
from rag_observatory.trace.schema import FailureLabel, JsonObject, RagTrace

STAGES = (
    "query",
    "retrieval",
    "reranking",
    "context",
    "prompt",
    "generation",
    "evaluation",
    "diagnostics",
)

FAILURE_STAGE = {
    "ambiguous_question": "query",
    "retrieval_miss": "retrieval",
    "retrieval_noise": "retrieval",
    "reranking_error": "reranking",
    "context_truncation": "context",
    "context_pollution": "context",
    "contradicted_by_context": "generation",
    "missing_citation": "generation",
    "unsupported_answer": "generation",
    "wrong_citation": "generation",
    "metric_disagreement": "evaluation",
}


@dataclass(frozen=True)
class StageEvent:
    name: str
    attributes: JsonObject = field(default_factory=dict)

    def to_dict(self) -> JsonObject:
        return {"name": self.name, "attributes": dict(self.attributes)}


@dataclass(frozen=True)
class SpanLink:
    span_id: str
    reason: str

    def to_dict(self) -> JsonObject:
        return {"span_id": self.span_id, "reason": self.reason}


@dataclass(frozen=True)
class StageSpan:
    span_id: str
    parent_span_id: str | None
    name: str
    stage: str
    started_at: str | None = None
    ended_at: str | None = None
    latency_ms: float | None = None
    status: str = "unset"
    error_type: str | None = None
    input: JsonObject = field(default_factory=dict)
    output: JsonObject = field(default_factory=dict)
    metrics: JsonObject = field(default_factory=dict)
    attributes: JsonObject = field(default_factory=dict)
    events: list[StageEvent] = field(default_factory=list)
    links: list[SpanLink] = field(default_factory=list)

    def to_dict(self) -> JsonObject:
        return {
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "stage": self.stage,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "error_type": self.error_type,
            "input": dict(self.input),
            "output": dict(self.output),
            "metrics": dict(self.metrics),
            "attributes": dict(self.attributes),
            "events": [event.to_dict() for event in self.events],
            "links": [link.to_dict() for link in self.links],
        }


@dataclass(frozen=True)
class InternalRun:
    run_id: str
    trace_id: str
    spans: list[StageSpan]
    started_at: str | None = None
    ended_at: str | None = None
    schema_version: str = "internal-run.v1"
    attributes: JsonObject = field(default_factory=dict)
    links: list[JsonObject] = field(default_factory=list)

    def to_dict(self) -> JsonObject:
        return {
            "format": "rag-observatory.internal-run.v1",
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "schema_version": self.schema_version,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "attributes": dict(self.attributes),
            "spans": [span.to_dict() for span in self.spans],
            "links": [dict(link) for link in self.links],
        }


def stage_for_failure(label: FailureLabel) -> str:
    explicit_stage = label.extra.get("stage")
    if isinstance(explicit_stage, str) and explicit_stage in STAGES:
        return explicit_stage
    return FAILURE_STAGE.get(label.mode, "diagnostics")


def internal_run_from_trace(trace: RagTrace) -> InternalRun:
    """Convert the stable public trace into exporter-agnostic stage spans."""

    labels = classify_trace(trace)
    span_ids = {stage: f"span-{stage}" for stage in STAGES}
    events = _stage_events(trace, labels)
    spans = [
        _span(
            "query",
            None,
            input={
                "conversation": (
                    trace.conversation.to_dict() if trace.conversation is not None else None
                )
            },
            output={"query": trace.query.to_dict()},
            attributes={"query_id": trace.query.query_id},
            events=events["query"],
        ),
        _span(
            "retrieval",
            span_ids["query"],
            input={"query_id": trace.query.query_id},
            output={"documents": [document.to_dict() for document in trace.retrieved_documents]},
            metrics={
                "candidate_count": len(trace.retrieved_documents),
                "relevant_document_count": sum(
                    document.is_relevant is True for document in trace.retrieved_documents
                ),
            },
            attributes=_without_none({"retriever": trace.metadata.retriever}),
            events=events["retrieval"],
        ),
        _span(
            "reranking",
            span_ids["retrieval"],
            output={"documents": [document.to_dict() for document in trace.reranked_documents]},
            metrics={"candidate_count": len(trace.reranked_documents)},
            attributes=_without_none({"reranker": trace.metadata.reranker}),
            events=events["reranking"],
            observed=bool(trace.reranked_documents),
        ),
        _span(
            "context",
            span_ids["reranking"],
            output={"chunks": [chunk.to_dict() for chunk in trace.selected_context]},
            metrics={
                "chunk_count": len(trace.selected_context),
                "token_count": sum(chunk.token_count or 0 for chunk in trace.selected_context),
            },
            events=events["context"],
        ),
        _span(
            "prompt",
            span_ids["context"],
            output={"prompt": trace.prompt.to_dict() if trace.prompt is not None else None},
            attributes=_without_none(
                {"template_id": trace.prompt.template_id if trace.prompt is not None else None}
            ),
            events=events["prompt"],
            observed=trace.prompt is not None,
        ),
        _span(
            "generation",
            span_ids["prompt"],
            output={
                "answer": trace.answer.to_dict(),
                "claims": [claim.to_dict() for claim in trace.claims],
            },
            metrics={"citation_count": len(trace.answer.citations)},
            attributes=_without_none({"generator": trace.metadata.generator}),
            events=events["generation"],
        ),
        _span(
            "evaluation",
            span_ids["generation"],
            output={"metrics": [metric.to_dict() for metric in trace.metrics]},
            metrics={metric.name: metric.value for metric in trace.metrics},
            attributes=_without_none({"evaluator": trace.metadata.evaluator}),
            events=events["evaluation"],
            observed=bool(trace.metrics),
        ),
        _span(
            "diagnostics",
            span_ids["evaluation"],
            input={"stage_span_count": len(STAGES) - 1},
            output={
                "failure_labels": [label.to_dict() for label in labels],
                "diagnostic_notes": [note.to_dict() for note in trace.diagnostic_notes],
                "metadata": trace.metadata.to_dict(),
                "trace_extra": dict(trace.extra),
            },
            metrics={"failure_label_count": len(labels)},
            attributes={"diagnostic_mode": "recorded-plus-heuristic"},
            events=events["diagnostics"],
            links=_diagnostic_links(trace, labels, span_ids),
        ),
    ]

    trace_key = f"{trace.metadata.run_id}\0{trace.query.query_id}".encode()
    trace_id = f"trace-{hashlib.sha256(trace_key).hexdigest()[:16]}"
    attributes = _without_none(
        {
            "dataset": trace.metadata.dataset,
            "config_hash": trace.metadata.config_hash,
            "code_version": trace.metadata.code_version,
            "retriever": trace.metadata.retriever,
            "reranker": trace.metadata.reranker,
            "generator": trace.metadata.generator,
            "evaluator": trace.metadata.evaluator,
        }
    )
    return InternalRun(
        run_id=trace.metadata.run_id,
        trace_id=trace_id,
        spans=spans,
        started_at=trace.metadata.timestamp,
        attributes=attributes,
    )


def _span(
    stage: str,
    parent_span_id: str | None,
    *,
    input: JsonObject | None = None,
    output: JsonObject | None = None,
    metrics: JsonObject | None = None,
    attributes: JsonObject | None = None,
    events: list[StageEvent] | None = None,
    links: list[SpanLink] | None = None,
    observed: bool = True,
) -> StageSpan:
    return StageSpan(
        span_id=f"span-{stage}",
        parent_span_id=parent_span_id,
        name=f"rag.{stage}",
        stage=stage,
        status="ok" if observed else "unset",
        input=input or {},
        output=output or {},
        metrics=metrics or {},
        attributes=attributes or {},
        events=events or [],
        links=links or [],
    )


def _stage_events(trace: RagTrace, labels: list[FailureLabel]) -> dict[str, list[StageEvent]]:
    events: dict[str, list[StageEvent]] = {stage: [] for stage in STAGES}
    for label in labels:
        events[stage_for_failure(label)].append(
            StageEvent(
                name="failure_signal",
                attributes={
                    "mode": label.mode,
                    "severity": label.severity,
                    "detection_method": label.detection_method,
                    "evidence": label.evidence,
                    "rationale": label.rationale,
                },
            )
        )
    for note in trace.diagnostic_notes:
        stage = _normalize_stage(note.stage)
        events[stage].append(
            StageEvent(
                name="diagnostic_note",
                attributes={"note": note.note, "source_stage": note.stage},
            )
        )
    return events


def _diagnostic_links(
    trace: RagTrace,
    labels: list[FailureLabel],
    span_ids: dict[str, str],
) -> list[SpanLink]:
    stages = {stage_for_failure(label) for label in labels}
    stages.update(_normalize_stage(note.stage) for note in trace.diagnostic_notes)
    stages.discard("diagnostics")
    return [
        SpanLink(span_id=span_ids[stage], reason="failure_source")
        for stage in STAGES
        if stage in stages
    ]


def _normalize_stage(stage: str) -> str:
    aliases = {
        "context_selection": "context",
        "citation": "generation",
        "citations": "generation",
    }
    normalized = aliases.get(stage, stage)
    return normalized if normalized in STAGES else "diagnostics"


def _without_none(values: dict[str, Any]) -> JsonObject:
    return {key: value for key, value in values.items() if value is not None}
