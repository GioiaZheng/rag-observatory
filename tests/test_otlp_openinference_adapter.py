from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from rag_observatory.adapters.otlp_openinference import (
    OtlpOpenInferenceAdapterError,
    load_otlp_openinference_trace,
    trace_from_otlp_openinference_export,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "openinference" / "otlp_rag_trace.json"


class OtlpOpenInferenceAdapterTests(unittest.TestCase):
    def test_maps_openinference_rag_spans_into_trace(self) -> None:
        trace = load_otlp_openinference_trace(FIXTURE)

        self.assertEqual(trace.metadata.run_id, "0123456789abcdef0123456789abcdef")
        self.assertEqual(trace.metadata.timestamp, "2025-01-01T00:00:00Z")
        self.assertEqual(trace.metadata.retriever, "vector-search")
        self.assertEqual(trace.metadata.reranker, "synthetic-cross-encoder")
        self.assertEqual(trace.metadata.generator, "synthetic-generator")
        self.assertEqual(trace.query.text, "What prevents scurvy?")
        self.assertEqual(trace.answer.text, "Vitamin C prevents scurvy.")

        self.assertEqual(
            [document.doc_id for document in trace.retrieved_documents],
            ["retrieved:doc-vitamin-c", "retrieved:doc-vitamin-d"],
        )
        self.assertEqual(trace.retrieved_documents[0].score, 0.98)
        self.assertEqual(
            trace.retrieved_documents[0].extra["metadata"],
            {"source": "synthetic-medical-note"},
        )
        self.assertEqual(
            [document.doc_id for document in trace.reranked_documents],
            ["reranked:doc-vitamin-c", "reranked:doc-vitamin-d"],
        )
        self.assertEqual(trace.selected_context, [])
        self.assertIn("intentionally left empty", trace.diagnostic_notes[-1].note)
        self.assertEqual(
            [(metric.name, metric.value) for metric in trace.metrics],
            [
                ("llm.token_count.prompt", 32),
                ("llm.token_count.completion", 6),
                ("llm.token_count.total", 38),
            ],
        )

    def test_requires_trace_selection_for_multi_trace_export(self) -> None:
        export = json.loads(FIXTURE.read_text(encoding="utf-8"))
        second = copy.deepcopy(export["resourceSpans"][0]["scopeSpans"][0]["spans"][0])
        second["traceId"] = "ffffffffffffffffffffffffffffffff"
        second["spanId"] = "ffffffffffffffff"
        export["resourceSpans"][0]["scopeSpans"][0]["spans"].append(second)

        with self.assertRaisesRegex(OtlpOpenInferenceAdapterError, "pass --trace-id"):
            trace_from_otlp_openinference_export(export)

        trace = trace_from_otlp_openinference_export(
            export,
            trace_id="0123456789ABCDEF0123456789ABCDEF",
        )
        self.assertEqual(trace.metadata.run_id, "0123456789abcdef0123456789abcdef")

    def test_decodes_nested_otlp_any_values(self) -> None:
        export = json.loads(FIXTURE.read_text(encoding="utf-8"))
        resource_attributes = export["resourceSpans"][0]["resource"]["attributes"]
        resource_attributes.append(
            {
                "key": "deployment.labels",
                "value": {
                    "kvlistValue": {
                        "values": [
                            {"key": "stable", "value": {"boolValue": True}},
                            {
                                "key": "regions",
                                "value": {
                                    "arrayValue": {
                                        "values": [
                                            {"stringValue": "eu"},
                                            {"stringValue": "us"},
                                        ]
                                    }
                                },
                            },
                        ]
                    }
                },
            }
        )

        trace = trace_from_otlp_openinference_export(export)
        self.assertEqual(trace.metadata.extra["service_name"], "synthetic-rag-service")


if __name__ == "__main__":
    unittest.main()

