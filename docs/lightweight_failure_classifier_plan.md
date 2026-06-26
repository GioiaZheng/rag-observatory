# Lightweight Failure Classifier Investigation

This note defines the investigation path for a lightweight supervised failure
classifier. It should be read as a research plan, not as approval to add a
trained model to the core package.

## Position in the Labeling Stack

A supervised classifier may become useful after there are enough reviewed
traces and the failure label evaluation report is stable. Its role is triage
and ranking:

1. Manual labels remain authoritative.
2. Deterministic heuristics remain the first automated baseline.
3. Model-based judge outputs remain reviewable hypotheses, not ground truth.
4. A supervised classifier may prioritize likely labels or review queues when
   it outperforms the heuristic baseline on reviewed data.

Classifier outputs must not overwrite manual labels or remove heuristic labels.
If they are written back to traces in the future, they should use a distinct
detection method or explicit provenance under `extra` until the public schema
defines a stable method.

## Local Trace-Derived Features

Initial features should come only from validated trace fields and must not
require external services:

| Area | Candidate Features |
| --- | --- |
| Retrieval | retrieved document count, empty retrieval flag, top score, score spread, relevance annotation counts, first relevant rank |
| Reranking | reranked document count, top reranked relevance, first relevant reranked rank, rank movement for shared documents |
| Context selection | selected context count, selected token count, selected relevant document coverage, relevant retrieved documents not selected |
| Answer | answer length, empty answer flag, citation count, citation document coverage, citations pointing outside retrieved documents |
| Metrics | metric names, numeric values, pass/fail flags, number of failed metrics, metric disagreement flag |
| Pipeline metadata | pipeline stage flags, dataset name, component names when stable across reviewed runs |

Do not use `run_id`, timestamp, existing failure labels, report text, or any
future prediction output as model features. Those fields can leak the target or
make the model look better than it is.

## Target Shape

The first target should be multi-label classification over the documented
failure taxonomy. A case can have zero, one, or many expected modes. The clean
case with no expected labels is important because it exposes false positives.

Per-mode targets should be trained and evaluated independently at first. A
single global "failed run" target may be useful for triage, but it should not
replace per-mode reporting.

## Candidate Models

The first supervised experiments should stay small:

- majority and heuristic baselines;
- one-vs-rest logistic regression over numeric and boolean trace features;
- calibrated linear models for probability ranking;
- simple threshold rules learned from reviewed fixtures only after there is
  enough support.

The core package should not take a new modeling dependency for this
investigation. If a library such as scikit-learn is used later, keep it behind
an optional experiment path until the value is demonstrated.

## Evaluation Protocol

Every experiment must compare against the deterministic heuristic baseline with
the failure label evaluation report:

```bash
PYTHONPATH=src python -m rag_observatory.cli.main evaluate-labels tests/fixtures/reviewed_labels/expected_failure_labels.json --output outputs/reports/failure_label_evaluation.md
```

Report at least:

- per-mode precision, recall, and support;
- exact-match count across cases;
- abstention rate when thresholds allow abstention;
- inspectable false positives and false negatives;
- the reviewed fixture set and feature version used for the run.

Before there are enough reviewed examples per mode, only feature extraction and
error-analysis reports should be merged. Do not claim benchmark performance
from the toy fixture set.

## Calibration and Abstention

The classifier should abstain when confidence is low or when a mode has too
little reviewed support. Thresholds should be selected from reviewed validation
data, not from the final report set.

Calibration review should answer:

- which modes produce over-confident false positives;
- which modes are under-detected because the trace lacks features;
- whether thresholds differ by mode;
- whether abstention reduces harmful false positives without hiding common
  failures.

## Error Analysis Loop

False positives and false negatives should be inspected before adding features.
For each repeated error, classify the cause:

- missing or weak trace feature;
- ambiguous reviewed label;
- taxonomy mode overlap;
- deterministic heuristic already sufficient;
- trace schema does not record the needed evidence.

Only the first and last categories justify feature or schema work. Ambiguous
labels should go back to review instead of training a model around them.

## Relationship to Model-Based Judging

The supervised classifier and the model-based judge solve different problems.
The classifier should learn from reviewed trace-level signals and remain cheap
to run locally. The judge may inspect semantic evidence in a trace and produce
structured hypotheses.

Generated judge labels must not become training targets unless they are reviewed
and accepted. A useful future workflow is:

1. heuristics create deterministic labels;
2. classifier ranks uncertain or high-risk traces;
3. judge proposes semantic labels for selected traces;
4. humans review disagreements;
5. reviewed labels feed the evaluation set.

## Implementation Gates

Do not implement a supervised classifier in core until these gates are met:

- the reviewed fixture set includes enough positive and negative examples for
  the target modes;
- feature extraction has deterministic tests;
- heuristic baseline evaluation is available for comparison;
- model provenance records training data hash, feature version, model version,
  and threshold configuration;
- reports show clear false positive and false negative analysis;
- the implementation remains optional and local-first.

Until then, the correct next step is feature inventory and offline experiment
design, not model training.
