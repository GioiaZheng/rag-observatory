from __future__ import annotations

import gzip
import json
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any, TextIO

from rag_observatory.trace.schema import RagTrace, TraceValidationError

TRACE_COLLECTION_FORMAT = "rag-observatory.trace-collection.v1"
TRACE_COLLECTION_MANIFEST = "manifest.json"


class TraceCollectionError(ValueError):
    """Raised when a trace collection cannot be discovered or streamed."""


def load_trace(path: str | Path) -> RagTrace:
    trace_path = Path(path)
    with _open_text_for_read(trace_path) as handle:
        return RagTrace.from_json(handle.read())


def dump_trace(trace: RagTrace, path: str | Path) -> None:
    trace_path = Path(path)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with _open_text_for_write(trace_path) as handle:
        handle.write(trace.to_json() + "\n")


def iter_trace_collection(path: str | Path) -> Iterator[RagTrace]:
    """Stream traces from a single JSON file, JSONL shard, or manifest directory."""

    trace_path = Path(path)
    if trace_path.is_dir():
        yield from _iter_manifest(trace_path / TRACE_COLLECTION_MANIFEST)
        return

    if trace_path.name == TRACE_COLLECTION_MANIFEST:
        yield from _iter_manifest(trace_path)
        return

    if _is_jsonl_path(trace_path):
        yield from _iter_jsonl(trace_path)
        return

    yield load_trace(trace_path)


def dump_trace_collection(traces: Iterable[RagTrace], path: str | Path) -> None:
    """Write a trace collection as JSON Lines without materializing all traces."""

    trace_path = Path(path)
    if not _is_jsonl_path(trace_path):
        raise TraceCollectionError(f"{trace_path} must use .jsonl or .jsonl.gz")

    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with _open_text_for_write(trace_path) as handle:
        for trace in traces:
            payload = json.dumps(trace.to_dict(), sort_keys=True, separators=(",", ":"))
            handle.write(payload + "\n")


def _iter_jsonl(path: Path) -> Iterator[RagTrace]:
    with _open_text_for_read(path) as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                yield RagTrace.from_json(line)
            except TraceValidationError as exc:
                raise TraceCollectionError(
                    f"{path}:{line_number}: invalid trace record: {exc}"
                ) from exc


def _iter_manifest(manifest_path: Path) -> Iterator[RagTrace]:
    manifest = _load_manifest(manifest_path)
    for shard_path in _manifest_shards(manifest, manifest_path):
        yield from _iter_jsonl(shard_path)


def _load_manifest(path: Path) -> Mapping[str, Any]:
    try:
        with _open_text_for_read(path) as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise TraceCollectionError(f"{path}: invalid trace collection manifest: {exc}") from exc
    except OSError as exc:
        raise TraceCollectionError(f"{path}: cannot read trace collection manifest: {exc}") from exc

    if not isinstance(data, Mapping):
        raise TraceCollectionError(f"{path}: trace collection manifest must be an object")
    if data.get("format") != TRACE_COLLECTION_FORMAT:
        raise TraceCollectionError(f"{path}: format must be {TRACE_COLLECTION_FORMAT!r}")
    if not isinstance(data.get("shards"), list):
        raise TraceCollectionError(f"{path}: shards must be a list")
    return data


def _manifest_shards(manifest: Mapping[str, Any], manifest_path: Path) -> Iterator[Path]:
    shards = manifest["shards"]
    if not isinstance(shards, list):
        raise TraceCollectionError(f"{manifest_path}: shards must be a list")

    for index, shard in enumerate(shards):
        shard_path = _manifest_shard_path(shard, index, manifest_path)
        if not _is_jsonl_path(shard_path):
            raise TraceCollectionError(
                f"{manifest_path}: shards[{index}].path must use .jsonl or .jsonl.gz"
            )
        yield manifest_path.parent / shard_path


def _manifest_shard_path(value: Any, index: int, manifest_path: Path) -> Path:
    raw_path: Any
    if isinstance(value, str):
        raw_path = value
    elif isinstance(value, Mapping):
        raw_path = value.get("path")
    else:
        raise TraceCollectionError(
            f"{manifest_path}: shards[{index}] must be a path string or object"
        )

    if not isinstance(raw_path, str) or not raw_path:
        raise TraceCollectionError(f"{manifest_path}: shards[{index}].path must be a string")

    shard_path = Path(raw_path)
    if shard_path.is_absolute() or ".." in shard_path.parts:
        raise TraceCollectionError(
            f"{manifest_path}: shards[{index}].path must stay under the manifest directory"
        )
    return shard_path


def _is_jsonl_path(path: Path) -> bool:
    suffixes = path.suffixes
    return path.suffix == ".jsonl" or suffixes[-2:] == [".jsonl", ".gz"]


def _open_text_for_read(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, mode="rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def _open_text_for_write(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, mode="wt", encoding="utf-8")
    return path.open("w", encoding="utf-8")
