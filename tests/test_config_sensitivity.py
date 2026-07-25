from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "config_sensitivity" / "retrieval_depth_variants.json"
DOC = ROOT / "docs" / "config_sensitivity.md"
ACTUAL_REPORT = ROOT / "docs" / "reports" / "2026-07-25-scifact-retrieval-depth.md"


class ConfigurationSensitivityTests(unittest.TestCase):
    def test_variant_fixture_keeps_query_fixed(self) -> None:
        comparison = json.loads(FIXTURE.read_text(encoding="utf-8"))

        self.assertEqual(comparison["format"], "rag-observatory.config-sensitivity.v1")
        self.assertEqual(comparison["controlled_variable"], "retrieval_top_k")
        self.assertEqual(len(comparison["variants"]), 3)
        self.assertEqual(comparison["invariant_settings"]["generator"], "synthetic-generator")
        self.assertEqual(comparison["invariant_settings"]["evaluator"], "rule-based-review")

    def test_variant_fixture_shows_failure_label_changes(self) -> None:
        comparison = json.loads(FIXTURE.read_text(encoding="utf-8"))
        labels_by_variant = {
            variant["name"]: tuple(variant["failure_labels"]) for variant in comparison["variants"]
        }

        self.assertEqual(
            labels_by_variant["top_k_1"],
            ("retrieval_failure", "missing_evidence", "unsupported_generation"),
        )
        self.assertEqual(labels_by_variant["top_k_3"], ("context_pollution",))
        self.assertEqual(labels_by_variant["top_k_3_reranked"], ())

    def test_document_references_checked_fixture(self) -> None:
        doc = DOC.read_text(encoding="utf-8")

        self.assertIn("tests/fixtures/config_sensitivity/retrieval_depth_variants.json", doc)
        self.assertIn("retrieval_top_k", doc)
        self.assertIn("RAG failure is often configuration-sensitive", doc)

    def test_actual_report_records_provenance_and_scope(self) -> None:
        report = ACTUAL_REPORT.read_text(encoding="utf-8")

        self.assertIn("BEIR SciFact", report)
        self.assertIn("5f7d1de60b170fc8027bb7898e2efca1", report)
        self.assertIn("Trace records:** 40", report)
        self.assertIn("not a full generative RAG benchmark", report)
        self.assertIn("largest observed failure-rate change is localized to `retrieval`", report)


if __name__ == "__main__":
    unittest.main()
