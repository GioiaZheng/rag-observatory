# SciFact Retrieval-depth Configuration Run

## Run Provenance

- **Execution date:** 2026-07-25
- **Dataset:** [BEIR SciFact](https://huggingface.co/datasets/BeIR/scifact)
- **Dataset license:** CC-BY-SA-4.0
- **BEIR archive MD5:** `5f7d1de60b170fc8027bb7898e2efca1`
- **Retriever:** deterministic local `bm25-python-v1`
- **Controlled values:** `retrieval_top_k=1,5`
- **Test query IDs:** `1`, `3`, `5`, `13`, `36`, `42`, `48`, `49`, `50`, `51`, `53`, `54`, `56`, `57`, `70`, `72`, `75`, `94`, `99`, `100`
- **Generated traces:** 40

The runner reads the official BEIR `corpus.jsonl`, `queries.jsonl`, and `qrels/test.tsv` files. It keeps the query set, BM25 implementation, top-1 context policy, deterministic extractive answer, and qrels evaluator fixed while changing only retrieval depth.

## Scope and Limitations

- This is an actual retrieval-stage run over public SciFact records, not a synthetic fixture.
- It is not a full generative RAG benchmark: generation is a deterministic copy of the top retrieved document.
- The current `retrieval_noise` heuristic fires when any retrieved document is marked irrelevant, so increasing top-k can raise that label even when recall improves.
- Twenty sorted test queries are an inspectable smoke experiment, not a statistical claim about all SciFact queries or other systems.

## Generated Configuration Report

- **Controlled variable:** `retrieval_top_k`
- **Dataset:** `BeIR/scifact`
- **Configurations:** 2
- **Fixed queries per configuration:** 20
- **Trace records:** 40

## Invariant Configuration

- **context_policy:** `top_1`
- **evaluator:** `scifact-qrels-membership-v1`
- **generator:** `extractive-first-document-v1`
- **retriever_algorithm:** `bm25-python-v1`

## Observed Failure Signals

| Configuration | Traces | Failure-labelled traces | Signals |
| --- | ---: | ---: | --- |
| `retrieval_top_k=1` | 20 | 7 | `context_pollution` 7/20, `retrieval_miss` 7/20, `retrieval_noise` 7/20, `wrong_citation` 7/20 |
| `retrieval_top_k=5` | 20 | 20 | `context_pollution` 7/20, `context_truncation` 1/20, `retrieval_miss` 6/20, `retrieval_noise` 20/20, `wrong_citation` 7/20 |

## Evaluation Metric Summary

| Configuration | Metric | Mean numeric value | Passed |
| --- | --- | ---: | ---: |
| `retrieval_top_k=1` | `retrieval_hit` | 0.650 | 13/20 |
| `retrieval_top_k=5` | `retrieval_hit` | 0.700 | 14/20 |

## Stage Attribution

| Stage | `retrieval_top_k=1` | `retrieval_top_k=5` | Rate spread |
| --- | ---: | ---: | ---: |
| `query` | 0/20 (0%) | 0/20 (0%) | 0% |
| `retrieval` | 7/20 (35%) | 20/20 (100%) | 65% |
| `reranking` | 0/20 (0%) | 0/20 (0%) | 0% |
| `context` | 7/20 (35%) | 7/20 (35%) | 0% |
| `prompt` | 0/20 (0%) | 0/20 (0%) | 0% |
| `generation` | 7/20 (35%) | 7/20 (35%) | 0% |
| `evaluation` | 0/20 (0%) | 0/20 (0%) | 0% |
| `diagnostics` | 0/20 (0%) | 0/20 (0%) | 0% |

## Result

The largest observed failure-rate change is localized to `retrieval`.

## Per-query Changes

| Query ID | `retrieval_top_k=1` | `retrieval_top_k=5` |
| --- | --- | --- |
| `1` | `retrieval_miss`, `retrieval_noise`, `context_pollution`, `wrong_citation` | `retrieval_miss`, `retrieval_noise`, `context_pollution`, `wrong_citation` |
| `100` | none | `retrieval_noise` |
| `13` | `retrieval_miss`, `retrieval_noise`, `context_pollution`, `wrong_citation` | `retrieval_miss`, `retrieval_noise`, `context_pollution`, `wrong_citation` |
| `3` | none | `retrieval_noise` |
| `36` | `retrieval_miss`, `retrieval_noise`, `context_pollution`, `wrong_citation` | `retrieval_miss`, `retrieval_noise`, `context_pollution`, `wrong_citation` |
| `42` | `retrieval_miss`, `retrieval_noise`, `context_pollution`, `wrong_citation` | `retrieval_noise`, `context_truncation`, `context_pollution`, `wrong_citation` |
| `48` | `retrieval_miss`, `retrieval_noise`, `context_pollution`, `wrong_citation` | `retrieval_miss`, `retrieval_noise`, `context_pollution`, `wrong_citation` |
| `49` | none | `retrieval_noise` |
| `5` | none | `retrieval_noise` |
| `50` | none | `retrieval_noise` |
| `51` | none | `retrieval_noise` |
| `53` | none | `retrieval_noise` |
| `54` | `retrieval_miss`, `retrieval_noise`, `context_pollution`, `wrong_citation` | `retrieval_miss`, `retrieval_noise`, `context_pollution`, `wrong_citation` |
| `56` | none | `retrieval_noise` |
| `57` | none | `retrieval_noise` |
| `70` | none | `retrieval_noise` |
| `72` | `retrieval_miss`, `retrieval_noise`, `context_pollution`, `wrong_citation` | `retrieval_miss`, `retrieval_noise`, `context_pollution`, `wrong_citation` |
| `75` | none | `retrieval_noise` |
| `94` | none | `retrieval_noise` |
| `99` | none | `retrieval_noise` |

## Interpretation Boundary

The report compares exported run outputs for the same query IDs and checks that all recorded configuration fields except the controlled variable are invariant. It reports observed stage-level associations; it does not establish causal effects outside these runs.
