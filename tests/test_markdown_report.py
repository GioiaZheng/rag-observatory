import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_observatory.reports.markdown import render_markdown_report
from rag_observatory.taxonomy.failure_modes import classify_trace
from rag_observatory.trace.schema import RagTrace


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "toy_runs"


class MarkdownReportTests(unittest.TestCase):
    def load_trace(self, name: str) -> RagTrace:
        data = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
        return RagTrace.from_dict(data)

    def test_report_renders_required_sections(self) -> None:
        trace = self.load_trace("unsupported_answer.json")
        report = render_markdown_report(trace, failure_labels=classify_trace(trace))

        for heading in [
            "## Run",
            "## Query",
            "## Generated Answer",
            "## Retrieved Documents",
            "## Selected Context",
            "## Evidence and Citations",
            "## Evaluation Signals",
            "## Failure Modes",
            "## Likely Failure Source",
            "## Inspect Next",
        ]:
            self.assertIn(heading, report)

    def test_report_includes_failure_modes(self) -> None:
        trace = self.load_trace("unsupported_answer.json")
        report = render_markdown_report(trace, failure_labels=classify_trace(trace))

        self.assertIn("contradicted_by_context", report)
        self.assertIn("unsupported_answer", report)
        self.assertIn("Vitamin D prevents scurvy", report)


if __name__ == "__main__":
    unittest.main()
