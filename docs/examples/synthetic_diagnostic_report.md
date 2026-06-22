# RAG Diagnostic Report

## Run

- **Run ID:** toy-unsupported-answer
- **Timestamp:** 2026-06-22T00:00:00Z
- **Dataset:** toy_rag_observatory
- **Retriever:** toy-bm25
- **Reranker:** not used
- **Generator:** toy-generator
- **Evaluator:** toy-evaluator

## Query

- **Query ID:** q-scurvy
- **Text:** Which vitamin prevents scurvy?
- **Gold answer:** Vitamin C prevents scurvy.

## Generated Answer

Vitamin D prevents scurvy.

## Retrieved Documents

| Rank | Document | Score | Relevant | Snippet |
| --- | --- | ---: | --- | --- |
| 1 | `Scurvy` | 0.9900 | yes | Scurvy is caused by vitamin C deficiency. Vitamin C prevents scurvy. |

## Selected Context

- **ctx-scurvy** from `doc-scurvy` (rank 1, 12 tokens)
  Scurvy is caused by vitamin C deficiency. Vitamin C prevents scurvy.

## Evidence and Citations

- `doc-scurvy`: Vitamin C prevents scurvy.

## Evaluation Signals

| Metric | Value | Passed | Notes |
| --- | ---: | --- | --- |
| `faithfulness` | 0.0 | no | The answer changes vitamin C to vitamin D. |
| `answer_correctness` | 0.0 | no |  |

## Failure Modes

| Mode | Severity | Method | Rationale |
| --- | --- | --- | --- |
| `contradicted_by_context` | high | manual | The answer contradicts the selected context. |
| `unsupported_answer` | high | heuristic | A support-oriented metric indicates the answer is not grounded. |

## Likely Failure Source

Generation produced claims not supported by selected context. The answer makes claims not supported by the selected context.

## Inspect Next

- `contradicted_by_context`: mark the exact contradictory spans.
- `unsupported_answer`: compare answer claims against selected context.

## Diagnostic Notes

- **generation:** Retrieval and context selection succeeded, but generation changed the key entity.
