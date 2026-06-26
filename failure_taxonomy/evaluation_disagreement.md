# Evaluation Failure: Metric Disagreement

Evaluation failure occurs when automated evaluation signals disagree with
human-reviewed trace judgment or with each other. This category focuses on
metric disagreement, calibration gaps, and evaluator blind spots.

## Secondary Examples

- Metric passes an answer that human review marks unsupported.
- Metric fails an answer that is supported by selected evidence.
- Faithfulness and answer correctness metrics disagree.
- Retrieval metrics look strong while generation quality is poor.
- Citation metrics pass despite weak answer support.

## Trace Signals

Useful trace-level signals include:

- metric pass/fail values disagree within a trace;
- metric notes conflict with manual labels;
- reviewed labels identify a failure that metrics miss;
- metrics improve while human judgment worsens;
- evaluation thresholds produce unstable labels across similar cases.

## Minimal Example

Question: "Which vitamin prevents scurvy?"

Answer: "Vitamin C prevents scurvy."

Metric A passes because the answer matches the gold answer. Metric B fails
because the citation points to an irrelevant document.

Failure interpretation: evaluation signals disagree about whether the run
should be considered successful, so the trace needs review rather than a single
score.

## Distinguishing Tests

Evaluation failure differs from generation failure when the answer quality is
not the disputed object. The disputed object is the evaluator signal itself:
the metrics do not align with reviewed evidence or with each other.

It should be recorded alongside the underlying pipeline failure when both are
present. For example, an unsupported answer can also expose an evaluation
failure if a support metric incorrectly passes it.

## Measurement Notes

Candidate measurements:

- pairwise metric disagreement rate;
- metric-to-human agreement by failure mode;
- false pass and false fail counts;
- threshold sensitivity around reviewed cases;
- disagreement concentration by query type or dataset.

## Open Questions

- Which human review protocol should serve as the reference for metric
  disagreement?
- How much metric disagreement is acceptable when metrics measure different
  aspects of quality?
- Can evaluation disagreement predict where model-based or manual review should
  be prioritized?
