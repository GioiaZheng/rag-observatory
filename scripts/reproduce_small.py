from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = ROOT / "examples" / "reproduce-small"
DEFAULT_OUTPUT = ROOT / "outputs" / "reproduce-small"
REPRODUCE_SMALL_FORMAT = "rag-observatory.reproduce-small.v1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the small reproducible RAG observability workflow."
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT),
        help="Directory for generated traces, reports, and manifest.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = Path(args.output_dir)
    paths = _output_paths(output_dir)
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)

    modules = _load_modules()
    trace = modules["load_msmarco_genqa_trace"](EXAMPLE_DIR / "msmarco_genqa_export.json")
    modules["dump_trace"](trace, paths["trace"])

    labels = modules["classify_trace"](trace)
    diagnostic_markdown = modules["render_markdown_report"](trace, failure_labels=labels)
    paths["diagnostic_markdown"].write_text(diagnostic_markdown, encoding="utf-8")
    paths["diagnostic_html"].write_text(
        modules["render_html_report"](trace, failure_labels=labels),
        encoding="utf-8",
    )
    paths["diagnostic_screenshot"].write_text(
        modules["render_report_screenshot_svg"](trace, failure_labels=labels),
        encoding="utf-8",
    )

    baseline = modules["load_trace"](EXAMPLE_DIR / "comparison_baseline.json")
    reranked = modules["load_trace"](EXAMPLE_DIR / "comparison_reranked.json")
    comparison_markdown = modules["render_markdown_comparison"](baseline, reranked)
    paths["comparison_markdown"].write_text(comparison_markdown, encoding="utf-8")

    benchmark_summary = modules["load_failure_pattern_benchmark"](
        EXAMPLE_DIR / "benchmark_variants.json"
    )
    benchmark_markdown = modules["render_markdown_failure_pattern_benchmark"](benchmark_summary)
    paths["benchmark_summary"].write_text(benchmark_markdown, encoding="utf-8")

    manifest = _manifest(output_dir, paths, labels)
    paths["manifest"].write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(f"Wrote small reproduction artifacts to {output_dir}")
    return 0


def _load_modules() -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "src"))
    from rag_observatory.adapters.msmarco_genqa import load_msmarco_genqa_trace
    from rag_observatory.benchmark.failure_patterns import load_failure_pattern_benchmark
    from rag_observatory.io.json import dump_trace, load_trace
    from rag_observatory.reports.benchmark import render_markdown_failure_pattern_benchmark
    from rag_observatory.reports.comparison import render_markdown_comparison
    from rag_observatory.reports.html import render_html_report, render_report_screenshot_svg
    from rag_observatory.reports.markdown import render_markdown_report
    from rag_observatory.taxonomy.failure_modes import classify_trace

    return {
        "classify_trace": classify_trace,
        "dump_trace": dump_trace,
        "load_msmarco_genqa_trace": load_msmarco_genqa_trace,
        "load_failure_pattern_benchmark": load_failure_pattern_benchmark,
        "load_trace": load_trace,
        "render_markdown_failure_pattern_benchmark": render_markdown_failure_pattern_benchmark,
        "render_markdown_comparison": render_markdown_comparison,
        "render_markdown_report": render_markdown_report,
        "render_html_report": render_html_report,
        "render_report_screenshot_svg": render_report_screenshot_svg,
    }


def _output_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "trace": output_dir / "traces" / "msmarco_genqa_trace.json",
        "diagnostic_markdown": output_dir / "reports" / "msmarco_genqa_diagnostic.md",
        "diagnostic_html": output_dir / "reports" / "msmarco_genqa_diagnostic.html",
        "diagnostic_screenshot": output_dir / "reports" / "msmarco_genqa_diagnostic.svg",
        "comparison_markdown": output_dir / "reports" / "benchmark_comparison.md",
        "benchmark_summary": output_dir / "reports" / "failure_pattern_benchmark.md",
        "manifest": output_dir / "manifest.json",
    }


def _manifest(output_dir: Path, paths: dict[str, Path], labels: list[Any]) -> dict[str, Any]:
    return {
        "format": REPRODUCE_SMALL_FORMAT,
        "description": "Small reproducible trace-based RAG failure analysis workflow.",
        "inputs": {
            "msmarco_genqa_export": _relative(EXAMPLE_DIR / "msmarco_genqa_export.json", ROOT),
            "comparison_baseline": _relative(EXAMPLE_DIR / "comparison_baseline.json", ROOT),
            "comparison_reranked": _relative(EXAMPLE_DIR / "comparison_reranked.json", ROOT),
            "benchmark_manifest": _relative(EXAMPLE_DIR / "benchmark_variants.json", ROOT),
        },
        "artifacts": {
            "trace_schema_json": _relative(paths["trace"], output_dir),
            "markdown_report": _relative(paths["diagnostic_markdown"], output_dir),
            "html_report": _relative(paths["diagnostic_html"], output_dir),
            "screenshot_svg": _relative(paths["diagnostic_screenshot"], output_dir),
            "benchmark_comparison": _relative(paths["comparison_markdown"], output_dir),
            "failure_pattern_benchmark": _relative(paths["benchmark_summary"], output_dir),
        },
        "failure_modes": sorted({label.mode for label in labels}),
        "taxonomy_reference": "failure_taxonomy/README.md",
    }


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
