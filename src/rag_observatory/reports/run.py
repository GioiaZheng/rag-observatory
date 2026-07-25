from __future__ import annotations

from rag_observatory.trace.run import InternalRun, StageSpan


def render_markdown_run_report(run: InternalRun) -> str:
    lines = [
        "# Stage-aware RAG Run Report",
        "",
        f"- **Run ID:** `{_clean(run.run_id)}`",
        f"- **Trace ID:** `{_clean(run.trace_id)}`",
        f"- **Started:** {_clean(run.started_at or 'not recorded')}",
        "",
        "## Stage Summary",
        "",
        "| Stage | Status | Latency (ms) | Failure signals | Metrics |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for span in run.spans:
        signals = _failure_modes(span)
        metrics = ", ".join(
            f"`{_clean(name)}`={_clean(str(value))}" for name, value in span.metrics.items()
        )
        lines.append(
            f"| `{span.stage}` | {span.status} | "
            f"{span.latency_ms if span.latency_ms is not None else 'not recorded'} | "
            f"{', '.join(f'`{_clean(mode)}`' for mode in signals) or 'none'} | "
            f"{metrics or 'none'} |"
        )

    attributed = [(span.stage, mode) for span in run.spans for mode in _failure_modes(span)]
    lines.extend(["", "## Failure Attribution", ""])
    if attributed:
        lines.extend(["| Stage | Failure signal |", "| --- | --- |"])
        lines.extend(f"| `{_clean(stage)}` | `{_clean(mode)}` |" for stage, mode in attributed)
    else:
        lines.append("No failure signals were recorded or inferred.")

    diagnostic_span = next(
        (span for span in run.spans if span.stage == "diagnostics"),
        None,
    )
    lines.extend(["", "## Diagnostic Links", ""])
    if diagnostic_span is not None and diagnostic_span.links:
        lines.extend(["| Source span | Reason |", "| --- | --- |"])
        lines.extend(
            f"| `{_clean(link.span_id)}` | {_clean(link.reason)} |"
            for link in diagnostic_span.links
        )
    else:
        lines.append("No cross-stage diagnostic links were recorded.")

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "Failure attribution identifies the stage that emitted each observable signal. "
            "It does not by itself prove that the configuration caused the failure.",
            "",
        ]
    )
    return "\n".join(lines)


def _failure_modes(span: StageSpan) -> list[str]:
    modes: list[str] = []
    for event in span.events:
        if event.name != "failure_signal":
            continue
        mode = event.attributes.get("mode")
        if isinstance(mode, str):
            modes.append(mode)
    return modes


def _clean(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
