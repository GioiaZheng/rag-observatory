# Trace Schema

The trace schema records one RAG execution as a JSON object.

Required top-level fields:

- `metadata`
- `query`
- `retrieved_documents`
- `selected_context`
- `answer`

Optional top-level fields:

- `reranked_documents`
- `prompt`
- `metrics`
- `failures`
- `diagnostic_notes`
- `extra`

Unknown fields are rejected. Extension data must be placed under an explicit
`extra` object.

## Core Objects

- `metadata` records run ID, timestamp, dataset, component names, seed, and
  available pipeline stages.
- `query` records query ID, text, and optional gold answer.
- `retrieved_documents` records candidate evidence with rank, score, and
  optional relevance annotation.
- `reranked_documents` records post-reranking candidates when available.
- `selected_context` records the document chunks actually exposed to the
  generator.
- `prompt` records prompt content or a prompt template ID.
- `answer` records generated text and optional citations.
- `metrics` records evaluator outputs and pass/fail status.
- `failures` records manual or heuristic failure labels.
- `diagnostic_notes` records compact human notes by stage.

The schema is intentionally small in the first milestone and should evolve only
with tests.
