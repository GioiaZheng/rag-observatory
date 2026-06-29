# msmarco-genqa Adapter Plan

`rag-observatory` is related to `msmarco-genqa`, but the projects should stay
separate.

`msmarco-genqa` owns retrieval, reranking, generation, benchmark evaluation,
and reproducibility workflows. `rag-observatory` should only ingest selected
run outputs into trace objects so those runs can be inspected, reported, and
compared.

This document records the adapter boundary and the first implemented synthetic
export contract.

## Observed Source Surfaces

The related repository includes retrieval, reranking, generation, evaluation,
reporting, provenance, and generated artifact paths. Candidate future inputs
should come from stable exported files rather than internal runtime objects.

Candidate source areas:

- `outputs/*/provenance.backfill.json`
- `reports/generated/artifacts/*.json`
- `src/msmarco_genqa/retrieval/`
- `src/msmarco_genqa/reranking/`
- `src/msmarco_genqa/generation/`
- `src/msmarco_genqa/rag_eval.py`
- `src/msmarco_genqa/pipeline.py`

The first adapter should not depend on these modules directly. It should accept
a small JSON export that can be produced by `msmarco-genqa` or by a synthetic
fixture.

## Minimal Mapping

The adapter should map one run for one query into a `RagTrace`.

| Trace field | Candidate source |
| --- | --- |
| `metadata.run_id` | Run name, provenance ID, or explicit export ID. |
| `metadata.dataset` | Dataset or benchmark name, such as MS MARCO or TREC DL. |
| `metadata.config_hash` | Config hash or provenance hash when available. |
| `metadata.code_version` | Commit SHA or recorded code version when available. |
| `metadata.retriever` | Retrieval method, such as BM25, dense, or hybrid. |
| `metadata.reranker` | Reranker name when reranking was used. |
| `metadata.generator` | Generator or generation configuration label. |
| `query.query_id` | Query ID from the run or evaluation set. |
| `query.text` | Query text. |
| `query.gold_answer` | Reference answer when available. |
| `retrieved_documents` | Initial retrieval candidates with rank, score, text, and relevance if known. |
| `reranked_documents` | Post-reranking candidates with rank and score when available. |
| `selected_context` | Context-packing output actually exposed to generation. |
| `prompt` | Prompt template ID or prompt text when explicitly exported. |
| `answer` | Generated answer text and citations when available. |
| `metrics` | Retrieval, grounding, faithfulness, answer quality, or benchmark signals. |
| `failures` | Manual labels only, unless a future export includes stable labels. |
| `diagnostic_notes` | Compact notes about export assumptions or missing fields. |

## Boundary Rules

The adapter should:

- be optional and thin;
- transform explicit export data into `RagTrace`;
- use synthetic fixtures for tests;
- preserve provenance in `metadata.extra` or `trace.extra` when it does not yet
  belong in the public schema;
- leave failure classification to `rag-observatory` unless labels are explicitly
  exported.

The adapter should not:

- run retrieval, reranking, generation, or benchmark evaluation;
- import heavy model or dataset dependencies;
- parse notebooks;
- copy datasets, caches, generated reports, transcripts, or large outputs into
  this repository;
- duplicate `msmarco-genqa` pipeline logic.

## Implemented Synthetic Export Contract

The first adapter accepts a small JSON export with this top-level shape:

- `format`: fixed value `msmarco-genqa.trace-export.v1`
- `run`: run metadata mapped to `RagTrace.metadata`
- `query`: query text and optional reference answer
- `retrieved_documents`: initial retrieval candidates
- `reranked_documents`: optional reranked candidates, or `null`
- `selected_context`: context chunks exposed to generation
- `prompt`: optional prompt object, or `null`
- `answer`: generated answer and optional citations
- `metrics`: optional evaluation signals
- `failures`: optional explicitly exported labels
- `diagnostic_notes`: optional source notes
- `extra`: export-level metadata preserved under `trace.extra`

Missing optional export fields are recorded under
`trace.extra.msmarco_genqa_adapter.missing_optional_fields` and surfaced as an
adapter diagnostic note.

The mapper is available through Python:

```python
from rag_observatory.adapters.msmarco_genqa import load_msmarco_genqa_trace

trace = load_msmarco_genqa_trace("export.json")
```

And through the CLI:

```bash
rag-observe ingest-msmarco-genqa export.json --output trace.json
rag-observe report trace.json --output report.md
```

## Suggested Future Implementation

1. Keep the synthetic export fixture stable as the adapter contract evolves.
2. Add a second fixture with reranking and prompt data.
3. Add a fixture with explicitly exported manual labels.
4. Use the existing report and compare commands on produced traces.
5. Add non-toy exports only through DVC or another large-artifact workflow.

## Validation Expectations

Future adapter work should include:

- unit tests for the mapper;
- a schema validation test for the produced trace;
- a report or comparison smoke test using synthetic data;
- no real benchmark artifacts committed to the repository.
