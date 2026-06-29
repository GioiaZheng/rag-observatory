from __future__ import annotations

from rag_observatory.taxonomy.failure_modes import (
    DETECTION_METHOD_VALUES,
    FAILURE_MODE_VALUES,
    SEVERITY_VALUES,
)
from rag_observatory.trace.schema import RagTrace, TraceValidationError


def validate_trace(trace: RagTrace) -> None:
    """Validate relationships that require the complete trace."""

    errors: list[str] = []

    retrieved_ids = [doc.doc_id for doc in trace.retrieved_documents]
    reranked_ids = [doc.doc_id for doc in trace.reranked_documents]
    all_doc_ids = retrieved_ids + reranked_ids
    unique_doc_ids = set(all_doc_ids)

    if len(unique_doc_ids) != len(all_doc_ids):
        errors.append("document ids must be unique across retrieved and reranked documents")

    context_ids = [chunk.context_id for chunk in trace.selected_context]
    unique_context_ids = set(context_ids)
    if len(set(context_ids)) != len(context_ids):
        errors.append("selected context ids must be unique")

    for chunk in trace.selected_context:
        if chunk.doc_id not in unique_doc_ids:
            errors.append(
                f"selected context {chunk.context_id} references unknown doc_id {chunk.doc_id}"
            )

    for citation in trace.answer.citations:
        if citation.doc_id not in unique_doc_ids:
            errors.append(f"citation references unknown doc_id {citation.doc_id}")
        if citation.span_start is not None and citation.span_end is not None:
            if citation.span_start > citation.span_end:
                errors.append(f"citation span is invalid for doc_id {citation.doc_id}")

    claim_ids = [claim.claim_id for claim in trace.claims]
    if len(set(claim_ids)) != len(claim_ids):
        errors.append("claim ids must be unique")

    for claim in trace.claims:
        for evidence in claim.evidence:
            if evidence.doc_id is not None and evidence.doc_id not in unique_doc_ids:
                errors.append(
                    f"claim {claim.claim_id} evidence references unknown doc_id {evidence.doc_id}"
                )
            if evidence.context_id is not None and evidence.context_id not in unique_context_ids:
                errors.append(
                    f"claim {claim.claim_id} evidence references unknown context_id "
                    f"{evidence.context_id}"
                )

    for failure in trace.failures:
        if failure.mode not in FAILURE_MODE_VALUES:
            errors.append(f"unknown failure mode: {failure.mode}")
        if failure.detection_method not in DETECTION_METHOD_VALUES:
            errors.append(f"unknown detection method: {failure.detection_method}")
        if failure.severity not in SEVERITY_VALUES:
            errors.append(f"unknown failure severity: {failure.severity}")

    if errors:
        raise TraceValidationError("; ".join(errors))
