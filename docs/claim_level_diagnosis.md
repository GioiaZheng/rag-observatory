# Claim-Level Diagnosis

Claim-level diagnosis records externally reviewed or adapter-provided answer
claims inside a trace. It explains whether each claim is supported, partially
supported, contradicted, unsupported, or lacking sufficient evidence.

The contract is explicit by design: RAG Observatory does not automatically
segment answers into claims and does not require a hosted judge. Tokenization,
segmentation, and multilingual claim extraction should remain pluggable.

## Claim Object

Each claim records:

- `claim_id`
- `text`
- optional answer span offsets
- `support_label`
- `failure_category`
- evidence references
- optional confidence
- optional reviewer source
- diagnostic notes

Supported labels are:

- `supported`
- `partially_supported`
- `contradicted`
- `insufficient_evidence`
- `unsupported`
- `unreviewed`

Failure categories are:

- `none`
- `retrieval`
- `evidence_selection`
- `answer_construction`
- `evaluation`
- `unknown`

## Evidence References

Evidence references may point to a retrieved document, selected context chunk,
or both. A reference must include `doc_id` or `context_id`. Claims with
`insufficient_evidence` may have an empty evidence list because the diagnosis is
that the trace lacks supporting evidence.

## Relationship to Quality Dimensions

Quality dimensions such as faithfulness and answer relevance provide scalar or
pass/fail signals for a whole answer. Claim diagnosis provides inspectable
examples inside that answer. A faithfulness metric may fail because one claim is
contradicted while another is only partially supported.

## Relationship to Failure Taxonomy

Failure labels localize pipeline-level causes. Claim diagnosis explains the
answer-level evidence. For example:

| Claim Outcome | Possible Failure Label |
| --- | --- |
| `insufficient_evidence` with category `retrieval` | `retrieval_miss` |
| `partially_supported` with category `evidence_selection` | `context_truncation` |
| `contradicted` with category `answer_construction` | `contradicted_by_context` |
| `unsupported` with category `answer_construction` | `unsupported_answer` |

The two layers should remain separate. Failure labels summarize the run; claim
diagnoses preserve the concrete answer claims and evidence references that make
the diagnosis reviewable.

## Example

```json
{
  "claims": [
    {
      "claim_id": "claim-supported",
      "text": "Alexander Fleming discovered penicillin.",
      "support_label": "supported",
      "failure_category": "none",
      "evidence": [
        {
          "doc_id": "doc-penicillin",
          "context_id": "ctx-penicillin",
          "quote": "Alexander Fleming discovered penicillin in 1928."
        }
      ],
      "confidence": 1.0,
      "reviewer_source": "reviewed_fixture"
    }
  ]
}
```

The normal diagnostic report renders claim counts, attribution counts, and
per-claim evidence references when `trace.claims` is present.
