# Failure-Pattern Benchmark Comparison

The small benchmark comparison is designed to compare observable failure
patterns across pipeline variants. It is not a leaderboard and should not be
used to claim broad model or retrieval performance.

## Manifest

The checked example manifest lives at
[`examples/reproduce-small/benchmark_variants.json`](../examples/reproduce-small/benchmark_variants.json).

```json
{
  "format": "rag-observatory.failure-pattern-benchmark.v1",
  "benchmark_id": "small-failure-patterns-v1",
  "dataset": "rag-observatory-small-example",
  "description": "Synthetic two-variant comparison for failure-pattern inspection, not leaderboard scoring.",
  "variants": [
    {
      "name": "baseline",
      "trace_path": "comparison_baseline.json"
    },
    {
      "name": "reranked",
      "trace_path": "comparison_reranked.json"
    }
  ]
}
```

Trace paths are resolved relative to the manifest directory. This keeps the
example portable and avoids absolute local paths.

## CLI

Render the failure-pattern summary:

```bash
PYTHONPATH=src python -m rag_observatory.cli.main benchmark-summary examples/reproduce-small/benchmark_variants.json --output outputs/reports/failure_pattern_benchmark.md
```

The report includes:

- variant-level run metadata;
- failed and passed evaluation signals;
- failure taxonomy distribution;
- a concise first-versus-last interpretation.

## Reproduction Workflow

`make reproduce-small` writes the benchmark report to:

```text
outputs/reproduce-small/reports/failure_pattern_benchmark.md
```

The benchmark is deliberately small so it can run in CI and remain inspectable.
For larger evaluations, keep full traces in JSONL collections and treat this
report as a compact summary, not the source of record.
