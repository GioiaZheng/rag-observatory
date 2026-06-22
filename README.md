# rag-observatory

`rag-observatory` is a local-first research-engineering toolkit for observing
and diagnosing Retrieval-Augmented Generation runs.

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
```

## Status

The project is in its initial schema and reporting milestone. Interfaces should
be treated as early but intentionally small.
