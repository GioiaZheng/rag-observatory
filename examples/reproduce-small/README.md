# Small Reproduction Example

This directory contains public-safe synthetic inputs for the lightweight
reproduction workflow.

The example is intentionally small. It is not a benchmark leaderboard and does
not claim model quality. Its purpose is to demonstrate the trace-based
diagnostic loop:

1. Convert a synthetic `msmarco-genqa` export into the `rag-observatory` trace
   schema.
2. Render a Markdown and HTML diagnostic report.
3. Compare two small pipeline variants.
4. Write a manifest that records the produced artifacts.

Run it from the repository root:

```bash
make reproduce-small
```

If `make` is not available:

```bash
python scripts/reproduce_small.py --output-dir outputs/reproduce-small
```

The generated files are written under `outputs/reproduce-small/`, which is
ignored by Git.
