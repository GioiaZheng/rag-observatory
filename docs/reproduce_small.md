# Small Reproduction Workflow

The small reproduction workflow demonstrates the core project claim:
`rag-observatory` helps inspect why a RAG run fails, not only whether it
succeeds.

Run from the repository root:

```bash
make reproduce-small
```

If `make` is not available:

```bash
python scripts/reproduce_small.py --output-dir outputs/reproduce-small
```

The command writes artifacts under `outputs/reproduce-small/`:

```text
outputs/reproduce-small/
  manifest.json
  traces/
    msmarco_genqa_trace.json
  reports/
    msmarco_genqa_diagnostic.md
    msmarco_genqa_diagnostic.html
    benchmark_comparison.md
```

The workflow uses synthetic public-safe inputs in
[`examples/reproduce-small/`](../examples/reproduce-small/):

- `msmarco_genqa_export.json` exercises retrieval, reranking, prompt
  construction, generation, citations, evaluation signals, and failure
  taxonomy labels.
- `comparison_baseline.json` and `comparison_reranked.json` provide a small
  before/after comparison showing how pipeline changes alter observable failure
  patterns.

This is not a leaderboard. The example is deliberately small so it can run in
CI and remain easy to inspect.
