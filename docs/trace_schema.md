# Trace Schema

The trace schema records one RAG execution as a JSON object.

Required top-level fields:

- `metadata`
- `query`
- `retrieved_documents`
- `selected_context`
- `answer`

Optional top-level fields:

- `conversation`
- `reranked_documents`
- `prompt`
- `metrics`
- `claims`
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
- `conversation` records optional multi-turn metadata such as conversation ID,
  turn ID, original turn text, rewritten standalone query, prior-turn
  references, and answerability.
- `query` records query ID, text, and optional gold answer.
- `retrieved_documents` records candidate evidence with rank, score, and
  optional relevance annotation.
- `reranked_documents` records post-reranking candidates when available.
- `selected_context` records the document chunks actually exposed to the
  generator.
- `prompt` records prompt content or a prompt template ID.
- `answer` records generated text and optional citations.
- `metrics` records evaluator outputs and pass/fail status.
- `claims` records optional claim-level support and attribution diagnoses for
  generated answer claims.
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

## Conversational Traces

Single-turn traces remain valid when `conversation` is omitted or `null`.
Conversational RAG runs should be represented as one validated trace per turn,
with shared `conversation.conversation_id` and stable `conversation.turn_id`
values. This keeps retrieval candidates, selected context, answers, metrics,
and failure labels local to the turn that produced them.

```json
{
  "conversation": {
    "conversation_id": "conv-penicillin",
    "turn_id": "turn-002",
    "turn_index": 2,
    "original_turn_text": "When was it discovered?",
    "standalone_query": "When was penicillin discovered?",
    "prior_turn_references": ["turn-001"],
    "answerability": "answerable"
  }
}
```

`answerability` must be `answerable`, `unanswerable`, or `unknown`. A
conversation report can group multiple per-turn traces and distinguish
retrieval failures associated with query rewriting from failures caused by
insufficient evidence for unanswerable turns.

## Claim-Level Diagnosis

`claims` is an optional list of externally reviewed or adapter-provided claim
diagnoses. It is not produced by the schema itself. Each claim records claim
text, optional answer span offsets, evidence references, a support label,
failure attribution category, optional confidence, reviewer source, and
diagnostic notes.

Evidence references must include `doc_id` or `context_id` when present, and any
referenced IDs must exist in `retrieved_documents`, `reranked_documents`, or
`selected_context`. Claims labeled `insufficient_evidence` may use an empty
evidence list.

The detailed contract is documented in
[`docs/claim_level_diagnosis.md`](claim_level_diagnosis.md).
