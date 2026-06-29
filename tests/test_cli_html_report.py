from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "stage_contract" / "full_observability_trace.json"


class CliHtmlReportTests(unittest.TestCase):
    def test_cli_renders_html_report_and_svg_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "report.html"
            screenshot_path = Path(tmp) / "report.svg"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "rag_observatory.cli.main",
                    "html-report",
                    str(FIXTURE),
                    "--output",
                    str(output_path),
                    "--screenshot",
                    str(screenshot_path),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            html = output_path.read_text(encoding="utf-8")
            screenshot = screenshot_path.read_text(encoding="utf-8")

        self.assertIn("<!doctype html>", html)
        self.assertIn("Failure Modes", html)
        self.assertIn("<svg", screenshot)
        self.assertIn("RAG Diagnostic Report", screenshot)


if __name__ == "__main__":
    unittest.main()
