import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "openinference" / "otlp_rag_trace.json"


class CliIngestOtlpOpenInferenceTests(unittest.TestCase):
    def test_cli_ingests_otlp_export_and_report_reads_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            trace_path = Path(tmp) / "trace.json"
            report_path = Path(tmp) / "report.md"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")

            ingest = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "rag_observatory.cli.main",
                    "ingest-otlp-openinference",
                    str(FIXTURE),
                    "--output",
                    str(trace_path),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(ingest.returncode, 0, ingest.stderr)

            report = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "rag_observatory.cli.main",
                    "report",
                    str(trace_path),
                    "--output",
                    str(report_path),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(report.returncode, 0, report.stderr)
            rendered = report_path.read_text(encoding="utf-8")

        self.assertIn("# RAG Diagnostic Report", rendered)
        self.assertIn("0123456789abcdef0123456789abcdef", rendered)
        self.assertIn("Vitamin C prevents scurvy", rendered)


if __name__ == "__main__":
    unittest.main()

