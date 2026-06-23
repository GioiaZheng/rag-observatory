import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_observatory.taxonomy.failure_modes import (
    FAILURE_MODE_VALUES,
    HEURISTIC_LABEL_FUNCTIONS,
    classify_trace,
    metric_disagreement_label,
    missing_citation_label,
    retrieval_miss_label,
    unsupported_answer_label,
    wrong_citation_label,
)
from rag_observatory.trace.schema import RagTrace


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "toy_runs"


class FailureModeTests(unittest.TestCase):
    def load_trace(self, name: str) -> RagTrace:
        data = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
        return RagTrace.from_dict(data)

    def test_failure_mode_values_are_stable(self) -> None:
        self.assertEqual(
            FAILURE_MODE_VALUES,
            {
                "retrieval_miss",
                "retrieval_noise",
                "reranking_error",
                "context_truncation",
                "context_pollution",
                "unsupported_answer",
                "contradicted_by_context",
                "missing_citation",
                "wrong_citation",
                "ambiguous_question",
                "metric_disagreement",
                "unknown",
            },
        )

    def test_retrieval_miss_is_classified(self) -> None:
        labels = classify_trace(self.load_trace("retrieval_miss.json"))
        modes = {label.mode for label in labels}

        self.assertIn("retrieval_miss", modes)
        self.assertIn("retrieval_noise", modes)
        self.assertIn("context_pollution", modes)

    def test_retrieval_miss_label_function_emits_evidence(self) -> None:
        label = retrieval_miss_label(self.load_trace("retrieval_miss.json"))

        self.assertIsNotNone(label)
        self.assertEqual(label.mode, "retrieval_miss")
        self.assertEqual(label.detection_method, "heuristic")
        self.assertIn("not relevant", label.evidence or "")

    def test_unsupported_answer_label_function_uses_support_metrics(self) -> None:
        label = unsupported_answer_label(self.load_trace("unsupported_answer.json"))

        self.assertIsNotNone(label)
        self.assertEqual(label.mode, "unsupported_answer")
        self.assertEqual(label.severity, "high")
        self.assertEqual(label.evidence, "faithfulness failed")

    def test_missing_citation_label_function_checks_pipeline_stage(self) -> None:
        trace = self.load_trace("retrieval_miss.json")

        self.assertIsNone(missing_citation_label(trace))

        data = json.loads(
            (FIXTURE_DIR / "supported_answer.json").read_text(encoding="utf-8")
        )
        data["answer"]["citations"] = []
        trace_with_missing_citation = RagTrace.from_dict(data)

        label = missing_citation_label(trace_with_missing_citation)

        self.assertIsNotNone(label)
        self.assertEqual(label.mode, "missing_citation")

    def test_wrong_citation_label_function_checks_cited_relevance(self) -> None:
        label = wrong_citation_label(self.load_trace("comparison_before.json"))

        self.assertIsNotNone(label)
        self.assertEqual(label.mode, "wrong_citation")

    def test_metric_disagreement_label_function_checks_pass_fail_mix(self) -> None:
        data = json.loads(
            (FIXTURE_DIR / "supported_answer.json").read_text(encoding="utf-8")
        )
        data["metrics"][0]["passed"] = True
        data["metrics"][1]["passed"] = False
        trace = RagTrace.from_dict(data)

        label = metric_disagreement_label(trace)

        self.assertIsNotNone(label)
        self.assertEqual(label.mode, "metric_disagreement")

    def test_manual_labels_are_preserved_and_heuristics_are_added(self) -> None:
        labels = classify_trace(self.load_trace("unsupported_answer.json"))
        modes = {label.mode for label in labels}

        self.assertIn("contradicted_by_context", modes)
        self.assertIn("unsupported_answer", modes)

    def test_manual_labels_take_precedence_over_duplicate_heuristics(self) -> None:
        data = json.loads(
            (FIXTURE_DIR / "unsupported_answer.json").read_text(encoding="utf-8")
        )
        data["failures"].append(
            {
                "mode": "unsupported_answer",
                "detection_method": "manual",
                "severity": "medium",
                "evidence": "Reviewer marked the answer as unsupported.",
            }
        )
        labels = classify_trace(RagTrace.from_dict(data))
        unsupported_labels = [label for label in labels if label.mode == "unsupported_answer"]

        self.assertEqual(len(unsupported_labels), 1)
        self.assertEqual(unsupported_labels[0].detection_method, "manual")

    def test_heuristic_label_functions_have_stable_order(self) -> None:
        self.assertEqual(
            [label_function.__name__ for label_function in HEURISTIC_LABEL_FUNCTIONS],
            [
                "retrieval_miss_label",
                "retrieval_noise_label",
                "context_truncation_label",
                "context_pollution_label",
                "reranking_error_label",
                "metric_disagreement_label",
                "unsupported_answer_label",
                "missing_citation_label",
                "wrong_citation_label",
            ],
        )

    def test_failure_taxonomy_docs_cover_all_modes(self) -> None:
        docs = (ROOT / "docs" / "failure_taxonomy.md").read_text(encoding="utf-8")

        for mode in FAILURE_MODE_VALUES:
            with self.subTest(mode=mode):
                self.assertIn(f"`{mode}`", docs)


if __name__ == "__main__":
    unittest.main()
