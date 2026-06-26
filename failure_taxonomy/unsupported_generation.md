# Generation Failure: Unsupported Claims

Generation failure occurs when the answer makes claims that are not supported by
the selected evidence. This seed focuses on unsupported generation, including
hallucinated facts, over-specific claims, and incorrect synthesis.

## Secondary Examples

- Unsupported factual claim.
- Answer contradicts selected context.
- Answer adds a date, number, entity, or causal claim not present in evidence.
- Answer states a plausible fact from outside the trace.
- Answer cites evidence that does not support the claim.

## Trace Signals

Useful trace-level signals include:

- faithfulness, support, or groundedness metrics fail;
- answer text conflicts with selected context;
- citations point to documents that do not support the answer;
- manual review marks the answer as unsupported;
- selected context is adequate, but the answer still introduces new claims.

## Minimal Example

Question: "Which vitamin prevents scurvy?"

Selected context: "Vitamin C prevents scurvy."

Generated answer: "Vitamin D prevents scurvy."

Failure interpretation: the selected context contains the correct evidence, but
the generation step produces an unsupported and contradicted answer.

## Distinguishing Tests

Unsupported generation differs from retrieval or context failures when the
necessary evidence is present in selected context. If the evidence is absent,
the unsupported answer may be a symptom of an upstream failure.

It differs from evaluation failure when both human review and trace evidence
agree that the claim is unsupported.

## Measurement Notes

Candidate measurements:

- unsupported claim count per answer;
- contradiction count against selected context;
- citation support precision;
- answer sentence support coverage;
- false support rate from automated metrics.

## Open Questions

- How should partially supported answers be scored when some claims are correct
  and others are unsupported?
- Should citation errors be grouped under generation failure or separated as an
  attribution failure?
- What evidence granularity is needed for reliable unsupported claim review?
