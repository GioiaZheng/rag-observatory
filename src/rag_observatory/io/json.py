from __future__ import annotations

from pathlib import Path

from rag_observatory.trace.schema import RagTrace


def load_trace(path: str | Path) -> RagTrace:
    trace_path = Path(path)
    return RagTrace.from_json(trace_path.read_text(encoding="utf-8"))


def dump_trace(trace: RagTrace, path: str | Path) -> None:
    trace_path = Path(path)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(trace.to_json() + "\n", encoding="utf-8")
