# Context Failure: Pollution and Redundancy

Context failure occurs when selected context does not provide a clean and useful
evidence set for generation. This seed focuses on context pollution and
redundancy: the prompt contains distracting, duplicated, or misleading material
even when some useful evidence is available.

## Secondary Examples

- Irrelevant retrieved documents are selected into context.
- Redundant chunks crowd out distinct supporting evidence.
- Conflicting passages appear without enough disambiguation.
- Long boilerplate text consumes context budget.
- Selected chunks include nearby text that weakens or distracts from the answer.

## Trace Signals

Useful trace-level signals include:

- selected context includes documents annotated as not relevant;
- selected token count is high while evidence coverage remains low;
- many selected chunks share the same `doc_id` or near-duplicate text;
- answer support metrics fail despite at least one relevant selected chunk;
- diagnostic notes point to context packing or deduplication problems.

## Minimal Example

Question: "Which vitamin prevents scurvy?"

Selected context includes one sentence about vitamin C and several unrelated
passages about vitamin D, calcium, and immune health.

Failure interpretation: the prompt contains the right evidence but surrounds it
with distracting material that increases the chance of an unsupported answer.

## Distinguishing Tests

Context pollution differs from retrieval noise because it concerns what was
actually selected into the prompt, not everything retrieved. A retriever may
return noisy candidates, but the context stage can still recover by selecting
only useful evidence.

It differs from missing evidence when the key evidence is present but diluted or
contradicted by other selected content.

## Measurement Notes

Candidate measurements:

- selected irrelevant chunk count;
- selected relevant-to-irrelevant token ratio;
- unique supporting document coverage;
- duplicate or near-duplicate chunk rate;
- disagreement between selected context quality and final answer quality.

## Open Questions

- How much redundancy is useful evidence reinforcement versus harmful context
  waste?
- Should conflicting context be treated as pollution or as a separate ambiguity
  category?
- Which context quality metrics best predict generation support?
