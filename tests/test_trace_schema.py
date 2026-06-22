import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_observatory.trace.schema import RagTrace, TraceValidationError


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "toy_runs"


class TraceSchemaTests(unittest.TestCase):
    def load_fixture_data(self, name: str) -> dict:
        return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))

    def test_valid_trace_loads(self) -> None:
        trace = RagTrace.from_dict(self.load_fixture_data("supported_answer.json"))

        self.assertEqual(trace.metadata.run_id, "toy-supported-answer")
        self.assertEqual(trace.query.query_id, "q-supported")
        self.assertEqual(trace.retrieved_documents[0].doc_id, "doc-observability")

    def test_missing_required_field_fails(self) -> None:
        data = self.load_fixture_data("supported_answer.json")
        del data["query"]

        with self.assertRaisesRegex(TraceValidationError, "trace.query is required"):
            RagTrace.from_dict(data)

    def test_unknown_field_fails(self) -> None:
        data = self.load_fixture_data("supported_answer.json")
        data["unexpected"] = "value"

        with self.assertRaisesRegex(TraceValidationError, "unknown field"):
            RagTrace.from_dict(data)

    def test_unknown_context_document_fails(self) -> None:
        data = copy.deepcopy(self.load_fixture_data("supported_answer.json"))
        data["selected_context"][0]["doc_id"] = "missing-doc"

        with self.assertRaisesRegex(TraceValidationError, "unknown doc_id"):
            RagTrace.from_dict(data)

    def test_trace_json_round_trip(self) -> None:
        trace = RagTrace.from_dict(self.load_fixture_data("unsupported_answer.json"))
        round_tripped = RagTrace.from_json(trace.to_json())

        self.assertEqual(round_tripped.metadata.run_id, trace.metadata.run_id)
        self.assertEqual(round_tripped.answer.text, trace.answer.text)


if __name__ == "__main__":
    unittest.main()
