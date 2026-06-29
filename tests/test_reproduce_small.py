from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReproduceSmallTests(unittest.TestCase):
    def test_small_reproduction_writes_expected_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "reproduce-small"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/reproduce_small.py",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            trace_path = output_dir / "traces" / "msmarco_genqa_trace.json"
            markdown_path = output_dir / "reports" / "msmarco_genqa_diagnostic.md"
            html_path = output_dir / "reports" / "msmarco_genqa_diagnostic.html"
            screenshot_path = output_dir / "reports" / "msmarco_genqa_diagnostic.svg"
            comparison_path = output_dir / "reports" / "benchmark_comparison.md"
            manifest_path = output_dir / "manifest.json"

            for path in (
                trace_path,
                markdown_path,
                html_path,
                screenshot_path,
                comparison_path,
                manifest_path,
            ):
                self.assertTrue(path.is_file(), f"missing artifact: {path}")

            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            self.assertEqual("small-msmarco-genqa-run-001", trace["metadata"]["run_id"])
            self.assertTrue(trace["metadata"]["pipeline_stages"]["reranking"])
            self.assertIsNotNone(trace["prompt"])

            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertIn("# RAG Diagnostic Report", markdown)
            self.assertIn("## Reranked Documents", markdown)
            self.assertIn("unsupported_answer", markdown)
            self.assertIn("reranking_error", markdown)

            html = html_path.read_text(encoding="utf-8")
            self.assertIn("<!doctype html>", html)
            self.assertIn("RAG Diagnostic Report", html)
            self.assertIn("Failure Modes", html)

            screenshot = screenshot_path.read_text(encoding="utf-8")
            self.assertIn("<svg", screenshot)
            self.assertIn("RAG Diagnostic Report", screenshot)

            comparison = comparison_path.read_text(encoding="utf-8")
            self.assertIn("# RAG Trace Comparison", comparison)
            self.assertIn("small-comparison-baseline", comparison)
            self.assertIn("small-comparison-reranked", comparison)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual("rag-observatory.reproduce-small.v1", manifest["format"])
            self.assertIn("html_report", manifest["artifacts"])
            self.assertIn("screenshot_svg", manifest["artifacts"])
            self.assertIn("reranking_error", manifest["failure_modes"])


if __name__ == "__main__":
    unittest.main()
