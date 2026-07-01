# Trace-Based Failure Analysis for RAG Systems

## Abstract

Retrieval-Augmented Generation systems often fail in ways that are hard to
understand from final answer accuracy alone. A failed answer may come from
missing evidence, a reranker that suppresses a useful document, polluted
context, omitted prompt evidence, unsupported generation, or disagreement
between automated metrics and human judgment. `rag-observatory` is a
research-engineering toolkit for making those failure paths inspectable through
local traces, a failure taxonomy, evidence-aware reports, and reproducible
small examples.

This report describes the current artifact set and the evidence path toward a
more complete observability and error-analysis toolkit. The current repository
does not claim to be a full RAG pipeline, a leaderboard, or a production
monitoring system. Its goal is narrower: help researchers explain why a RAG run
succeeds or fails.

## Motivation

Aggregate scores can show that a system regressed, but they rarely explain
where the regression entered the pipeline. RAG systems need diagnosis at
multiple stages:

- retrieval may miss relevant evidence;
- reranking may demote the correct document;
- context construction may include distracting or redundant passages;
- prompt construction may omit important evidence;
- generation may produce unsupported claims or incorrect citations;
- evaluation may disagree with human review.

The core research question is whether a small, inspectable trace format can
make those failures easier to reproduce and review.

## System Goal and Non-Goals

The project goal is:

> A reproducible observability and error-analysis toolkit for RAG systems.

The repository focuses on trace schemas, failure taxonomy, evidence analysis,
diagnostic reports, and small reproducible examples. It intentionally avoids
becoming another RAG pipeline. Pipeline implementations should live in projects
such as `msmarco-genqa`; `rag-observatory` should consume their exported traces
and explain what happened.

Current non-goals:

- no broad benchmark or leaderboard claim;
- no production telemetry backend;
- no claim that heuristic labels replace human review;
- no claim that synthetic fixtures represent real dataset-scale behavior;
- no dependency on private provider logs.

## Artifact Map

| Artifact | Purpose |
| --- | --- |
| `make reproduce-small` | Runs the small reproducible workflow from a clean checkout. |
| `examples/reproduce-small/` | Contains public-safe input traces and benchmark manifests. |
| `docs/trace_stage_contract.md` | Defines retrieval, reranking, context, prompt, generation, and evaluation trace stages. |
| `docs/opentelemetry_alignment.md` | Describes the exporter-agnostic internal run/span model. |
| `failure_taxonomy/` | Stores paper-oriented failure taxonomy seeds. |
| `docs/evaluator_protocol.md` | Documents context relevance, faithfulness, answer relevance, provenance, and abstention. |
| `docs/report_artifacts.md` | Describes Markdown, HTML, and SVG diagnostic report artifacts. |
| `docs/benchmark_comparison.md` | Defines the small failure-pattern benchmark summary, explicitly not a leaderboard. |
| `docs/research_evidence_plan.md` | Lists evidence needed before stronger paper or system-demo claims. |

## Trace Schema and Stage Contract

The public trace schema represents a RAG run as observable evidence rather than
hidden pipeline state. Required fields identify the run, query, retrieved
documents, selected context, and generated answer. Optional fields add
reranked documents, prompt details, quality metrics, claim-level support
judgments, failure labels, and diagnostic notes.

The full-stage fixture at
`tests/fixtures/stage_contract/full_observability_trace.json` demonstrates a
single synthetic run with retrieval, reranking, context selection, prompt
construction, generation, citations, evaluation metrics, and diagnostic notes.
The companion run/span fixture at
`tests/fixtures/stage_contract/opentelemetry_aligned_run.json` shows how the
same case can be represented as stage spans without requiring an OpenTelemetry
exporter.

This separation matters: the schema records what the pipeline did, while the
diagnostic layer interprets where the failure became visible.

## Failure Taxonomy

The taxonomy is deliberately operational. It describes observable failure
surfaces such as retrieval failure, reranking failure, context pollution,
missing evidence, unsupported generation, and evaluation disagreement. These
labels are not ground truth by themselves. They are review aids that should
point to trace evidence.

The current implementation includes deterministic heuristic labels and
reviewed label fixtures. This is useful for regression tests and small reports,
but it remains incomplete. Future work should compare heuristic labels against
human-reviewed labels, semantic evaluators, and optional model-based judges
with abstentions reported separately.

## Reproducible Small Workflow

The current reproduction path is intentionally small:

```bash
make reproduce-small
```

The command writes artifacts under `outputs/reproduce-small/`:

- `manifest.json`;
- normalized trace JSON under `traces/`;
- Markdown and HTML diagnostic reports under `reports/`;
- an SVG screenshot preview;
- benchmark comparison reports.

The generated files are not committed because they are run outputs. The checked
inputs and code paths are committed so the artifacts can be regenerated and
reviewed locally or in CI.

The small workflow is not dataset-scale evidence. It is a smoke test that ties
the trace schema, report renderer, failure taxonomy, and benchmark-summary path
together in one reproducible command.

## Diagnostic Reports

Reports are designed to answer practical review questions:

- Which query and run are being diagnosed?
- Which documents were retrieved and selected?
- Which evaluation signals passed or failed?
- Which failure labels were inferred or reviewed?
- Which evidence supports each interpretation?

Markdown reports are useful for code review and experiment logs. HTML reports
and SVG previews make the same information easier to inspect visually. The
current HTML artifact is static and local-first; it is not a dashboard.

## Benchmark Comparison

The small benchmark summary compares failure patterns across pipeline variants.
It reports run metadata, evaluation signals, failure-label distributions, and a
first-versus-last interpretation. This is useful for checking whether a
pipeline change moves the observed failure surface, for example from missing
evidence to context pollution.

The current benchmark fixture is synthetic and small. It should not be used to
claim broad retrieval or generation performance. Larger experiments need fixed
datasets, documented preprocessing, artifact hashes or DVC pointers, reviewed
labels, and scaling measurements.

## Relationship to `msmarco-genqa`

`msmarco-genqa` can produce RAG pipeline outputs: queries, candidates, reranked
documents, generated answers, citations, and evaluation metadata.
`rag-observatory` should consume those exports and produce diagnostics. This
boundary keeps the research story focused:

- `msmarco-genqa` owns data generation and pipeline variants;
- `rag-observatory` owns trace contracts, failure analysis, reports, and
  reproducible observability artifacts.

Together, the two projects can support the larger claim:

> The contribution is not only building a RAG pipeline; it is explaining why a
> RAG pipeline fails.

## Limitations

Current limitations are important:

- most checked examples are synthetic;
- heuristic labels are useful but not enough for research claims;
- no dataset-scale benchmark results are reported here;
- no model-based judge or supervised failure classifier is implemented yet;
- no OpenTelemetry exporter is implemented yet;
- large traces and corpus artifacts still need careful versioning and storage;
- human review protocols need more examples before paper-level conclusions.

These limitations are not cosmetic. They define the next evidence required
before making stronger public claims.

## Future Work

Near-term work should prioritize:

1. adapters from public pipeline outputs into the stable trace schema;
2. reviewed labels and quality scores with disagreement notes;
3. report generation from non-toy `msmarco-genqa` exports;
4. evals-as-code quality gates for trace fixtures and small experiments;
5. JSONL-scale parsing and memory measurements;
6. optional model-based judge outputs after the human-review protocol is
   inspectable;
7. a paper-ready report with figures generated from reproducible artifacts.

The strongest version of the project is not a larger demo. It is a disciplined
evidence chain: trace, diagnosis, report, comparison, and reproducible
artifact.
