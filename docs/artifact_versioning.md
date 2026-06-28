# Artifact Versioning

RAG Observatory is local-first, but reproducible research eventually needs a
clear boundary between reviewable source code, large immutable artifacts, and
generated outputs. DVC is optional: the core package, fixtures, and tests must
continue to work without DVC or remote access.

## Storage Policy

| Artifact | Store In | Reason |
| --- | --- | --- |
| Source code, docs, configs, small synthetic fixtures | Git | Reviewable and small enough for normal diffs |
| Trace schema examples and reviewed toy cases | Git | Required for deterministic tests |
| Large corpora, retrieval indexes, model weights, non-toy trace exports | DVC | Content-addressed, versioned, too large for Git |
| Benchmark outputs, reports, temporary run directories | Generated output directories | Reproducible from code and inputs |
| Secrets, cloud credentials, local tokens | Local environment only | Must never be committed |

The current `.gitignore` keeps large artifact directories out of Git while
allowing top-level `.dvc` pointer files under `data/raw/` and `data/processed/`.

## Optional DVC Setup

Install DVC only when working with large experiment artifacts:

```bash
python -m pip install "dvc[s3]"
```

The repository includes a safe local default remote:

```text
../rag-observatory-dvc
```

This path is useful for local smoke tests and does not contain credentials. For
shared storage, add remotes without credentials in Git:

```bash
dvc remote add shared s3://example-bucket/rag-observatory
dvc remote modify --local shared access_key_id <access-key>
dvc remote modify --local shared secret_access_key <secret-key>
```

Only `.dvc/config` should be committed. User-specific settings belong in
`.dvc/config.local`, which is ignored.

## Reproducible Smoke Artifact

The committed `dvc.yaml` defines one generated benchmark artifact:

```bash
dvc repro trace_io_smoke
```

It runs:

```bash
python scripts/benchmark_trace_io.py --sizes 1000 --output outputs/benchmarks/trace-io-dvc
```

The output directory is generated, ignored by Git, and can be tracked by DVC if
the workflow later needs a locked benchmark artifact:

```bash
dvc add outputs/benchmarks/trace-io-dvc
git add outputs/benchmarks/trace-io-dvc.dvc .gitignore
```

Do not commit the generated benchmark directory itself.

## Adding Large Artifacts

Use DVC for non-toy artifacts such as corpora, indexes, model weights, or large
trace exports:

```bash
dvc add data/raw/msmarco-validation
git add data/raw/msmarco-validation.dvc .gitignore
dvc push
git commit -m "data: track msmarco validation artifact"
```

For processed artifacts:

```bash
dvc add data/processed/retrieval-index
git add data/processed/retrieval-index.dvc .gitignore
dvc push
```

Pointer files should be reviewed like code because they bind a code revision to
a content hash.

## Clean Checkout Workflow

From a fresh checkout:

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests
```

Core tests should pass without DVC. To restore large artifacts:

```bash
python -m pip install "dvc[s3]"
dvc pull
dvc checkout
```

If a remote is unavailable, keep working on code and toy fixtures. Document the
missing artifact and rerun `dvc pull` after credentials or network access are
fixed.

## Failure Recovery

If DVC state becomes confusing:

```bash
dvc status
dvc doctor
dvc checkout
```

If generated outputs are stale, delete only the generated directory and rerun
the stage:

```bash
dvc repro trace_io_smoke
```

Do not repair DVC issues by committing large files to Git.
