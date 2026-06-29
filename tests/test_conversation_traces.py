import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_observatory.io.json import load_trace
from rag_observatory.reports.conversation import render_markdown_conversation_report
from rag_observatory.trace.schema import RagTrace, TraceValidationError

ROOT = Path(__file__).resolve().parents[1]
TOY_RUNS = ROOT / "tests" / "fixtures" / "toy_runs"
CONVERSATION_FIXTURES = ROOT / "tests" / "fixtures" / "conversations"


class ConversationTraceTests(unittest.TestCase):
    def test_single_turn_trace_remains_backward_compatible(self) -> None:
        trace = load_trace(TOY_RUNS / "supported_answer.json")

        self.assertIsNone(trace.conversation)
        self.assertEqual(trace.metadata.run_id, "toy-supported-answer")

    def test_multi_turn_fixtures_validate(self) -> None:
        traces = _load_conversation_traces()

        self.assertEqual(len(traces), 3)
        self.assertTrue(all(trace.conversation is not None for trace in traces))
        self.assertEqual(traces[1].conversation.turn_id, "turn-002")
        self.assertEqual(traces[1].conversation.prior_turn_references, ["turn-001"])
        self.assertEqual(traces[2].conversation.answerability, "unanswerable")

    def test_invalid_answerability_fails(self) -> None:
        data = load_trace(CONVERSATION_FIXTURES / "turn_001_supported.json").to_dict()
        data["conversation"]["answerability"] = "maybe"

        with self.assertRaisesRegex(TraceValidationError, "conversation.answerability"):
            RagTrace.from_dict(data)

    def test_conversation_report_distinguishes_rewrite_and_insufficient_evidence(self) -> None:
        report = render_markdown_conversation_report(_load_conversation_traces())

        self.assertIn("# Conversational RAG Diagnostic Report", report)
        self.assertIn("conv-penicillin", report)
        self.assertIn("query rewriting", report)
        self.assertIn("insufficient evidence for unanswerable turn", report)
        self.assertIn("retrieval_miss", report)

    def test_cli_renders_conversation_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "conversation.md"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "rag_observatory.cli.main",
                    "conversation-report",
                    str(CONVERSATION_FIXTURES / "turn_001_supported.json"),
                    str(CONVERSATION_FIXTURES / "turn_002_bad_rewrite.json"),
                    str(CONVERSATION_FIXTURES / "turn_003_unanswerable.json"),
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

        self.assertIn("Turn Overview", report)
        self.assertIn("query rewriting", report)


def _load_conversation_traces() -> list[RagTrace]:
    return [
        load_trace(CONVERSATION_FIXTURES / "turn_001_supported.json"),
        load_trace(CONVERSATION_FIXTURES / "turn_002_bad_rewrite.json"),
        load_trace(CONVERSATION_FIXTURES / "turn_003_unanswerable.json"),
    ]


if __name__ == "__main__":
    unittest.main()
