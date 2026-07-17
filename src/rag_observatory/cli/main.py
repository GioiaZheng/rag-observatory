from __future__ import annotations

import argparse
from pathlib import Path

from rag_observatory.adapters.msmarco_genqa import load_msmarco_genqa_trace
from rag_observatory.adapters.otlp_openinference import load_otlp_openinference_trace
from rag_observatory.benchmark.failure_patterns import load_failure_pattern_benchmark
from rag_observatory.evaluation.failure_labels import evaluate_heuristic_failure_labels
from rag_observatory.evaluation.quality import evaluate_rule_based_quality
from rag_observatory.io.json import dump_trace, load_trace
from rag_observatory.reports.benchmark import render_markdown_failure_pattern_benchmark
from rag_observatory.reports.comparison import render_markdown_comparison
from rag_observatory.reports.conversation import render_markdown_conversation_report
from rag_observatory.reports.failure_label_evaluation import (
    render_markdown_failure_label_evaluation,
)
from rag_observatory.reports.html import render_html_report, render_report_screenshot_svg
from rag_observatory.reports.markdown import render_markdown_report
from rag_observatory.reports.quality import render_markdown_quality_evaluation
from rag_observatory.taxonomy.failure_modes import classify_trace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rag-observe")
    subparsers = parser.add_subparsers(dest="command", required=True)

    report = subparsers.add_parser("report", help="Render a markdown diagnostic report.")
    report.add_argument("trace", help="Path to a RAG trace JSON file.")
    report.add_argument("--output", "-o", help="Output markdown file. Prints to stdout if omitted.")

    html_report = subparsers.add_parser("html-report", help="Render an HTML diagnostic report.")
    html_report.add_argument("trace", help="Path to a RAG trace JSON file.")
    html_report.add_argument(
        "--output", "-o", help="Output HTML file. Prints to stdout if omitted."
    )
    html_report.add_argument(
        "--screenshot",
        help="Optional output SVG preview file for documentation and CI checks.",
    )

    compare = subparsers.add_parser("compare", help="Render a markdown trace comparison.")
    compare.add_argument("before", help="Path to the baseline RAG trace JSON file.")
    compare.add_argument("after", help="Path to the comparison RAG trace JSON file.")
    compare.add_argument(
        "--output", "-o", help="Output markdown file. Prints to stdout if omitted."
    )

    benchmark_summary = subparsers.add_parser(
        "benchmark-summary",
        help="Render a markdown failure-pattern benchmark summary.",
    )
    benchmark_summary.add_argument(
        "manifest",
        help="Path to a small failure-pattern benchmark manifest.",
    )
    benchmark_summary.add_argument(
        "--output",
        "-o",
        help="Output markdown file. Prints to stdout if omitted.",
    )

    conversation_report = subparsers.add_parser(
        "conversation-report",
        help="Render a markdown diagnostic report across conversational RAG turns.",
    )
    conversation_report.add_argument(
        "traces", nargs="+", help="Paths to per-turn RAG trace JSON files."
    )
    conversation_report.add_argument(
        "--output",
        "-o",
        help="Output markdown file. Prints to stdout if omitted.",
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

    evaluate_quality = subparsers.add_parser(
        "evaluate-quality",
        help="Render a markdown quality evaluator comparison report.",
    )
    evaluate_quality.add_argument(
        "expected_scores",
        help="Path to a reviewed expected quality scores JSON file.",
    )
    evaluate_quality.add_argument(
        "--output",
        "-o",
        help="Output markdown file. Prints to stdout if omitted.",
    )

    ingest_msmarco = subparsers.add_parser(
        "ingest-msmarco-genqa",
        help="Convert an msmarco-genqa JSON export into a RAG trace JSON file.",
    )
    ingest_msmarco.add_argument("export", help="Path to an msmarco-genqa JSON export.")
    ingest_msmarco.add_argument("--output", "-o", required=True, help="Output trace JSON file.")

    ingest_otlp = subparsers.add_parser(
        "ingest-otlp-openinference",
        help="Convert an OTLP/HTTP JSON export with OpenInference spans into a RAG trace.",
    )
    ingest_otlp.add_argument("export", help="Path to an OTLP/HTTP JSON trace export.")
    ingest_otlp.add_argument(
        "--trace-id",
        help="Trace ID to select when the export contains more than one trace.",
    )
    ingest_otlp.add_argument("--output", "-o", required=True, help="Output trace JSON file.")

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

    if args.command == "html-report":
        trace = load_trace(args.trace)
        labels = classify_trace(trace)
        report = render_html_report(trace, failure_labels=labels)
        _write_or_print(report, args.output)
        if args.screenshot:
            _write_or_print(
                render_report_screenshot_svg(trace, failure_labels=labels),
                args.screenshot,
            )
        return 0

    if args.command == "compare":
        before = load_trace(args.before)
        after = load_trace(args.after)
        comparison = render_markdown_comparison(before, after)
        _write_or_print(comparison, args.output)
        return 0

    if args.command == "benchmark-summary":
        summary = load_failure_pattern_benchmark(args.manifest)
        report = render_markdown_failure_pattern_benchmark(summary)
        _write_or_print(report, args.output)
        return 0

    if args.command == "conversation-report":
        traces = [load_trace(trace_path) for trace_path in args.traces]
        report = render_markdown_conversation_report(traces)
        _write_or_print(report, args.output)
        return 0

    if args.command == "evaluate-labels":
        label_evaluation = evaluate_heuristic_failure_labels(args.expected_labels)
        report = render_markdown_failure_label_evaluation(label_evaluation)
        _write_or_print(report, args.output)
        return 0

    if args.command == "evaluate-quality":
        quality_evaluation = evaluate_rule_based_quality(args.expected_scores)
        report = render_markdown_quality_evaluation(quality_evaluation)
        _write_or_print(report, args.output)
        return 0

    if args.command == "ingest-msmarco-genqa":
        trace = load_msmarco_genqa_trace(args.export)
        dump_trace(trace, args.output)
        return 0

    if args.command == "ingest-otlp-openinference":
        trace = load_otlp_openinference_trace(args.export, trace_id=args.trace_id)
        dump_trace(trace, args.output)
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

