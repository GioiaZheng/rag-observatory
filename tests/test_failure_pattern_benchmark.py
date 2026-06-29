from __future__ import annotations

import unittest
from pathlib import Path

from rag_observatory.benchmark.failure_patterns import load_failure_pattern_benchmark
from rag_observatory.reports.benchmark import render_markdown_failure_pattern_benchmark

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "examples" / "reproduce-small" / "benchmark_variants.json"


class FailurePatternBenchmarkTests(unittest.TestCase):
    def test_loads_small_failure_pattern_benchmark(self) -> None:
        summary = load_failure_pattern_benchmark(MANIFEST)

        self.assertEqual(summary.benchmark_id, "small-failure-patterns-v1")
        self.assertEqual(summary.dataset, "rag-observatory-small-example")
        self.assertEqual([variant.name for variant in summary.variants], ["baseline", "reranked"])
        self.assertIn("context_pollution", summary.variants[0].failure_modes)
        self.assertIn("unsupported_answer", summary.variants[0].failure_modes)
        self.assertEqual(summary.variants[1].failure_modes, ("retrieval_noise",))
        self.assertIn(("context_pollution", 1), summary.failure_distribution)

    def test_renders_failure_pattern_summary_report(self) -> None:
        summary = load_failure_pattern_benchmark(MANIFEST)
        report = render_markdown_failure_pattern_benchmark(summary)

        self.assertIn("# Failure-Pattern Benchmark Summary", report)
        self.assertIn("not a leaderboard", report)
        self.assertIn("small-failure-patterns-v1", report)
        self.assertIn("## Failure Distribution", report)
        self.assertIn("## Evaluation Signals", report)
        self.assertIn("context_pollution", report)
        self.assertIn("faithfulness", report)


if __name__ == "__main__":
    unittest.main()
