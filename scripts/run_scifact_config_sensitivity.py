from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "outputs" / "scifact-config-sensitivity"
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class CorpusDocument:
    doc_id: str
    title: str
    text: str
    terms: Counter[str]


class Bm25Index:
    def __init__(self, documents: list[CorpusDocument]) -> None:
        self.documents = documents
        self.average_length = sum(document.terms.total() for document in documents) / len(documents)
        document_frequency: Counter[str] = Counter()
        for document in documents:
            document_frequency.update(document.terms)
        self.idf = {
            term: math.log(1 + (len(documents) - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def search(self, query: str, *, top_k: int) -> list[tuple[CorpusDocument, float]]:
        query_terms = Counter(_tokenize(query))
        scored = [(document, self._score(document, query_terms)) for document in self.documents]
        scored.sort(key=lambda item: (-item[1], item[0].doc_id))
        return scored[:top_k]

    def _score(self, document: CorpusDocument, query_terms: Counter[str]) -> float:
        score = 0.0
        document_length = document.terms.total()
        for term, query_frequency in query_terms.items():
            frequency = document.terms.get(term, 0)
            if frequency == 0:
                continue
            denominator = frequency + 1.5 * (
                1 - 0.75 + 0.75 * document_length / self.average_length
            )
            score += self.idf.get(term, 0.0) * frequency * 2.5 / denominator * query_frequency
        return score


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a deterministic BM25 retrieval-depth comparison on a local BEIR SciFact export."
        )
    )
    parser.add_argument(
        "dataset_dir",
        help="Directory containing corpus.jsonl, queries.jsonl, and qrels/test.tsv.",
    )
    parser.add_argument(
        "--query-count",
        type=int,
        default=20,
        help="Number of sorted test queries to run. Default: 20.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        nargs="+",
        default=[1, 5],
        help="Retrieval depths to compare. Default: 1 5.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT),
        help="Directory for generated traces, report, and manifest.",
    )
    parser.add_argument(
        "--report-output",
        help="Optional second path for the generated Markdown report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.query_count < 1:
        raise ValueError("--query-count must be positive")
    if len(set(args.top_k)) < 2 or any(top_k < 1 for top_k in args.top_k):
        raise ValueError("--top-k requires at least two distinct positive values")

    dataset_dir = Path(args.dataset_dir)
    output_dir = Path(args.output_dir)
    documents = _load_corpus(dataset_dir / "corpus.jsonl")
    queries = _load_queries(dataset_dir / "queries.jsonl")
    qrels = _load_qrels(dataset_dir / "qrels" / "test.tsv")
    query_ids = sorted(set(queries) & set(qrels), key=_query_sort_key)[: args.query_count]
    if len(query_ids) < args.query_count:
        raise ValueError(
            f"requested {args.query_count} queries but only found {len(query_ids)} test queries"
        )

    modules = _load_modules()
    index = Bm25Index(documents)
    traces: list[Any] = []
    trace_paths: list[Path] = []
    for top_k in sorted(set(args.top_k)):
        for query_id in query_ids:
            ranked = index.search(queries[query_id], top_k=top_k)
            trace = _make_trace(
                modules["RagTrace"],
                query_id=query_id,
                query_text=queries[query_id],
                ranked=ranked,
                relevant_ids=qrels[query_id],
                top_k=top_k,
            )
            trace_path = output_dir / "traces" / f"top-k-{top_k}" / f"{query_id}.json"
            modules["dump_trace"](trace, trace_path)
            traces.append(trace)
            trace_paths.append(trace_path)

    generated_report = modules["render_markdown_configuration_report"](
        traces, controlled_variable="retrieval_top_k"
    )
    report = _documented_report(
        generated_report,
        query_ids=query_ids,
        top_k_values=sorted(set(args.top_k)),
    )
    report_path = output_dir / "report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    if args.report_output:
        second_report_path = Path(args.report_output)
        second_report_path.parent.mkdir(parents=True, exist_ok=True)
        second_report_path.write_text(report, encoding="utf-8")

    manifest = {
        "format": "rag-observatory.scifact-config-run.v1",
        "dataset": "BeIR/scifact",
        "dataset_license": "CC-BY-SA-4.0",
        "dataset_url": "https://huggingface.co/datasets/BeIR/scifact",
        "dataset_archive_md5": "5f7d1de60b170fc8027bb7898e2efca1",
        "retriever": "bm25-python-v1",
        "controlled_variable": "retrieval_top_k",
        "top_k_values": sorted(set(args.top_k)),
        "query_ids": query_ids,
        "trace_count": len(traces),
        "report": str(report_path),
        "traces": [str(path) for path in trace_paths],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(traces)} actual SciFact retrieval traces and report to {output_dir}")
    return 0


def _load_modules() -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "src"))
    from rag_observatory.io.json import dump_trace
    from rag_observatory.reports.configuration import (
        render_markdown_configuration_report,
    )
    from rag_observatory.trace.schema import RagTrace

    return {
        "RagTrace": RagTrace,
        "dump_trace": dump_trace,
        "render_markdown_configuration_report": render_markdown_configuration_report,
    }


def _documented_report(
    generated_report: str,
    *,
    query_ids: list[str],
    top_k_values: list[int],
) -> str:
    generated_section = generated_report.replace(
        "# Configuration-sensitive Failure Report\n\n",
        "## Generated Configuration Report\n\n",
        1,
    )
    provenance = [
        "# SciFact Retrieval-depth Configuration Run",
        "",
        "## Run Provenance",
        "",
        "- **Execution date:** 2026-07-25",
        "- **Dataset:** [BEIR SciFact](https://huggingface.co/datasets/BeIR/scifact)",
        "- **Dataset license:** CC-BY-SA-4.0",
        "- **BEIR archive MD5:** `5f7d1de60b170fc8027bb7898e2efca1`",
        "- **Retriever:** deterministic local `bm25-python-v1`",
        f"- **Controlled values:** `retrieval_top_k={','.join(map(str, top_k_values))}`",
        f"- **Test query IDs:** {', '.join(f'`{query_id}`' for query_id in query_ids)}",
        f"- **Generated traces:** {len(query_ids) * len(top_k_values)}",
        "",
        "The runner reads the official BEIR `corpus.jsonl`, `queries.jsonl`, and "
        "`qrels/test.tsv` files. It keeps the query set, BM25 implementation, "
        "top-1 context policy, deterministic extractive answer, and qrels evaluator "
        "fixed while changing only retrieval depth.",
        "",
        "## Scope and Limitations",
        "",
        "- This is an actual retrieval-stage run over public SciFact records, not a "
        "synthetic fixture.",
        "- It is not a full generative RAG benchmark: generation is a deterministic "
        "copy of the top retrieved document.",
        "- The current `retrieval_noise` heuristic fires when any retrieved document "
        "is marked irrelevant, so increasing top-k can raise that label even when "
        "recall improves.",
        "- Twenty sorted test queries are an inspectable smoke experiment, not a "
        "statistical claim about all SciFact queries or other systems.",
        "",
    ]
    return "\n".join(provenance) + "\n" + generated_section


def _load_corpus(path: Path) -> list[CorpusDocument]:
    documents: list[CorpusDocument] = []
    for record in _read_jsonl(path):
        doc_id = str(record["_id"])
        title = str(record.get("title", ""))
        text = str(record["text"])
        documents.append(
            CorpusDocument(
                doc_id=doc_id,
                title=title,
                text=text,
                terms=Counter(_tokenize(f"{title} {text}")),
            )
        )
    if not documents:
        raise ValueError(f"{path} contains no documents")
    return documents


def _load_queries(path: Path) -> dict[str, str]:
    return {str(record["_id"]): str(record["text"]) for record in _read_jsonl(path)}


def _load_qrels(path: Path) -> dict[str, set[str]]:
    qrels: dict[str, set[str]] = defaultdict(set)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            score = int(row["score"])
            if score > 0:
                qrels[str(row["query-id"])].add(str(row["corpus-id"]))
    return dict(qrels)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must contain a JSON object")
            records.append(value)
    return records


def _make_trace(
    rag_trace_type: Any,
    *,
    query_id: str,
    query_text: str,
    ranked: list[tuple[CorpusDocument, float]],
    relevant_ids: set[str],
    top_k: int,
) -> Any:
    retrieved_documents = [
        {
            "doc_id": document.doc_id,
            "title": document.title or None,
            "source": "BeIR/scifact",
            "text": document.text,
            "score": round(score, 8),
            "rank": rank,
            "is_relevant": document.doc_id in relevant_ids,
        }
        for rank, (document, score) in enumerate(ranked, start=1)
    ]
    first_document = retrieved_documents[0]
    retrieval_hit = any(document["is_relevant"] for document in retrieved_documents)
    return rag_trace_type.from_dict(
        {
            "metadata": {
                "run_id": f"scifact-{query_id}-top-k-{top_k}",
                "timestamp": "2026-07-25T00:00:00Z",
                "dataset": "BeIR/scifact",
                "config_hash": f"bm25-top-k-{top_k}",
                "code_version": "bm25-python-v1",
                "retriever": "bm25-python-v1",
                "generator": "extractive-first-document-v1",
                "evaluator": "scifact-qrels-membership-v1",
                "random_seed": 0,
                "pipeline_stages": {
                    "retrieval": True,
                    "reranking": False,
                    "context_selection": True,
                    "prompt": False,
                    "generation": True,
                    "citations": True,
                    "evaluation": True,
                },
                "extra": {
                    "configuration": {
                        "retrieval_top_k": top_k,
                        "retriever_algorithm": "bm25-python-v1",
                        "context_policy": "top_1",
                        "generator": "extractive-first-document-v1",
                        "evaluator": "scifact-qrels-membership-v1",
                    },
                    "dataset_url": "https://huggingface.co/datasets/BeIR/scifact",
                    "dataset_license": "CC-BY-SA-4.0",
                },
            },
            "query": {"query_id": query_id, "text": query_text},
            "retrieved_documents": retrieved_documents,
            "selected_context": [
                {
                    "context_id": f"context-{first_document['doc_id']}",
                    "doc_id": first_document["doc_id"],
                    "text": first_document["text"],
                    "rank": 1,
                }
            ],
            "answer": {
                "text": str(first_document["text"]),
                "citations": [{"doc_id": first_document["doc_id"]}],
            },
            "metrics": [
                {
                    "name": "retrieval_hit",
                    "value": 1 if retrieval_hit else 0,
                    "passed": retrieval_hit,
                    "threshold": 1.0,
                    "notes": "At least one SciFact qrel document appears inside top-k.",
                }
            ],
            "failures": [],
            "diagnostic_notes": [
                {
                    "stage": "retrieval",
                    "note": (
                        f"Deterministic BM25 retrieved {top_k} documents; "
                        f"qrels hit={retrieval_hit}."
                    ),
                }
            ],
        }
    )


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def _query_sort_key(query_id: str) -> tuple[int, str]:
    try:
        return (int(query_id), query_id)
    except ValueError:
        return (sys.maxsize, query_id)


if __name__ == "__main__":
    raise SystemExit(main())
