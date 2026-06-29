import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_observatory.adapters.msmarco_genqa import (
    MSMARCO_GENQA_EXPORT_FORMAT,
    MsmarcoGenqaAdapterError,
    load_msmarco_genqa_trace,
    trace_from_msmarco_genqa_export,
)
from rag_observatory.io.json import dump_trace, load_trace
from rag_observatory.reports.markdown import render_markdown_report
from rag_observatory.taxonomy.failure_modes import classify_trace
from rag_observatory.trace.schema import RagTrace

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "msmarco_genqa" / "synthetic_export.json"


class MsmarcoGenqaAdapterTests(unittest.TestCase):
    def test_maps_synthetic_export_to_valid_trace(self) -> None:
        trace = load_msmarco_genqa_trace(FIXTURE)

        self.assertEqual(trace.metadata.run_id, "synthetic-msmarco-genqa-run-001")
        self.assertEqual(trace.metadata.dataset, "synthetic-msmarco-genqa")
        self.assertEqual(trace.query.query_id, "msmarco-synthetic-q001")
        self.assertEqual(len(trace.retrieved_documents), 2)
        self.assertEqual(len(trace.selected_context), 1)
        self.assertEqual(trace.answer.citations[0].doc_id, "doc-penicillin")
        self.assertEqual(trace.reranked_documents, [])
        self.assertIsNone(trace.prompt)

        adapter_extra = trace.extra["msmarco_genqa_adapter"]
        self.assertEqual(adapter_extra["source_format"], MSMARCO_GENQA_EXPORT_FORMAT)
        self.assertEqual(
            adapter_extra["missing_optional_fields"],
            ["reranked_documents", "prompt"],
        )
        self.assertTrue(
            any(note.stage == "adapter" for note in trace.diagnostic_notes),
            "missing optional fields should be explicit in diagnostic notes",
        )

        reloaded = RagTrace.from_dict(trace.to_dict())
        self.assertEqual(reloaded.metadata.run_id, trace.metadata.run_id)

    def test_mapped_trace_can_render_report(self) -> None:
        trace = load_msmarco_genqa_trace(FIXTURE)
        report = render_markdown_report(trace, failure_labels=classify_trace(trace))

        self.assertIn("# RAG Diagnostic Report", report)
        self.assertIn("synthetic-msmarco-genqa-run-001", report)
        self.assertIn("retrieval_noise", report)

    def test_rejects_unknown_export_format(self) -> None:
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        data["format"] = "unknown-format"

        with self.assertRaisesRegex(MsmarcoGenqaAdapterError, "export.format"):
            trace_from_msmarco_genqa_export(data)

    def test_round_trip_through_trace_io(self) -> None:
        trace = load_msmarco_genqa_trace(FIXTURE)

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "trace.json"
            dump_trace(trace, output_path)
            loaded = load_trace(output_path)

        self.assertEqual(loaded.query.text, trace.query.text)
        self.assertEqual(loaded.extra["export_id"], "synthetic-export-001")


if __name__ == "__main__":
    unittest.main()
