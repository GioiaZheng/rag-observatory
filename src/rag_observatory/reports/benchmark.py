from __future__ import annotations

from rag_observatory.benchmark.failure_patterns import BenchmarkFailurePatternSummary


def render_markdown_failure_pattern_benchmark(
    summary: BenchmarkFailurePatternSummary,
) -> str:
    lines = [
        "# Failure-Pattern Benchmark Summary",
        "",
        "This report compares small pipeline variants by observable failure patterns. "
        "It is not a leaderboard and should not be read as a broad performance claim.",
        "",
        "## Benchmark",
        "",
        f"- **Benchmark ID:** {_clean(summary.benchmark_id)}",
        f"- **Dataset:** {_clean(summary.dataset)}",
        f"- **Description:** {_clean(summary.description)}",
        "",
    ]
    lines.extend(_variant_section(summary))
    lines.extend(_distribution_section(summary))
    lines.extend(_metric_section(summary))
    lines.extend(_interpretation_section(summary))
    return "\n".join(lines).rstrip() + "\n"


def _variant_section(summary: BenchmarkFailurePatternSummary) -> list[str]:
    lines = [
        "## Variants",
        "",
        "| Variant | Run ID | Retriever | Reranker | Failed Metrics | Failure Modes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for variant in summary.variants:
        lines.append(
            "| "
            f"`{_clean(variant.name)}` | "
            f"`{_clean(variant.run_id)}` | "
            f"{_clean(variant.retriever or 'not recorded')} | "
            f"{_clean(variant.reranker or 'not used')} | "
            f"{_format_inline_list(variant.failed_metrics)} | "
            f"{_format_inline_list(variant.failure_modes)} |"
        )
    lines.append("")
    return lines


def _distribution_section(summary: BenchmarkFailurePatternSummary) -> list[str]:
    lines = [
        "## Failure Distribution",
        "",
        "| Failure Mode | Variants |",
        "| --- | ---: |",
    ]
    if not summary.failure_distribution:
        lines.append("| none | 0 |")
    else:
        for mode, count in summary.failure_distribution:
            lines.append(f"| `{_clean(mode)}` | {count} |")
    lines.append("")
    return lines


def _metric_section(summary: BenchmarkFailurePatternSummary) -> list[str]:
    lines = [
        "## Evaluation Signals",
        "",
        "| Variant | Passed Metrics | Failed Metrics |",
        "| --- | --- | --- |",
    ]
    for variant in summary.variants:
        lines.append(
            "| "
            f"`{_clean(variant.name)}` | "
            f"{_format_inline_list(variant.passed_metrics)} | "
            f"{_format_inline_list(variant.failed_metrics)} |"
        )
    lines.append("")
    return lines


def _interpretation_section(summary: BenchmarkFailurePatternSummary) -> list[str]:
    lines = ["## Interpretation", ""]
    if not summary.variants:
        lines.append("No variants were recorded.")
        lines.append("")
        return lines

    first = summary.variants[0]
    last = summary.variants[-1]
    removed = set(first.failure_modes) - set(last.failure_modes)
    added = set(last.failure_modes) - set(first.failure_modes)
    if removed:
        lines.append(
            "- Later variants remove these initial failure modes: "
            + _format_inline_list(tuple(sorted(removed)))
            + "."
        )
    if added:
        lines.append(
            "- Later variants introduce these failure modes: "
            + _format_inline_list(tuple(sorted(added)))
            + "."
        )
    if not removed and not added:
        lines.append("- The first and last variants expose the same failure-mode set.")
    lines.append("- Inspect per-trace reports before drawing broader conclusions.")
    lines.append("")
    return lines


def _format_inline_list(values: tuple[str, ...]) -> str:
    if not values:
        return "none"
    return ", ".join(f"`{_clean(value)}`" for value in values)


def _clean(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
