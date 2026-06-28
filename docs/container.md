# Container Image

The Docker image provides a clean execution path for package installation,
unit tests, and CLI smoke tests before heavier system dependencies are added.

## Base Image Policy

The image is pinned to:

```text
python:3.10.19-slim-bookworm
```

This matches the lowest Python version supported by the package and the
non-container CI job. Patch updates should be made deliberately in a small PR
that rebuilds the image and reruns the unit tests. The image should stay CPU
only until the project has a real FAISS, CUDA, or GPU dependency.

## Build

```bash
docker build --tag rag-observatory:test .
```

The `.dockerignore` excludes local caches, generated outputs, DVC cache data,
large data directories, virtual environments, and database or index files.

## Test

Run the default test command:

```bash
docker run --rm rag-observatory:test
```

Run a CLI smoke test against a synthetic fixture:

```bash
docker run --rm rag-observatory:test rag-observe report tests/fixtures/toy_runs/unsupported_answer.json --output /tmp/unsupported_answer.md
```

## Boundaries

The container is not a deployment image and does not publish to a registry. It
does not include credentials, large datasets, DVC remotes, FAISS, CUDA, or
external services. Those should be added only after the project has a real
multi-service or system-dependency workflow.
