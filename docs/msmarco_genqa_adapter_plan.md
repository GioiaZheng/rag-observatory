# msmarco-genqa Adapter Plan

`rag-observatory` is related to `msmarco-genqa`, but the projects should stay
separate.

`msmarco-genqa` owns retrieval, reranking, generation, benchmark evaluation,
and reproducibility workflows. `rag-observatory` should only ingest selected
run outputs into trace objects so those runs can be inspected, reported, and
compared.

This document is a planning note. It does not introduce adapter code.

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

## Suggested Future Implementation

1. Add a synthetic `msmarco-genqa` export fixture under `tests/fixtures/`.
2. Implement a mapper from that export object to `RagTrace`.
3. Validate the trace using the existing schema validation path.
4. Add a CLI only if the mapper proves stable, for example:

```bash
rag-observe ingest-msmarco-genqa export.json --output trace.json
```

5. Use the existing report and compare commands on the produced trace.

## Validation Expectations

Future adapter work should include:

- unit tests for the mapper;
- a schema validation test for the produced trace;
- a report or comparison smoke test using synthetic data;
- no real benchmark artifacts committed to the repository.
