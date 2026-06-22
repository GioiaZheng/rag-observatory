import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_observatory.reports.markdown import render_markdown_report
from rag_observatory.taxonomy.failure_modes import classify_trace
from rag_observatory.trace.schema import RagTrace


ROOT = Path(__file__).resolve().parents[1]


class DocumentedExampleTests(unittest.TestCase):
    def test_synthetic_report_example_matches_renderer(self) -> None:
        trace_data = json.loads(
            (ROOT / "tests" / "fixtures" / "toy_runs" / "unsupported_answer.json").read_text(
                encoding="utf-8"
            )
        )
        trace = RagTrace.from_dict(trace_data)
        expected_report = render_markdown_report(trace, failure_labels=classify_trace(trace))
        documented_report = (ROOT / "docs" / "examples" / "synthetic_diagnostic_report.md").read_text(
            encoding="utf-8"
        )

        self.assertEqual(documented_report, expected_report)


if __name__ == "__main__":
    unittest.main()
