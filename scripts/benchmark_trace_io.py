from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))

from rag_observatory.io.json import TRACE_COLLECTION_FORMAT, iter_trace_collection  # noqa: E402

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class BenchmarkResult:
    traces: int
    seconds: float
    traces_per_second: float
    peak_rss_mib: float | None
    collection_path: Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate synthetic trace collections and benchmark streaming parse speed."
    )
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=[1_000, 10_000, 50_000],
        help="Trace counts to generate and parse.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs") / "benchmarks" / "trace-io",
        help="Directory for generated collections and summary.md.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir: Path = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[BenchmarkResult] = []
    for size in args.sizes:
        if size <= 0:
            raise ValueError("--sizes values must be positive")
        collection_path = output_dir / f"synthetic-{size}"
        collection_path.mkdir(parents=True, exist_ok=True)
        shard_path = collection_path / "part-00000.jsonl"

        _write_synthetic_jsonl(shard_path, size)
        _write_manifest(collection_path, size, shard_path.name)

        started = time.perf_counter()
        parsed = sum(1 for _ in iter_trace_collection(collection_path))
        seconds = time.perf_counter() - started
        if parsed != size:
            raise RuntimeError(f"expected {size} traces but parsed {parsed}")

        results.append(
            BenchmarkResult(
                traces=size,
                seconds=seconds,
                traces_per_second=parsed / seconds if seconds else float("inf"),
                peak_rss_mib=_peak_rss_mib(),
                collection_path=collection_path,
            )
        )

    markdown = _render_markdown(results)
    summary_path = output_dir / "summary.md"
    summary_path.write_text(markdown, encoding="utf-8")
    print(markdown, end="")
    return 0


def _write_synthetic_jsonl(path: Path, size: int) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for index in range(size):
            handle.write(json.dumps(_trace_record(index), sort_keys=True, separators=(",", ":")))
            handle.write("\n")


def _write_manifest(collection_path: Path, size: int, shard_name: str) -> None:
    manifest = {
        "format": TRACE_COLLECTION_FORMAT,
        "version": 1,
        "trace_count": size,
        "shards": [{"path": shard_name, "records": size, "compression": "none"}],
        "document_store": None,
        "deduplication": {
            "strategy": "self-contained-traces",
            "stable_keys": ["doc_id"],
        },
    }
    (collection_path / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _trace_record(index: int) -> JsonObject:
    query_id = f"q-{index:06d}"
    doc_id = f"doc-{index % 1000:06d}"
    return {
        "metadata": {
            "run_id": f"synthetic-run-{index:06d}",
            "timestamp": "2026-06-28T00:00:00Z",
            "dataset": "synthetic_trace_io",
            "retriever": "synthetic-retriever",
            "generator": "synthetic-generator",
        },
        "query": {
            "query_id": query_id,
            "text": f"What evidence supports synthetic query {index}?",
        },
        "retrieved_documents": [
            {
                "doc_id": doc_id,
                "title": f"Synthetic document {index % 1000}",
                "text": f"Synthetic evidence passage for query {index}.",
                "rank": 1,
                "score": 1.0,
                "is_relevant": True,
            }
        ],
        "selected_context": [
            {
                "context_id": f"ctx-{index:06d}",
                "doc_id": doc_id,
                "text": f"Synthetic evidence passage for query {index}.",
                "rank": 1,
                "token_count": 6,
            }
        ],
        "answer": {
            "text": f"Synthetic answer for query {index}.",
            "citations": [{"doc_id": doc_id}],
        },
        "metrics": [
            {
                "name": "synthetic_pass",
                "value": 1.0,
                "passed": True,
                "threshold": 0.5,
            }
        ],
        "failures": [],
        "diagnostic_notes": [],
        "extra": {"benchmark_query_index": index},
    }


def _render_markdown(results: list[BenchmarkResult]) -> str:
    lines = [
        "# Trace I/O Benchmark",
        "",
        "| traces | seconds | traces/sec | peak RSS MiB | collection |",
        "| ---: | ---: | ---: | ---: | --- |",
    ]
    for result in results:
        peak_rss = "n/a" if result.peak_rss_mib is None else f"{result.peak_rss_mib:.1f}"
        lines.append(
            "| "
            f"{result.traces} | "
            f"{result.seconds:.3f} | "
            f"{result.traces_per_second:.1f} | "
            f"{peak_rss} | "
            f"{result.collection_path.as_posix()} |"
        )
    return "\n".join(lines) + "\n"


def _peak_rss_mib() -> float | None:
    if os.name == "nt":
        return _windows_peak_working_set_mib()

    try:
        import resource
    except ImportError:
        return None

    peak = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if sys.platform == "darwin":
        return peak / (1024 * 1024)
    return peak / 1024


def _windows_peak_working_set_mib() -> float | None:
    from ctypes import wintypes

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("page_fault_count", wintypes.DWORD),
            ("peak_working_set_size", ctypes.c_size_t),
            ("working_set_size", ctypes.c_size_t),
            ("quota_peak_paged_pool_usage", ctypes.c_size_t),
            ("quota_paged_pool_usage", ctypes.c_size_t),
            ("quota_peak_non_paged_pool_usage", ctypes.c_size_t),
            ("quota_non_paged_pool_usage", ctypes.c_size_t),
            ("pagefile_usage", ctypes.c_size_t),
            ("peak_pagefile_usage", ctypes.c_size_t),
        ]

    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ProcessMemoryCounters),
        wintypes.DWORD,
    ]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(ProcessMemoryCounters)
    process = kernel32.GetCurrentProcess()
    ok = psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb)
    if not ok:
        return None
    return counters.peak_working_set_size / (1024 * 1024)


if __name__ == "__main__":
    raise SystemExit(main())
