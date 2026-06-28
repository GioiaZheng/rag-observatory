# Research Evidence Plan

This agenda defines the evidence needed before RAG Observatory can support a
system demonstration paper, short paper, or public research report. It is not a
paper draft and makes no venue-specific claims.

## Research Questions

1. Can trace-level observability explain why a RAG pipeline succeeds or fails
   more concretely than aggregate task metrics alone?
2. Which failure categories are reliably diagnosable from local trace artifacts
   without external provider logs or hidden pipeline state?
3. How often do deterministic heuristics, semantic evaluators, and human
   reviewers disagree, and what do those disagreements reveal?
4. What artifact format and report structure make RAG debugging reproducible at
   both toy scale and dataset scale?
5. Which parts of the workflow remain inspectable, local-first, and low-cost as
   the number of traces grows?

## Planned Claims and Required Evidence

| Planned Claim | Required Evidence | Repository Artifact |
| --- | --- | --- |
| Trace-based reports localize RAG failures beyond pass/fail metrics. | Human-reviewed case studies showing retrieval, context, generation, and evaluation failures. | `docs/examples/`, failure taxonomy, reviewed trace fixtures |
| The failure taxonomy covers common RAG diagnosis paths. | Inter-annotator review over a representative trace sample, with unresolved or overlapping labels recorded. | `failure_taxonomy/`, `docs/failure_taxonomy.md`, reviewed label fixtures |
| Deterministic heuristics are useful but incomplete. | Precision/recall and disagreement analysis against reviewed labels. | `evaluate-labels` CLI, failure label evaluation report |
| Quality evaluators add semantic signal without replacing review. | Context relevance, faithfulness, and answer relevance comparisons with abstention and provenance. | `evaluate-quality` CLI, `docs/evaluator_protocol.md` |
| Streaming trace collections scale better than monolithic JSON. | 1K, 10K, 50K, and representative exported trace parsing measurements with peak memory. | `docs/streaming_trace_storage.md`, `scripts/benchmark_trace_io.py` |
| Results are reproducible from source and versioned artifacts. | Clean-checkout commands, container test path, and optional DVC metadata for large artifacts. | `Dockerfile`, `dvc.yaml`, `docs/artifact_versioning.md` |

## Datasets and Pipeline Variants

Initial experiments should include:

- toy synthetic traces for contract and regression tests;
- MS MARCO-derived question answering traces when export and licensing
  boundaries are documented;
- at least one small public QA dataset with releasable examples;
- retrieval-only, retrieval plus reranking, and retrieval plus reranking plus
  citation variants;
- at least one intentionally weak baseline to create inspectable failures.

Datasets must be documented with source, license, preprocessing, split, trace
count, and whether raw text can be released. Private or unreleasable data should
not become a dependency for the paper evidence path.

## Baselines

The minimum comparison set should include:

- aggregate task metrics without trace diagnostics;
- deterministic heuristic failure labels;
- reviewed human failure labels;
- rule-based quality evaluator outputs;
- optional model-based judge outputs;
- optional supervised triage outputs after reviewed support is large enough.

Every automated baseline should report abstentions separately from failures.
Model-based and supervised outputs should be treated as reviewable hypotheses,
not ground truth.

## Human Annotation Protocol

Human review should record:

- trace ID and query ID;
- available evidence inspected;
- failure labels with severity, evidence, and rationale;
- quality dimension judgments and abstentions;
- uncertainty notes;
- reviewer identity or anonymized reviewer ID;
- timestamp and protocol version.

At least a subset should receive two independent reviews. Disagreements should
be classified as taxonomy overlap, missing trace evidence, ambiguous query,
metric disagreement, or reviewer error. Resolved labels and unresolved conflicts
should both remain auditable.

## Evaluation Disagreement Protocol

For each reviewed trace, compare:

- manual labels versus heuristic labels;
- heuristic labels versus model-based labels when available;
- quality evaluator outputs versus reviewed quality scores;
- aggregate task metrics versus human judgment.

Disagreement reports should preserve examples, not only counts. Each repeated
error should map to a next action: taxonomy clarification, schema extension,
metric calibration, prompt or evaluator revision, or no action when the case is
outside project scope.

## Ablation Plan

Run ablations only after representative traces exist:

| Ablation | Question |
| --- | --- |
| Remove reranking signals | Which ranking failures become invisible? |
| Remove selected context chunks | Which generation failures can no longer be grounded? |
| Remove citations | How much evidence attribution is lost? |
| Disable heuristic labels | How much diagnosis depends on reviewed or model-based labels? |
| Disable semantic quality evaluator | Which disagreements remain unseen by taxonomy labels? |
| Use monolithic JSON instead of JSONL collections | How much memory and parsing cost changes? |

## Scalability, Cost, and Reproducibility Evidence

Report:

- trace counts and average trace size;
- parsing throughput and peak resident memory;
- report generation time;
- evaluator runtime and abstention rate;
- model-based judge cost per trace when used;
- artifact hashes or DVC pointers for large inputs;
- exact code revision and container image base;
- commands needed to reproduce tables and figures.

Do not report cost or scalability claims from toy fixtures.

## Candidate Figures and Tables

| Output | Evidence Source |
| --- | --- |
| Failure taxonomy overview figure | `failure_taxonomy/` and reviewed examples |
| Trace lifecycle diagram | trace schema and streaming collection docs |
| Per-mode precision/recall table | failure label evaluation report |
| Quality dimension agreement table | quality evaluation report |
| Disagreement case study table | reviewed traces and report examples |
| Scaling plot for JSON versus JSONL | benchmark outputs |
| Reproducibility checklist | Docker, DVC, and clean-checkout commands |

## Open Risks and Missing Evidence

- The current fixture set is synthetic and too small for performance or
  coverage claims.
- Relevance annotations may be unavailable or inconsistent across datasets.
- Semantic evaluator scores may look precise while still depending on weak
  trace evidence.
- Failure modes may overlap, especially context pollution, wrong citation, and
  unsupported generation.
- Human review cost may limit the size of the validated set.
- Some useful corpora or model outputs may not be redistributable.
- DVC improves artifact versioning but does not solve memory-efficient parsing.
- Container reproducibility does not guarantee GPU or index reproducibility.

## Milestones

1. Stabilize trace schema, taxonomy, evaluator contracts, and local reports.
2. Export representative non-toy traces from at least one public dataset.
3. Create reviewed label and quality-score sets with disagreement notes.
4. Run heuristic and quality evaluator baselines.
5. Add optional model-based judge or supervised triage only after reviewed
   baselines are inspectable.
6. Run scalability and reproducibility experiments with versioned artifacts.
7. Decide whether the evidence supports a system demonstration, short paper, or
   public technical report.
