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

    def test_all_missing_required_top_level_fields_fail(self) -> None:
        required_fields = [
            "metadata",
            "query",
            "retrieved_documents",
            "selected_context",
            "answer",
        ]

        for field in required_fields:
            with self.subTest(field=field):
                data = self.load_fixture_data("supported_answer.json")
                del data[field]

                with self.assertRaisesRegex(TraceValidationError, f"trace.{field} is required"):
                    RagTrace.from_dict(data)

    def test_missing_nested_required_field_fails(self) -> None:
        data = self.load_fixture_data("supported_answer.json")
        del data["metadata"]["run_id"]

        with self.assertRaisesRegex(
            TraceValidationError,
            "metadata.run_id must be a non-empty string",
        ):
            RagTrace.from_dict(data)

    def test_unknown_field_fails(self) -> None:
        data = self.load_fixture_data("supported_answer.json")
        data["unexpected"] = "value"

        with self.assertRaisesRegex(TraceValidationError, "unknown field"):
            RagTrace.from_dict(data)

    def test_unknown_nested_field_fails(self) -> None:
        data = self.load_fixture_data("supported_answer.json")
        data["metadata"]["unexpected"] = "value"

        with self.assertRaisesRegex(
            TraceValidationError,
            "metadata contains unknown field",
        ):
            RagTrace.from_dict(data)

    def test_malformed_nested_object_fails(self) -> None:
        data = self.load_fixture_data("supported_answer.json")
        data["metadata"] = []

        with self.assertRaisesRegex(TraceValidationError, "metadata must be an object"):
            RagTrace.from_dict(data)

    def test_malformed_nested_list_fails(self) -> None:
        data = self.load_fixture_data("supported_answer.json")
        data["retrieved_documents"] = {"doc_id": "doc"}

        with self.assertRaisesRegex(
            TraceValidationError,
            "trace.retrieved_documents must be a list",
        ):
            RagTrace.from_dict(data)

    def test_malformed_list_item_fails(self) -> None:
        data = self.load_fixture_data("supported_answer.json")
        data["retrieved_documents"][0] = "doc"

        with self.assertRaisesRegex(TraceValidationError, "document must be an object"):
            RagTrace.from_dict(data)

    def test_invalid_failure_label_values_fail(self) -> None:
        data = self.load_fixture_data("supported_answer.json")
        data["failures"] = [
            {
                "mode": "not_a_failure_mode",
                "detection_method": "not_a_detection_method",
                "severity": "critical",
            }
        ]

        with self.assertRaises(TraceValidationError) as error:
            RagTrace.from_dict(data)

        message = str(error.exception)
        self.assertIn("unknown failure mode: not_a_failure_mode", message)
        self.assertIn("unknown detection method: not_a_detection_method", message)
        self.assertIn("unknown failure severity: critical", message)

    def test_failure_label_severity_must_be_string(self) -> None:
        data = self.load_fixture_data("supported_answer.json")
        data["failures"] = [
            {
                "mode": "unsupported_answer",
                "detection_method": "manual",
                "severity": ["high"],
            }
        ]

        with self.assertRaisesRegex(
            TraceValidationError,
            "failure_label.severity must be a string",
        ):
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
