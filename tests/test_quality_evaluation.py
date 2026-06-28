import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_observatory.evaluation.quality import (
    ANSWER_RELEVANCE,
    CONTEXT_RELEVANCE,
    FAITHFULNESS,
    EvaluatorInput,
    ReviewedQualityCase,
    ReviewedQualityScore,
    RuleBasedQualityEvaluator,
    evaluate_quality_cases,
    evaluate_rule_based_quality,
    load_reviewed_quality_cases,
)
from rag_observatory.io.json import load_trace
from rag_observatory.reports.quality import render_markdown_quality_evaluation

ROOT = Path(__file__).resolve().parents[1]
TOY_RUNS = ROOT / "tests" / "fixtures" / "toy_runs"
QUALITY_FIXTURES = ROOT / "tests" / "fixtures" / "quality_evaluation"
EXPECTED_QUALITY = QUALITY_FIXTURES / "expected_quality_scores.json"


class QualityEvaluationTests(unittest.TestCase):
    def test_rule_based_quality_scores_supported_trace_with_provenance(self) -> None:
        trace = load_trace(TOY_RUNS / "supported_answer.json")
        evaluation = RuleBasedQualityEvaluator().evaluate(EvaluatorInput(trace=trace))

        self.assertEqual(evaluation.trace_id, "toy-supported-answer")
        self.assertEqual(evaluation.query_id, "q-supported")
        self.assertEqual(evaluation.provenance.evaluator_name, "rule_based_quality")
        self.assertEqual(evaluation.provenance.method, "deterministic")
        self.assertEqual(evaluation.provenance.input_run_id, trace.metadata.run_id)
        self.assertEqual(evaluation.provenance.input_query_id, trace.query.query_id)

        self.assertTrue(evaluation.score_for(CONTEXT_RELEVANCE).passed)
        self.assertTrue(evaluation.score_for(FAITHFULNESS).passed)
        self.assertTrue(evaluation.score_for(ANSWER_RELEVANCE).passed)
        self.assertIn("selected context", evaluation.score_for(CONTEXT_RELEVANCE).evidence or "")
        self.assertIn("faithfulness", evaluation.score_for(FAITHFULNESS).evidence or "")

    def test_rule_based_quality_abstains_without_reviewable_signals(self) -> None:
        trace = load_trace(QUALITY_FIXTURES / "abstain_no_signals.json")
        evaluation = RuleBasedQualityEvaluator().evaluate(EvaluatorInput(trace=trace))

        self.assertTrue(all(score.abstained for score in evaluation.scores))
        self.assertTrue(all(score.passed is None for score in evaluation.scores))
        self.assertIn(
            "relevance annotations",
            evaluation.score_for(CONTEXT_RELEVANCE).abstention_reason or "",
        )
        self.assertIn(
            "no faithfulness metric",
            evaluation.score_for(FAITHFULNESS).abstention_reason or "",
        )

    def test_reviewed_quality_fixture_matches_rule_based_evaluator(self) -> None:
        cases = load_reviewed_quality_cases(EXPECTED_QUALITY)
        evaluation = evaluate_rule_based_quality(EXPECTED_QUALITY)

        self.assertEqual(len(cases), 4)
        self.assertEqual(evaluation.total_cases, 4)
        self.assertEqual(evaluation.total_rows, 12)
        self.assertEqual(evaluation.agreement_count, 12)
        self.assertEqual(evaluation.disagreement_count, 0)
        self.assertEqual(evaluation.abstention_count, 4)
        self.assertTrue(any("retrieval_miss" in row.failure_modes for row in evaluation.rows))

    def test_disagreement_report_surfaces_failure_labels_and_evidence(self) -> None:
        cases = [
            ReviewedQualityCase(
                case_id="expected-context-pass",
                trace_path=TOY_RUNS / "retrieval_miss.json",
                expected_scores=(
                    ReviewedQualityScore(
                        dimension=CONTEXT_RELEVANCE,
                        passed=True,
                        abstained=False,
                    ),
                ),
            )
        ]

        evaluation = evaluate_quality_cases(cases, RuleBasedQualityEvaluator())
        report = render_markdown_quality_evaluation(evaluation)

        self.assertEqual(evaluation.disagreement_count, 1)
        self.assertIn("# Quality Evaluation", report)
        self.assertIn("## Disagreements", report)
        self.assertIn("context_relevance", report)
        self.assertIn("retrieval_miss", report)
        self.assertIn("selected context chunks", report)


if __name__ == "__main__":
    unittest.main()
