from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_observatory.taxonomy.failure_modes import classify_trace
from rag_observatory.trace.schema import RagTrace

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "stage_contract" / "full_observability_trace.json"


class TraceStageContractTests(unittest.TestCase):
    def test_full_stage_contract_fixture_is_valid(self) -> None:
        trace = RagTrace.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))

        self.assertEqual(trace.metadata.run_id, "stage-contract-full-observability")
        self.assertTrue(trace.metadata.pipeline_stages["retrieval"])
        self.assertTrue(trace.metadata.pipeline_stages["reranking"])
        self.assertTrue(trace.metadata.pipeline_stages["prompt"])
        self.assertEqual(len(trace.retrieved_documents), 2)
        self.assertEqual(len(trace.reranked_documents), 2)
        self.assertEqual(trace.selected_context[0].doc_id, "reranked-doc-calcium-channel-blockers")
        self.assertIsNotNone(trace.prompt)
        self.assertEqual(trace.metrics[0].name, "context_relevance")

    def test_stage_contract_fixture_maps_to_expected_failure_labels(self) -> None:
        trace = RagTrace.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))
        modes = {label.mode for label in classify_trace(trace)}

        self.assertEqual(
            modes,
            {
                "retrieval_noise",
                "reranking_error",
                "context_truncation",
                "context_pollution",
                "metric_disagreement",
                "unsupported_answer",
                "wrong_citation",
            },
        )

    def test_stage_contract_document_references_checked_fixture(self) -> None:
        docs = (ROOT / "docs" / "trace_stage_contract.md").read_text(encoding="utf-8")

        self.assertIn("tests/fixtures/stage_contract/full_observability_trace.json", docs)
        self.assertIn("retrieval", docs)
        self.assertIn("reranking", docs)
        self.assertIn("prompt", docs)
        self.assertIn("generation", docs)
        self.assertIn("evaluation", docs)


if __name__ == "__main__":
    unittest.main()
