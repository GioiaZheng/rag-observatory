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

Run the small end-to-end reproduction workflow:

```bash
make reproduce-small
```

If `make` is not available, run the underlying script directly:

```bash
python scripts/reproduce_small.py --output-dir outputs/reproduce-small
```

This writes a normalized trace, Markdown report, HTML report, benchmark
comparison, and manifest under `outputs/reproduce-small/`. The workflow is
documented in [`docs/reproduce_small.md`](docs/reproduce_small.md).

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

Render a conversational report from per-turn traces:

```bash
PYTHONPATH=src python -m rag_observatory.cli.main conversation-report tests/fixtures/conversations/turn_001_supported.json tests/fixtures/conversations/turn_002_bad_rewrite.json tests/fixtures/conversations/turn_003_unanswerable.json --output outputs/reports/conversation.md
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m rag_observatory.cli.main conversation-report tests/fixtures/conversations/turn_001_supported.json tests/fixtures/conversations/turn_002_bad_rewrite.json tests/fixtures/conversations/turn_003_unanswerable.json --output outputs/reports/conversation.md
```

Convert a synthetic `msmarco-genqa` export into a RAG trace:

```bash
PYTHONPATH=src python -m rag_observatory.cli.main ingest-msmarco-genqa tests/fixtures/msmarco_genqa/synthetic_export.json --output outputs/traces/msmarco_genqa_trace.json
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m rag_observatory.cli.main ingest-msmarco-genqa tests/fixtures/msmarco_genqa/synthetic_export.json --output outputs/traces/msmarco_genqa_trace.json
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

Evaluate core RAG quality dimensions against reviewed expected scores:

```bash
PYTHONPATH=src python -m rag_observatory.cli.main evaluate-quality tests/fixtures/quality_evaluation/expected_quality_scores.json --output outputs/reports/quality_evaluation.md
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m rag_observatory.cli.main evaluate-quality tests/fixtures/quality_evaluation/expected_quality_scores.json --output outputs/reports/quality_evaluation.md
```

The evaluator protocol for context relevance, faithfulness, answer relevance,
provenance, and abstention is documented in
[`docs/evaluator_protocol.md`](docs/evaluator_protocol.md).

The stage-level trace contract for retrieval, reranking, prompt construction,
generation, and evaluation is documented in
[`docs/trace_stage_contract.md`](docs/trace_stage_contract.md).

Claim-level answer support and attribution diagnosis is documented in
[`docs/claim_level_diagnosis.md`](docs/claim_level_diagnosis.md).

A public-safe synthetic example of the rendered report shape is checked in at
[`docs/examples/synthetic_diagnostic_report.md`](docs/examples/synthetic_diagnostic_report.md).
Generated run outputs should still be written outside the committed tree, such
as under an ignored `outputs/` directory.

For dataset-scale trace parsing, keep individual traces inspectable and use the
streaming JSONL collection format documented in
[`docs/streaming_trace_storage.md`](docs/streaming_trace_storage.md). A
synthetic throughput and peak-memory smoke test is available with:

```bash
python scripts/benchmark_trace_io.py --sizes 1000 10000 50000 --output outputs/benchmarks/trace-io
```

Large experiment artifacts are managed outside Git by default. Optional DVC
metadata and workflows are documented in
[`docs/artifact_versioning.md`](docs/artifact_versioning.md).

Container build and smoke-test commands are documented in
[`docs/container.md`](docs/container.md).

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

Research claims should stay tied to explicit evidence requirements. The current
system-demonstration evidence agenda is in
[`docs/research_evidence_plan.md`](docs/research_evidence_plan.md).

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
