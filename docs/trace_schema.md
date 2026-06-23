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

## Minimal Valid Trace

This is the smallest shape accepted by the current schema:

```json
{
  "metadata": {
    "run_id": "toy-run-001",
    "timestamp": "2026-06-22T00:00:00Z"
  },
  "query": {
    "query_id": "q-001",
    "text": "What is RAG observability used for?"
  },
  "retrieved_documents": [],
  "selected_context": [],
  "answer": {
    "text": "RAG observability is used to inspect and diagnose RAG behavior."
  }
}
```

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

## Optional Fields Example

Optional fields should add diagnostic context without turning the trace into a
pipeline implementation:

```json
{
  "metadata": {
    "run_id": "toy-run-002",
    "timestamp": "2026-06-22T00:00:00Z",
    "dataset": "toy_rag_observatory",
    "retriever": "toy-bm25",
    "generator": "toy-generator",
    "pipeline_stages": {
      "retrieval": true,
      "context_selection": true,
      "generation": true,
      "citations": true,
      "evaluation": true
    }
  },
  "query": {
    "query_id": "q-scurvy",
    "text": "Which vitamin prevents scurvy?",
    "gold_answer": "Vitamin C prevents scurvy."
  },
  "retrieved_documents": [
    {
      "doc_id": "doc-scurvy",
      "title": "Scurvy",
      "text": "Scurvy is caused by vitamin C deficiency. Vitamin C prevents scurvy.",
      "score": 0.99,
      "rank": 1,
      "is_relevant": true
    }
  ],
  "selected_context": [
    {
      "context_id": "ctx-scurvy",
      "doc_id": "doc-scurvy",
      "text": "Vitamin C prevents scurvy.",
      "rank": 1,
      "token_count": 4
    }
  ],
  "prompt": {
    "template_id": "toy-qa-v1",
    "variables": {
      "instruction": "Answer using the provided context."
    }
  },
  "answer": {
    "text": "Vitamin C prevents scurvy.",
    "citations": [
      {
        "doc_id": "doc-scurvy",
        "quote": "Vitamin C prevents scurvy."
      }
    ]
  },
  "metrics": [
    {
      "name": "faithfulness",
      "value": 1.0,
      "passed": true,
      "threshold": 0.8
    }
  ],
  "failures": [],
  "diagnostic_notes": [
    {
      "stage": "summary",
      "note": "Toy success case with selected evidence and citation."
    }
  ]
}
```

## Extension Data

Every object-level `extra` field must be a JSON object. Use it for explicit
extension data that is not stable enough to become part of the public schema:

```json
{
  "metadata": {
    "run_id": "toy-run-extra",
    "timestamp": "2026-06-22T00:00:00Z",
    "extra": {
      "experiment_group": "local-debug"
    }
  },
  "query": {
    "query_id": "q-extra",
    "text": "What should go in extra?"
  },
  "retrieved_documents": [],
  "selected_context": [],
  "answer": {
    "text": "Use extra for explicit extension data."
  },
  "extra": {
    "trace_source": "synthetic-example"
  }
}
```

Do not place unknown fields beside schema fields. For example,
`metadata.experiment_group` is rejected, while
`metadata.extra.experiment_group` is accepted.
