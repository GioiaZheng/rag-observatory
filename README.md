# rag-observatory

[![tests](https://github.com/GioiaZheng/rag-observatory/actions/workflows/tests.yml/badge.svg)](https://github.com/GioiaZheng/rag-observatory/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)

**Trace-based observability and failure analysis for Retrieval-Augmented Generation.**

[Project page](https://gioiazheng.github.io/projects/rag-observatory/) ·
[Reproduce a small run](docs/reproduce_small.md) ·
[Trace contract](docs/trace_stage_contract.md) ·
[Evaluator protocol](docs/evaluator_protocol.md)

`rag-observatory` helps answer a question that aggregate RAG metrics cannot:
**why did this run fail?** It turns execution traces into inspectable diagnostic
artifacts covering retrieval, reranking, context selection, generation,
evidence use, evaluation signals, and failure labels.

The project is a diagnostic layer around RAG experiments—not another pipeline,
chatbot, or framework wrapper.

## What it provides

| Capability | Output |
| --- | --- |
| Trace validation | Versioned, inspectable records of queries, retrieved documents, selected context, answers, metrics, and provenance |
| Failure diagnosis | Manual and heuristic labels spanning retrieval, evidence use, and generation errors |
| Evidence inspection | Claim-level support and attribution views |
| Run comparison | Before/after trace comparisons and failure-pattern summaries |
| Reporting | Portable Markdown and HTML reports with SVG previews |
| Evaluation | Reviewed-label and RAG quality-dimension checks |
| Integration | Narrow `msmarco-genqa` and OTLP/JSON + OpenInference ingestion adapters |
| Reproducibility | Manifests, public-safe fixtures, CI, Docker, and a one-command small workflow |

## A concrete diagnosis

A checked-in synthetic trace retrieves the correct evidence—“Vitamin C prevents
scurvy”—but the generator answers “Vitamin D prevents scurvy.” The resulting
report distinguishes successful retrieval from a generation failure:

| Signal | Diagnosis |
| --- | --- |
| Retrieval | Relevant evidence was retrieved and selected |
| Faithfulness | Failed: the answer contradicts the selected context |
| Failure modes | `contradicted_by_context`, `unsupported_answer` |
| Likely source | Generation changed the key entity |

See the complete
[synthetic diagnostic report](docs/examples/synthetic_diagnostic_report.md).
The example is intentionally small and public-safe; it demonstrates the trace
and reporting contract rather than a dataset-scale benchmark result.

## Quickstart

Requires Python 3.10 or newer.

```bash
git clone https://github.com/GioiaZheng/rag-observatory.git
cd rag-observatory
python -m pip install -e .
```

Generate a report from a toy trace:

```bash
rag-observe report \
  tests/fixtures/toy_runs/unsupported_answer.json \
  --output outputs/reports/unsupported_answer.md
```

Run the end-to-end small reproduction workflow:

```bash
make reproduce-small
```

If `make` is unavailable:

```bash
python scripts/reproduce_small.py --output-dir outputs/reproduce-small
```

The workflow writes a normalized trace, Markdown and HTML diagnostics, an SVG
preview, run comparisons, a failure-pattern summary, and a manifest under
`outputs/reproduce-small/`. See
[Small Reproduction Workflow](docs/reproduce_small.md) for the artifact tree and
input fixtures.

## CLI workflows

After installation, the main commands are:

```bash
# Render Markdown or HTML diagnostics
rag-observe report TRACE.json --output report.md
rag-observe html-report TRACE.json --output report.html --screenshot report.svg

# Compare two runs for the same query
rag-observe compare BEFORE.json AFTER.json --output comparison.md

# Summarize a small set of pipeline variants
rag-observe benchmark-summary VARIANTS.json --output benchmark.md

# Inspect multi-turn behavior
rag-observe conversation-report TURN_1.json TURN_2.json --output conversation.md

# Convert a public-safe msmarco-genqa export
rag-observe ingest-msmarco-genqa EXPORT.json --output trace.json

# Convert one OpenInference trace from an OTLP/HTTP JSON export
rag-observe ingest-otlp-openinference OTLP.json --output trace.json

# Check reviewed failure labels and quality dimensions
rag-observe evaluate-labels EXPECTED_LABELS.json --output labels.md
rag-observe evaluate-quality EXPECTED_SCORES.json --output quality.md
```

Use `python -m rag_observatory.cli.main ...` with `PYTHONPATH=src` when
working from a source checkout without installation.

## Trace and diagnosis model

The central object is a RAG execution trace:

```text
query
  → retrieval candidates
  → reranked / selected context
  → generated answer
  → claims and evidence
  → evaluation signals
  → failure diagnosis
```

The stage-level contract preserves enough information to separate failures that
look identical in a single score. For example, a wrong answer may come from
missing evidence, poor context selection, ignored evidence, or an unsupported
generation. Configuration and provenance fields make those diagnoses
comparable across runs.

## Evidence and reproducibility

The repository currently provides:

- public-safe synthetic traces and reviewed expected outputs;
- a one-command small workflow exercised in CI;
- trace comparison and failure-pattern examples;
- Ruff, formatting, strict mypy, unit-test, Docker, and CLI smoke-test gates;
- streaming JSONL guidance and a synthetic trace-I/O smoke benchmark;
- optional DVC-oriented artifact versioning guidance.

Research claims remain evidence-gated. Generated experiment outputs are kept
outside the committed tree by default, while small fixtures and report examples
remain reviewable in Git.

## Documentation

| Topic | Document |
| --- | --- |
| Small reproducible workflow | [docs/reproduce_small.md](docs/reproduce_small.md) |
| Stage-level trace contract | [docs/trace_stage_contract.md](docs/trace_stage_contract.md) |
| Evaluator protocol | [docs/evaluator_protocol.md](docs/evaluator_protocol.md) |
| Claim-level diagnosis | [docs/claim_level_diagnosis.md](docs/claim_level_diagnosis.md) |
| OpenTelemetry alignment | [docs/opentelemetry_alignment.md](docs/opentelemetry_alignment.md) |
| OTLP + OpenInference ingestion | [docs/otlp_openinference_ingestion.md](docs/otlp_openinference_ingestion.md) |
| Report artifacts | [docs/report_artifacts.md](docs/report_artifacts.md) |
| Benchmark comparison | [docs/benchmark_comparison.md](docs/benchmark_comparison.md) |
| Configuration sensitivity | [docs/config_sensitivity.md](docs/config_sensitivity.md) |
| Streaming trace storage | [docs/streaming_trace_storage.md](docs/streaming_trace_storage.md) |
| Artifact versioning | [docs/artifact_versioning.md](docs/artifact_versioning.md) |
| Container workflow | [docs/container.md](docs/container.md) |
| Research evidence plan | [docs/research_evidence_plan.md](docs/research_evidence_plan.md) |

## Repository layout

```text
src/rag_observatory/
  trace/          trace schema and validation
  taxonomy/       failure labels and heuristic classification
  reports/        Markdown and HTML diagnostics
  io/             trace loading, saving, and collections
  cli/            command-line entry points

tests/            tests and small synthetic fixtures
examples/         public-safe reproduction inputs
docs/             contracts, protocols, examples, and design notes
configs/          configuration templates
failure_taxonomy/ versioned taxonomy seeds
```

## Project boundaries and status

The core trace-validation, reporting, comparison, and evaluator-protocol loop is
implemented and tested. Interfaces are still early and may evolve while the
project adds broader reviewed trace coverage.

Current boundaries:

- checked-in evidence is small and synthetic, not a leaderboard or
  dataset-scale benchmark;
- heuristic labels support inspection but are not a learned failure classifier;
- the OTLP/JSON adapter is an offline importer, not a production OTLP receiver,
  Collector backend, or hosted dashboard;
- pipeline code belongs here only as a fixture, minimal demo, or narrow adapter.

See the
[msmarco-genqa adapter plan](docs/msmarco_genqa_adapter_plan.md) and
[lightweight classifier plan](docs/lightweight_failure_classifier_plan.md) for
the intentionally narrow integration and modeling boundaries.

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy src
python -m unittest discover -s tests
pre-commit run --all-files
```

## License

MIT License. See [LICENSE](LICENSE).

