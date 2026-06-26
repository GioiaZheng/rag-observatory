# Retrieval Failure

Retrieval failure occurs when the retrieval stage does not surface the evidence
needed to answer the query. In a RAG trace, this is an upstream failure: later
stages cannot use evidence that never entered the candidate set.

## Secondary Examples

- Relevant document missing from `retrieved_documents`.
- Retrieved set is empty.
- Retrieved documents are topically related but do not contain the answer.
- Retrieved documents contain stale, partial, or non-authoritative evidence.
- Query formulation misses the entity, time frame, or constraint needed for
  retrieval.

## Trace Signals

Useful trace-level signals include:

- `retrieved_documents` is empty.
- No retrieved document is annotated as relevant.
- The gold answer or reviewed evidence cannot be matched to retrieved text.
- Recall-oriented metrics fail while generation metrics may still look fluent.
- Diagnostic notes identify a query rewrite or retrieval coverage issue.

## Minimal Example

Question: "Which vitamin prevents scurvy?"

Retrieved evidence: documents about vitamin D, calcium, and bone health.

Expected evidence: a document stating that vitamin C prevents scurvy.

Failure interpretation: the generator has no supporting evidence for the
correct answer because the retriever missed the relevant document.

## Distinguishing Tests

Retrieval failure should be separated from ranking failure. If relevant evidence
appears somewhere in the retrieved set but is ranked too low, the primary issue
is ranking. If the evidence is absent from the retrieved set, the primary issue
is retrieval.

It should also be separated from generation failure. If evidence is present and
selected but the answer is wrong, retrieval is not the first cause.

## Measurement Notes

Candidate measurements:

- recall at candidate depth;
- first relevant rank;
- fraction of reviewed supporting facts covered by retrieved documents;
- retrieval miss rate by query type;
- correlation between retrieval miss and unsupported generation labels.

## Open Questions

- How should partial evidence be scored when no single document fully supports
  the answer?
- Should query rewrite failures be grouped under retrieval failure or tracked as
  a separate upstream category?
- What is the minimum reviewed annotation needed to call a retrieval miss?
