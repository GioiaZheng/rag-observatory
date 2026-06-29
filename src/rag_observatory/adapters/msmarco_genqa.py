from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from rag_observatory.trace.schema import (
    Answer,
    Citation,
    ContextChunk,
    DiagnosticNote,
    Document,
    FailureLabel,
    Metric,
    Prompt,
    Query,
    RagTrace,
    RunMetadata,
)

JsonObject = dict[str, Any]

MSMARCO_GENQA_EXPORT_FORMAT = "msmarco-genqa.trace-export.v1"
ADAPTER_VERSION = "v1"

_TOP_LEVEL_FIELDS = {
    "format",
    "run",
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
}
_OPTIONAL_EXPORT_FIELDS = (
    "reranked_documents",
    "prompt",
    "metrics",
    "failures",
    "diagnostic_notes",
)


class MsmarcoGenqaAdapterError(ValueError):
    """Raised when an msmarco-genqa export cannot be mapped into a trace."""


def load_msmarco_genqa_trace(path: str | Path) -> RagTrace:
    export_path = Path(path)
    try:
        data = json.loads(export_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MsmarcoGenqaAdapterError(f"{export_path}: invalid JSON export: {exc}") from exc
    return trace_from_msmarco_genqa_export(data)


def trace_from_msmarco_genqa_export(export: Mapping[str, Any]) -> RagTrace:
    data = _expect_mapping(export, "export")
    _reject_unknown(data, _TOP_LEVEL_FIELDS, "export")

    export_format = _required_str(data, "format", "export")
    if export_format != MSMARCO_GENQA_EXPORT_FORMAT:
        raise MsmarcoGenqaAdapterError(f"export.format must be {MSMARCO_GENQA_EXPORT_FORMAT!r}")

    missing_optional_fields = _missing_optional_fields(data, _OPTIONAL_EXPORT_FIELDS)
    diagnostic_notes = _diagnostic_notes(data.get("diagnostic_notes", []))
    if missing_optional_fields:
        diagnostic_notes.append(
            DiagnosticNote(
                stage="adapter",
                note=(
                    "Missing optional msmarco-genqa export field(s): "
                    + ", ".join(missing_optional_fields)
                ),
                extra={"missing_optional_fields": list(missing_optional_fields)},
            )
        )

    trace = RagTrace(
        metadata=_metadata(_required_mapping(data, "run", "export")),
        query=_query(_required_mapping(data, "query", "export")),
        retrieved_documents=_documents(
            _required_list(data, "retrieved_documents", "export"),
            "retrieved_documents",
        ),
        reranked_documents=_optional_documents(data, "reranked_documents"),
        selected_context=_context_chunks(
            _required_list(data, "selected_context", "export"),
            "selected_context",
        ),
        prompt=_prompt(data.get("prompt")),
        answer=_answer(_required_mapping(data, "answer", "export")),
        metrics=_metrics(data.get("metrics", [])),
        failures=_failures(data.get("failures", [])),
        diagnostic_notes=diagnostic_notes,
        extra=_trace_extra(data, missing_optional_fields),
    )

    return RagTrace.from_dict(trace.to_dict())


def _metadata(data: Mapping[str, Any]) -> RunMetadata:
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
        "run",
    )
    return RunMetadata(
        run_id=_required_str(data, "run_id", "run"),
        timestamp=_required_str(data, "timestamp", "run"),
        dataset=_optional_str(data, "dataset", "run"),
        config_hash=_optional_str(data, "config_hash", "run"),
        code_version=_optional_str(data, "code_version", "run"),
        retriever=_optional_str(data, "retriever", "run"),
        reranker=_optional_str(data, "reranker", "run"),
        generator=_optional_str(data, "generator", "run"),
        evaluator=_optional_str(data, "evaluator", "run"),
        random_seed=_optional_int(data, "random_seed", "run"),
        pipeline_stages=_optional_bool_map(data, "pipeline_stages", "run"),
        extra=_optional_object(data, "extra", "run"),
    )


def _query(data: Mapping[str, Any]) -> Query:
    _reject_unknown(data, {"query_id", "text", "gold_answer", "extra"}, "query")
    return Query(
        query_id=_required_str(data, "query_id", "query"),
        text=_required_str(data, "text", "query"),
        gold_answer=_optional_str(data, "gold_answer", "query"),
        extra=_optional_object(data, "extra", "query"),
    )


def _documents(values: Iterable[Any], label: str) -> list[Document]:
    return [
        _document(_expect_mapping(value, f"{label}[{index}]"), f"{label}[{index}]")
        for index, value in enumerate(values)
    ]


def _optional_documents(data: Mapping[str, Any], key: str) -> list[Document]:
    value = data.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise MsmarcoGenqaAdapterError(f"export.{key} must be a list or null")
    return _documents(value, key)


def _document(data: Mapping[str, Any], label: str) -> Document:
    _reject_unknown(
        data,
        {"doc_id", "text", "title", "source", "score", "rank", "is_relevant", "extra"},
        label,
    )
    return Document(
        doc_id=_required_str(data, "doc_id", label),
        text=_required_str(data, "text", label),
        title=_optional_str(data, "title", label),
        source=_optional_str(data, "source", label),
        score=_optional_float(data, "score", label),
        rank=_optional_int(data, "rank", label),
        is_relevant=_optional_bool(data, "is_relevant", label),
        extra=_optional_object(data, "extra", label),
    )


def _context_chunks(values: Iterable[Any], label: str) -> list[ContextChunk]:
    chunks: list[ContextChunk] = []
    for index, value in enumerate(values):
        item_label = f"{label}[{index}]"
        data = _expect_mapping(value, item_label)
        _reject_unknown(
            data, {"context_id", "doc_id", "text", "rank", "token_count", "extra"}, item_label
        )
        chunks.append(
            ContextChunk(
                context_id=_required_str(data, "context_id", item_label),
                doc_id=_required_str(data, "doc_id", item_label),
                text=_required_str(data, "text", item_label),
                rank=_optional_int(data, "rank", item_label),
                token_count=_optional_int(data, "token_count", item_label),
                extra=_optional_object(data, "extra", item_label),
            )
        )
    return chunks


def _prompt(value: Any) -> Prompt | None:
    if value is None:
        return None
    data = _expect_mapping(value, "prompt")
    _reject_unknown(data, {"content", "template_id", "variables", "extra"}, "prompt")
    return Prompt(
        content=_optional_str(data, "content", "prompt"),
        template_id=_optional_str(data, "template_id", "prompt"),
        variables=_optional_object(data, "variables", "prompt"),
        extra=_optional_object(data, "extra", "prompt"),
    )


def _answer(data: Mapping[str, Any]) -> Answer:
    _reject_unknown(data, {"text", "citations", "extra"}, "answer")
    return Answer(
        text=_required_str(data, "text", "answer"),
        citations=_citations(data.get("citations", [])),
        extra=_optional_object(data, "extra", "answer"),
    )


def _citations(values: Any) -> list[Citation]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise MsmarcoGenqaAdapterError("answer.citations must be a list")

    citations: list[Citation] = []
    for index, value in enumerate(values):
        label = f"answer.citations[{index}]"
        data = _expect_mapping(value, label)
        _reject_unknown(data, {"doc_id", "quote", "span_start", "span_end", "extra"}, label)
        citations.append(
            Citation(
                doc_id=_required_str(data, "doc_id", label),
                quote=_optional_str(data, "quote", label),
                span_start=_optional_int(data, "span_start", label),
                span_end=_optional_int(data, "span_end", label),
                extra=_optional_object(data, "extra", label),
            )
        )
    return citations


def _metrics(values: Any) -> list[Metric]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise MsmarcoGenqaAdapterError("export.metrics must be a list or null")

    metrics: list[Metric] = []
    for index, value in enumerate(values):
        label = f"metrics[{index}]"
        data = _expect_mapping(value, label)
        _reject_unknown(data, {"name", "value", "passed", "threshold", "notes", "extra"}, label)
        if "value" not in data:
            raise MsmarcoGenqaAdapterError(f"{label}.value is required")
        metrics.append(
            Metric(
                name=_required_str(data, "name", label),
                value=data["value"],
                passed=_optional_bool(data, "passed", label),
                threshold=_optional_float(data, "threshold", label),
                notes=_optional_str(data, "notes", label),
                extra=_optional_object(data, "extra", label),
            )
        )
    return metrics


def _failures(values: Any) -> list[FailureLabel]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise MsmarcoGenqaAdapterError("export.failures must be a list or null")

    failures: list[FailureLabel] = []
    for index, value in enumerate(values):
        label = f"failures[{index}]"
        data = _expect_mapping(value, label)
        _reject_unknown(
            data,
            {"mode", "detection_method", "severity", "evidence", "rationale", "extra"},
            label,
        )
        failures.append(
            FailureLabel(
                mode=_required_str(data, "mode", label),
                detection_method=_required_str(data, "detection_method", label),
                severity=_optional_str(data, "severity", label) or "medium",
                evidence=_optional_str(data, "evidence", label),
                rationale=_optional_str(data, "rationale", label),
                extra=_optional_object(data, "extra", label),
            )
        )
    return failures


def _diagnostic_notes(values: Any) -> list[DiagnosticNote]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise MsmarcoGenqaAdapterError("export.diagnostic_notes must be a list or null")

    notes: list[DiagnosticNote] = []
    for index, value in enumerate(values):
        label = f"diagnostic_notes[{index}]"
        data = _expect_mapping(value, label)
        _reject_unknown(data, {"stage", "note", "extra"}, label)
        notes.append(
            DiagnosticNote(
                stage=_required_str(data, "stage", label),
                note=_required_str(data, "note", label),
                extra=_optional_object(data, "extra", label),
            )
        )
    return notes


def _trace_extra(data: Mapping[str, Any], missing_optional_fields: tuple[str, ...]) -> JsonObject:
    extra = _optional_object(data, "extra", "export")
    extra["msmarco_genqa_adapter"] = {
        "source_format": MSMARCO_GENQA_EXPORT_FORMAT,
        "adapter_version": ADAPTER_VERSION,
        "missing_optional_fields": list(missing_optional_fields),
    }
    return extra


def _missing_optional_fields(data: Mapping[str, Any], fields: Iterable[str]) -> tuple[str, ...]:
    missing = [field for field in fields if field not in data or data[field] is None]
    return tuple(missing)


def _required_mapping(data: Mapping[str, Any], key: str, label: str) -> Mapping[str, Any]:
    return _expect_mapping(data.get(key), f"{label}.{key}")


def _expect_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise MsmarcoGenqaAdapterError(f"{label} must be an object")
    return value


def _required_list(data: Mapping[str, Any], key: str, label: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        raise MsmarcoGenqaAdapterError(f"{label}.{key} must be a list")
    return value


def _reject_unknown(data: Mapping[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        joined = ", ".join(unknown)
        raise MsmarcoGenqaAdapterError(f"{label} contains unknown field(s): {joined}")


def _required_str(data: Mapping[str, Any], key: str, label: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MsmarcoGenqaAdapterError(f"{label}.{key} must be a non-empty string")
    return value


def _optional_str(data: Mapping[str, Any], key: str, label: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise MsmarcoGenqaAdapterError(f"{label}.{key} must be a string")
    return value


def _optional_int(data: Mapping[str, Any], key: str, label: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise MsmarcoGenqaAdapterError(f"{label}.{key} must be an integer")
    return value


def _optional_float(data: Mapping[str, Any], key: str, label: str) -> float | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise MsmarcoGenqaAdapterError(f"{label}.{key} must be numeric")
    return float(value)


def _optional_bool(data: Mapping[str, Any], key: str, label: str) -> bool | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise MsmarcoGenqaAdapterError(f"{label}.{key} must be a boolean")
    return value


def _optional_object(data: Mapping[str, Any], key: str, label: str) -> JsonObject:
    value = data.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise MsmarcoGenqaAdapterError(f"{label}.{key} must be an object")
    return dict(value)


def _optional_bool_map(data: Mapping[str, Any], key: str, label: str) -> dict[str, bool]:
    value = data.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise MsmarcoGenqaAdapterError(f"{label}.{key} must be an object")

    result: dict[str, bool] = {}
    for map_key, map_value in value.items():
        if not isinstance(map_key, str) or not map_key:
            raise MsmarcoGenqaAdapterError(f"{label}.{key} keys must be non-empty strings")
        if not isinstance(map_value, bool):
            raise MsmarcoGenqaAdapterError(f"{label}.{key}.{map_key} must be a boolean")
        result[map_key] = map_value
    return result
