# Model-Based Judge Contract

This document defines the contract for optional model-based failure labeling.
It is a design boundary, not an implementation plan for a provider, API call,
or replacement for manual review.

## Role in the Labeling Stack

Model-based labels are an optional semantic layer after manual labels and
deterministic heuristic labels:

1. Manual labels remain authoritative when present.
2. Heuristic labels remain the first automated layer and should stay
   deterministic.
3. Model-based labels may add structured hypotheses when the trace contains
   enough evidence for semantic judgment.

Every accepted model-based label must be stored as a normal `FailureLabel` with
`detection_method` set to `model_based`.

## Allowed Inputs

A judge may inspect only information already recorded in a validated trace:

- `metadata` identifiers and pipeline component names
- `query.text` and `query.gold_answer` when available
- `retrieved_documents` text, scores, ranks, relevance annotations, and metadata
- `reranked_documents` when available
- `selected_context` chunks shown to the generator
- `prompt` content, template ID, and variables when recorded
- `answer.text` and answer citations
- `metrics` values, thresholds, pass/fail status, and notes
- existing `failures`
- explicit `extra` fields when their meaning is documented by the caller

The judge must not inspect external corpora, hidden caches, provider logs, or
unrecorded pipeline state.

## Output Shape

The judge output must be a single JSON object:

```json
{
  "labels": [
    {
      "mode": "unsupported_answer",
      "severity": "high",
      "confidence": 0.82,
      "evidence": "The answer says vitamin D prevents scurvy, while selected context says vitamin C prevents scurvy.",
      "rationale": "The answer changes the key entity relative to selected evidence.",
      "source_spans": [
        {
          "field": "answer.text",
          "text": "Vitamin D prevents scurvy."
        },
        {
          "field": "selected_context[0].text",
          "text": "Vitamin C prevents scurvy."
        }
      ]
    }
  ],
  "abstained": false,
  "abstention_reason": null,
  "provenance": {
    "judge_model": "model-name",
    "prompt_version": "judge-v1",
    "temperature": 0,
    "input_trace_hash": "sha256:..."
  }
}
```

For each item in `labels`, `mode` must be one of the documented failure modes.
`severity` should use the same values accepted by the trace schema. `evidence`
and `rationale` should be concise enough for a diagnostic report.

## Mapping to FailureLabel

Accepted labels map into the public trace schema as follows:

| Judge field | `FailureLabel` field |
| --- | --- |
| `mode` | `mode` |
| `severity` | `severity` |
| `evidence` | `evidence` |
| `rationale` | `rationale` |
| fixed value `model_based` | `detection_method` |

Until the public schema stabilizes, `confidence`, `source_spans`, and
`provenance` should be placed in `FailureLabel.extra`.

## Provenance Requirements

Every model-based labeling pass must record:

- judge model identifier
- prompt version
- temperature or decoding setting
- deterministic input trace hash
- timestamp or run identifier from the caller

The prompt version must change whenever label instructions, allowed inputs,
abstention rules, or output requirements change.

## Abstention Rules

The judge must abstain instead of emitting a label when:

- the trace lacks the answer, selected context, or citation fields needed for
  the requested judgment
- the requested failure mode is outside the documented taxonomy
- the judge cannot point to evidence in the trace
- the conclusion depends on external knowledge not present in the trace
- labels conflict and the trace does not contain enough evidence to resolve the
  conflict
- confidence is below the configured acceptance threshold
- output cannot be serialized as valid JSON matching the contract

When abstaining, `labels` must be empty, `abstained` must be `true`, and
`abstention_reason` must be non-empty.

## Safety Invariants

Model-based judging must preserve these invariants:

- It must not overwrite or remove manual labels.
- It must not delete heuristic labels.
- It must not invent evidence outside the trace.
- It must not assign labels outside the documented taxonomy.
- It must be versioned and repeatable enough for regression review.
- It must be optional for all core commands.

## Initial Candidate Modes

The first useful modes for model-based review are semantic or attribution-heavy
cases where simple heuristics are intentionally conservative:

- `unsupported_answer`
- `contradicted_by_context`
- `wrong_citation`
- `ambiguous_question`
- `unknown`

The judge should not be used to expand the taxonomy implicitly. New modes should
be documented first, then added to the contract.

## Validation Plan

Before any implementation is accepted, the contract should be validated with:

- reviewed synthetic traces with expected labels
- disagreement reports against heuristic labels
- explicit abstention examples
- manual review of false positives and false negatives
- provenance checks that make prompt and input changes visible

Judge output should be treated as a reviewable signal, not as ground truth.
