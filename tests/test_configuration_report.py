from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_observatory.reports.configuration import (
    ConfigurationReportError,
    render_markdown_configuration_report,
)
from rag_observatory.trace.schema import RagTrace

ROOT = Path(__file__).resolve().parents[1]


class ConfigurationReportTests(unittest.TestCase):
    def test_report_compares_actual_trace_records_and_localizes_stage(self) -> None:
        report = render_markdown_configuration_report(
            [_trace(top_k=1, relevant=False), _trace(top_k=5, relevant=True)],
            controlled_variable="retrieval_top_k",
        )

        self.assertIn("Trace records:** 2", report)
        self.assertIn("`retrieval_miss` 1/1", report)
        self.assertIn("| `retrieval_top_k=5` | `retrieval_hit` | 1.000 | 1/1 |", report)
        self.assertIn("largest observed failure-rate change is localized to `retrieval`", report)
        self.assertIn("reports observed stage-level associations", report)

    def test_report_rejects_non_invariant_configuration(self) -> None:
        first = _trace(top_k=1, relevant=False, context_policy="top_1")
        second = _trace(top_k=5, relevant=True, context_policy="top_2")

        with self.assertRaisesRegex(
            ConfigurationReportError,
            "other than the controlled variable are not invariant",
        ):
            render_markdown_configuration_report(
                [first, second],
                controlled_variable="retrieval_top_k",
            )

    def test_cli_reads_exported_traces_and_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            trace_paths = [temp_dir / "top-1.json", temp_dir / "top-5.json"]
            trace_paths[0].write_text(
                _trace(top_k=1, relevant=False).to_json(),
                encoding="utf-8",
            )
            trace_paths[1].write_text(
                _trace(top_k=5, relevant=True).to_json(),
                encoding="utf-8",
            )
            report_path = temp_dir / "report.md"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "rag_observatory.cli.main",
                    "config-report",
                    *(str(path) for path in trace_paths),
                    "--controlled-variable",
                    "retrieval_top_k",
                    "--output",
                    str(report_path),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = report_path.read_text(encoding="utf-8")

        self.assertIn("# Configuration-sensitive Failure Report", report)
        self.assertIn("localized to `retrieval`", report)


def _trace(
    *,
    top_k: int,
    relevant: bool,
    context_policy: str = "top_1",
) -> RagTrace:
    doc_id = "supporting-doc" if relevant else "distractor"
    return RagTrace.from_dict(
        {
            "metadata": {
                "run_id": f"config-q1-top-k-{top_k}",
                "timestamp": "2026-07-25T00:00:00Z",
                "dataset": "test-export",
                "config_hash": f"top-k-{top_k}",
                "retriever": "test-retriever",
                "generator": "test-generator",
                "evaluator": "qrels",
                "pipeline_stages": {"retrieval": True, "generation": True},
                "extra": {
                    "configuration": {
                        "retrieval_top_k": top_k,
                        "context_policy": context_policy,
                    }
                },
            },
            "query": {"query_id": "q1", "text": "fixed query"},
            "retrieved_documents": [
                {
                    "doc_id": doc_id,
                    "text": "evidence",
                    "rank": 1,
                    "is_relevant": relevant,
                }
            ],
            "selected_context": [
                {
                    "context_id": f"context-{doc_id}",
                    "doc_id": doc_id,
                    "text": "evidence",
                    "rank": 1,
                }
            ],
            "answer": {"text": "answer", "citations": [{"doc_id": doc_id}]},
            "metrics": [
                {
                    "name": "retrieval_hit",
                    "value": 1 if relevant else 0,
                    "passed": relevant,
                }
            ],
        }
    )


if __name__ == "__main__":
    unittest.main()
