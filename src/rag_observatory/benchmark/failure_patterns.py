from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rag_observatory.io.json import load_trace
from rag_observatory.taxonomy.failure_modes import classify_trace

BENCHMARK_MANIFEST_FORMAT = "rag-observatory.failure-pattern-benchmark.v1"


class BenchmarkManifestError(ValueError):
    """Raised when a small benchmark manifest cannot be loaded."""


@dataclass(frozen=True)
class BenchmarkVariantSummary:
    name: str
    trace_path: Path
    run_id: str
    query_id: str
    description: str | None
    retriever: str | None
    reranker: str | None
    generator: str | None
    failure_modes: tuple[str, ...]
    passed_metrics: tuple[str, ...]
    failed_metrics: tuple[str, ...]


@dataclass(frozen=True)
class BenchmarkFailurePatternSummary:
    benchmark_id: str
    dataset: str
    description: str
    variants: tuple[BenchmarkVariantSummary, ...]
    failure_distribution: tuple[tuple[str, int], ...]


def load_failure_pattern_benchmark(path: str | Path) -> BenchmarkFailurePatternSummary:
    manifest_path = Path(path)
    data = _load_json_object(manifest_path)

    if data.get("format") != BENCHMARK_MANIFEST_FORMAT:
        raise BenchmarkManifestError(f"manifest.format must be {BENCHMARK_MANIFEST_FORMAT!r}")

    benchmark_id = _required_str(data, "benchmark_id", "manifest")
    dataset = _required_str(data, "dataset", "manifest")
    description = _required_str(data, "description", "manifest")
    variants = _load_variants(data.get("variants"), manifest_path)
    distribution = Counter(mode for variant in variants for mode in variant.failure_modes)

    return BenchmarkFailurePatternSummary(
        benchmark_id=benchmark_id,
        dataset=dataset,
        description=description,
        variants=tuple(variants),
        failure_distribution=tuple(sorted(distribution.items())),
    )


def _load_variants(value: Any, manifest_path: Path) -> list[BenchmarkVariantSummary]:
    if not isinstance(value, list) or not value:
        raise BenchmarkManifestError("manifest.variants must be a non-empty list")

    variants: list[BenchmarkVariantSummary] = []
    seen_names: set[str] = set()
    for index, item in enumerate(value):
        label = f"manifest.variants[{index}]"
        data = _expect_mapping(item, label)
        name = _required_str(data, "name", label)
        if name in seen_names:
            raise BenchmarkManifestError(f"{label}.name must be unique")
        seen_names.add(name)

        trace_path = _trace_path(data.get("trace_path"), label, manifest_path)
        trace = load_trace(trace_path)
        labels = classify_trace(trace)
        passed_metrics = tuple(metric.name for metric in trace.metrics if metric.passed is True)
        failed_metrics = tuple(metric.name for metric in trace.metrics if metric.passed is False)
        variants.append(
            BenchmarkVariantSummary(
                name=name,
                trace_path=trace_path,
                run_id=trace.metadata.run_id,
                query_id=trace.query.query_id,
                description=_optional_str(data, "description", label),
                retriever=trace.metadata.retriever,
                reranker=trace.metadata.reranker,
                generator=trace.metadata.generator,
                failure_modes=tuple(label.mode for label in labels),
                passed_metrics=passed_metrics,
                failed_metrics=failed_metrics,
            )
        )
    return variants


def _load_json_object(path: Path) -> Mapping[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkManifestError(f"{path}: invalid JSON manifest: {exc}") from exc

    return _expect_mapping(data, "manifest")


def _trace_path(value: Any, label: str, manifest_path: Path) -> Path:
    if not isinstance(value, str) or not value:
        raise BenchmarkManifestError(f"{label}.trace_path must be a non-empty string")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise BenchmarkManifestError(f"{label}.trace_path must stay under the manifest directory")
    return manifest_path.parent / path


def _expect_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BenchmarkManifestError(f"{label} must be an object")
    return value


def _required_str(data: Mapping[str, Any], key: str, label: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BenchmarkManifestError(f"{label}.{key} must be a non-empty string")
    return value


def _optional_str(data: Mapping[str, Any], key: str, label: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise BenchmarkManifestError(f"{label}.{key} must be a string")
    return value
