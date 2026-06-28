from __future__ import annotations

from collections.abc import Iterable

from rag_observatory.evaluation.quality import (
    QualityCaseComparison,
    QualityEvaluationComparison,
)


def render_markdown_quality_evaluation(evaluation: QualityEvaluationComparison) -> str:
    lines = ["# Quality Evaluation", ""]
    lines.extend(_summary_section(evaluation))
    lines.extend(_dimension_section(evaluation.rows))
    lines.extend(_disagreement_section(evaluation.rows))
    lines.extend(_case_outcomes_section(evaluation.rows))
    return "\n".join(lines).rstrip() + "\n"


def _summary_section(evaluation: QualityEvaluationComparison) -> list[str]:
    return [
        "## Summary",
        "",
        f"- **Evaluator:** {_clean(evaluation.evaluator_name)} "
        f"({_clean(evaluation.evaluator_version)}, {_clean(evaluation.method)})",
        f"- **Cases:** {evaluation.total_cases}",
        f"- **Judgments:** {evaluation.total_rows}",
        (
            "- **Agreements:** "
            f"{evaluation.agreement_count} / {evaluation.total_rows} "
            f"({_format_rate(evaluation.agreement_count, evaluation.total_rows)})"
        ),
        (
            "- **Disagreements:** "
            f"{evaluation.disagreement_count} / {evaluation.total_rows} "
            f"({_format_rate(evaluation.disagreement_count, evaluation.total_rows)})"
        ),
        (
            "- **Abstentions:** "
            f"{evaluation.abstention_count} / {evaluation.total_rows} "
            f"({_format_rate(evaluation.abstention_count, evaluation.total_rows)})"
        ),
        "",
    ]


def _dimension_section(rows: tuple[QualityCaseComparison, ...]) -> list[str]:
    lines = [
        "## Per-Dimension Outcomes",
        "",
        "| Dimension | Judgments | Agreements | Disagreements | Abstentions |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    dimensions = sorted({row.dimension for row in rows})
    if not dimensions:
        lines.append("| none | 0 | 0 | 0 | 0 |")
        lines.append("")
        return lines

    for dimension in dimensions:
        dimension_rows = [row for row in rows if row.dimension == dimension]
        agreements = sum(1 for row in dimension_rows if row.exact_match)
        abstentions = sum(1 for row in dimension_rows if row.observed_abstained)
        lines.append(
            "| "
            f"`{_clean(dimension)}` | "
            f"{len(dimension_rows)} | "
            f"{agreements} | "
            f"{len(dimension_rows) - agreements} | "
            f"{abstentions} |"
        )
    lines.append("")
    return lines


def _disagreement_section(rows: tuple[QualityCaseComparison, ...]) -> list[str]:
    disagreements = [row for row in rows if not row.exact_match]
    lines = [
        "## Disagreements",
        "",
        "| Case | Dimension | Expected | Observed | Failure Labels | Evidence | Rationale |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    if not disagreements:
        lines.append("| none | none | none | none | none | none | none |")
        lines.append("")
        return lines

    for row in disagreements:
        lines.append(_row_to_table(row))
    lines.append("")
    return lines


def _case_outcomes_section(rows: tuple[QualityCaseComparison, ...]) -> list[str]:
    lines = [
        "## Case Outcomes",
        "",
        "| Case | Dimension | Expected | Observed | Score | Abstention Reason | Failure Labels |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    if not rows:
        lines.append("| none | none | none | none | n/a | none | none |")
        lines.append("")
        return lines

    for row in rows:
        score = "n/a" if row.score is None else f"{row.score:.2f}"
        lines.append(
            "| "
            f"`{_clean(row.case_id)}` | "
            f"`{_clean(row.dimension)}` | "
            f"{_format_state(row.expected_passed, row.expected_abstained)} | "
            f"{_format_state(row.observed_passed, row.observed_abstained)} | "
            f"{score} | "
            f"{_format_optional_text(row.abstention_reason)} | "
            f"{_format_modes(row.failure_modes)} |"
        )
    lines.append("")
    return lines


def _row_to_table(row: QualityCaseComparison) -> str:
    return (
        "| "
        f"`{_clean(row.case_id)}` | "
        f"`{_clean(row.dimension)}` | "
        f"{_format_state(row.expected_passed, row.expected_abstained)} | "
        f"{_format_state(row.observed_passed, row.observed_abstained)} | "
        f"{_format_modes(row.failure_modes)} | "
        f"{_format_optional_text(row.evidence)} | "
        f"{_format_optional_text(row.rationale)} |"
    )


def _format_state(passed: bool | None, abstained: bool) -> str:
    if abstained:
        return "abstained"
    if passed is True:
        return "pass"
    if passed is False:
        return "fail"
    return "n/a"


def _format_modes(modes: Iterable[str]) -> str:
    values = tuple(modes)
    if not values:
        return "none"
    return ", ".join(f"`{_clean(mode)}`" for mode in values)


def _format_optional_text(value: str | None) -> str:
    if value is None or not value:
        return "none"
    return _clean(value)


def _format_rate(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{numerator / denominator:.2f}"


def _clean(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
