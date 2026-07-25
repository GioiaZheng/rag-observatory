# OpenTelemetry Alignment

`rag-observatory` is OpenTelemetry-aligned without requiring an OpenTelemetry
SDK in the core package. The project accepts OTLP/HTTP JSON exports containing
OpenInference spans through a tested offline adapter, while keeping its stable
RAG diagnosis schema as the reporting contract. A network receiver or OTLP
exporter remains a separate production concern.

This keeps the project focused on its research-engineering purpose: explaining
where and why a RAG run succeeded or failed.

## Design Position

OpenTelemetry traces model work as spans. A span represents a unit of work and
typically carries a name, parent span ID, timestamps, span context, attributes,
events, links, and status. `rag-observatory` can borrow that shape without
requiring a tracing backend.

The internal model should preserve the existing public trace schema while
making stage-level execution explicit:

```text
Run
  Query
  Retrieval
  Reranking
  Context
  Prompt
  Generation
  Evaluation
  Diagnostics
```

`Context` covers context selection, truncation, compression, and pollution
analysis. `Diagnostics` records human-review notes, inferred failure labels,
and cross-stage interpretation.

## Internal Run Model

Each run should have stable identifiers and a list of stage spans:

| Field | Purpose |
| --- | --- |
| `run_id` | Human-readable run identifier, compatible with current `metadata.run_id`. |
| `trace_id` | Stable trace identifier shared by all stage spans in the run. |
| `schema_version` | Version of the internal run model, independent of exporter formats. |
| `started_at` / `ended_at` | Run-level timestamps when available. |
| `attributes` | Low-cardinality metadata such as dataset, experiment, retriever, generator, and config hash. |
| `spans` | Ordered stage spans for query, retrieval, reranking, context, prompt, generation, evaluation, and diagnostics. |
| `links` | Optional relations to baseline runs, variants, previous turns, or parent experiments. |

Keep raw prompts, raw documents, and generated answers out of run attributes.
They belong in stage `input`, `output`, or evidence payloads where they can be
redacted, summarized, or omitted for public reports.

## Stage Span Contract

Every stage span should use the same diagnostic envelope:

| Field | Purpose |
| --- | --- |
| `span_id` | Stable span identifier within the run. |
| `parent_span_id` | Parent span ID, normally the root run span. |
| `name` | Stable span name such as `rag.retrieval` or `rag.evaluation`. |
| `stage` | Normalized stage enum. |
| `started_at` / `ended_at` | Stage timestamps when available. |
| `latency_ms` | Stage latency, computed or supplied. |
| `status` | `unset`, `ok`, or `error`. |
| `error_type` | Optional failure or operational error category. |
| `input` | Stage input or references to upstream outputs. |
| `output` | Stage output or references to produced artifacts. |
| `metrics` | Stage-local evaluator or operational measurements. |
| `attributes` | Low-cardinality metadata useful for grouping and filtering. |
| `events` | Timestamped notable events, warnings, or review annotations. |
| `links` | Optional links to related spans or runs. |

This envelope lets reports compare stages consistently: latency regression,
quality regression, retrieval miss, reranking error, context pollution,
unsupported generation, or evaluator disagreement can all be represented as
stage-local facts plus cross-stage diagnosis.

## RAG Stage Map

| Stage | Span name | Input | Output | Common metrics | Failure signals |
| --- | --- | --- | --- | --- | --- |
| Query | `rag.query` | User turn, conversation state | Standalone query, answerability | rewrite latency, answerability confidence | `query_drift`, `answerability_mismatch` |
| Retrieval | `rag.retrieval` | Query text, retrieval config | Candidate documents with ranks and scores | recall@k, relevant count, latency | `retrieval_miss`, `retrieval_noise` |
| Reranking | `rag.reranking` | Retrieved candidates, reranker config | Reranked candidates | rank delta, latency | `reranking_error`, `useful_evidence_suppressed` |
| Context | `rag.context` | Candidate documents, token budget | Selected or compressed context | token count, evidence coverage | `context_truncation`, `context_pollution`, `support_sentence_removed` |
| Prompt | `rag.prompt` | Selected context, template variables | Prompt text or template reference | prompt tokens, construction latency | `missing_variable`, `omitted_evidence`, `instruction_conflict` |
| Generation | `rag.generation` | Prompt or prompt reference | Answer text, citations, claims | output tokens, latency, citation count | `unsupported_answer`, `missing_citation`, `wrong_citation` |
| Evaluation | `rag.evaluation` | Trace outputs, expected labels | Scores, thresholds, pass/fail state | faithfulness, relevance, provenance, abstention | `metric_disagreement`, `failed_quality_gate` |
| Diagnostics | `rag.diagnostics` | Stage spans and evaluator results | Failure taxonomy, notes, report summary | label confidence, review coverage | `evaluation_disagreement`, `needs_human_review` |

## Attribute Rules

Attributes should stay small, stable, and useful for aggregation:

- Good attributes: dataset name, experiment ID, retriever family, top-k,
  reranker family, compression mode, generator family, evaluator version,
  config hash.
- Avoid attributes: full query text, full prompt text, full document text,
  generated answer text, raw stack traces, user identifiers.
- Put large or sensitive content in payload fields that can be redacted or
  omitted from exported telemetry.
- Prefer references such as `doc_id`, `context_id`, `prompt_template_id`, and
  `claim_id` when linking evidence across stages.

## Quality Gates

The same run model can support CI quality gates without turning reports into
one-off tables:

| Gate | Span source | Example rule |
| --- | --- | --- |
| Retrieval quality | `rag.retrieval` | Fail if oracle evidence is absent from top-k for reviewed examples. |
| Context quality | `rag.context` | Fail if selected context omits known supporting evidence. |
| Generation quality | `rag.generation` + `rag.evaluation` | Fail if faithfulness drops below threshold. |
| Citation quality | `rag.generation` | Fail if citation capture is enabled but no citations are emitted. |
| Regression quality | Linked baseline and candidate runs | Fail if failure labels increase versus baseline. |
| Latency quality | Any stage span | Warn or fail if p95 stage latency regresses beyond tolerance. |

Quality gates should report the responsible stage, the metric that changed, and
the evidence needed for review. This keeps evaluation reproducible and makes
regressions explainable.

## Mapping From Public Trace Fields

The current public trace schema can map into the internal run model without
replacing the JSON trace contract:

| Public Trace Field | Internal Run Span | Notes |
| --- | --- | --- |
| `metadata` | run attributes | Keep low-cardinality run metadata such as dataset, experiment, model family, and config hash. |
| `query` / `conversation` | `rag.query` | Record query identity and rewrite references, not full user history in attributes. |
| `retrieved_documents` | `rag.retrieval` | Preserve ranks, scores, relevant-document flags, and candidate counts. |
| `reranked_documents` | `rag.reranking` | Preserve post-rerank order and rank deltas when reranking is enabled. |
| `selected_context` | `rag.context` | Preserve context document IDs, positions, token counts, and evidence coverage. |
| `prompt` | `rag.prompt` | Use template IDs and prompt references when raw prompt text should be redacted. |
| `answer` / `claims` | `rag.generation` | Track answer references, citations, claim support, and citation errors. |
| `metrics` / `failures` / `diagnostic_notes` | `rag.evaluation` and `rag.diagnostics` | Separate evaluator scores from cross-stage failure interpretation. |

## Implemented OTLP/JSON Ingestion

The `ingest-otlp-openinference` command reads the standard OTLP
`resourceSpans` / `scopeSpans` / `spans` envelope and decodes typed OTLP
`AnyValue` attributes. It maps OpenInference `RETRIEVER`, `RERANKER`, and `LLM`
spans into the public trace schema.

The adapter deliberately leaves `selected_context` empty because the
OpenInference retrieval and reranking document attributes do not prove which
chunks entered the final prompt. It records that missing observability as a
diagnostic note instead of inventing context selection. See
[OTLP + OpenInference Ingestion](otlp_openinference_ingestion.md) for the exact
mapping and boundaries.

## Implemented Public Trace Conversion

The `run-report` command now executes the mapping described above:

```bash
rag-observe run-report TRACE.json \
  --run-output outputs/internal-run.json \
  --output outputs/stage-report.md
```

`internal_run_from_trace` converts every public `RagTrace` into the ordered
query, retrieval, reranking, context, prompt, generation, evaluation, and
diagnostics spans. Optional unobserved stages remain explicit with `unset`
status. Large query, document, prompt, answer, claim, and review payloads stay
inside span input/output fields, while run and span attributes contain only
grouping metadata.

The stage-aware Markdown report consumes the converted spans rather than
reclassifying a flat trace. Failure signals are emitted as events on the
responsible stage, and the diagnostics span links back to those source spans.
Unknown or explicitly unlocalized labels remain on diagnostics instead of
being assigned to a stage without evidence.

## Checked Fixtures

The synthetic fixture
[`tests/fixtures/stage_contract/opentelemetry_aligned_run.json`](../tests/fixtures/stage_contract/opentelemetry_aligned_run.json)
shows the same diagnostic case as
[`tests/fixtures/stage_contract/full_observability_trace.json`](../tests/fixtures/stage_contract/full_observability_trace.json)
in a run-plus-spans shape. It is intentionally exporter-agnostic: the fixture
borrows span structure from tracing systems but does not require an
OpenTelemetry SDK or OTLP backend.

The fixture is used by tests to check that:

- all RAG stages share the same diagnostic envelope;
- large text payloads stay out of low-cardinality attributes;
- stage-local failure signals can be connected to cross-stage diagnostics.

The synthetic OTLP fixture
[`tests/fixtures/openinference/otlp_rag_trace.json`](../tests/fixtures/openinference/otlp_rag_trace.json)
checks the actual importer, including OTLP typed values, OpenInference flattened
document attributes, multi-trace selection, the CLI path, and downstream report
generation.

## Migration Path

1. Keep the current trace schema as the stable reporting and diagnosis model.
2. Maintain the tested OTLP/JSON + OpenInference offline import boundary.
3. Keep extending explicit context-selection conventions for imported formats.
4. Add CI quality-gate examples over imported, reviewed traces.
5. Consider a hardened OTLP/HTTP receiver only after persistence, admission
   control, redaction, backpressure, and operational ownership are defined.

The SDK/exporter step is intentionally last. The project should first own its
RAG-specific semantics, then map them outward.

## References

- OpenTelemetry traces:
  <https://opentelemetry.io/docs/concepts/signals/traces/>
- OpenTelemetry GenAI semantic conventions:
  <https://github.com/open-telemetry/semantic-conventions/tree/main/docs/gen-ai>

