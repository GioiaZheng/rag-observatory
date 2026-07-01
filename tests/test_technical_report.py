from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "reports" / "2026-07-01-trace-based-rag-failure-analysis.md"
REPORT_INDEX = ROOT / "docs" / "reports" / "README.md"
README = ROOT / "README.md"


class TechnicalReportTests(unittest.TestCase):
    def test_report_covers_expected_sections(self) -> None:
        report = REPORT.read_text(encoding="utf-8")

        for heading in (
            "## Abstract",
            "## Motivation",
            "## System Goal and Non-Goals",
            "## Artifact Map",
            "## Trace Schema and Stage Contract",
            "## Failure Taxonomy",
            "## Reproducible Small Workflow",
            "## Diagnostic Reports",
            "## Benchmark Comparison",
            "## Limitations",
            "## Future Work",
        ):
            self.assertIn(heading, report)

    def test_report_links_claims_to_repository_artifacts(self) -> None:
        report = REPORT.read_text(encoding="utf-8")

        for artifact in (
            "make reproduce-small",
            "examples/reproduce-small/",
            "docs/trace_stage_contract.md",
            "docs/opentelemetry_alignment.md",
            "failure_taxonomy/",
            "docs/report_artifacts.md",
            "docs/benchmark_comparison.md",
            "docs/research_evidence_plan.md",
            "outputs/reproduce-small/",
        ):
            self.assertIn(artifact, report)

    def test_report_keeps_claims_modest(self) -> None:
        report = REPORT.read_text(encoding="utf-8")

        self.assertIn("does not claim to be a full RAG pipeline", report)
        self.assertIn("not a leaderboard", report)
        self.assertIn("synthetic", report)
        self.assertIn("no dataset-scale benchmark results are reported here", report)
        self.assertIn("heuristic labels are useful but not enough", report)

    def test_report_is_linked_from_indexes(self) -> None:
        report_path = "docs/reports/2026-07-01-trace-based-rag-failure-analysis.md"
        report_name = "2026-07-01-trace-based-rag-failure-analysis.md"

        self.assertIn(report_name, REPORT_INDEX.read_text(encoding="utf-8"))
        self.assertIn(report_path, README.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
