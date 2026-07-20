from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rag_observatory.evaluation.quality import (  # noqa: E402
    EvaluatorInput,
    RuleBasedQualityEvaluator,
)
from rag_observatory.io.json import load_trace  # noqa: E402
from rag_observatory.taxonomy.failure_modes import classify_trace  # noqa: E402

JsonObject = dict[str, Any]


def solve_case(
    case: Mapping[str, Any],
    *,
    dataset_dir: Path,
    dimensions: Sequence[str],
    threshold: float,
) -> JsonObject:
    trace_path = (dataset_dir / _required_str(case, "trace_path")).resolve()
    trace = load_trace(trace_path)
    quality = RuleBasedQualityEvaluator(threshold=threshold).evaluate(
        EvaluatorInput(trace=trace, dimensions=tuple(dimensions))
    )

    return {
        "case_id": _required_str(case, "case_id"),
        "input": {
            "trace_path": _display_path(trace_path),
            "run_id": trace.metadata.run_id,
            "query_id": trace.query.query_id,
            "question": trace.query.text,
            "gold_answer": trace.query.gold_answer,
        },
        "output": {
            "answer": trace.answer.text,
            "citation_count": len(trace.answer.citations),
        },
        "scores": [
            {
                "dimension": score.dimension,
                "score": score.score,
                "passed": score.passed,
                "threshold": score.threshold,
                "abstained": score.abstained,
                "abstention_reason": score.abstention_reason,
                "evidence": score.evidence,
                "rationale": score.rationale,
            }
            for score in quality.scores
        ],
        "failure_labels": [
            {
                "mode": label.mode,
                "severity": label.severity,
                "method": label.detection_method,
                "evidence": label.evidence,
            }
            for label in classify_trace(trace)
        ],
    }


def _required_str(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()
