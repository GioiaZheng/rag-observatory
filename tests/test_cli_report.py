import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "toy_runs"


class CliReportTests(unittest.TestCase):
    def test_cli_renders_report_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "report.md"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "rag_observatory.cli.main",
                    "report",
                    str(FIXTURE_DIR / "unsupported_answer.json"),
                    "--output",
                    str(output_path),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = output_path.read_text(encoding="utf-8")

        self.assertIn("# RAG Diagnostic Report", report)
        self.assertIn("unsupported_answer", report)


if __name__ == "__main__":
    unittest.main()
