# Failure Taxonomy

The initial taxonomy is small and stable enough for toy traces and early
diagnostic reports.

| Mode | Definition | Initial Detection |
| --- | --- | --- |
| `retrieval_miss` | Retrieved evidence does not contain what is needed to answer. | Heuristic or manual |
| `retrieval_noise` | Retrieval includes irrelevant or distracting evidence. | Heuristic |
| `reranking_error` | Reranking promotes weaker evidence over stronger evidence. | Heuristic |
| `context_truncation` | Relevant retrieved evidence is not selected into context. | Heuristic |
| `context_pollution` | Selected context contains irrelevant or misleading evidence. | Heuristic |
| `unsupported_answer` | Answer claims are not supported by selected context. | Heuristic or manual |
| `contradicted_by_context` | Answer conflicts with available context. | Manual |
| `missing_citation` | Expected citation references are absent. | Heuristic |
| `wrong_citation` | Citations point to evidence that does not support the answer. | Heuristic |
| `ambiguous_question` | Query is under-specified. | Manual |
| `metric_disagreement` | Evaluation signals disagree about success or failure. | Heuristic |
| `unknown` | Failure cannot yet be localized. | Manual |

Heuristic labels are intentionally conservative and depend on fields already
present in the trace.
