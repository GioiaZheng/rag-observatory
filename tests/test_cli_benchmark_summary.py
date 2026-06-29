from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "examples" / "reproduce-small" / "benchmark_variants.json"


class CliBenchmarkSummaryTests(unittest.TestCase):
    def test_cli_renders_failure_pattern_benchmark_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "benchmark.md"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "rag_observatory.cli.main",
                    "benchmark-summary",
                    str(MANIFEST),
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

        self.assertIn("# Failure-Pattern Benchmark Summary", report)
        self.assertIn("baseline", report)
        self.assertIn("reranked", report)
        self.assertIn("Failure Distribution", report)


if __name__ == "__main__":
    unittest.main()
