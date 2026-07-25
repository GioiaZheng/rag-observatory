from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from rag_observatory.taxonomy.failure_modes import classify_trace
from rag_observatory.trace.run import STAGES, stage_for_failure
from rag_observatory.trace.schema import RagTrace


class ConfigurationReportError(ValueError):
    """Raised when traces do not form a controlled configuration comparison."""


@dataclass(frozen=True)
class _Variant:
    value: Any
    traces: list[RagTrace]


def render_markdown_configuration_report(
    traces: Sequence[RagTrace],
    *,
    controlled_variable: str,
) -> str:
    variants, invariant_configuration = _validated_variants(
        traces, controlled_variable=controlled_variable
    )
    dataset_names = sorted({trace.metadata.dataset or "not recorded" for trace in traces})
    query_ids = sorted({trace.query.query_id for trace in traces})
    lines = [
        "# Configuration-sensitive Failure Report",
        "",
        f"- **Controlled variable:** `{_clean(controlled_variable)}`",
        f"- **Dataset:** {', '.join(f'`{_clean(name)}`' for name in dataset_names)}",
        f"- **Configurations:** {len(variants)}",
        f"- **Fixed queries per configuration:** {len(query_ids)}",
        f"- **Trace records:** {len(traces)}",
        "",
        "## Invariant Configuration",
        "",
    ]
    if invariant_configuration:
        for key, value in sorted(invariant_configuration.items()):
            lines.append(f"- **{_clean(key)}:** `{_clean(_display(value))}`")
    else:
        lines.append("No additional configuration fields were recorded.")

    lines.extend(
        [
            "",
            "## Observed Failure Signals",
            "",
            "| Configuration | Traces | Failure-labelled traces | Signals |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for variant in variants:
        label_counts = _label_counts(variant.traces)
        labelled_count = sum(bool(classify_trace(trace)) for trace in variant.traces)
        signals = ", ".join(
            f"`{_clean(label)}` {count}/{len(variant.traces)}"
            for label, count in sorted(label_counts.items())
        )
        lines.append(
            f"| `{_clean(controlled_variable)}={_clean(_display(variant.value))}` | "
            f"{len(variant.traces)} | {labelled_count} | {signals or 'none'} |"
        )

    lines.extend(
        [
            "",
            "## Evaluation Metric Summary",
            "",
            "| Configuration | Metric | Mean numeric value | Passed |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for variant in variants:
        for metric_name, mean_value, passed, recorded in _metric_summaries(variant.traces):
            lines.append(
                f"| `{_clean(controlled_variable)}={_clean(_display(variant.value))}` | "
                f"`{_clean(metric_name)}` | "
                f"{mean_value:.3f} | {passed}/{recorded} |"
            )

    lines.extend(
        [
            "",
            "## Stage Attribution",
            "",
            "| Stage | "
            + " | ".join(
                f"`{_clean(controlled_variable)}={_clean(_display(variant.value))}`"
                for variant in variants
            )
            + " | Rate spread |",
            "| --- | " + " | ".join("---:" for _ in variants) + " | ---: |",
        ]
    )
    stage_spreads: dict[str, float] = {}
    for stage in STAGES:
        counts = [_stage_failure_count(variant.traces, stage) for variant in variants]
        rates = [
            count / len(variant.traces) for count, variant in zip(counts, variants, strict=True)
        ]
        spread = max(rates) - min(rates)
        stage_spreads[stage] = spread
        lines.append(
            f"| `{stage}` | "
            + " | ".join(
                f"{count}/{len(variant.traces)} ({rate:.0%})"
                for count, rate, variant in zip(counts, rates, variants, strict=True)
            )
            + f" | {spread:.0%} |"
        )

    sensitive_stages = [
        stage
        for stage, spread in stage_spreads.items()
        if spread > 0 and spread == max(stage_spreads.values())
    ]
    lines.extend(["", "## Result", ""])
    if sensitive_stages:
        lines.append(
            "The largest observed failure-rate change is localized to "
            + ", ".join(f"`{stage}`" for stage in sensitive_stages)
            + "."
        )
    else:
        lines.append("No stage-level failure-rate change was observed across configurations.")

    lines.extend(
        [
            "",
            "## Per-query Changes",
            "",
            "| Query ID | "
            + " | ".join(
                f"`{_clean(controlled_variable)}={_clean(_display(variant.value))}`"
                for variant in variants
            )
            + " |",
            "| --- | " + " | ".join("---" for _ in variants) + " |",
        ]
    )
    traces_by_variant = [
        {trace.query.query_id: trace for trace in variant.traces} for variant in variants
    ]
    for query_id in query_ids:
        cells: list[str] = []
        for variant_traces in traces_by_variant:
            labels = [label.mode for label in classify_trace(variant_traces[query_id])]
            cells.append(", ".join(f"`{_clean(label)}`" for label in labels) or "none")
        lines.append(f"| `{_clean(query_id)}` | " + " | ".join(cells) + " |")

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "The report compares exported run outputs for the same query IDs and checks that "
            "all recorded configuration fields except the controlled variable are invariant. "
            "It reports observed stage-level associations; it does not establish causal effects "
            "outside these runs.",
            "",
        ]
    )
    return "\n".join(lines)


def _validated_variants(
    traces: Sequence[RagTrace],
    *,
    controlled_variable: str,
) -> tuple[list[_Variant], dict[str, Any]]:
    if not controlled_variable:
        raise ConfigurationReportError("controlled_variable must not be empty")
    if not traces:
        raise ConfigurationReportError("at least one trace is required")

    grouped: dict[str, list[RagTrace]] = defaultdict(list)
    values: dict[str, Any] = {}
    invariant: dict[str, Any] | None = None
    for trace in traces:
        configuration = _configuration(trace)
        if controlled_variable not in configuration:
            raise ConfigurationReportError(
                f"{trace.metadata.run_id}: configuration is missing {controlled_variable!r}"
            )
        candidate_invariant = {
            key: value for key, value in configuration.items() if key != controlled_variable
        }
        if invariant is None:
            invariant = candidate_invariant
        elif candidate_invariant != invariant:
            raise ConfigurationReportError(
                "configuration fields other than the controlled variable are not invariant"
            )
        value = configuration[controlled_variable]
        key = json.dumps(value, sort_keys=True)
        values[key] = value
        grouped[key].append(trace)

    if len(grouped) < 2:
        raise ConfigurationReportError("at least two controlled-variable values are required")

    query_sets = [{trace.query.query_id for trace in group} for group in grouped.values()]
    if any(query_set != query_sets[0] for query_set in query_sets[1:]):
        raise ConfigurationReportError("each configuration must contain the same query IDs")
    for key, group in grouped.items():
        if len({trace.query.query_id for trace in group}) != len(group):
            raise ConfigurationReportError(
                f"configuration value {_display(values[key])!r} repeats a query ID"
            )

    ordered_keys = sorted(grouped, key=lambda key: _display(values[key]))
    variants = [_Variant(value=values[key], traces=grouped[key]) for key in ordered_keys]
    return variants, invariant or {}


def _configuration(trace: RagTrace) -> dict[str, Any]:
    configuration = trace.metadata.extra.get("configuration")
    if not isinstance(configuration, Mapping):
        raise ConfigurationReportError(
            f"{trace.metadata.run_id}: metadata.extra.configuration must be an object"
        )
    return dict(configuration)


def _label_counts(traces: Sequence[RagTrace]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for trace in traces:
        for label in classify_trace(trace):
            counts[label.mode] += 1
    return counts


def _stage_failure_count(traces: Sequence[RagTrace], stage: str) -> int:
    return sum(
        any(stage_for_failure(label) == stage for label in classify_trace(trace))
        for trace in traces
    )


def _metric_summaries(
    traces: Sequence[RagTrace],
) -> list[tuple[str, float, int, int]]:
    values: dict[str, list[float]] = defaultdict(list)
    pass_counts: dict[str, int] = defaultdict(int)
    recorded_counts: dict[str, int] = defaultdict(int)
    for trace in traces:
        for metric in trace.metrics:
            if isinstance(metric.value, (int, float)) and not isinstance(metric.value, bool):
                values[metric.name].append(float(metric.value))
            if metric.passed is not None:
                recorded_counts[metric.name] += 1
                pass_counts[metric.name] += metric.passed
    return [
        (
            name,
            sum(metric_values) / len(metric_values),
            pass_counts[name],
            recorded_counts[name],
        )
        for name, metric_values in sorted(values.items())
    ]


def _display(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True)


def _clean(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
