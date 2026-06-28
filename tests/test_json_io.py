import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_observatory.io.json import (
    TRACE_COLLECTION_FORMAT,
    TRACE_COLLECTION_MANIFEST,
    TraceCollectionError,
    dump_trace,
    dump_trace_collection,
    iter_trace_collection,
    load_trace,
)
from rag_observatory.trace.schema import RagTrace

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "toy_runs"


def _load_supported_trace() -> RagTrace:
    data = json.loads((FIXTURE_DIR / "supported_answer.json").read_text(encoding="utf-8"))
    return RagTrace.from_dict(data)


def _trace_json_line(trace: RagTrace) -> str:
    return json.dumps(trace.to_dict(), sort_keys=True)


class JsonIoTests(unittest.TestCase):
    def test_dump_and_load_trace(self) -> None:
        trace = _load_supported_trace()

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "trace.json"
            dump_trace(trace, output_path)
            loaded = load_trace(output_path)

        self.assertEqual(loaded.metadata.run_id, trace.metadata.run_id)
        self.assertEqual(loaded.answer.text, trace.answer.text)

    def test_dump_and_iter_trace_collection_jsonl(self) -> None:
        trace = _load_supported_trace()

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "traces.jsonl"
            dump_trace_collection([trace, trace], output_path)
            loaded = list(iter_trace_collection(output_path))

        self.assertEqual([item.metadata.run_id for item in loaded], [trace.metadata.run_id] * 2)

    def test_iter_trace_collection_reads_single_json(self) -> None:
        trace = _load_supported_trace()

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "trace.json"
            dump_trace(trace, output_path)
            loaded = list(iter_trace_collection(output_path))

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].query.query_id, trace.query.query_id)

    def test_iter_trace_collection_skips_blank_jsonl_lines(self) -> None:
        trace = _load_supported_trace()

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "traces.jsonl"
            output_path.write_text(_trace_json_line(trace) + "\n\n", encoding="utf-8")
            loaded = list(iter_trace_collection(output_path))

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].metadata.run_id, trace.metadata.run_id)

    def test_iter_trace_collection_reads_gzip_jsonl(self) -> None:
        trace = _load_supported_trace()

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "traces.jsonl.gz"
            with gzip.open(output_path, mode="wt", encoding="utf-8") as handle:
                handle.write(_trace_json_line(trace) + "\n")
            loaded = list(iter_trace_collection(output_path))

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].answer.text, trace.answer.text)

    def test_iter_trace_collection_reports_bad_jsonl_line(self) -> None:
        trace = _load_supported_trace()

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "bad.jsonl"
            output_path.write_text(
                _trace_json_line(trace) + "\n" + '{"metadata":' + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(TraceCollectionError, r":2: invalid trace record"):
                list(iter_trace_collection(output_path))

    def test_iter_trace_collection_reads_manifest_directory(self) -> None:
        trace = _load_supported_trace()

        with tempfile.TemporaryDirectory() as tmp:
            collection_dir = Path(tmp)
            shard_path = collection_dir / "part-00000.jsonl"
            dump_trace_collection([trace], shard_path)
            manifest = {
                "format": TRACE_COLLECTION_FORMAT,
                "version": 1,
                "trace_count": 1,
                "shards": [{"path": shard_path.name, "records": 1, "compression": "none"}],
            }
            (collection_dir / TRACE_COLLECTION_MANIFEST).write_text(
                json.dumps(manifest), encoding="utf-8"
            )

            loaded_from_directory = list(iter_trace_collection(collection_dir))
            loaded_from_manifest = list(
                iter_trace_collection(collection_dir / TRACE_COLLECTION_MANIFEST)
            )

        self.assertEqual(len(loaded_from_directory), 1)
        self.assertEqual(loaded_from_directory, loaded_from_manifest)

    def test_iter_trace_collection_rejects_manifest_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            collection_dir = Path(tmp)
            manifest = {
                "format": TRACE_COLLECTION_FORMAT,
                "version": 1,
                "shards": [{"path": "../outside.jsonl"}],
            }
            (collection_dir / TRACE_COLLECTION_MANIFEST).write_text(
                json.dumps(manifest), encoding="utf-8"
            )

            with self.assertRaisesRegex(TraceCollectionError, "manifest directory"):
                list(iter_trace_collection(collection_dir))

    def test_dump_trace_collection_requires_jsonl_path(self) -> None:
        trace = _load_supported_trace()

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(TraceCollectionError, "must use .jsonl"):
                dump_trace_collection([trace], Path(tmp) / "traces.json")


if __name__ == "__main__":
    unittest.main()
