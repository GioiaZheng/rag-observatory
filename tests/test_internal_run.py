from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_observatory.reports.run import render_markdown_run_report
from rag_observatory.trace.run import STAGES, internal_run_from_trace
from rag_observatory.trace.schema import RagTrace

ROOT = Path(__file__).resolve().parents[1]
TRACE_PATH = ROOT / "tests" / "fixtures" / "stage_contract" / "full_observability_trace.json"


class InternalRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.trace = RagTrace.from_json(TRACE_PATH.read_text(encoding="utf-8"))
        self.run = internal_run_from_trace(self.trace)

    def test_converter_builds_all_stage_spans_and_preserves_payloads(self) -> None:
        self.assertEqual([span.stage for span in self.run.spans], list(STAGES))
        spans = {span.stage: span for span in self.run.spans}

        self.assertEqual(spans["query"].output["query"], self.trace.query.to_dict())
        self.assertEqual(
            spans["retrieval"].output["documents"],
            [document.to_dict() for document in self.trace.retrieved_documents],
        )
        self.assertEqual(
            spans["reranking"].output["documents"],
            [document.to_dict() for document in self.trace.reranked_documents],
        )
        self.assertEqual(
            spans["diagnostics"].output["metadata"],
            self.trace.metadata.to_dict(),
        )

    def test_large_text_is_kept_out_of_attributes(self) -> None:
        serialized_attributes = json.dumps(
            {
                "run": self.run.attributes,
                "spans": [span.attributes for span in self.run.spans],
            }
        )

        self.assertNotIn(self.trace.query.text, serialized_attributes)
        self.assertNotIn(self.trace.answer.text, serialized_attributes)

    def test_report_consumes_stage_spans_and_attributes_failures(self) -> None:
        report = render_markdown_run_report(self.run)

        self.assertIn("# Stage-aware RAG Run Report", report)
        self.assertIn("| `reranking` | `reranking_error` |", report)
        self.assertIn("| `generation` | `wrong_citation` |", report)
        self.assertIn("span-reranking", report)

    def test_cli_writes_internal_run_and_stage_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "run.md"
            run_path = Path(tmp) / "run.json"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "rag_observatory.cli.main",
                    "run-report",
                    str(TRACE_PATH),
                    "--output",
                    str(report_path),
                    "--run-output",
                    str(run_path),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            run_data = json.loads(run_path.read_text(encoding="utf-8"))
            report = report_path.read_text(encoding="utf-8")

        self.assertEqual(run_data["format"], "rag-observatory.internal-run.v1")
        self.assertIn("Failure Attribution", report)


if __name__ == "__main__":
    unittest.main()
