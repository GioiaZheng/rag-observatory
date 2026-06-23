# Failure Taxonomy

The initial taxonomy is small and stable enough for toy traces and early
diagnostic reports.

## Detection Methods

| Method | Meaning |
| --- | --- |
| `manual` | Assigned by a human reviewer from trace inspection. |
| `heuristic` | Assigned by deterministic rules over fields already present in the trace. |
| `model_based` | Reserved for future model-assisted checks with explicit inputs and outputs. |
| `future` | Reserved for planned detection methods that are not implemented yet. |

Heuristic labels are intentionally conservative. They should point to likely
inspection areas, not claim complete causal proof.

## Modes

| Mode | Definition | Initial Detection | Compact Example |
| --- | --- | --- | --- |
| `retrieval_miss` | Retrieved evidence does not contain what is needed to answer. | Heuristic or manual | No documents are retrieved, or all retrieved documents are annotated as not relevant. |
| `retrieval_noise` | Retrieval includes irrelevant or distracting evidence. | Heuristic | A relevant document is retrieved, but irrelevant documents are also present. |
| `reranking_error` | Reranking promotes weaker evidence over stronger evidence. | Heuristic | The top reranked document is annotated not relevant while a lower reranked document is relevant. |
| `context_truncation` | Relevant retrieved evidence is not selected into context. | Heuristic | A relevant retrieved document exists, but no selected context chunk references it. |
| `context_pollution` | Selected context contains irrelevant or misleading evidence. | Heuristic | A selected context chunk comes from a document annotated as not relevant. |
| `unsupported_answer` | Answer claims are not supported by selected context. | Heuristic or manual | A faithfulness, support, or groundedness metric fails. |
| `contradicted_by_context` | Answer conflicts with available context. | Manual | Context says vitamin C prevents scurvy, but the answer says vitamin D. |
| `missing_citation` | Expected citation references are absent. | Heuristic | Citation capture is enabled, but `answer.citations` is empty. |
| `wrong_citation` | Citations point to evidence that does not support the answer. | Heuristic | The answer cites a document annotated as not relevant. |
| `ambiguous_question` | Query is under-specified. | Manual | The query asks for "the capital" without identifying the country. |
| `metric_disagreement` | Evaluation signals disagree about success or failure. | Heuristic | One metric passes while another metric fails. |
| `unknown` | Failure cannot yet be localized. | Manual | A reviewer flags the run but cannot assign a more specific mode. |

## Overlap Rules

Failure labels can overlap because a trace may expose problems at multiple
pipeline stages. For example, `retrieval_noise` can coexist with
`context_pollution` when an irrelevant retrieved document is also selected into
the prompt. `context_truncation` can coexist with `unsupported_answer` when
necessary evidence was retrieved but not exposed to the generator, and the
answer then becomes unsupported.

Manual labels are preserved when heuristic labels are added. When a more
specific label is available, prefer it over `unknown`.

The taxonomy should grow only when existing labels cannot describe a repeated
diagnostic pattern in traces.
