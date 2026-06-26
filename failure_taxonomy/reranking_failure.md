# Ranking Failure

Ranking failure occurs when useful evidence is available in the candidate set
but is ordered too low to influence context selection or generation. In systems
with a reranker, this category includes reranking failure.

## Secondary Examples

- Correct document ranked below distractors.
- Reranker promotes an irrelevant document above a relevant one.
- The top-ranked document is only weakly related while stronger evidence exists
  lower in the list.
- Ranking favors lexical overlap over answer-bearing evidence.
- Ranking is unstable across similar queries.

## Trace Signals

Useful trace-level signals include:

- `retrieved_documents` contains relevant evidence outside the top selected
  range.
- `reranked_documents` moves relevant evidence downward.
- First relevant rank is high even when retrieval recall is nonzero.
- Selected context excludes high-quality evidence because of rank order.
- Ranking-sensitive metrics change when candidate order changes.

## Minimal Example

Question: "Which vitamin prevents scurvy?"

Retrieved candidates include:

1. A long document about vitamin D and bones.
2. A document stating that vitamin C prevents scurvy.

Selected context uses only candidate 1 because it is ranked first.

Failure interpretation: evidence exists, but ranking makes the correct document
unlikely to be selected.

## Distinguishing Tests

Ranking failure differs from retrieval failure because the relevant evidence is
present in the candidate set. It differs from context failure when the ranking
order itself explains why the selected context is weak.

When both ranking and context selection contribute, record the chain explicitly:
ranking placed evidence too low, and context selection then omitted it.

## Measurement Notes

Candidate measurements:

- mean reciprocal rank for reviewed supporting evidence;
- first relevant rank before and after reranking;
- rank movement for relevant versus irrelevant documents;
- recall at selected context depth;
- per-query ranking disagreement between retriever and reranker.

## Open Questions

- When should a low-ranked relevant document count as a ranking failure rather
  than acceptable retrieval depth behavior?
- How should redundant relevant documents affect ranking evaluation?
- Can rank movement predict downstream unsupported generation better than raw
  retrieval recall?
