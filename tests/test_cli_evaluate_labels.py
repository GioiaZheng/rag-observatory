import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "reviewed_labels" / "expected_failure_labels.json"


class CliEvaluateLabelsTests(unittest.TestCase):
    def test_cli_renders_failure_label_evaluation_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "failure_label_evaluation.md"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "rag_observatory.cli.main",
                    "evaluate-labels",
                    str(FIXTURE_PATH),
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

        self.assertIn("# Failure Label Evaluation", report)
        self.assertIn("## Per-Mode Metrics", report)
        self.assertIn("Exact matches:** 7 / 7", report)
        self.assertIn("False Positives", report)
        self.assertIn("none", report)


if __name__ == "__main__":
    unittest.main()
