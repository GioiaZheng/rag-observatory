from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_observatory.reports.html import render_html_report, render_report_screenshot_svg
from rag_observatory.taxonomy.failure_modes import classify_trace
from rag_observatory.trace.schema import RagTrace

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "stage_contract" / "full_observability_trace.json"


class HtmlReportTests(unittest.TestCase):
    def load_trace(self) -> RagTrace:
        return RagTrace.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))

    def test_html_report_renders_semantic_sections(self) -> None:
        trace = self.load_trace()
        labels = classify_trace(trace)
        report = render_html_report(trace, failure_labels=labels)

        self.assertIn("<!doctype html>", report)
        self.assertIn('<main class="report">', report)
        self.assertIn("Trace-based RAG failure analysis", report)
        self.assertIn("Retrieved Documents", report)
        self.assertIn("Reranked Documents", report)
        self.assertIn("Selected Context", report)
        self.assertIn("Evaluation Signals", report)
        self.assertIn("Failure Modes", report)
        self.assertIn("reranking_error", report)
        self.assertNotIn("<pre>", report)

    def test_html_report_escapes_trace_text(self) -> None:
        trace_data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        trace_data["query"]["text"] = "What does <script>alert(1)</script> mean?"
        trace = RagTrace.from_dict(trace_data)
        report = render_html_report(trace)

        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", report)
        self.assertNotIn("<script>alert(1)</script>", report)

    def test_svg_preview_renders_checked_summary(self) -> None:
        trace = self.load_trace()
        labels = classify_trace(trace)
        preview = render_report_screenshot_svg(trace, failure_labels=labels)

        self.assertIn("<svg", preview)
        self.assertIn("RAG Diagnostic Report", preview)
        self.assertIn("reranking error", preview)
        self.assertIn("Pipeline stages", preview)


if __name__ == "__main__":
    unittest.main()
