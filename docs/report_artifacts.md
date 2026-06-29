# Report Artifacts

`rag-observatory` supports Markdown reports for review and HTML reports for
sharing compact diagnostic artifacts.

## HTML Diagnostic Report

Render a semantic HTML report from any trace:

```bash
PYTHONPATH=src python -m rag_observatory.cli.main html-report tests/fixtures/stage_contract/full_observability_trace.json --output outputs/reports/full_observability.html
```

The HTML report is dependency-light and deterministic. It includes:

- run metadata;
- query and generated answer;
- retrieved and reranked evidence tables;
- selected context;
- evaluation signals;
- failure taxonomy labels;
- inspect-next guidance.

## Screenshot Preview

The same command can write a deterministic SVG preview:

```bash
PYTHONPATH=src python -m rag_observatory.cli.main html-report tests/fixtures/stage_contract/full_observability_trace.json --output outputs/reports/full_observability.html --screenshot outputs/reports/full_observability.svg
```

The SVG preview is a checked screenshot-style artifact for documentation and
CI. It is not a browser raster capture. A browser-rendered screenshot can be
added later if the project introduces a browser dependency for visual tests.

## Reproduction Workflow

`make reproduce-small` writes:

```text
outputs/reproduce-small/reports/msmarco_genqa_diagnostic.html
outputs/reproduce-small/reports/msmarco_genqa_diagnostic.svg
```

Generated artifacts should stay under ignored output directories unless a
specific example is intentionally checked in.
