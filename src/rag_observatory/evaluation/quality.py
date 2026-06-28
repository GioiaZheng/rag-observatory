from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from rag_observatory.io.json import load_trace
from rag_observatory.taxonomy.failure_modes import classify_trace
from rag_observatory.trace.schema import Metric, RagTrace

JsonObject = dict[str, Any]

CONTEXT_RELEVANCE = "context_relevance"
FAITHFULNESS = "faithfulness"
ANSWER_RELEVANCE = "answer_relevance"


@dataclass(frozen=True)
class QualityDimensionDefinition:
    dimension: str
    question: str
    required_trace_signals: tuple[str, ...]
    abstention_guidance: str


QUALITY_DIMENSION_DEFINITIONS: dict[str, QualityDimensionDefinition] = {
    CONTEXT_RELEVANCE: QualityDimensionDefinition(
        dimension=CONTEXT_RELEVANCE,
        question="Is the selected context relevant to the query and answer task?",
        required_trace_signals=("selected_context", "retrieved_documents.is_relevant"),
        abstention_guidance="Abstain when selected context cannot be mapped to relevance annotations.",
    ),
    FAITHFULNESS: QualityDimensionDefinition(
        dimension=FAITHFULNESS,
        question="Is the answer supported by the selected context?",
        required_trace_signals=("answer", "selected_context", "faithfulness-like metric"),
        abstention_guidance="Abstain when no support-oriented metric or reviewed signal is present.",
    ),
    ANSWER_RELEVANCE: QualityDimensionDefinition(
        dimension=ANSWER_RELEVANCE,
        question="Does the answer address the user query?",
        required_trace_signals=("query", "answer", "answer relevance/correctness metric"),
        abstention_guidance="Abstain when no answer relevance or correctness signal is present.",
    ),
}

CORE_QUALITY_DIMENSIONS = tuple(QUALITY_DIMENSION_DEFINITIONS)


@dataclass(frozen=True)
class EvaluatorProvenance:
    evaluator_name: str
    evaluator_version: str
    method: str
    input_run_id: str | None = None
    input_query_id: str | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    extra: JsonObject = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluatorInput:
    trace: RagTrace
    dimensions: tuple[str, ...] = CORE_QUALITY_DIMENSIONS


@dataclass(frozen=True)
class QualityScore:
    dimension: str
    score: float | None
    passed: bool | None
    threshold: float | None
    evidence: str | None
    rationale: str | None
    abstained: bool = False
    abstention_reason: str | None = None


@dataclass(frozen=True)
class QualityEvaluation:
    trace_id: str
    query_id: str
    scores: tuple[QualityScore, ...]
    provenance: EvaluatorProvenance

    def score_for(self, dimension: str) -> QualityScore:
        for score in self.scores:
            if score.dimension == dimension:
                return score
        raise KeyError(f"missing quality score for dimension: {dimension}")


class TraceQualityEvaluator(Protocol):
    evaluator_name: str
    evaluator_version: str
    method: str

    def evaluate(self, evaluator_input: EvaluatorInput) -> QualityEvaluation:
        """Evaluate a trace and return auditable quality scores."""


class RuleBasedQualityEvaluator:
    evaluator_name = "rule_based_quality"
    evaluator_version = "v1"
    method = "deterministic"

    def __init__(self, *, threshold: float = 0.8) -> None:
        self.threshold = threshold

    def evaluate(self, evaluator_input: EvaluatorInput) -> QualityEvaluation:
        trace = evaluator_input.trace
        dimensions = _normalize_dimensions(evaluator_input.dimensions, "evaluator_input.dimensions")
        provenance = EvaluatorProvenance(
            evaluator_name=self.evaluator_name,
            evaluator_version=self.evaluator_version,
            method=self.method,
            input_run_id=trace.metadata.run_id,
            input_query_id=trace.query.query_id,
            extra={"threshold": self.threshold},
        )
        return QualityEvaluation(
            trace_id=trace.metadata.run_id,
            query_id=trace.query.query_id,
            scores=tuple(self._score_dimension(trace, dimension) for dimension in dimensions),
            provenance=provenance,
        )

    def _score_dimension(self, trace: RagTrace, dimension: str) -> QualityScore:
        if dimension == CONTEXT_RELEVANCE:
            return _score_context_relevance(trace, self.threshold)
        if dimension == FAITHFULNESS:
            metric = _find_metric(trace, ("faithfulness", "support", "grounded"))
            return _score_metric_dimension(trace, dimension, metric, self.threshold)
        if dimension == ANSWER_RELEVANCE:
            metric = _find_metric(trace, ("answer_relevance", "answer_correctness"))
            return _score_metric_dimension(trace, dimension, metric, self.threshold)
        raise ValueError(f"unknown quality dimension: {dimension}")


@dataclass(frozen=True)
class ReviewedQualityScore:
    dimension: str
    passed: bool | None
    abstained: bool = False


@dataclass(frozen=True)
class ReviewedQualityCase:
    case_id: str
    trace_path: Path
    expected_scores: tuple[ReviewedQualityScore, ...]


@dataclass(frozen=True)
class QualityCaseComparison:
    case_id: str
    trace_path: Path
    dimension: str
    expected_passed: bool | None
    observed_passed: bool | None
    expected_abstained: bool
    observed_abstained: bool
    score: float | None
    evidence: str | None
    rationale: str | None
    abstention_reason: str | None
    failure_modes: tuple[str, ...]

    @property
    def exact_match(self) -> bool:
        return (
            self.expected_passed == self.observed_passed
            and self.expected_abstained == self.observed_abstained
        )


@dataclass(frozen=True)
class QualityEvaluationComparison:
    rows: tuple[QualityCaseComparison, ...]
    evaluator_name: str
    evaluator_version: str
    method: str

    @property
    def total_rows(self) -> int:
        return len(self.rows)

    @property
    def total_cases(self) -> int:
        return len({row.case_id for row in self.rows})

    @property
    def agreement_count(self) -> int:
        return sum(1 for row in self.rows if row.exact_match)

    @property
    def disagreement_count(self) -> int:
        return self.total_rows - self.agreement_count

    @property
    def abstention_count(self) -> int:
        return sum(1 for row in self.rows if row.observed_abstained)


def load_reviewed_quality_cases(expected_scores_path: str | Path) -> list[ReviewedQualityCase]:
    path = Path(expected_scores_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError("expected quality scores file must be an object")

    raw_cases = data.get("cases")
    if not isinstance(raw_cases, list):
        raise ValueError("expected quality scores file must contain a cases list")

    cases: list[ReviewedQualityCase] = []
    for index, raw_case in enumerate(raw_cases):
        if not isinstance(raw_case, Mapping):
            raise ValueError(f"case at index {index} must be an object")
        case_id = _required_str(raw_case, "case_id", f"case[{index}]")
        trace_path = _required_str(raw_case, "trace_path", f"case[{index}]")
        expected_scores = _load_expected_scores(
            raw_case.get("expected_scores"),
            f"case[{index}].expected_scores",
        )
        cases.append(
            ReviewedQualityCase(
                case_id=case_id,
                trace_path=path.parent / trace_path,
                expected_scores=expected_scores,
            )
        )
    _ensure_unique_ids((case.case_id for case in cases), "reviewed quality case")
    return cases


def evaluate_rule_based_quality(
    expected_scores_path: str | Path,
) -> QualityEvaluationComparison:
    return evaluate_quality_cases(
        load_reviewed_quality_cases(expected_scores_path),
        RuleBasedQualityEvaluator(),
    )


def evaluate_quality_cases(
    cases: Sequence[ReviewedQualityCase],
    evaluator: TraceQualityEvaluator,
) -> QualityEvaluationComparison:
    _ensure_unique_ids((case.case_id for case in cases), "reviewed quality case")

    rows: list[QualityCaseComparison] = []
    for case in cases:
        dimensions = tuple(score.dimension for score in case.expected_scores)
        trace = load_trace(case.trace_path)
        evaluation = evaluator.evaluate(EvaluatorInput(trace=trace, dimensions=dimensions))
        scores_by_dimension = {score.dimension: score for score in evaluation.scores}
        failure_modes = _failure_modes(trace)

        for expected in case.expected_scores:
            observed = scores_by_dimension[expected.dimension]
            rows.append(
                QualityCaseComparison(
                    case_id=case.case_id,
                    trace_path=case.trace_path,
                    dimension=expected.dimension,
                    expected_passed=expected.passed,
                    observed_passed=observed.passed,
                    expected_abstained=expected.abstained,
                    observed_abstained=observed.abstained,
                    score=observed.score,
                    evidence=observed.evidence,
                    rationale=observed.rationale,
                    abstention_reason=observed.abstention_reason,
                    failure_modes=failure_modes,
                )
            )

    return QualityEvaluationComparison(
        rows=tuple(rows),
        evaluator_name=evaluator.evaluator_name,
        evaluator_version=evaluator.evaluator_version,
        method=evaluator.method,
    )


def _score_context_relevance(trace: RagTrace, threshold: float) -> QualityScore:
    if not trace.selected_context:
        return _abstain(
            CONTEXT_RELEVANCE,
            "selected_context is empty",
            "No selected context chunks are available for relevance judgment.",
        )

    relevance_by_doc_id = {
        document.doc_id: document.is_relevant
        for document in trace.retrieved_documents
        if document.is_relevant is not None
    }
    annotated = [
        relevance_by_doc_id[chunk.doc_id]
        for chunk in trace.selected_context
        if chunk.doc_id in relevance_by_doc_id
    ]
    if not annotated:
        return _abstain(
            CONTEXT_RELEVANCE,
            "selected context lacks relevance annotations",
            "No selected context chunk maps to a retrieved document with relevance annotation.",
        )

    relevant_count = sum(1 for value in annotated if value is True)
    score = relevant_count / len(annotated)
    passed = score >= threshold
    return QualityScore(
        dimension=CONTEXT_RELEVANCE,
        score=score,
        passed=passed,
        threshold=threshold,
        evidence=(
            f"{relevant_count}/{len(annotated)} selected context chunks map to "
            "relevant retrieved documents"
        ),
        rationale=(
            "Context relevance is estimated from selected context document IDs "
            "and retrieval relevance annotations."
        ),
    )


def _score_metric_dimension(
    trace: RagTrace,
    dimension: str,
    metric: Metric | None,
    default_threshold: float,
) -> QualityScore:
    if metric is None:
        return _abstain(
            dimension,
            f"no {dimension} metric is recorded",
            "No metric in the trace provides an auditable scalar or pass/fail signal.",
        )

    score = _numeric_metric_value(metric)
    threshold = metric.threshold if metric.threshold is not None else default_threshold
    passed = metric.passed
    if passed is None and score is not None:
        passed = score >= threshold
    if passed is None and score is None:
        return _abstain(
            dimension,
            f"{metric.name} has neither pass/fail nor numeric value",
            "The recorded metric cannot be converted into a quality judgment.",
        )

    return QualityScore(
        dimension=dimension,
        score=score,
        passed=passed,
        threshold=threshold,
        evidence=_metric_evidence(trace, metric),
        rationale=f"`{metric.name}` is treated as the auditable signal for {dimension}.",
    )


def _metric_evidence(trace: RagTrace, metric: Metric) -> str:
    parts = [f"{metric.name}={metric.value!r}"]
    if metric.passed is not None:
        parts.append(f"passed={metric.passed}")
    if metric.threshold is not None:
        parts.append(f"threshold={metric.threshold}")
    if metric.notes:
        parts.append(f"notes={metric.notes}")
    parts.append(f"run_id={trace.metadata.run_id}")
    return "; ".join(parts)


def _abstain(dimension: str, reason: str, rationale: str) -> QualityScore:
    return QualityScore(
        dimension=dimension,
        score=None,
        passed=None,
        threshold=None,
        evidence=None,
        rationale=rationale,
        abstained=True,
        abstention_reason=reason,
    )


def _find_metric(trace: RagTrace, keywords: tuple[str, ...]) -> Metric | None:
    for metric in trace.metrics:
        metric_name = metric.name.lower()
        if any(keyword in metric_name for keyword in keywords):
            return metric
    return None


def _numeric_metric_value(metric: Metric) -> float | None:
    value = metric.value
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _load_expected_scores(value: Any, label: str) -> tuple[ReviewedQualityScore, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")

    scores: list[ReviewedQualityScore] = []
    for index, raw_score in enumerate(value):
        if not isinstance(raw_score, Mapping):
            raise ValueError(f"{label}[{index}] must be an object")
        dimension = _required_str(raw_score, "dimension", f"{label}[{index}]")
        dimension = _normalize_dimension(dimension, f"{label}[{index}].dimension")
        passed = _optional_bool_or_none(raw_score, "passed", f"{label}[{index}]")
        abstained = _optional_bool(raw_score, "abstained", f"{label}[{index}]") or False
        if abstained and passed is not None:
            raise ValueError(f"{label}[{index}].passed must be null when abstained is true")
        scores.append(ReviewedQualityScore(dimension=dimension, passed=passed, abstained=abstained))

    dimensions = [score.dimension for score in scores]
    _ensure_unique_ids(dimensions, "quality dimension")
    return tuple(scores)


def _normalize_dimensions(values: Iterable[str], label: str) -> tuple[str, ...]:
    dimensions = tuple(_normalize_dimension(value, label) for value in values)
    _ensure_unique_ids(dimensions, "quality dimension")
    return dimensions


def _normalize_dimension(value: str, label: str) -> str:
    if value not in QUALITY_DIMENSION_DEFINITIONS:
        raise ValueError(f"{label} contains unknown quality dimension: {value}")
    return value


def _failure_modes(trace: RagTrace) -> tuple[str, ...]:
    modes: list[str] = []
    seen: set[str] = set()
    for label in classify_trace(trace):
        if label.mode not in seen:
            modes.append(label.mode)
            seen.add(label.mode)
    return tuple(modes)


def _required_str(data: Mapping[str, Any], key: str, label: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label}.{key} must be a non-empty string")
    return value


def _optional_bool(data: Mapping[str, Any], key: str, label: str) -> bool | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError(f"{label}.{key} must be a boolean")
    return value


def _optional_bool_or_none(data: Mapping[str, Any], key: str, label: str) -> bool | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError(f"{label}.{key} must be a boolean or null")
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
