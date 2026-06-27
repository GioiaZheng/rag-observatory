import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_observatory.compare.traces import compare_traces
from rag_observatory.reports.comparison import render_markdown_comparison
from rag_observatory.trace.schema import RagTrace

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "toy_runs"


class TraceComparisonTests(unittest.TestCase):
    def load_trace(self, name: str) -> RagTrace:
        data = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
        return RagTrace.from_dict(data)

    def test_compare_traces_tracks_core_pipeline_changes(self) -> None:
        before = self.load_trace("comparison_before.json")
        after = self.load_trace("comparison_after.json")

        comparison = compare_traces(before, after)

        self.assertTrue(comparison.same_query_id)
        self.assertTrue(comparison.same_query_text)
        self.assertEqual(comparison.retrieved_documents.added_ids, ["doc-france"])
        self.assertEqual(comparison.retrieved_documents.removed_ids, ["doc-lyon"])
        self.assertEqual(comparison.retrieved_documents.kept_ids, ["doc-paris"])
        self.assertEqual(comparison.retrieved_documents.rank_changes[0].item_id, "doc-paris")
        self.assertEqual(comparison.retrieved_documents.rank_changes[0].before_rank, 2)
        self.assertEqual(comparison.retrieved_documents.rank_changes[0].after_rank, 1)
        self.assertEqual(comparison.selected_context_documents.added_ids, ["doc-paris"])
        self.assertEqual(comparison.selected_context_documents.removed_ids, ["doc-lyon"])
        self.assertTrue(comparison.answer_changed)

        faithfulness = next(
            metric for metric in comparison.metric_changes if metric.name == "faithfulness"
        )
        self.assertEqual(faithfulness.status, "changed")
        self.assertEqual(faithfulness.before_value, 0.0)
        self.assertEqual(faithfulness.after_value, 1.0)
        self.assertIn("contradicted_by_context", comparison.failure_labels.removed_ids)
        self.assertIn("unsupported_answer", comparison.failure_labels.removed_ids)

    def test_comparison_report_renders_required_sections(self) -> None:
        before = self.load_trace("comparison_before.json")
        after = self.load_trace("comparison_after.json")
        report = render_markdown_comparison(before, after)

        for heading in [
            "## Run Pair",
            "## Query",
            "## Retrieved Documents",
            "## Selected Context Documents",
            "## Generated Answer",
            "## Evaluation Signals",
            "## Failure Labels",
        ]:
            self.assertIn(heading, report)

        self.assertIn("doc-france", report)
        self.assertIn("doc-lyon", report)
        self.assertIn("unsupported_answer", report)


if __name__ == "__main__":
    unittest.main()
