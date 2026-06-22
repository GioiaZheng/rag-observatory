from __future__ import annotations

import argparse
from pathlib import Path

from rag_observatory.io.json import load_trace
from rag_observatory.reports.markdown import render_markdown_report
from rag_observatory.taxonomy.failure_modes import classify_trace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rag-observe")
    subparsers = parser.add_subparsers(dest="command", required=True)

    report = subparsers.add_parser("report", help="Render a markdown diagnostic report.")
    report.add_argument("trace", help="Path to a RAG trace JSON file.")
    report.add_argument("--output", "-o", help="Output markdown file. Prints to stdout if omitted.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "report":
        trace = load_trace(args.trace)
        labels = classify_trace(trace)
        report = render_markdown_report(trace, failure_labels=labels)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report, encoding="utf-8")
        else:
            print(report, end="")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
