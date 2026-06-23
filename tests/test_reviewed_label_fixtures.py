import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_observatory.taxonomy.failure_modes import FAILURE_MODE_VALUES, classify_trace
from rag_observatory.trace.schema import RagTrace


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "reviewed_labels"


class ReviewedLabelFixtureTests(unittest.TestCase):
    def load_cases(self) -> list[dict]:
        data = json.loads(
            (FIXTURE_DIR / "expected_failure_labels.json").read_text(encoding="utf-8")
        )
        return data["cases"]

    def load_trace(self, relative_path: str) -> RagTrace:
        trace_path = (FIXTURE_DIR / relative_path).resolve()
        return RagTrace.from_json(trace_path.read_text(encoding="utf-8"))

    def test_reviewed_expected_labels_are_valid_modes(self) -> None:
        for case in self.load_cases():
            with self.subTest(case_id=case["case_id"]):
                self.assertLessEqual(set(case["expected_modes"]), FAILURE_MODE_VALUES)

    def test_reviewed_label_fixtures_match_classifier_outputs(self) -> None:
        for case in self.load_cases():
            with self.subTest(case_id=case["case_id"]):
                trace = self.load_trace(case["trace_path"])
                predicted_modes = {label.mode for label in classify_trace(trace)}

                self.assertEqual(predicted_modes, set(case["expected_modes"]))


if __name__ == "__main__":
    unittest.main()
