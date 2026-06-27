from __future__ import annotations

import argparse
from pathlib import Path

from rag_observatory.evaluation.failure_labels import evaluate_heuristic_failure_labels
from rag_observatory.io.json import load_trace
from rag_observatory.reports.comparison import render_markdown_comparison
from rag_observatory.reports.failure_label_evaluation import (
    render_markdown_failure_label_evaluation,
)
from rag_observatory.reports.markdown import render_markdown_report
from rag_observatory.taxonomy.failure_modes import classify_trace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rag-observe")
    subparsers = parser.add_subparsers(dest="command", required=True)

    report = subparsers.add_parser("report", help="Render a markdown diagnostic report.")
    report.add_argument("trace", help="Path to a RAG trace JSON file.")
    report.add_argument("--output", "-o", help="Output markdown file. Prints to stdout if omitted.")

    compare = subparsers.add_parser("compare", help="Render a markdown trace comparison.")
    compare.add_argument("before", help="Path to the baseline RAG trace JSON file.")
    compare.add_argument("after", help="Path to the comparison RAG trace JSON file.")
    compare.add_argument(
        "--output", "-o", help="Output markdown file. Prints to stdout if omitted."
    )

    evaluate_labels = subparsers.add_parser(
        "evaluate-labels",
        help="Render a markdown failure label evaluation report.",
    )
    evaluate_labels.add_argument(
        "expected_labels",
        help="Path to a reviewed expected failure labels JSON file.",
    )
    evaluate_labels.add_argument(
        "--output",
        "-o",
        help="Output markdown file. Prints to stdout if omitted.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "report":
        trace = load_trace(args.trace)
        labels = classify_trace(trace)
        report = render_markdown_report(trace, failure_labels=labels)
        _write_or_print(report, args.output)
        return 0

    if args.command == "compare":
        before = load_trace(args.before)
        after = load_trace(args.after)
        comparison = render_markdown_comparison(before, after)
        _write_or_print(comparison, args.output)
        return 0

    if args.command == "evaluate-labels":
        evaluation = evaluate_heuristic_failure_labels(args.expected_labels)
        report = render_markdown_failure_label_evaluation(evaluation)
        _write_or_print(report, args.output)
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


def _write_or_print(text: str, output: str | None) -> None:
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    raise SystemExit(main())
