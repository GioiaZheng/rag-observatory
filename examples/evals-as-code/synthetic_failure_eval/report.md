# Synthetic Failure Eval

## Task

- **Task ID:** `synthetic_failure_eval_v1`
- **Dataset:** `dataset.jsonl`
- **Threshold:** 0.8
- **Dimensions:** `context_relevance`, `faithfulness`, `answer_relevance`

## Summary

- **Cases:** 3
- **Quality judgments:** 9
- **Quality agreements:** 9
- **Quality disagreements:** 0
- **Quality abstentions:** 2
- **Failure-label exact matches:** 3

## Inputs and Outputs

| Case | Trace | Query | Answer | Failure Labels |
| --- | --- | --- | --- | --- |
| `clean_supported` | `tests/fixtures/reviewed_labels/traces/clean_supported_answer.json` | What city is the capital of France? | Paris is the capital of France. | none |
| `unsupported_generation` | `tests/fixtures/toy_runs/unsupported_answer.json` | Which vitamin prevents scurvy? | Vitamin D prevents scurvy. | `contradicted_by_context`, `unsupported_answer` |
| `retrieval_miss` | `tests/fixtures/toy_runs/retrieval_miss.json` | Who discovered penicillin? | Frederick Banting discovered penicillin. | `retrieval_miss`, `retrieval_noise`, `context_pollution` |

## Quality Scores

| Case | Dimension | Expected | Observed | Score | Threshold | Evidence |
| --- | --- | --- | --- | ---: | ---: | --- |
| `clean_supported` | `context_relevance` | pass | pass | 1.00 | 0.80 | 1/1 selected context chunks map to relevant retrieved documents |
| `clean_supported` | `faithfulness` | abstained | abstained | n/a | n/a | no faithfulness metric is recorded |
| `clean_supported` | `answer_relevance` | pass | pass | 1.00 | 0.80 | answer_correctness=1.0; passed=True; threshold=0.8; run_id=reviewed-clean-supported-answer |
| `unsupported_generation` | `context_relevance` | pass | pass | 1.00 | 0.80 | 1/1 selected context chunks map to relevant retrieved documents |
| `unsupported_generation` | `faithfulness` | fail | fail | 0.00 | 0.80 | faithfulness=0.0; passed=False; threshold=0.8; notes=The answer changes vitamin C to vitamin D.; run_id=toy-unsupported-answer |
| `unsupported_generation` | `answer_relevance` | fail | fail | 0.00 | 0.80 | answer_correctness=0.0; passed=False; threshold=0.8; run_id=toy-unsupported-answer |
| `retrieval_miss` | `context_relevance` | fail | fail | 0.00 | 0.80 | 0/1 selected context chunks map to relevant retrieved documents |
| `retrieval_miss` | `faithfulness` | abstained | abstained | n/a | n/a | no faithfulness metric is recorded |
| `retrieval_miss` | `answer_relevance` | fail | fail | 0.00 | 0.80 | answer_correctness=0.0; passed=False; threshold=0.8; run_id=toy-retrieval-miss |

## Failure Label Checks

| Case | Expected | Observed | False Positives | False Negatives | Exact Match |
| --- | --- | --- | --- | --- | --- |
| `clean_supported` | none | none | none | none | True |
| `unsupported_generation` | `contradicted_by_context`, `unsupported_answer` | `contradicted_by_context`, `unsupported_answer` | none | none | True |
| `retrieval_miss` | `retrieval_miss`, `retrieval_noise`, `context_pollution` | `retrieval_miss`, `retrieval_noise`, `context_pollution` | none | none | True |

## Interpretation

This checked fixture treats evaluation as versioned project code: the dataset, task configuration, solver, scorer, runner, and report are all reviewable. It is intentionally synthetic and should not be reported as dataset-scale evidence.
