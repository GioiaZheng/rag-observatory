from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "examples" / "evals-as-code" / "synthetic_failure_eval"
RUNNER = EVAL_DIR / "run_eval.py"
CHECKED_REPORT = EVAL_DIR / "report.md"
DOC = ROOT / "docs" / "evals_as_code.md"
README = ROOT / "README.md"


class EvalsAsCodeWorkflowTests(unittest.TestCase):
    def test_synthetic_eval_runs_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            completed = subprocess.run(
                [sys.executable, str(RUNNER), "--output-dir", tmp_dir],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("Wrote eval results", completed.stdout)
            generated_report = (Path(tmp_dir) / "report.md").read_text(encoding="utf-8")
            checked_report = CHECKED_REPORT.read_text(encoding="utf-8")
            self.assertEqual(generated_report, checked_report)

            results = json.loads((Path(tmp_dir) / "results.json").read_text(encoding="utf-8"))
            self.assertEqual(results["task"]["task_id"], "synthetic_failure_eval_v1")
            self.assertEqual(results["summary"]["case_count"], 3)
            self.assertEqual(results["summary"]["quality_judgments"], 9)
            self.assertEqual(results["summary"]["quality_disagreements"], 0)
            self.assertEqual(results["summary"]["failure_label_exact_matches"], 3)

    def test_eval_asset_layout_is_documented(self) -> None:
        for filename in (
            "dataset.jsonl",
            "task.yaml",
            "solver.py",
            "scorer.py",
            "run_eval.py",
            "report.md",
        ):
            self.assertTrue((EVAL_DIR / filename).exists(), filename)

        doc = DOC.read_text(encoding="utf-8")
        readme = README.read_text(encoding="utf-8")
        self.assertIn("examples/evals-as-code/synthetic_failure_eval/", doc)
        self.assertIn("dataset.jsonl", doc)
        self.assertIn("docs/evals_as_code.md", readme)


if __name__ == "__main__":
    unittest.main()
