# Configuration Sensitivity

RAG failures are often configuration-sensitive rather than random. A trace can
show that an answer failed, but a useful observability layer should also help
explain which architecture choice made the failure more likely.

This note treats RAG design as a configuration space: retrieval depth, query
rewriting, reranking, and context compression are observable choices that can
change both the answer and the failure mode. The goal is not to turn
`rag-observatory` into a RAG pipeline. The goal is to make traces rich enough
to compare pipeline variants and diagnose why one configuration fails where
another succeeds.

## Sensitivity Matrix

| Config Choice | Possible Failure | Trace Needed |
| --- | --- | --- |
| retrieval depth too low | relevant evidence missing | retrieved docs + oracle evidence |
| retrieval depth too high | context pollution | doc scores + context position |
| reranker too aggressive | correct doc suppressed | pre-rerank / post-rerank ranks |
| context compression | support sentence removed | original vs compressed context |
| query rewriting | query drift | original query + rewritten query |

## Trace Implications

Configuration-sensitive diagnosis requires traces to preserve intermediate
states, not only the final answer. For each run variant, prefer recording:

- original query and rewritten query, if rewriting is enabled;
- retrieved candidates before reranking;
- reranked candidates after reranking;
- selected context with source document IDs and positions;
- compressed context with links back to original spans;
- generation output and evaluation signals;
- failure labels and evaluator rationale.

If a trace lacks one of these stages, the evaluator should abstain from the
corresponding diagnosis rather than inventing a cause.

## Variant Comparison

When comparing two RAG configurations, keep the query set fixed and change only
the configuration under test. A useful comparison report should answer:

- Did the failure label change?
- Did the useful evidence appear earlier or later in the candidate list?
- Did reranking promote or suppress the supporting document?
- Did compression remove evidence needed for faithfulness?
- Did query rewriting preserve the user's intent?

This keeps the interpretation tied to observable trace differences instead of a
single aggregate score.

## Checked Fixture

The fixture
[`tests/fixtures/config_sensitivity/retrieval_depth_variants.json`](../tests/fixtures/config_sensitivity/retrieval_depth_variants.json)
records one synthetic query under three small configurations. Its controlled
variable is `retrieval_top_k`:

- `top_k_1`: the supporting document is outside the retrieval cutoff, producing
  `retrieval_failure`, `missing_evidence`, and `unsupported_generation`.
- `top_k_3`: the supporting document is recovered, but context still includes a
  distracting neighboring document, producing `context_pollution`.
- `top_k_3_reranked`: reranking promotes the supporting document before context
  selection, removing the observed failure labels for the synthetic case.

This is a diagnostic fixture, not a benchmark claim. It demonstrates the shape
of a configuration-sensitive comparison while keeping the query, generator, and
evaluator fixed.

## Boundary

`msmarco-genqa` can own the pipeline variants:

- BM25 vs dense retrieval;
- retrieval `top_k` sweeps;
- with or without reranking;
- with or without query rewriting;
- with or without context compression.

`rag-observatory` should own the diagnostic layer:

- trace schema coverage;
- failure taxonomy comparison;
- evaluator abstention when evidence is missing;
- per-configuration failure summaries;
- reports that connect failures to architecture choices.

The research question is:

> RAG failure is often configuration-sensitive, not random.

The corresponding engineering question is whether the trace contains enough
evidence to support that claim.
