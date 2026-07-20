from __future__ import annotations

from collections.abc import Mapping
from typing import Any

JsonObject = dict[str, Any]


def score_case(case: Mapping[str, Any], solved: Mapping[str, Any]) -> JsonObject:
    expected_labels = _string_list(case.get("expected_failure_labels"), "expected_failure_labels")
    observed_labels = [
        _required_str(label, "mode")
        for label in _object_list(solved.get("failure_labels"), "failure_labels")
    ]
    expected_set = set(expected_labels)
    observed_set = set(observed_labels)

    score_rows = _score_quality(case, solved)
    return {
        "case_id": _required_str(case, "case_id"),
        "failure_label_evaluation": {
            "expected": expected_labels,
            "observed": observed_labels,
            "false_positives": sorted(observed_set - expected_set),
            "false_negatives": sorted(expected_set - observed_set),
            "exact_match": expected_set == observed_set,
        },
        "quality_evaluation": score_rows,
        "quality_exact_match": all(row["exact_match"] for row in score_rows),
    }


def _score_quality(case: Mapping[str, Any], solved: Mapping[str, Any]) -> list[JsonObject]:
    expected_scores = _object_list(case.get("expected_scores"), "expected_scores")
    observed_scores = {
        _required_str(score, "dimension"): score
        for score in _object_list(solved.get("scores"), "scores")
    }

    rows: list[JsonObject] = []
    for expected in expected_scores:
        dimension = _required_str(expected, "dimension")
        observed = observed_scores.get(dimension)
        if observed is None:
            raise ValueError(f"missing observed score for dimension: {dimension}")
        expected_passed = expected.get("passed")
        expected_abstained = expected.get("abstained") is True
        observed_passed = observed.get("passed")
        observed_abstained = observed.get("abstained") is True
        rows.append(
            {
                "dimension": dimension,
                "expected_passed": expected_passed,
                "observed_passed": observed_passed,
                "expected_abstained": expected_abstained,
                "observed_abstained": observed_abstained,
                "score": observed.get("score"),
                "threshold": observed.get("threshold"),
                "evidence": observed.get("evidence"),
                "abstention_reason": observed.get("abstention_reason"),
                "exact_match": (
                    expected_passed == observed_passed and expected_abstained == observed_abstained
                ),
            }
        )
    return rows


def summarize(scored_cases: list[Mapping[str, Any]]) -> JsonObject:
    quality_rows = [row for scored in scored_cases for row in scored["quality_evaluation"]]
    return {
        "case_count": len(scored_cases),
        "quality_judgments": len(quality_rows),
        "quality_agreements": sum(1 for row in quality_rows if row["exact_match"]),
        "quality_disagreements": sum(1 for row in quality_rows if not row["exact_match"]),
        "quality_abstentions": sum(1 for row in quality_rows if row["observed_abstained"]),
        "failure_label_exact_matches": sum(
            1 for scored in scored_cases if scored["failure_label_evaluation"]["exact_match"]
        ),
    }


def _required_str(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{label} must contain strings")
        result.append(item)
    return result


def _object_list(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    result: list[Mapping[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError(f"{label} must contain objects")
        result.append(item)
    return result
