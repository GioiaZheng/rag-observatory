from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scorer import score_case, summarize
from solver import solve_case

JsonObject = dict[str, Any]
EVAL_DIR = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the synthetic evals-as-code fixture for RAG failure diagnosis."
    )
    parser.add_argument("--task", default=str(EVAL_DIR / "task.yaml"), help="Task YAML path.")
    parser.add_argument(
        "--output-dir",
        help="Directory for generated results.json and report.md. Defaults to task.yaml.",
    )
    args = parser.parse_args()

    task_path = Path(args.task).resolve()
    task = load_task(task_path)
    dataset_path = (task_path.parent / _required_str(task, "dataset_path")).resolve()
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else (task_path.parent / _required_str(task, "default_output_dir")).resolve()
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    dimensions = _string_list(task.get("dimensions"), "dimensions")
    threshold = float(task["threshold"])
    cases = load_dataset(dataset_path)
    solved_cases = [
        solve_case(
            case,
            dataset_dir=dataset_path.parent,
            dimensions=dimensions,
            threshold=threshold,
        )
        for case in cases
    ]
    scored_cases = [
        score_case(case, solved) for case, solved in zip(cases, solved_cases, strict=True)
    ]
    result = {
        "task": {
            "task_id": _required_str(task, "task_id"),
            "description": _required_str(task, "description"),
            "dataset_path": dataset_path.relative_to(EVAL_DIR).as_posix(),
            "threshold": threshold,
            "dimensions": dimensions,
        },
        "summary": summarize(scored_cases),
        "cases": [
            {"case": solved, "evaluation": scored}
            for solved, scored in zip(solved_cases, scored_cases, strict=True)
        ],
    }

    results_path = output_dir / _required_str(task, "results_filename")
    report_path = output_dir / _required_str(task, "report_filename")
    results_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(render_report(result), encoding="utf-8")
    print(f"Wrote eval results to {results_path}")
    print(f"Wrote eval report to {report_path}")
    return 0


def load_task(path: Path) -> JsonObject:
    data: JsonObject = {}
    current_list_key: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith("  - "):
            if current_list_key is None:
                raise ValueError(f"list item without key in {path}: {line}")
            data.setdefault(current_list_key, []).append(stripped.removeprefix("- ").strip())
            continue
        if ":" not in line:
            raise ValueError(f"unsupported task line in {path}: {line}")
        key, value = line.split(":", 1)
        current_list_key = None
        value = value.strip()
        if value:
            data[key.strip()] = _parse_scalar(value)
        else:
            current_list_key = key.strip()
            data[current_list_key] = []
    return data


def load_dataset(path: Path) -> list[JsonObject]:
    cases: list[JsonObject] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw_case = json.loads(line)
        if not isinstance(raw_case, dict):
            raise ValueError(f"{path}:{line_number} must contain a JSON object")
        cases.append(raw_case)
    return cases


def render_report(result: Mapping[str, Any]) -> str:
    task = _object(result["task"], "task")
    summary = _object(result["summary"], "summary")
    cases = _object_list(result["cases"], "cases")
    lines = [
        "# Synthetic Failure Eval",
        "",
        "## Task",
        "",
        f"- **Task ID:** `{_clean(str(task['task_id']))}`",
        f"- **Dataset:** `{_clean(str(task['dataset_path']))}`",
        f"- **Threshold:** {task['threshold']}",
        f"- **Dimensions:** {', '.join(f'`{_clean(item)}`' for item in task['dimensions'])}",
        "",
        "## Summary",
        "",
        f"- **Cases:** {summary['case_count']}",
        f"- **Quality judgments:** {summary['quality_judgments']}",
        f"- **Quality agreements:** {summary['quality_agreements']}",
        f"- **Quality disagreements:** {summary['quality_disagreements']}",
        f"- **Quality abstentions:** {summary['quality_abstentions']}",
        f"- **Failure-label exact matches:** {summary['failure_label_exact_matches']}",
        "",
        "## Inputs and Outputs",
        "",
        "| Case | Trace | Query | Answer | Failure Labels |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in cases:
        case = _object(item["case"], "case")
        input_data = _object(case["input"], "input")
        output = _object(case["output"], "output")
        lines.append(
            "| "
            f"`{_clean(str(case['case_id']))}` | "
            f"`{_clean(str(input_data['trace_path']))}` | "
            f"{_clean(str(input_data['question']))} | "
            f"{_clean(str(output['answer']))} | "
            f"{_format_labels(case['failure_labels'])} |"
        )
    lines.extend(
        [
            "",
            "## Quality Scores",
            "",
            "| Case | Dimension | Expected | Observed | Score | Threshold | Evidence |",
            "| --- | --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    for item in cases:
        case = _object(item["case"], "case")
        evaluation = _object(item["evaluation"], "evaluation")
        for row in _object_list(evaluation["quality_evaluation"], "quality_evaluation"):
            lines.append(
                "| "
                f"`{_clean(str(case['case_id']))}` | "
                f"`{_clean(str(row['dimension']))}` | "
                f"{_format_state(row['expected_passed'], row['expected_abstained'])} | "
                f"{_format_state(row['observed_passed'], row['observed_abstained'])} | "
                f"{_format_number(row['score'])} | "
                f"{_format_number(row['threshold'])} | "
                f"{_format_optional(row['evidence'] or row['abstention_reason'])} |"
            )
    lines.extend(
        [
            "",
            "## Failure Label Checks",
            "",
            "| Case | Expected | Observed | False Positives | False Negatives | Exact Match |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in cases:
        case = _object(item["case"], "case")
        evaluation = _object(item["evaluation"], "evaluation")
        labels = _object(evaluation["failure_label_evaluation"], "failure_label_evaluation")
        lines.append(
            "| "
            f"`{_clean(str(case['case_id']))}` | "
            f"{_format_values(labels['expected'])} | "
            f"{_format_values(labels['observed'])} | "
            f"{_format_values(labels['false_positives'])} | "
            f"{_format_values(labels['false_negatives'])} | "
            f"{labels['exact_match']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This checked fixture treats evaluation as versioned project code: "
            "the dataset, task configuration, solver, scorer, runner, and report "
            "are all reviewable. It is intentionally synthetic and should not be "
            "reported as dataset-scale evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def _parse_scalar(value: str) -> str | float:
    try:
        return float(value)
    except ValueError:
        return value


def _required_str(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{label} must be a list of strings")
    return value


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _object_list(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise ValueError(f"{label} must be a list of objects")
    return value


def _format_labels(labels: Any) -> str:
    label_objects = _object_list(labels, "failure_labels")
    return _format_values([label["mode"] for label in label_objects])


def _format_values(values: Any) -> str:
    if not isinstance(values, list) or not values:
        return "none"
    return ", ".join(f"`{_clean(str(value))}`" for value in values)


def _format_state(passed: Any, abstained: Any) -> str:
    if abstained is True:
        return "abstained"
    if passed is True:
        return "pass"
    if passed is False:
        return "fail"
    return "n/a"


def _format_number(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _format_optional(value: Any) -> str:
    if value is None or value == "":
        return "none"
    return _clean(str(value))


def _clean(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


if __name__ == "__main__":
    raise SystemExit(main())
