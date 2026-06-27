# rag-observatory

[![tests](https://github.com/GioiaZheng/rag-observatory/actions/workflows/tests.yml/badge.svg)](https://github.com/GioiaZheng/rag-observatory/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)

`rag-observatory` is a research-engineering toolkit for understanding and
diagnosing Retrieval-Augmented Generation systems through traceability, failure
taxonomy, evidence analysis, and reproducible reports.

The project is not a RAG pipeline. Its central object is a RAG execution trace:
query, retrieval candidates, selected context, generated answer, evidence,
evaluation signals, and failure diagnosis.

## Current Scope

The first milestone implements the smallest credible observability loop:

1. Load a trace from JSON.
2. Validate the trace schema.
3. Apply manual and simple heuristic failure labels.
4. Render a compact markdown diagnostic report.
5. Test schema validation, taxonomy stability, report generation, and CLI output.

## Quickstart

Run the tests:

```bash
python -m unittest discover -s tests
```

Install the development tools and run the repository quality gates:

```bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy src
pre-commit run --all-files
```

Render a diagnostic report from a toy trace:

```bash
PYTHONPATH=src python -m rag_observatory.cli.main report tests/fixtures/toy_runs/unsupported_answer.json --output outputs/reports/unsupported_answer.md
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m rag_observatory.cli.main report tests/fixtures/toy_runs/unsupported_answer.json --output outputs/reports/unsupported_answer.md
```

After installation, the same command is available as:

```bash
rag-observe report tests/fixtures/toy_runs/unsupported_answer.json --output outputs/reports/unsupported_answer.md
```

Compare two traces for the same query:

```bash
PYTHONPATH=src python -m rag_observatory.cli.main compare tests/fixtures/toy_runs/comparison_before.json tests/fixtures/toy_runs/comparison_after.json --output outputs/reports/comparison.md
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m rag_observatory.cli.main compare tests/fixtures/toy_runs/comparison_before.json tests/fixtures/toy_runs/comparison_after.json --output outputs/reports/comparison.md
```

Evaluate failure labels against reviewed expected labels:

```bash
PYTHONPATH=src python -m rag_observatory.cli.main evaluate-labels tests/fixtures/reviewed_labels/expected_failure_labels.json --output outputs/reports/failure_label_evaluation.md
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m rag_observatory.cli.main evaluate-labels tests/fixtures/reviewed_labels/expected_failure_labels.json --output outputs/reports/failure_label_evaluation.md
```

A public-safe synthetic example of the rendered report shape is checked in at
[`docs/examples/synthetic_diagnostic_report.md`](docs/examples/synthetic_diagnostic_report.md).
Generated run outputs should still be written outside the committed tree, such
as under an ignored `outputs/` directory.

## Project Boundaries

This repository focuses on:

- trace schemas
- failure taxonomy
- evidence attribution
- diagnostic reports
- reproducible run artifacts

It does not aim to provide:

- another RAG pipeline
- a chatbot
- a dashboard-first application
- a generic framework wrapper

Pipeline code should appear only as a fixture, a minimal demo, or an adapter
for observing external systems.

Adapter planning should stay explicit and narrow. The current `msmarco-genqa`
boundary note is in
[`docs/msmarco_genqa_adapter_plan.md`](docs/msmarco_genqa_adapter_plan.md).

Modeling investigations should stay optional and evidence-gated. The current
lightweight classifier note is in
[`docs/lightweight_failure_classifier_plan.md`](docs/lightweight_failure_classifier_plan.md).

## Repository Layout

```text
src/rag_observatory/
  trace/          Trace schema and validation
  taxonomy/       Failure labels and heuristic classification
  reports/        Markdown diagnostic reports
  io/             JSON trace loading and saving
  cli/            Command line entry points

tests/
  fixtures/       Small synthetic traces

docs/             Design notes and public technical documentation
configs/          Configuration templates
failure_taxonomy/ Paper-oriented taxonomy seeds
```

## Status

The project is in its initial schema and reporting milestone. Interfaces should
be treated as early but intentionally small.

## License

MIT License. See [LICENSE](LICENSE).
