# Evals-as-Code Workflow

Evaluation assets should be versioned and reviewable in the same way as source
code. A small eval should not be a one-off notebook output or a static table
that cannot be regenerated.

The checked synthetic example lives in
[`examples/evals-as-code/synthetic_failure_eval/`](../examples/evals-as-code/synthetic_failure_eval/).

It contains:

| File | Role |
| --- | --- |
| `dataset.jsonl` | Public-safe cases with trace paths, expected quality scores, and expected failure labels. |
| `task.yaml` | Task metadata, threshold, dimensions, and default output paths. |
| `solver.py` | Loads each trace and emits answers, quality scores, and failure labels. |
| `scorer.py` | Compares solver outputs with expected scores and labels. |
| `run_eval.py` | Runs the dataset and writes deterministic JSON and Markdown artifacts. |
| `report.md` | Checked reference report for code review and regression tests. |

Run it from the repository root:

```bash
python examples/evals-as-code/synthetic_failure_eval/run_eval.py
```

By default, generated artifacts are written under:

```text
outputs/evals-as-code/synthetic_failure_eval/
  results.json
  report.md
```

To write to another directory:

```bash
python examples/evals-as-code/synthetic_failure_eval/run_eval.py --output-dir outputs/evals-as-code/manual
```

This workflow differs from a static experiment table in three ways:

- inputs, solver code, scorer code, thresholds, outputs, and reports are all
  committed or reproducible;
- scores record pass/fail, abstentions, evidence, thresholds, and failure
  labels;
- the same command can be run across revisions to inspect changes.

The current example is deliberately synthetic. It is for workflow validation,
not evidence that a model-based judge, supervised classifier, or benchmark
setup is reliable on real workloads.
