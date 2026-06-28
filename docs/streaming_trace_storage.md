# Streaming Trace Storage

Single-trace JSON remains the canonical interchange format for inspection,
debugging, and paper examples. Dataset-scale evaluation should use a streaming
collection wrapper so tooling can process many traces without loading one large
artifact into memory.

## Collection Format

The first collection format is JSON Lines:

- one validated `RagTrace` JSON object per line
- UTF-8 text
- optional gzip compression with `.jsonl.gz`
- blank lines ignored
- malformed records reported with file path and line number

The Python API streams records through `iter_trace_collection(path)`. The path
may be a single `.json`, `.jsonl`, `.jsonl.gz`, a `manifest.json`, or a directory
containing `manifest.json`.

## Manifest

Large experiments should be sharded and discovered through a portable manifest:

```json
{
  "format": "rag-observatory.trace-collection.v1",
  "version": 1,
  "trace_count": 50000,
  "shards": [
    {
      "path": "part-00000.jsonl.gz",
      "records": 10000,
      "compression": "gzip"
    }
  ],
  "document_store": null,
  "deduplication": {
    "strategy": "self-contained-traces",
    "stable_keys": ["doc_id"]
  }
}
```

Shard paths are relative to the manifest directory. Absolute paths and parent
directory escapes are rejected so collections remain portable across machines
and artifact stores.

## Document Payload Reuse

The v1 reader validates self-contained traces. Repeated documents should keep a
stable `doc_id` so downstream reports can group repeated evidence across
queries. A future document store may be referenced from the manifest, but any
trace consumed by the public reader should still be materialized into the normal
trace schema before validation. This keeps single traces inspectable while
leaving room for exporters to deduplicate raw corpora outside the trace record.

## Benchmark Command

Synthetic benchmark inputs can be generated and parsed with:

```bash
python -m pip install -e .
python scripts/benchmark_trace_io.py --sizes 1000 10000 50000 --output outputs/benchmarks/trace-io
```

The script writes deterministic JSONL collections, streams them through
`iter_trace_collection`, and reports records, elapsed seconds, records per
second, and process peak resident memory where the platform exposes it. These
numbers are engineering smoke tests, not benchmark claims about a real corpus.

Representative MS MARCO-scale claims should be reported only after the same
command is run against representative exported traces and committed benchmark
inputs are replaced by `.dvc` pointers or another large-artifact mechanism.
