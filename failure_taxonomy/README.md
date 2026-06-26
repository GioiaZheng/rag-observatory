# Failure Taxonomy Seeds

This directory collects early research notes for a `rag-observatory` failure
taxonomy. The notes are intentionally compact and revision-friendly. They are
not final benchmark categories, and they should evolve with reviewed traces,
diagnostic reports, and empirical error analysis.

## Draft Primary Categories

| Primary Category | Seed File | Secondary Examples | Working Definition |
| --- | --- | --- | --- |
| Retrieval Failure | [retrieval_failure.md](retrieval_failure.md) | Relevant document missing | The retrieval stage fails to surface evidence needed for a correct answer. |
| Ranking Failure | [reranking_failure.md](reranking_failure.md) | Correct document ranked too low | Evidence exists in candidates, but ordering makes it unlikely to be used. |
| Context Failure | [context_pollution.md](context_pollution.md) | Context pollution / redundancy | Selected context contains distracting, redundant, or misleading material. |
| Prompt Failure | [missing_evidence.md](missing_evidence.md) | Important evidence omitted | The prompt or selected context omits evidence that was available upstream. |
| Generation Failure | [unsupported_generation.md](unsupported_generation.md) | Unsupported claim / hallucination | The generated answer makes claims not supported by the selected evidence. |
| Evaluation Failure | [evaluation_disagreement.md](evaluation_disagreement.md) | Metric disagrees with human judgment | Automated evaluation signals disagree with reviewed trace-level judgment. |

## Intended Use

These files are seeds for future paper writing and taxonomy refinement:

- convert observed trace failures into stable terminology;
- separate pipeline-stage causes from surface symptoms;
- define observable signals that can be tested locally;
- record examples without claiming benchmark completeness;
- keep manual, heuristic, model-based, and learned labels comparable.

## Boundary Notes

The taxonomy should remain trace-based. A category should be added or promoted
only when repeated traces show a diagnostic pattern that existing labels cannot
describe clearly.

The current public schema uses smaller operational labels under
`docs/failure_taxonomy.md`. This directory is broader and more research-facing:
it may group several operational labels under one paper-level category.
