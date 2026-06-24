from __future__ import annotations

from rag_observatory.evaluation.failure_labels import (
    CaseEvaluation,
    FailureLabelEvaluation,
    ModeMetrics,
)


def render_markdown_failure_label_evaluation(
    evaluation: FailureLabelEvaluation,
    *,
    labeler_name: str = "heuristic",
) -> str:
    lines = ["# Failure Label Evaluation", ""]
    lines.extend(_summary_section(evaluation, labeler_name))
    lines.extend(_mode_metrics_section(evaluation.mode_metrics))
    lines.extend(_examples_section("False Positives", evaluation.cases, "false_positives"))
    lines.extend(_examples_section("False Negatives", evaluation.cases, "false_negatives"))
    lines.extend(_case_outcomes_section(evaluation.cases))
    return "\n".join(lines).rstrip() + "\n"


def _summary_section(evaluation: FailureLabelEvaluation, labeler_name: str) -> list[str]:
    return [
        "## Summary",
        "",
        f"- **Labeler:** {_clean(labeler_name)}",
        f"- **Cases:** {evaluation.total_cases}",
        (
            "- **Exact matches:** "
            f"{evaluation.exact_match_count} / {evaluation.total_cases} "
            f"({_format_rate(evaluation.exact_match_count, evaluation.total_cases)})"
        ),
        (
            "- **Abstentions:** "
            f"{evaluation.abstention_count} / {evaluation.total_cases} "
            f"({_format_optional_rate(evaluation.abstention_rate)})"
        ),
        "",
    ]


def _mode_metrics_section(metrics: tuple[ModeMetrics, ...]) -> list[str]:
    lines = [
        "## Per-Mode Metrics",
        "",
        "| Mode | Precision | Recall | Support | TP | FP | FN |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    if not metrics:
        lines.append("| none | n/a | n/a | 0 | 0 | 0 | 0 |")
        lines.append("")
        return lines

    for metric in metrics:
        lines.append(
            "| "
            f"`{_clean(metric.mode)}` | "
            f"{_format_optional_rate(metric.precision)} | "
            f"{_format_optional_rate(metric.recall)} | "
            f"{metric.support} | "
            f"{metric.true_positives} | "
            f"{metric.false_positives} | "
            f"{metric.false_negatives} |"
        )
    lines.append("")
    return lines


def _examples_section(
    title: str,
    cases: tuple[CaseEvaluation, ...],
    field_name: str,
) -> list[str]:
    lines = [f"## {title}", ""]
    rows: list[tuple[str, str, str]] = []
    for case in cases:
        modes = getattr(case, field_name)
        for mode in modes:
            rows.append((case.case_id, mode, case.trace_path.as_posix()))

    if not rows:
        lines.append("none")
        lines.append("")
        return lines

    lines.extend(["| Case | Mode | Trace |", "| --- | --- | --- |"])
    for case_id, mode, trace_path in rows:
        lines.append(f"| `{_clean(case_id)}` | `{_clean(mode)}` | `{_clean(trace_path)}` |")
    lines.append("")
    return lines


def _case_outcomes_section(cases: tuple[CaseEvaluation, ...]) -> list[str]:
    lines = [
        "## Case Outcomes",
        "",
        "| Case | Expected | Predicted | Status | Abstained |",
        "| --- | --- | --- | --- | --- |",
    ]
    if not cases:
        lines.append("| none | none | none | n/a | no |")
        lines.append("")
        return lines

    for case in cases:
        status = "exact" if case.exact_match else "mismatch"
        abstained = "yes" if case.abstained else "no"
        lines.append(
            "| "
            f"`{_clean(case.case_id)}` | "
            f"{_format_modes(case.expected_modes)} | "
            f"{_format_modes(case.predicted_modes)} | "
            f"{status} | "
            f"{abstained} |"
        )
    lines.append("")
    return lines


def _format_modes(modes: tuple[str, ...]) -> str:
    if not modes:
        return "none"
    return ", ".join(f"`{_clean(mode)}`" for mode in modes)


def _format_optional_rate(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def _format_rate(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{numerator / denominator:.2f}"


def _clean(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
