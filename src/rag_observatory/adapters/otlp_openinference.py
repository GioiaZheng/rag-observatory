from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rag_observatory.trace.schema import (
    Answer,
    DiagnosticNote,
    Document,
    Metric,
    Prompt,
    Query,
    RagTrace,
    RunMetadata,
)

JsonObject = dict[str, Any]

OTLP_OPENINFERENCE_ADAPTER_VERSION = "v1"
OTLP_JSON_FORMAT = "otlp-json"
OPENINFERENCE_SEMANTIC_CONVENTIONS = "openinference"

_DOCUMENT_ATTRIBUTE = re.compile(
    r"^(?P<prefix>retrieval\.documents|reranker\.(?:input|output)_documents)\."
    r"(?P<index>\d+)\.document\.(?P<field>id|content|score|metadata)$"
)


class OtlpOpenInferenceAdapterError(ValueError):
    """Raised when an OTLP/JSON export cannot be mapped into a RAG trace."""


@dataclass(frozen=True)
class _Span:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    start_time_unix_nano: int | None
    end_time_unix_nano: int | None
    attributes: JsonObject
    resource_attributes: JsonObject
    status_code: str | int | None

    @property
    def openinference_kind(self) -> str | None:
        value = self.attributes.get("openinference.span.kind")
        if not isinstance(value, str) or not value.strip():
            return None
        return value.upper()


def load_otlp_openinference_trace(
    path: str | Path,
    *,
    trace_id: str | None = None,
) -> RagTrace:
    export_path = Path(path)
    try:
        data = json.loads(export_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OtlpOpenInferenceAdapterError(
            f"{export_path}: invalid OTLP/JSON export: {exc}"
        ) from exc
    except OSError as exc:
        raise OtlpOpenInferenceAdapterError(f"{export_path}: cannot read export: {exc}") from exc

    return trace_from_otlp_openinference_export(data, trace_id=trace_id)


def trace_from_otlp_openinference_export(
    export: Mapping[str, Any],
    *,
    trace_id: str | None = None,
) -> RagTrace:
    data = _expect_mapping(export, "export")
    spans = _read_spans(data)
    selected_trace_id, trace_spans = _select_trace(spans, trace_id)
    ordered_spans = sorted(trace_spans, key=_span_sort_key)
    root = _root_span(ordered_spans)

    retriever_spans = _spans_of_kind(ordered_spans, "RETRIEVER")
    reranker_spans = _spans_of_kind(ordered_spans, "RERANKER")
    llm_spans = _spans_of_kind(ordered_spans, "LLM")

    diagnostic_notes: list[DiagnosticNote] = []
    retrieved_documents = _documents_from_spans(
        retriever_spans,
        "retrieval.documents",
        stage="retrieval",
        id_namespace="retrieved",
        diagnostic_notes=diagnostic_notes,
    )
    reranked_documents = _documents_from_spans(
        reranker_spans,
        "reranker.output_documents",
        stage="reranking",
        id_namespace="reranked",
        diagnostic_notes=diagnostic_notes,
    )

    query_text = _query_text(root, retriever_spans, reranker_spans, llm_spans)
    if query_text is None:
        raise OtlpOpenInferenceAdapterError(
            "selected trace has no query in reranker.query, retriever input, root input, "
            "or LLM input messages"
        )

    answer_text = _answer_text(root, llm_spans)
    if answer_text is None:
        raise OtlpOpenInferenceAdapterError(
            "selected trace has no answer in root output, LLM output, or LLM output messages"
        )

    prompt = _prompt(llm_spans)
    timestamp = _trace_timestamp(ordered_spans)
    resource_attributes = root.resource_attributes
    service_name = _optional_text(resource_attributes.get("service.name"))

    pipeline_stages = {
        "retrieval": bool(retriever_spans),
        "reranking": bool(reranker_spans),
        "generation": bool(llm_spans),
        "context_selection": False,
    }
    if retrieved_documents and not reranked_documents:
        diagnostic_notes.append(
            DiagnosticNote(
                stage="adapter",
                note="No OpenInference RERANKER output documents were present.",
            )
        )
    diagnostic_notes.append(
        DiagnosticNote(
            stage="context",
            note=(
                "OpenInference retrieval and reranking attributes do not identify the final "
                "selected prompt context; selected_context is intentionally left empty."
            ),
        )
    )

    trace = RagTrace(
        metadata=RunMetadata(
            run_id=selected_trace_id,
            timestamp=timestamp,
            retriever=_component_name(retriever_spans),
            reranker=_attribute_text(reranker_spans, "reranker.model_name"),
            generator=_generator_name(llm_spans),
            pipeline_stages=pipeline_stages,
            extra={
                "source_format": OTLP_JSON_FORMAT,
                "semantic_conventions": OPENINFERENCE_SEMANTIC_CONVENTIONS,
                "adapter_version": OTLP_OPENINFERENCE_ADAPTER_VERSION,
                "service_name": service_name,
                "root_span_id": root.span_id,
                "span_count": len(ordered_spans),
            },
        ),
        query=Query(
            query_id=selected_trace_id,
            text=query_text,
            extra={"source": "OpenInference span attributes"},
        ),
        retrieved_documents=retrieved_documents,
        reranked_documents=reranked_documents,
        selected_context=[],
        prompt=prompt,
        answer=Answer(
            text=answer_text,
            extra={"source": "OpenInference span attributes"},
        ),
        metrics=_metrics(llm_spans),
        diagnostic_notes=diagnostic_notes,
        extra={
            "otlp_openinference": {
                "trace_id": selected_trace_id,
                "adapter_version": OTLP_OPENINFERENCE_ADAPTER_VERSION,
            }
        },
    )
    return RagTrace.from_dict(trace.to_dict())


def _read_spans(export: Mapping[str, Any]) -> list[_Span]:
    resource_spans = export.get("resourceSpans")
    if not isinstance(resource_spans, list):
        raise OtlpOpenInferenceAdapterError("export.resourceSpans must be a list")

    spans: list[_Span] = []
    for resource_index, raw_resource_span in enumerate(resource_spans):
        resource_label = f"resourceSpans[{resource_index}]"
        resource_span = _expect_mapping(raw_resource_span, resource_label)
        raw_resource = resource_span.get("resource", {})
        resource = _expect_mapping(raw_resource, f"{resource_label}.resource")
        resource_attributes = _decode_attributes(
            resource.get("attributes", []), f"{resource_label}.resource.attributes"
        )

        scope_spans = resource_span.get("scopeSpans")
        if not isinstance(scope_spans, list):
            raise OtlpOpenInferenceAdapterError(f"{resource_label}.scopeSpans must be a list")
        for scope_index, raw_scope_span in enumerate(scope_spans):
            scope_label = f"{resource_label}.scopeSpans[{scope_index}]"
            scope_span = _expect_mapping(raw_scope_span, scope_label)
            raw_spans = scope_span.get("spans")
            if not isinstance(raw_spans, list):
                raise OtlpOpenInferenceAdapterError(f"{scope_label}.spans must be a list")
            for span_index, raw_span in enumerate(raw_spans):
                label = f"{scope_label}.spans[{span_index}]"
                span = _expect_mapping(raw_span, label)
                status = span.get("status", {})
                status_data = _expect_mapping(status, f"{label}.status")
                parent_span_id = _optional_text(span.get("parentSpanId"))
                spans.append(
                    _Span(
                        trace_id=_required_text(span, "traceId", label),
                        span_id=_required_text(span, "spanId", label),
                        parent_span_id=parent_span_id,
                        name=_required_text(span, "name", label),
                        start_time_unix_nano=_optional_integer(
                            span.get("startTimeUnixNano"), f"{label}.startTimeUnixNano"
                        ),
                        end_time_unix_nano=_optional_integer(
                            span.get("endTimeUnixNano"), f"{label}.endTimeUnixNano"
                        ),
                        attributes=_decode_attributes(
                            span.get("attributes", []), f"{label}.attributes"
                        ),
                        resource_attributes=resource_attributes,
                        status_code=status_data.get("code"),
                    )
                )

    if not spans:
        raise OtlpOpenInferenceAdapterError("export contains no spans")
    return spans


def _decode_attributes(value: Any, label: str) -> JsonObject:
    if value is None:
        return {}
    if not isinstance(value, list):
        raise OtlpOpenInferenceAdapterError(f"{label} must be a list")

    attributes: JsonObject = {}
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        attribute = _expect_mapping(item, item_label)
        key = _required_text(attribute, "key", item_label)
        if key in attributes:
            raise OtlpOpenInferenceAdapterError(f"{label} contains duplicate key {key!r}")
        raw_value = _expect_mapping(attribute.get("value"), f"{item_label}.value")
        attributes[key] = _decode_any_value(raw_value, f"{item_label}.value")
    return attributes


def _decode_any_value(value: Mapping[str, Any], label: str) -> Any:
    variants = [
        key
        for key in (
            "stringValue",
            "boolValue",
            "intValue",
            "doubleValue",
            "arrayValue",
            "kvlistValue",
            "bytesValue",
        )
        if key in value
    ]
    if len(variants) != 1:
        raise OtlpOpenInferenceAdapterError(f"{label} must contain exactly one AnyValue field")

    variant = variants[0]
    raw_value = value[variant]
    if variant == "intValue":
        return _required_integer(raw_value, f"{label}.intValue")
    if variant == "doubleValue":
        if not isinstance(raw_value, (int, float)) or isinstance(raw_value, bool):
            raise OtlpOpenInferenceAdapterError(f"{label}.doubleValue must be numeric")
        return float(raw_value)
    if variant == "boolValue":
        if not isinstance(raw_value, bool):
            raise OtlpOpenInferenceAdapterError(f"{label}.boolValue must be boolean")
        return raw_value
    if variant in {"stringValue", "bytesValue"}:
        if not isinstance(raw_value, str):
            raise OtlpOpenInferenceAdapterError(f"{label}.{variant} must be a string")
        return raw_value
    if variant == "arrayValue":
        array_value = _expect_mapping(raw_value, f"{label}.arrayValue")
        values = array_value.get("values", [])
        if not isinstance(values, list):
            raise OtlpOpenInferenceAdapterError(f"{label}.arrayValue.values must be a list")
        return [
            _decode_any_value(_expect_mapping(item, f"{label}.arrayValue.values[{index}]"), label)
            for index, item in enumerate(values)
        ]

    kvlist_value = _expect_mapping(raw_value, f"{label}.kvlistValue")
    return _decode_attributes(kvlist_value.get("values", []), f"{label}.kvlistValue.values")


def _select_trace(spans: list[_Span], trace_id: str | None) -> tuple[str, list[_Span]]:
    trace_ids = sorted({span.trace_id for span in spans})
    if trace_id is None:
        if len(trace_ids) != 1:
            joined = ", ".join(trace_ids)
            raise OtlpOpenInferenceAdapterError(
                f"export contains multiple trace IDs ({joined}); pass --trace-id"
            )
        selected_trace_id = trace_ids[0]
    else:
        matches = [candidate for candidate in trace_ids if candidate.lower() == trace_id.lower()]
        if not matches:
            raise OtlpOpenInferenceAdapterError(f"trace ID {trace_id!r} is not present in export")
        selected_trace_id = matches[0]

    return selected_trace_id, [span for span in spans if span.trace_id == selected_trace_id]


def _root_span(spans: list[_Span]) -> _Span:
    span_ids = {span.span_id for span in spans}
    roots = [
        span for span in spans if span.parent_span_id is None or span.parent_span_id not in span_ids
    ]
    if not roots:
        raise OtlpOpenInferenceAdapterError("selected trace has no root span")
    return sorted(roots, key=_span_sort_key)[0]


def _spans_of_kind(spans: list[_Span], kind: str) -> list[_Span]:
    return [span for span in spans if span.openinference_kind == kind]


def _documents_from_spans(
    spans: list[_Span],
    prefix: str,
    *,
    stage: str,
    id_namespace: str,
    diagnostic_notes: list[DiagnosticNote],
) -> list[Document]:
    documents: list[Document] = []
    for span in spans:
        indexed: dict[int, JsonObject] = {}
        for key, value in span.attributes.items():
            match = _DOCUMENT_ATTRIBUTE.match(key)
            if match is None or match.group("prefix") != prefix:
                continue
            index = int(match.group("index"))
            indexed.setdefault(index, {})[match.group("field")] = value

        for index in sorted(indexed):
            raw_document = indexed[index]
            content = _optional_text(raw_document.get("content"))
            if content is None:
                diagnostic_notes.append(
                    DiagnosticNote(
                        stage=stage,
                        note=f"Skipped {prefix}.{index}: document.content is missing.",
                        extra={"source_span_id": span.span_id},
                    )
                )
                continue
            source_id = _optional_text(raw_document.get("id")) or f"{span.span_id}-{index}"
            score = _optional_number(raw_document.get("score"), f"{prefix}.{index}.document.score")
            metadata = _metadata_object(raw_document.get("metadata"))
            documents.append(
                Document(
                    doc_id=f"{id_namespace}:{source_id}",
                    text=content,
                    score=score,
                    rank=index + 1,
                    extra={
                        "openinference_document_id": source_id,
                        "source_span_id": span.span_id,
                        "metadata": metadata,
                    },
                )
            )
    return documents


def _query_text(
    root: _Span,
    retriever_spans: list[_Span],
    reranker_spans: list[_Span],
    llm_spans: list[_Span],
) -> str | None:
    candidates: list[Any] = []
    candidates.extend(span.attributes.get("reranker.query") for span in reranker_spans)
    candidates.extend(span.attributes.get("input.value") for span in retriever_spans)
    candidates.append(root.attributes.get("input.value"))
    candidates.extend(
        _message_contents(span.attributes, "llm.input_messages") for span in llm_spans
    )
    return _first_payload_text(candidates, ("query", "question", "input", "text"))


def _answer_text(root: _Span, llm_spans: list[_Span]) -> str | None:
    candidates: list[Any] = [root.attributes.get("output.value")]
    for span in reversed(llm_spans):
        candidates.append(span.attributes.get("output.value"))
        candidates.append(_message_contents(span.attributes, "llm.output_messages"))
    return _first_payload_text(candidates, ("answer", "output", "text", "content"))


def _prompt(llm_spans: list[_Span]) -> Prompt | None:
    for span in reversed(llm_spans):
        template = _optional_text(span.attributes.get("llm.prompt_template.template"))
        variables = _metadata_object(span.attributes.get("llm.prompt_template.variables"))
        input_value = _first_payload_text(
            [
                span.attributes.get("input.value"),
                _message_contents(span.attributes, "llm.input_messages"),
            ],
            ("prompt", "input", "text", "content"),
        )
        if input_value is not None or template is not None:
            return Prompt(
                content=input_value,
                template_id=template,
                variables=variables,
                extra={"source_span_id": span.span_id},
            )
    return None


def _message_contents(attributes: Mapping[str, Any], prefix: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(prefix)}\.(\d+)\.message\.content$")
    indexed: list[tuple[int, str]] = []
    for key, value in attributes.items():
        match = pattern.match(key)
        text = _optional_text(value)
        if match is not None and text is not None:
            indexed.append((int(match.group(1)), text))
    if not indexed:
        return None
    return "\n".join(text for _, text in sorted(indexed))


def _first_payload_text(candidates: list[Any], preferred_keys: tuple[str, ...]) -> str | None:
    for value in candidates:
        text = _payload_text(value, preferred_keys)
        if text is not None:
            return text
    return None


def _payload_text(value: Any, preferred_keys: tuple[str, ...]) -> str | None:
    text = _optional_text(value)
    if text is None:
        return None
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(decoded, Mapping):
        for key in preferred_keys:
            candidate = _optional_text(decoded.get(key))
            if candidate is not None:
                return candidate
    if isinstance(decoded, str) and decoded.strip():
        return decoded
    return text


def _metrics(llm_spans: list[_Span]) -> list[Metric]:
    metric_names = (
        "llm.token_count.prompt",
        "llm.token_count.completion",
        "llm.token_count.total",
    )
    metrics: list[Metric] = []
    for span in llm_spans:
        for name in metric_names:
            value = span.attributes.get(name)
            if isinstance(value, int) and not isinstance(value, bool):
                metrics.append(
                    Metric(
                        name=name,
                        value=value,
                        extra={"source_span_id": span.span_id},
                    )
                )
    return metrics


def _component_name(spans: list[_Span]) -> str | None:
    if not spans:
        return None
    return spans[-1].name


def _generator_name(spans: list[_Span]) -> str | None:
    return _attribute_text(spans, "llm.model_name") or _attribute_text(
        spans, "gen_ai.request.model"
    )


def _attribute_text(spans: list[_Span], key: str) -> str | None:
    for span in reversed(spans):
        value = _optional_text(span.attributes.get(key))
        if value is not None:
            return value
    return None


def _trace_timestamp(spans: list[_Span]) -> str:
    timestamps = [
        span.start_time_unix_nano for span in spans if span.start_time_unix_nano is not None
    ]
    if not timestamps:
        raise OtlpOpenInferenceAdapterError("selected trace has no startTimeUnixNano")
    timestamp = datetime.fromtimestamp(min(timestamps) / 1_000_000_000, tz=timezone.utc)
    return timestamp.isoformat().replace("+00:00", "Z")


def _span_sort_key(span: _Span) -> tuple[int, str]:
    return (span.start_time_unix_nano or 0, span.span_id)


def _metadata_object(value: Any) -> JsonObject:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {"raw": value}
        if isinstance(decoded, Mapping):
            return dict(decoded)
    return {"raw": value}


def _optional_number(value: Any, label: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise OtlpOpenInferenceAdapterError(f"{label} must be numeric")
    return float(value)


def _expect_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OtlpOpenInferenceAdapterError(f"{label} must be an object")
    return value


def _required_text(data: Mapping[str, Any], key: str, label: str) -> str:
    value = _optional_text(data.get(key))
    if value is None:
        raise OtlpOpenInferenceAdapterError(f"{label}.{key} must be a non-empty string")
    return value


def _optional_text(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def _optional_integer(value: Any, label: str) -> int | None:
    if value is None:
        return None
    return _required_integer(value, label)


def _required_integer(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise OtlpOpenInferenceAdapterError(f"{label} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError as exc:
            raise OtlpOpenInferenceAdapterError(f"{label} must be an integer") from exc
    raise OtlpOpenInferenceAdapterError(f"{label} must be an integer")
