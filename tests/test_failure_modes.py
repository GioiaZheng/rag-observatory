import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_observatory.taxonomy.failure_modes import FAILURE_MODE_VALUES, classify_trace
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

    def test_manual_labels_are_preserved_and_heuristics_are_added(self) -> None:
        labels = classify_trace(self.load_trace("unsupported_answer.json"))
        modes = {label.mode for label in labels}

        self.assertIn("contradicted_by_context", modes)
        self.assertIn("unsupported_answer", modes)

    def test_failure_taxonomy_docs_cover_all_modes(self) -> None:
        docs = (ROOT / "docs" / "failure_taxonomy.md").read_text(encoding="utf-8")

        for mode in FAILURE_MODE_VALUES:
            with self.subTest(mode=mode):
                self.assertIn(f"`{mode}`", docs)


if __name__ == "__main__":
    unittest.main()
