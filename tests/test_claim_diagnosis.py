import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_observatory.io.json import load_trace
from rag_observatory.reports.markdown import render_markdown_report
from rag_observatory.taxonomy.failure_modes import classify_trace
from rag_observatory.trace.schema import RagTrace, TraceValidationError

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "claims" / "claim_attribution.json"


class ClaimDiagnosisTests(unittest.TestCase):
    def test_claim_fixture_validates_with_expected_breakdown(self) -> None:
        trace = load_trace(FIXTURE)
        labels = [claim.support_label for claim in trace.claims]
        categories = [claim.failure_category for claim in trace.claims]

        self.assertEqual(len(trace.claims), 4)
        self.assertIn("supported", labels)
        self.assertIn("partially_supported", labels)
        self.assertIn("contradicted", labels)
        self.assertIn("insufficient_evidence", labels)
        self.assertIn("retrieval", categories)
        self.assertIn("answer_construction", categories)

    def test_markdown_report_renders_claim_breakdown(self) -> None:
        trace = load_trace(FIXTURE)
        report = render_markdown_report(trace, failure_labels=classify_trace(trace))

        self.assertIn("## Claim-Level Diagnosis", report)
        self.assertIn("Support Summary", report)
        self.assertIn("Attribution Summary", report)
        self.assertIn("partially_supported", report)
        self.assertIn("contradicted", report)
        self.assertIn("insufficient_evidence", report)
        self.assertIn("answer_construction", report)
        self.assertIn("retrieval", report)

    def test_unknown_claim_evidence_doc_id_fails(self) -> None:
        data = _load_fixture_data()
        data["claims"][0]["evidence"][0]["doc_id"] = "missing-doc"

        with self.assertRaisesRegex(TraceValidationError, "unknown doc_id missing-doc"):
            RagTrace.from_dict(data)

    def test_claim_evidence_reference_requires_id(self) -> None:
        data = _load_fixture_data()
        data["claims"][0]["evidence"][0] = {"quote": "no id"}

        with self.assertRaisesRegex(TraceValidationError, "doc_id or context_id"):
            RagTrace.from_dict(data)

    def test_claim_confidence_must_be_probability(self) -> None:
        data = _load_fixture_data()
        data["claims"][0]["confidence"] = 1.2

        with self.assertRaisesRegex(TraceValidationError, "confidence"):
            RagTrace.from_dict(data)

    def test_claim_diagnosis_round_trip(self) -> None:
        trace = load_trace(FIXTURE)
        round_tripped = RagTrace.from_json(trace.to_json())

        self.assertEqual(round_tripped.claims[1].support_label, "partially_supported")
        self.assertEqual(round_tripped.claims[3].evidence, [])


def _load_fixture_data() -> dict:
    return copy.deepcopy(json.loads(FIXTURE.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
