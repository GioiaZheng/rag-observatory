import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_observatory.io.json import dump_trace, load_trace
from rag_observatory.trace.schema import RagTrace

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "toy_runs"


class JsonIoTests(unittest.TestCase):
    def test_dump_and_load_trace(self) -> None:
        data = json.loads((FIXTURE_DIR / "supported_answer.json").read_text(encoding="utf-8"))
        trace = RagTrace.from_dict(data)

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "trace.json"
            dump_trace(trace, output_path)
            loaded = load_trace(output_path)

        self.assertEqual(loaded.metadata.run_id, trace.metadata.run_id)
        self.assertEqual(loaded.answer.text, trace.answer.text)


if __name__ == "__main__":
    unittest.main()
