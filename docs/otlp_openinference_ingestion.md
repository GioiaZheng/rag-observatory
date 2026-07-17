# OTLP/JSON + OpenInference Ingestion

`rag-observatory` can convert a standard OTLP/HTTP JSON trace export containing
OpenInference semantic attributes into its validated RAG diagnosis schema.
This is an offline ingestion path, not a network receiver.

## Usage

```bash
rag-observe ingest-otlp-openinference traces.json \
  --output outputs/imported-trace.json
```

An OTLP export can contain multiple trace IDs. Select one explicitly:

```bash
rag-observe ingest-otlp-openinference traces.json \
  --trace-id 0123456789abcdef0123456789abcdef \
  --output outputs/imported-trace.json
```

The command fails rather than choosing an arbitrary trace when more than one
trace ID is present.

## Supported Envelope

The adapter reads the OTLP/HTTP JSON `ExportTraceServiceRequest` shape:

```text
resourceSpans[]
  scopeSpans[]
    spans[]
      traceId, spanId, parentSpanId
      startTimeUnixNano, endTimeUnixNano
      attributes[]
```

OTLP `AnyValue` string, boolean, integer, double, array, key-value-list, and
bytes representations are decoded. OTLP integer strings are accepted as
required by the JSON encoding.

## OpenInference Mapping

| OpenInference signal | `rag-observatory` field |
| --- | --- |
| Root `input.value`, retriever input, or `reranker.query` | `query.text` |
| Root or LLM `output.value`; LLM output message content | `answer.text` |
| `RETRIEVER` + `retrieval.documents.*` | `retrieved_documents` |
| `RERANKER` + `reranker.output_documents.*` | `reranked_documents` |
| `reranker.model_name` | `metadata.reranker` |
| `llm.model_name` or `gen_ai.request.model` | `metadata.generator` |
| LLM prompt input or template attributes | `prompt` |
| OpenInference token-count attributes | trace metrics |
| OTLP resource `service.name` | `metadata.extra.service_name` |

OpenInference document IDs are preserved under
`extra.openinference_document_id`. Stage-qualified public IDs prevent the
current schema from conflating retrieval candidates with reranker outputs.

## Deliberate Non-Mappings

- Retrieval or reranker output does not prove final prompt selection, so the
  adapter does not synthesize `selected_context`.
- OpenInference does not provide reviewed relevance truth, so the adapter does
  not invent `is_relevant` labels or automatic retrieval failures.
- Arbitrary resource attributes are not copied into the trace. Only
  `service.name` is retained by the current version.
- User identifiers, authorization metadata, raw headers, and credentials are
  not extracted or logged.
- A network listener, authentication, persistence, retention, backpressure,
  and multi-tenant isolation are outside this adapter's scope.

## Privacy Boundary

OpenInference `input.value`, `output.value`, messages, document content, and
prompt attributes can contain private data. Export only traces that are safe for
the destination environment, and apply redaction before writing the OTLP JSON
file. The adapter does not contact a model provider or telemetry service.

## Verification

The checked synthetic fixture contains no production data:

```bash
PYTHONPATH=src python -m unittest tests.test_otlp_openinference_adapter
PYTHONPATH=src python -m unittest tests.test_cli_ingest_otlp_openinference
```

The test path verifies typed OTLP decoding, flattened OpenInference documents,
explicit multi-trace selection, CLI conversion, schema validation, and report
generation.

## Standards

- [OpenTelemetry Protocol specification](https://opentelemetry.io/docs/specs/otlp/)
- [OpenInference specification](https://arize-ai.github.io/openinference/spec/)
- [OpenInference semantic conventions](https://arize-ai.github.io/openinference/spec/semantic_conventions.html)

