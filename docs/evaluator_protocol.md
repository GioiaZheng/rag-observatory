# Evaluator Protocol

RAG Observatory treats evaluator outputs as auditable signals, not ground truth.
The core package defines a provider-neutral protocol so deterministic rules,
reviewed human labels, supervised models, and optional model-based judges can be
compared without coupling the repository to one framework or API provider.

## Core Dimensions

The first quality dimensions are:

| Dimension | Question | Typical Trace Signals |
| --- | --- | --- |
| `context_relevance` | Is the selected context relevant to the query and answer task? | selected context document IDs, retrieval relevance annotations |
| `faithfulness` | Is the answer supported by the selected context? | faithfulness, support, or groundedness metrics |
| `answer_relevance` | Does the answer address the user query? | answer relevance or answer correctness metrics |

These dimensions are deliberately separate from failure labels. A trace may
fail a quality dimension and still require taxonomy-level diagnosis to explain
where the failure entered the pipeline.

## Input Contract

An evaluator receives a validated `RagTrace` and an explicit tuple of requested
dimensions. Evaluators may inspect only fields already present in the trace.
Core tests must not call external APIs.

Optional model-based evaluators should be implemented as adapters around this
contract. They should preserve the same input boundaries documented in
[`docs/model_based_judge_contract.md`](model_based_judge_contract.md).

## Output Contract

Each score records:

- dimension
- scalar score when available
- pass/fail judgment when available
- threshold when used
- evidence
- rationale
- abstention flag and reason

The evaluation result also records provenance: evaluator name, version, method,
input run ID, input query ID, and optional model or prompt identifiers.

## Abstention

An evaluator should abstain when the trace does not contain enough reviewable
signal for a requested dimension. Abstention is preferable to fabricating a
score from missing evidence.

The deterministic baseline abstains when:

- selected context cannot be mapped to relevance annotations;
- no faithfulness-like metric is recorded;
- no answer relevance or answer correctness metric is recorded;
- a recorded metric has neither pass/fail nor numeric value.

## Reviewed Comparison

Reviewed quality fixtures use expected pass/fail/abstain outcomes per dimension.
The comparison report shows agreement counts, disagreement rows, abstentions,
evidence, rationale, and existing failure labels for the same trace.

Run the current deterministic baseline with:

```bash
PYTHONPATH=src python -m rag_observatory.cli.main evaluate-quality tests/fixtures/quality_evaluation/expected_quality_scores.json --output outputs/reports/quality_evaluation.md
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m rag_observatory.cli.main evaluate-quality tests/fixtures/quality_evaluation/expected_quality_scores.json --output outputs/reports/quality_evaluation.md
```

The toy fixture set is for contract validation and disagreement inspection. It
must not be reported as evidence that a model-based judge or supervised
classifier is accurate on real workloads.
