from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from rag_observatory.io.json import load_trace
from rag_observatory.taxonomy.failure_modes import (
    FAILURE_MODE_DEFINITIONS,
    FAILURE_MODE_VALUES,
    classify_trace,
)

FAILURE_MODE_ORDER = tuple(FAILURE_MODE_DEFINITIONS)


@dataclass(frozen=True)
class ReviewedLabelCase:
    case_id: str
    trace_path: Path
    expected_modes: tuple[str, ...]


@dataclass(frozen=True)
class LabelPrediction:
    case_id: str
    predicted_modes: tuple[str, ...]
    abstained: bool = False


@dataclass(frozen=True)
class CaseEvaluation:
    case_id: str
    trace_path: Path
    expected_modes: tuple[str, ...]
    predicted_modes: tuple[str, ...]
    false_positives: tuple[str, ...]
    false_negatives: tuple[str, ...]
    abstained: bool = False

    @property
    def exact_match(self) -> bool:
        return not self.false_positives and not self.false_negatives


@dataclass(frozen=True)
class ModeMetrics:
    mode: str
    true_positives: int
    false_positives: int
    false_negatives: int
    support: int

    @property
    def precision(self) -> float | None:
        denominator = self.true_positives + self.false_positives
        if denominator == 0:
            return None
        return self.true_positives / denominator

    @property
    def recall(self) -> float | None:
        denominator = self.true_positives + self.false_negatives
        if denominator == 0:
            return None
        return self.true_positives / denominator


@dataclass(frozen=True)
class FailureLabelEvaluation:
    cases: tuple[CaseEvaluation, ...]
    mode_metrics: tuple[ModeMetrics, ...]

    @property
    def total_cases(self) -> int:
        return len(self.cases)

    @property
    def exact_match_count(self) -> int:
        return sum(1 for case in self.cases if case.exact_match)

    @property
    def abstention_count(self) -> int:
        return sum(1 for case in self.cases if case.abstained)

    @property
    def abstention_rate(self) -> float | None:
        if not self.cases:
            return None
        return self.abstention_count / len(self.cases)


def load_reviewed_label_cases(expected_labels_path: str | Path) -> list[ReviewedLabelCase]:
    path = Path(expected_labels_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_cases = data.get("cases")
    if not isinstance(raw_cases, list):
        raise ValueError("expected labels file must contain a cases list")

    cases: list[ReviewedLabelCase] = []
    for index, raw_case in enumerate(raw_cases):
        if not isinstance(raw_case, dict):
            raise ValueError(f"case at index {index} must be an object")

        case_id = _required_str(raw_case, "case_id", f"case[{index}]")
        trace_path = _required_str(raw_case, "trace_path", f"case[{index}]")
        expected_modes = _normalize_modes(
            raw_case.get("expected_modes", []),
            f"case[{index}].expected_modes",
        )
        cases.append(
            ReviewedLabelCase(
                case_id=case_id,
                trace_path=path.parent / trace_path,
                expected_modes=expected_modes,
            )
        )
    _ensure_unique_ids((case.case_id for case in cases), "reviewed label case")
    return cases


def evaluate_heuristic_failure_labels(
    expected_labels_path: str | Path,
) -> FailureLabelEvaluation:
    cases = load_reviewed_label_cases(expected_labels_path)
    predictions = [
        LabelPrediction(
            case_id=case.case_id,
            predicted_modes=_normalize_modes(
                (label.mode for label in classify_trace(load_trace(case.trace_path))),
                f"{case.case_id}.predicted_modes",
            ),
        )
        for case in cases
    ]
    return evaluate_failure_labels(cases, predictions)


def evaluate_failure_labels(
    cases: Sequence[ReviewedLabelCase],
    predictions: Sequence[LabelPrediction],
) -> FailureLabelEvaluation:
    _ensure_unique_ids((case.case_id for case in cases), "reviewed label case")
    _ensure_unique_ids(
        (prediction.case_id for prediction in predictions),
        "label prediction",
    )

    predictions_by_id = {prediction.case_id: prediction for prediction in predictions}
    case_ids = {case.case_id for case in cases}
    prediction_ids = set(predictions_by_id)
    missing_predictions = sorted(case_ids - prediction_ids)
    extra_predictions = sorted(prediction_ids - case_ids)
    if missing_predictions:
        joined = ", ".join(missing_predictions)
        raise ValueError(f"missing predictions for case(s): {joined}")
    if extra_predictions:
        joined = ", ".join(extra_predictions)
        raise ValueError(f"predictions reference unknown case(s): {joined}")

    case_evaluations: list[CaseEvaluation] = []
    for case in cases:
        prediction = predictions_by_id[case.case_id]
        expected_modes = _normalize_modes(case.expected_modes, f"{case.case_id}.expected_modes")
        predicted_modes = _normalize_modes(
            prediction.predicted_modes,
            f"{case.case_id}.predicted_modes",
        )
        expected = set(expected_modes)
        predicted = set(predicted_modes)
        case_evaluations.append(
            CaseEvaluation(
                case_id=case.case_id,
                trace_path=case.trace_path,
                expected_modes=expected_modes,
                predicted_modes=predicted_modes,
                false_positives=_sort_modes(predicted - expected),
                false_negatives=_sort_modes(expected - predicted),
                abstained=prediction.abstained,
            )
        )

    return FailureLabelEvaluation(
        cases=tuple(case_evaluations),
        mode_metrics=_compute_mode_metrics(case_evaluations),
    )


def _compute_mode_metrics(cases: Sequence[CaseEvaluation]) -> tuple[ModeMetrics, ...]:
    observed_modes: set[str] = set()
    for case in cases:
        observed_modes.update(case.expected_modes)
        observed_modes.update(case.predicted_modes)

    metrics: list[ModeMetrics] = []
    for mode in _sort_modes(observed_modes):
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        for case in cases:
            expected = set(case.expected_modes)
            predicted = set(case.predicted_modes)
            if mode in expected and mode in predicted:
                true_positives += 1
            elif mode in predicted:
                false_positives += 1
            elif mode in expected:
                false_negatives += 1
        metrics.append(
            ModeMetrics(
                mode=mode,
                true_positives=true_positives,
                false_positives=false_positives,
                false_negatives=false_negatives,
                support=true_positives + false_negatives,
            )
        )
    return tuple(metrics)


def _normalize_modes(values: Iterable[str], label: str) -> tuple[str, ...]:
    if isinstance(values, str):
        raise ValueError(f"{label} must be a list of failure modes")

    modes: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value:
            raise ValueError(f"{label} must contain non-empty strings")
        if value not in FAILURE_MODE_VALUES:
            raise ValueError(f"{label} contains unknown failure mode: {value}")
        modes.add(value)
    return _sort_modes(modes)


def _sort_modes(values: Iterable[str]) -> tuple[str, ...]:
    order = {mode: index for index, mode in enumerate(FAILURE_MODE_ORDER)}
    return tuple(sorted(values, key=lambda mode: (order.get(mode, len(order)), mode)))


def _required_str(data: dict[str, object], key: str, label: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label}.{key} must be a non-empty string")
    return value


def _ensure_unique_ids(values: Iterable[str], label: str) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        joined = ", ".join(sorted(duplicates))
        raise ValueError(f"duplicate {label} id(s): {joined}")
