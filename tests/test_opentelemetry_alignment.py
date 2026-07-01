from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "stage_contract" / "opentelemetry_aligned_run.json"
DOC = ROOT / "docs" / "opentelemetry_alignment.md"


class OpenTelemetryAlignmentTests(unittest.TestCase):
    def test_internal_run_fixture_has_stage_spans(self) -> None:
        run = json.loads(FIXTURE.read_text(encoding="utf-8"))

        self.assertEqual(run["format"], "rag-observatory.internal-run.v1")
        self.assertEqual(
            run["source_trace_path"], "tests/fixtures/stage_contract/full_observability_trace.json"
        )
        self.assertEqual(
            [span["stage"] for span in run["spans"]],
            [
                "query",
                "retrieval",
                "reranking",
                "context",
                "prompt",
                "generation",
                "evaluation",
                "diagnostics",
            ],
        )

    def test_stage_spans_share_diagnostic_envelope(self) -> None:
        run = json.loads(FIXTURE.read_text(encoding="utf-8"))
        required_fields = {
            "span_id",
            "parent_span_id",
            "name",
            "stage",
            "started_at",
            "ended_at",
            "latency_ms",
            "status",
            "error_type",
            "input",
            "output",
            "metrics",
            "attributes",
            "events",
            "links",
        }

        for span in run["spans"]:
            self.assertEqual(set(span), required_fields)
            self.assertIsInstance(span["input"], dict)
            self.assertIsInstance(span["output"], dict)
            self.assertIsInstance(span["metrics"], dict)
            self.assertIsInstance(span["attributes"], dict)
            self.assertIsInstance(span["events"], list)

    def test_fixture_keeps_large_text_out_of_attributes(self) -> None:
        run = json.loads(FIXTURE.read_text(encoding="utf-8"))
        forbidden_attribute_names = {"query_text", "prompt_text", "document_text", "answer_text"}

        self.assertTrue(forbidden_attribute_names.isdisjoint(run["attributes"]))
        for span in run["spans"]:
            self.assertTrue(forbidden_attribute_names.isdisjoint(span["attributes"]))

    def test_document_references_checked_fixture_and_mapping(self) -> None:
        doc = DOC.read_text(encoding="utf-8")

        self.assertIn("tests/fixtures/stage_contract/opentelemetry_aligned_run.json", doc)
        self.assertIn("Public Trace Field", doc)
        self.assertIn("Internal Run Span", doc)
        self.assertIn("retrieved_documents", doc)
        self.assertIn("selected_context", doc)


if __name__ == "__main__":
    unittest.main()
