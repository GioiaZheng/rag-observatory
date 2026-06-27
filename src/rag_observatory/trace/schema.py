from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

JsonObject = dict[str, Any]


class TraceValidationError(ValueError):
    """Raised when a trace does not satisfy the public schema."""


def _expect_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TraceValidationError(f"{label} must be an object")
    return value


def _reject_unknown(data: Mapping[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        joined = ", ".join(unknown)
        raise TraceValidationError(f"{label} contains unknown field(s): {joined}")


def _required_str(data: Mapping[str, Any], key: str, label: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TraceValidationError(f"{label}.{key} must be a non-empty string")
    return value


def _optional_str(data: Mapping[str, Any], key: str, label: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TraceValidationError(f"{label}.{key} must be a string")
    return value


def _optional_int(data: Mapping[str, Any], key: str, label: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise TraceValidationError(f"{label}.{key} must be an integer")
    return value


def _optional_float(data: Mapping[str, Any], key: str, label: str) -> float | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TraceValidationError(f"{label}.{key} must be numeric")
    return float(value)


def _optional_bool(data: Mapping[str, Any], key: str, label: str) -> bool | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise TraceValidationError(f"{label}.{key} must be a boolean")
    return value


def _optional_object(data: Mapping[str, Any], key: str, label: str) -> JsonObject:
    value = data.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TraceValidationError(f"{label}.{key} must be an object")
    _ensure_jsonable(value, f"{label}.{key}")
    return dict(value)


def _optional_bool_map(data: Mapping[str, Any], key: str, label: str) -> dict[str, bool]:
    value = data.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TraceValidationError(f"{label}.{key} must be an object")
    result: dict[str, bool] = {}
    for map_key, map_value in value.items():
        if not isinstance(map_key, str) or not map_key:
            raise TraceValidationError(f"{label}.{key} keys must be non-empty strings")
        if not isinstance(map_value, bool):
            raise TraceValidationError(f"{label}.{key}.{map_key} must be a boolean")
        result[map_key] = map_value
    return result


def _ensure_jsonable(value: Any, label: str) -> None:
    try:
        json.dumps(value)
    except TypeError as exc:
        raise TraceValidationError(f"{label} must be JSON serializable") from exc


def _list_from(
    data: Mapping[str, Any],
    key: str,
    label: str,
    factory: Any,
) -> list[Any]:
    value = data.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise TraceValidationError(f"{label}.{key} must be a list")
    return [factory(item) for item in value]


@dataclass(frozen=True)
class RunMetadata:
    run_id: str
    timestamp: str
    dataset: str | None = None
    config_hash: str | None = None
    code_version: str | None = None
    retriever: str | None = None
    reranker: str | None = None
    generator: str | None = None
    evaluator: str | None = None
    random_seed: int | None = None
    pipeline_stages: dict[str, bool] = field(default_factory=dict)
    extra: JsonObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Any) -> RunMetadata:
        data = _expect_mapping(value, "metadata")
        _reject_unknown(
            data,
            {
                "run_id",
                "timestamp",
                "dataset",
                "config_hash",
                "code_version",
                "retriever",
                "reranker",
                "generator",
                "evaluator",
                "random_seed",
                "pipeline_stages",
                "extra",
            },
            "metadata",
        )
        return cls(
            run_id=_required_str(data, "run_id", "metadata"),
            timestamp=_required_str(data, "timestamp", "metadata"),
            dataset=_optional_str(data, "dataset", "metadata"),
            config_hash=_optional_str(data, "config_hash", "metadata"),
            code_version=_optional_str(data, "code_version", "metadata"),
            retriever=_optional_str(data, "retriever", "metadata"),
            reranker=_optional_str(data, "reranker", "metadata"),
            generator=_optional_str(data, "generator", "metadata"),
            evaluator=_optional_str(data, "evaluator", "metadata"),
            random_seed=_optional_int(data, "random_seed", "metadata"),
            pipeline_stages=_optional_bool_map(data, "pipeline_stages", "metadata"),
            extra=_optional_object(data, "extra", "metadata"),
        )

    def to_dict(self) -> JsonObject:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "dataset": self.dataset,
            "config_hash": self.config_hash,
            "code_version": self.code_version,
            "retriever": self.retriever,
            "reranker": self.reranker,
            "generator": self.generator,
            "evaluator": self.evaluator,
            "random_seed": self.random_seed,
            "pipeline_stages": dict(self.pipeline_stages),
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class Query:
    query_id: str
    text: str
    gold_answer: str | None = None
    extra: JsonObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Any) -> Query:
        data = _expect_mapping(value, "query")
        _reject_unknown(data, {"query_id", "text", "gold_answer", "extra"}, "query")
        return cls(
            query_id=_required_str(data, "query_id", "query"),
            text=_required_str(data, "text", "query"),
            gold_answer=_optional_str(data, "gold_answer", "query"),
            extra=_optional_object(data, "extra", "query"),
        )

    def to_dict(self) -> JsonObject:
        return {
            "query_id": self.query_id,
            "text": self.text,
            "gold_answer": self.gold_answer,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class Document:
    doc_id: str
    text: str
    title: str | None = None
    source: str | None = None
    score: float | None = None
    rank: int | None = None
    is_relevant: bool | None = None
    extra: JsonObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Any) -> Document:
        data = _expect_mapping(value, "document")
        _reject_unknown(
            data,
            {"doc_id", "text", "title", "source", "score", "rank", "is_relevant", "extra"},
            "document",
        )
        return cls(
            doc_id=_required_str(data, "doc_id", "document"),
            text=_required_str(data, "text", "document"),
            title=_optional_str(data, "title", "document"),
            source=_optional_str(data, "source", "document"),
            score=_optional_float(data, "score", "document"),
            rank=_optional_int(data, "rank", "document"),
            is_relevant=_optional_bool(data, "is_relevant", "document"),
            extra=_optional_object(data, "extra", "document"),
        )

    def to_dict(self) -> JsonObject:
        return {
            "doc_id": self.doc_id,
            "text": self.text,
            "title": self.title,
            "source": self.source,
            "score": self.score,
            "rank": self.rank,
            "is_relevant": self.is_relevant,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class ContextChunk:
    context_id: str
    doc_id: str
    text: str
    rank: int | None = None
    token_count: int | None = None
    extra: JsonObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Any) -> ContextChunk:
        data = _expect_mapping(value, "context_chunk")
        _reject_unknown(
            data,
            {"context_id", "doc_id", "text", "rank", "token_count", "extra"},
            "context_chunk",
        )
        return cls(
            context_id=_required_str(data, "context_id", "context_chunk"),
            doc_id=_required_str(data, "doc_id", "context_chunk"),
            text=_required_str(data, "text", "context_chunk"),
            rank=_optional_int(data, "rank", "context_chunk"),
            token_count=_optional_int(data, "token_count", "context_chunk"),
            extra=_optional_object(data, "extra", "context_chunk"),
        )

    def to_dict(self) -> JsonObject:
        return {
            "context_id": self.context_id,
            "doc_id": self.doc_id,
            "text": self.text,
            "rank": self.rank,
            "token_count": self.token_count,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class Prompt:
    content: str | None = None
    template_id: str | None = None
    variables: JsonObject = field(default_factory=dict)
    extra: JsonObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Any) -> Prompt:
        data = _expect_mapping(value, "prompt")
        _reject_unknown(data, {"content", "template_id", "variables", "extra"}, "prompt")
        content = _optional_str(data, "content", "prompt")
        template_id = _optional_str(data, "template_id", "prompt")
        if content is None and template_id is None:
            raise TraceValidationError("prompt.content or prompt.template_id is required")
        return cls(
            content=content,
            template_id=template_id,
            variables=_optional_object(data, "variables", "prompt"),
            extra=_optional_object(data, "extra", "prompt"),
        )

    def to_dict(self) -> JsonObject:
        return {
            "content": self.content,
            "template_id": self.template_id,
            "variables": dict(self.variables),
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class Citation:
    doc_id: str
    quote: str | None = None
    span_start: int | None = None
    span_end: int | None = None
    extra: JsonObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Any) -> Citation:
        data = _expect_mapping(value, "citation")
        _reject_unknown(data, {"doc_id", "quote", "span_start", "span_end", "extra"}, "citation")
        return cls(
            doc_id=_required_str(data, "doc_id", "citation"),
            quote=_optional_str(data, "quote", "citation"),
            span_start=_optional_int(data, "span_start", "citation"),
            span_end=_optional_int(data, "span_end", "citation"),
            extra=_optional_object(data, "extra", "citation"),
        )

    def to_dict(self) -> JsonObject:
        return {
            "doc_id": self.doc_id,
            "quote": self.quote,
            "span_start": self.span_start,
            "span_end": self.span_end,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class Answer:
    text: str
    citations: list[Citation] = field(default_factory=list)
    extra: JsonObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Any) -> Answer:
        data = _expect_mapping(value, "answer")
        _reject_unknown(data, {"text", "citations", "extra"}, "answer")
        return cls(
            text=_required_str(data, "text", "answer"),
            citations=_list_from(data, "citations", "answer", Citation.from_dict),
            extra=_optional_object(data, "extra", "answer"),
        )

    def to_dict(self) -> JsonObject:
        return {
            "text": self.text,
            "citations": [citation.to_dict() for citation in self.citations],
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class Metric:
    name: str
    value: Any
    passed: bool | None = None
    threshold: float | None = None
    notes: str | None = None
    extra: JsonObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Any) -> Metric:
        data = _expect_mapping(value, "metric")
        _reject_unknown(data, {"name", "value", "passed", "threshold", "notes", "extra"}, "metric")
        if "value" not in data:
            raise TraceValidationError("metric.value is required")
        _ensure_jsonable(data["value"], "metric.value")
        return cls(
            name=_required_str(data, "name", "metric"),
            value=data["value"],
            passed=_optional_bool(data, "passed", "metric"),
            threshold=_optional_float(data, "threshold", "metric"),
            notes=_optional_str(data, "notes", "metric"),
            extra=_optional_object(data, "extra", "metric"),
        )

    def to_dict(self) -> JsonObject:
        return {
            "name": self.name,
            "value": self.value,
            "passed": self.passed,
            "threshold": self.threshold,
            "notes": self.notes,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class FailureLabel:
    mode: str
    detection_method: str
    severity: str = "medium"
    evidence: str | None = None
    rationale: str | None = None
    extra: JsonObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Any) -> FailureLabel:
        data = _expect_mapping(value, "failure_label")
        _reject_unknown(
            data,
            {"mode", "detection_method", "severity", "evidence", "rationale", "extra"},
            "failure_label",
        )
        severity = _optional_str(data, "severity", "failure_label") or "medium"
        return cls(
            mode=_required_str(data, "mode", "failure_label"),
            detection_method=_required_str(data, "detection_method", "failure_label"),
            severity=severity,
            evidence=_optional_str(data, "evidence", "failure_label"),
            rationale=_optional_str(data, "rationale", "failure_label"),
            extra=_optional_object(data, "extra", "failure_label"),
        )

    def to_dict(self) -> JsonObject:
        return {
            "mode": self.mode,
            "detection_method": self.detection_method,
            "severity": self.severity,
            "evidence": self.evidence,
            "rationale": self.rationale,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class DiagnosticNote:
    stage: str
    note: str
    extra: JsonObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Any) -> DiagnosticNote:
        data = _expect_mapping(value, "diagnostic_note")
        _reject_unknown(data, {"stage", "note", "extra"}, "diagnostic_note")
        return cls(
            stage=_required_str(data, "stage", "diagnostic_note"),
            note=_required_str(data, "note", "diagnostic_note"),
            extra=_optional_object(data, "extra", "diagnostic_note"),
        )

    def to_dict(self) -> JsonObject:
        return {
            "stage": self.stage,
            "note": self.note,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class RagTrace:
    metadata: RunMetadata
    query: Query
    retrieved_documents: list[Document]
    selected_context: list[ContextChunk]
    answer: Answer
    reranked_documents: list[Document] = field(default_factory=list)
    prompt: Prompt | None = None
    metrics: list[Metric] = field(default_factory=list)
    failures: list[FailureLabel] = field(default_factory=list)
    diagnostic_notes: list[DiagnosticNote] = field(default_factory=list)
    extra: JsonObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Any) -> RagTrace:
        data = _expect_mapping(value, "trace")
        _reject_unknown(
            data,
            {
                "metadata",
                "query",
                "retrieved_documents",
                "reranked_documents",
                "selected_context",
                "prompt",
                "answer",
                "metrics",
                "failures",
                "diagnostic_notes",
                "extra",
            },
            "trace",
        )
        for required in ("metadata", "query", "retrieved_documents", "selected_context", "answer"):
            if required not in data:
                raise TraceValidationError(f"trace.{required} is required")

        prompt = data.get("prompt")
        trace = cls(
            metadata=RunMetadata.from_dict(data["metadata"]),
            query=Query.from_dict(data["query"]),
            retrieved_documents=_list_from(
                data, "retrieved_documents", "trace", Document.from_dict
            ),
            reranked_documents=_list_from(data, "reranked_documents", "trace", Document.from_dict),
            selected_context=_list_from(data, "selected_context", "trace", ContextChunk.from_dict),
            prompt=Prompt.from_dict(prompt) if prompt is not None else None,
            answer=Answer.from_dict(data["answer"]),
            metrics=_list_from(data, "metrics", "trace", Metric.from_dict),
            failures=_list_from(data, "failures", "trace", FailureLabel.from_dict),
            diagnostic_notes=_list_from(
                data, "diagnostic_notes", "trace", DiagnosticNote.from_dict
            ),
            extra=_optional_object(data, "extra", "trace"),
        )

        from rag_observatory.trace.validation import validate_trace

        validate_trace(trace)
        return trace

    @classmethod
    def from_json(cls, text: str) -> RagTrace:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise TraceValidationError(f"invalid trace JSON: {exc}") from exc
        return cls.from_dict(data)

    def to_dict(self) -> JsonObject:
        return {
            "metadata": self.metadata.to_dict(),
            "query": self.query.to_dict(),
            "retrieved_documents": [doc.to_dict() for doc in self.retrieved_documents],
            "reranked_documents": [doc.to_dict() for doc in self.reranked_documents],
            "selected_context": [chunk.to_dict() for chunk in self.selected_context],
            "prompt": self.prompt.to_dict() if self.prompt is not None else None,
            "answer": self.answer.to_dict(),
            "metrics": [metric.to_dict() for metric in self.metrics],
            "failures": [failure.to_dict() for failure in self.failures],
            "diagnostic_notes": [note.to_dict() for note in self.diagnostic_notes],
            "extra": dict(self.extra),
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)
