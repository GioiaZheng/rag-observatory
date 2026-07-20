from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "module_boundaries.md"
README = ROOT / "README.md"


class ModuleBoundaryDocumentTests(unittest.TestCase):
    def test_document_defines_expected_module_map(self) -> None:
        doc = DOC.read_text(encoding="utf-8")

        for module in (
            "Trace schema",
            "Trace collector / adapters",
            "Evaluation engine",
            "Failure taxonomy",
            "Failure analyzer",
            "Report generator",
            "Visualization layer",
        ):
            self.assertIn(module, doc)

    def test_document_keeps_pipeline_boundary_explicit(self) -> None:
        doc = DOC.read_text(encoding="utf-8")

        self.assertIn("msmarco-genqa", doc)
        self.assertIn("experiments, pipeline variants, and generated traces", doc)
        self.assertIn("observation, diagnosis, interpretation, evaluation", doc)
        self.assertIn("composable research modules", doc)
        self.assertIn("all-in-one RAG system", doc)

    def test_document_defines_independent_testability(self) -> None:
        doc = DOC.read_text(encoding="utf-8")

        self.assertIn("synthetic public-safe fixture", doc)
        self.assertIn("deterministic expected output or report", doc)
        self.assertIn("does not require credentials or network access", doc)
        self.assertIn("clear abstention behavior", doc)

    def test_readme_links_module_boundaries(self) -> None:
        readme = README.read_text(encoding="utf-8")

        self.assertIn("docs/module_boundaries.md", readme)


if __name__ == "__main__":
    unittest.main()
