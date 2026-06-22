from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag_observatory.trace.schema import FailureLabel, RagTrace


FAILURE_MODE_VALUES = {
    "retrieval_miss",
    "retrieval_noise",
    "reranking_error",
    "context_truncation",
    "context_pollution",
    "unsupported_answer",
    "contradicted_by_context",
    "missing_citation",
    "wrong_citation",
    "ambiguous_question",
    "metric_disagreement",
    "unknown",
}

DETECTION_METHOD_VALUES = {"manual", "heuristic", "model_based", "future"}
SEVERITY_VALUES = {"low", "medium", "high"}


@dataclass(frozen=True)
class FailureModeDefinition:
    mode: str
    definition: str
    detection_method: str
    minimal_example: str
    limitations: str


FAILURE_MODE_DEFINITIONS: dict[str, FailureModeDefinition] = {
    "retrieval_miss": FailureModeDefinition(
        mode="retrieval_miss",
        definition="The retrieved set lacks evidence needed to answer the query.",
        detection_method="heuristic",
        minimal_example="All retrieved documents are annotated as not relevant.",
        limitations="Requires relevance annotations or human review.",
    ),
    "retrieval_noise": FailureModeDefinition(
        mode="retrieval_noise",
        definition="The retriever returned irrelevant or distracting documents.",
        detection_method="heuristic",
        minimal_example="A relevant document is present, but irrelevant documents are also retrieved.",
        limitations="Noise severity depends on context selection and ranking.",
    ),
    "reranking_error": FailureModeDefinition(
        mode="reranking_error",
        definition="Reranking promoted weaker evidence over stronger evidence.",
        detection_method="heuristic",
        minimal_example="An irrelevant reranked document appears before a relevant one.",
        limitations="Requires reranked documents and relevance annotations.",
    ),
    "context_truncation": FailureModeDefinition(
        mode="context_truncation",
        definition="Relevant retrieved evidence was not included in the selected context.",
        detection_method="heuristic",
        minimal_example="A relevant retrieved document exists, but no selected context uses it.",
        limitations="Does not prove token-budget pressure without prompt construction metadata.",
    ),
    "context_pollution": FailureModeDefinition(
        mode="context_pollution",
        definition="Selected context contains irrelevant or misleading evidence.",
        detection_method="heuristic",
        minimal_example="Selected context includes a document annotated as not relevant.",
        limitations="Requires relevance annotations or human review.",
    ),
    "unsupported_answer": FailureModeDefinition(
        mode="unsupported_answer",
        definition="The answer makes claims not supported by the selected context.",
        detection_method="heuristic",
        minimal_example="A faithfulness or support metric fails.",
        limitations="Rule-based detection depends on available metric outputs.",
    ),
    "contradicted_by_context": FailureModeDefinition(
        mode="contradicted_by_context",
        definition="The answer conflicts with evidence present in retrieved or selected context.",
        detection_method="manual",
        minimal_example="Context says vitamin C prevents scurvy, but the answer says vitamin D.",
        limitations="Currently best assigned manually unless contradiction metrics are available.",
    ),
    "missing_citation": FailureModeDefinition(
        mode="missing_citation",
        definition="The answer lacks expected citation or evidence references.",
        detection_method="heuristic",
        minimal_example="Citation capture is enabled, but the answer contains no citations.",
        limitations="Only meaningful when citations are expected by the pipeline.",
    ),
    "wrong_citation": FailureModeDefinition(
        mode="wrong_citation",
        definition="The answer cites evidence that does not support the claim.",
        detection_method="heuristic",
        minimal_example="A cited document is annotated as not relevant.",
        limitations="Requires citation references and relevance annotations.",
    ),
    "ambiguous_question": FailureModeDefinition(
        mode="ambiguous_question",
        definition="The query is underspecified enough that multiple answers may be valid.",
        detection_method="manual",
        minimal_example="The query asks for 'the capital' without identifying a country.",
        limitations="Ambiguity detection is not implemented beyond manual labels.",
    ),
    "metric_disagreement": FailureModeDefinition(
        mode="metric_disagreement",
        definition="Evaluation signals disagree about whether the run succeeded.",
        detection_method="heuristic",
        minimal_example="One metric passes while another metric fails.",
        limitations="Does not identify which metric is better calibrated.",
    ),
    "unknown": FailureModeDefinition(
        mode="unknown",
        definition="A failure is suspected but cannot yet be assigned to a stable label.",
        detection_method="manual",
        minimal_example="Human reviewer flags the run but cannot localize the cause.",
        limitations="Should be replaced by a more specific label when possible.",
    ),
}


def get_failure_mode_definition(mode: str) -> FailureModeDefinition:
    try:
        return FAILURE_MODE_DEFINITIONS[mode]
    except KeyError as exc:
        raise KeyError(f"unknown failure mode: {mode}") from exc


def classify_trace(trace: "RagTrace") -> list["FailureLabel"]:
    """Preserve manual labels and add conservative heuristic labels."""

    from rag_observatory.trace.schema import FailureLabel

    labels = list(trace.failures)
    seen_modes = {label.mode for label in labels}

    def add(mode: str, severity: str, evidence: str, rationale: str) -> None:
        if mode in seen_modes:
            return
        labels.append(
            FailureLabel(
                mode=mode,
                detection_method="heuristic",
                severity=severity,
                evidence=evidence,
                rationale=rationale,
            )
        )
        seen_modes.add(mode)

    relevance_annotations = [doc.is_relevant for doc in trace.retrieved_documents]
    annotated_retrieved = [value for value in relevance_annotations if value is not None]
    relevant_doc_ids = {doc.doc_id for doc in trace.retrieved_documents if doc.is_relevant is True}
    irrelevant_doc_ids = {doc.doc_id for doc in trace.retrieved_documents if doc.is_relevant is False}
    selected_doc_ids = {chunk.doc_id for chunk in trace.selected_context}

    if not trace.retrieved_documents:
        add(
            "retrieval_miss",
            "high",
            "retrieved_documents is empty",
            "No retrieved evidence is available for the generator.",
        )
    elif annotated_retrieved and not any(annotated_retrieved):
        add(
            "retrieval_miss",
            "high",
            "all retrieved documents are annotated as not relevant",
            "The retriever did not surface evidence marked relevant.",
        )

    if any(value is False for value in relevance_annotations):
        add(
            "retrieval_noise",
            "medium",
            "at least one retrieved document is annotated as not relevant",
            "Irrelevant retrieved evidence may distract later stages.",
        )

    if relevant_doc_ids and not (selected_doc_ids & relevant_doc_ids):
        add(
            "context_truncation",
            "high",
            "relevant retrieved documents were not selected for context",
            "Context selection excluded all retrieved evidence marked relevant.",
        )

    if selected_doc_ids & irrelevant_doc_ids:
        add(
            "context_pollution",
            "medium",
            "selected context includes documents annotated as not relevant",
            "The prompt may contain misleading or distracting context.",
        )

    if trace.reranked_documents:
        ranked_docs = sorted(
            trace.reranked_documents,
            key=lambda doc: doc.rank if doc.rank is not None else 10**9,
        )
        if ranked_docs and ranked_docs[0].is_relevant is False:
            lower_relevant = any(doc.is_relevant is True for doc in ranked_docs[1:])
            if lower_relevant:
                add(
                    "reranking_error",
                    "high",
                    "top reranked document is not relevant while lower documents are relevant",
                    "Reranking appears to have promoted weaker evidence.",
                )

    metric_pass_values = [metric.passed for metric in trace.metrics if metric.passed is not None]
    if any(value is True for value in metric_pass_values) and any(
        value is False for value in metric_pass_values
    ):
        add(
            "metric_disagreement",
            "medium",
            "metric pass/fail outputs disagree",
            "Evaluation signals do not agree on the run outcome.",
        )

    for metric in trace.metrics:
        metric_name = metric.name.lower()
        if metric.passed is False and (
            "faithfulness" in metric_name
            or "support" in metric_name
            or "grounded" in metric_name
        ):
            add(
                "unsupported_answer",
                "high",
                f"{metric.name} failed",
                "A support-oriented metric indicates the answer is not grounded.",
            )

    citations_expected = trace.metadata.pipeline_stages.get("citations") is True
    if citations_expected and not trace.answer.citations:
        add(
            "missing_citation",
            "medium",
            "citation stage is enabled but answer.citations is empty",
            "The answer lacks expected evidence references.",
        )

    cited_irrelevant = [
        citation.doc_id for citation in trace.answer.citations if citation.doc_id in irrelevant_doc_ids
    ]
    if cited_irrelevant:
        add(
            "wrong_citation",
            "high",
            "answer cites documents annotated as not relevant",
            "The cited evidence may not support the generated answer.",
        )

    return labels
