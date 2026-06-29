# RAG Trace Stage Contract

`rag-observatory` treats a RAG run as an inspectable sequence of evidence
decisions. The schema should make it possible to ask where a failure first
became visible: retrieval, reranking, context selection, prompt construction,
generation, or evaluation.

This contract documents how stage-level signals are represented in the current
trace schema. It does not add a new pipeline implementation.

## Stage Map

| Stage | Trace fields | Reproducibility role | Diagnostic signals |
| --- | --- | --- | --- |
| Query | `query`, `conversation` | Identifies the question or conversation turn being diagnosed. | Ambiguity, rewrite loss, answerability mismatch. |
| Retrieval | `retrieved_documents` | Records the initial candidate evidence set with ranks and scores. | Missing relevant evidence, retrieval noise, weak scores. |
| Reranking | `reranked_documents` | Records post-reranking evidence order when a reranker is used. | Relevant evidence demoted below irrelevant candidates. |
| Context selection | `selected_context` | Records exactly what the generator saw. | Context pollution, truncation, redundant or misleading chunks. |
| Prompt construction | `prompt` | Records prompt text or template ID and variables needed to reproduce the call shape. | Missing variables, omitted evidence, unexpected instructions. |
| Generation | `answer`, `claims` | Records answer text, citations, and optional claim-level support review. | Unsupported claims, contradictions, missing or wrong citations. |
| Evaluation | `metrics`, `failures`, `diagnostic_notes` | Records evaluator outputs and reviewed labels. | Metric disagreement, failed faithfulness, human-review notes. |

Use `metadata.pipeline_stages` to record which stages were active in the source
run. A missing stage should be represented by an omitted or empty optional field,
not by inventing placeholder outputs.

## Required and Diagnostic Fields

The required fields are intentionally small:

- `metadata`
- `query`
- `retrieved_documents`
- `selected_context`
- `answer`

These fields are enough to identify a run, inspect candidate evidence, inspect
the context passed to generation, and inspect the answer.

Optional fields add diagnostic detail:

- `conversation` links a trace to a turn in a multi-turn interaction.
- `reranked_documents` separates reranking errors from retrieval errors.
- `prompt` records prompt construction without requiring a prompt framework.
- `metrics` records evaluator outputs and thresholds.
- `claims` records claim-level support and attribution decisions.
- `failures` records manual, heuristic, or model-based failure labels.
- `diagnostic_notes` records compact reviewer observations by stage.
- `extra` preserves explicit adapter or experiment metadata.

Unknown fields are rejected. Experimental data should live under the nearest
`extra` object until it is stable enough to become part of the public schema.

## Stage-To-Taxonomy Signals

| Observable trace condition | Likely operational label |
| --- | --- |
| No retrieved documents, or all retrieved documents are annotated not relevant. | `retrieval_miss` |
| Retrieved set contains irrelevant documents that may distract later stages. | `retrieval_noise` |
| Top reranked document is irrelevant while lower reranked documents are relevant. | `reranking_error` |
| Relevant retrieved evidence exists but no selected context references it. | `context_truncation` |
| Selected context references an irrelevant document. | `context_pollution` |
| A support-oriented metric such as faithfulness fails. | `unsupported_answer` |
| Citation capture is enabled but `answer.citations` is empty. | `missing_citation` |
| Answer cites a document annotated as not relevant. | `wrong_citation` |
| Some metrics pass while others fail. | `metric_disagreement` |

These labels are inspection aids. They identify likely failure surfaces but do
not replace human review for research claims.

## Full-Stage Example

The checked fixture
[`tests/fixtures/stage_contract/full_observability_trace.json`](../tests/fixtures/stage_contract/full_observability_trace.json)
shows one trace with retrieval, reranking, prompt construction, generation,
citations, evaluation metrics, and failure labels. The fixture is deliberately
synthetic and public-safe.

It illustrates this failure path:

1. Retrieval contains both relevant and irrelevant candidate evidence.
2. Reranking promotes an irrelevant candidate above the relevant one.
3. Context selection passes the irrelevant reranked document into the prompt.
4. Generation answers the right question shape but transfers unsupported
   evidence from the wrong document.
5. Evaluation signals disagree: answer relevance passes, while context
   relevance and faithfulness fail.

The expected diagnostic labels include:

- `retrieval_noise`
- `reranking_error`
- `context_truncation`
- `context_pollution`
- `metric_disagreement`
- `unsupported_answer`
- `wrong_citation`

## Boundary Notes

The schema records observations, not pipeline internals. For example,
`reranked_documents` records the resulting order and scores, but it does not
prescribe how the reranker was implemented. `prompt` records text, template ID,
and variables, but it does not require a particular prompt library.

For dataset-scale runs, store traces as JSONL collections rather than one large
JSON file. See [`docs/streaming_trace_storage.md`](streaming_trace_storage.md).
