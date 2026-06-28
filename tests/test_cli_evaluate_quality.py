import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "quality_evaluation" / "expected_quality_scores.json"


class CliEvaluateQualityTests(unittest.TestCase):
    def test_cli_renders_quality_evaluation_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "quality_evaluation.md"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "rag_observatory.cli.main",
                    "evaluate-quality",
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

        self.assertIn("# Quality Evaluation", report)
        self.assertIn("rule_based_quality", report)
        self.assertIn("context_relevance", report)
        self.assertIn("Agreements:** 12 / 12", report)
        self.assertIn("## Disagreements", report)


if __name__ == "__main__":
    unittest.main()
