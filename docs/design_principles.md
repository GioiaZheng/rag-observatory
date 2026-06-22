# Design Principles

`rag-observatory` is built around trace-level diagnosis rather than pipeline
construction.

## Principles

- Keep the trace schema explicit and serializable.
- Prefer deterministic fixtures before model integrations.
- Keep the command line workflow useful before adding a UI.
- Store reproducible artifacts, not ad hoc notebook state.
- Treat retrieval, reranking, generation, and evaluation as observable stages.
- Keep adapters thin so the core remains independent of any one RAG system.

## Boundary

The project may include minimal toy runs and adapters, but the durable asset is
the diagnostic layer: schemas, taxonomy, reports, and comparison tools.
