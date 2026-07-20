# Module Boundaries

`rag-observatory` should grow as composable research modules, not as one
all-in-one RAG system. Each module should have a clear input/output contract,
be testable with synthetic fixtures, and remain replaceable when a better
implementation appears.

The main boundary is simple:

- `msmarco-genqa` owns experiments, pipeline variants, and generated traces.
- `rag-observatory` owns observation, diagnosis, interpretation, evaluation,
  and reports over those traces.

## Module Map

| Module | Status | Input | Output | Notes |
| --- | --- | --- | --- | --- |
| Trace schema | Core | RAG trace JSON or adapter output | Validated `RagTrace` objects | The public contract for diagnosis and reports. |
| Trace collector / adapters | Optional | External exports such as `msmarco-genqa` JSON or OTLP/OpenInference JSON | Public trace schema | Adapters should translate, not redefine the core schema. |
| Evaluation engine | Core | Validated traces and reviewed expectations | Quality scores, abstentions, and comparison rows | Deterministic evaluators live in core; model-based judges should be optional adapters. |
| Failure taxonomy | Core | Observable trace conditions and reviewed labels | Stable failure modes and definitions | Taxonomy labels should point to evidence, not replace review. |
| Failure analyzer | Core | Validated traces and taxonomy rules | Failure labels, evidence, rationale, and severity | Heuristics should stay conservative and testable. |
| Report generator | Core | Traces, labels, comparisons, and evaluation results | Markdown, HTML, SVG, or benchmark summaries | Reports should be reproducible from committed fixtures and commands. |
| Visualization layer | Optional | Report artifacts or bounded snapshots | Reader-facing views | Keep this optional until trace and evaluation contracts are stable. |

## Core Versus Optional

Core modules are required to keep the repository useful from a clean checkout:

- trace schema and validation;
- deterministic failure analysis;
- deterministic quality evaluation;
- report generation;
- small reproducible fixtures and tests.

Optional modules connect the core to external systems:

- dataset or pipeline adapters;
- OTLP/OpenInference importers;
- model-based judges;
- supervised failure triage;
- richer visual interfaces.

Optional modules should not make the core package require private data,
credentials, network access, or a specific RAG framework.

## Independent Testability

A module is independently testable when it has:

- a synthetic public-safe fixture;
- a documented input contract;
- a deterministic expected output or report;
- a local test that does not require credentials or network access;
- clear abstention behavior when evidence is missing;
- no hidden dependency on `msmarco-genqa` internals.

For example, an adapter test should prove that an external export maps into the
public trace schema. It should not require running the original pipeline.

## Adapter Boundary

Adapters may preserve source metadata under explicit fields, but they should
not leak pipeline-specific assumptions into the core schema. If an external
export does not show which chunks entered the prompt, the adapter should record
that gap as a diagnostic note or abstention rather than inventing selected
context.

This keeps downstream reports honest: missing observability is itself a useful
diagnostic result.

## Adding a Module

Before adding a module, check that it answers a concrete diagnosis or
reproducibility need. A useful first pass should include:

1. a short design note or README section;
2. a minimal fixture;
3. a small deterministic test;
4. a narrow command or API entry point when needed;
5. a statement of non-goals and limitations.

Do not split the repository or introduce a large framework until a module has
independent users, independent release value, or a clear maintenance reason.

## Non-Goals

The module map does not mean:

- building a complete RAG pipeline in this repository;
- making every adapter part of the core contract;
- adopting a dashboard-first architecture before reports are stable;
- treating synthetic fixtures as dataset-scale evidence;
- hiding missing trace evidence behind inferred labels.

The architecture should make failures easier to explain, not make the project
look larger than it is.
