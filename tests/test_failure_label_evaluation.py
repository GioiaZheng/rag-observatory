import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_observatory.evaluation.failure_labels import (
    LabelPrediction,
    ReviewedLabelCase,
    evaluate_failure_labels,
    evaluate_heuristic_failure_labels,
)
from rag_observatory.reports.failure_label_evaluation import (
    render_markdown_failure_label_evaluation,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "reviewed_labels"


class FailureLabelEvaluationTests(unittest.TestCase):
    def test_evaluation_computes_mode_metrics_and_abstention_rate(self) -> None:
        cases = [
            ReviewedLabelCase(
                case_id="case-a",
                trace_path=Path("case-a.json"),
                expected_modes=("unsupported_answer", "missing_citation"),
            ),
            ReviewedLabelCase(
                case_id="case-b",
                trace_path=Path("case-b.json"),
                expected_modes=("retrieval_miss",),
            ),
            ReviewedLabelCase(
                case_id="case-c",
                trace_path=Path("case-c.json"),
                expected_modes=(),
            ),
        ]
        predictions = [
            LabelPrediction(
                case_id="case-a",
                predicted_modes=("unsupported_answer", "wrong_citation"),
            ),
            LabelPrediction(case_id="case-b", predicted_modes=(), abstained=True),
            LabelPrediction(case_id="case-c", predicted_modes=("retrieval_noise",)),
        ]

        evaluation = evaluate_failure_labels(cases, predictions)
        metrics = {metric.mode: metric for metric in evaluation.mode_metrics}

        self.assertEqual(evaluation.total_cases, 3)
        self.assertEqual(evaluation.abstention_count, 1)
        self.assertAlmostEqual(evaluation.abstention_rate or 0, 1 / 3)
        self.assertEqual(metrics["unsupported_answer"].true_positives, 1)
        self.assertEqual(metrics["unsupported_answer"].precision, 1.0)
        self.assertEqual(metrics["unsupported_answer"].recall, 1.0)
        self.assertEqual(metrics["missing_citation"].false_negatives, 1)
        self.assertIsNone(metrics["missing_citation"].precision)
        self.assertEqual(metrics["missing_citation"].recall, 0.0)
        self.assertEqual(metrics["wrong_citation"].false_positives, 1)
        self.assertEqual(metrics["wrong_citation"].precision, 0.0)
        self.assertIsNone(metrics["wrong_citation"].recall)

    def test_reviewed_fixtures_evaluate_cleanly_for_current_heuristics(self) -> None:
        evaluation = evaluate_heuristic_failure_labels(
            FIXTURE_DIR / "expected_failure_labels.json"
        )

        self.assertEqual(evaluation.total_cases, 7)
        self.assertEqual(evaluation.exact_match_count, 7)
        self.assertEqual(evaluation.abstention_count, 0)
        self.assertTrue(all(not case.false_positives for case in evaluation.cases))
        self.assertTrue(all(not case.false_negatives for case in evaluation.cases))
        self.assertTrue(all(metric.precision == 1.0 for metric in evaluation.mode_metrics))
        self.assertTrue(all(metric.recall == 1.0 for metric in evaluation.mode_metrics))

    def test_markdown_report_surfaces_metrics_and_inspectable_examples(self) -> None:
        cases = [
            ReviewedLabelCase(
                case_id="case-a",
                trace_path=Path("fixtures/case-a.json"),
                expected_modes=("missing_citation",),
            )
        ]
        predictions = [
            LabelPrediction(case_id="case-a", predicted_modes=("wrong_citation",))
        ]

        report = render_markdown_failure_label_evaluation(
            evaluate_failure_labels(cases, predictions),
            labeler_name="test-labeler",
        )

        self.assertIn("# Failure Label Evaluation", report)
        self.assertIn("test-labeler", report)
        self.assertIn("## Per-Mode Metrics", report)
        self.assertIn("## False Positives", report)
        self.assertIn("## False Negatives", report)
        self.assertIn("fixtures/case-a.json", report)
        self.assertIn("wrong_citation", report)
        self.assertIn("missing_citation", report)


if __name__ == "__main__":
    unittest.main()
