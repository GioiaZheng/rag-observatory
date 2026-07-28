# Contributing

Thank you for considering a contribution to `rag-observatory`.

The project is intentionally narrow: it models, validates, compares, and
reports on RAG execution traces. Pipeline implementations belong here only
when they are needed as a small fixture, example, or ingestion adapter.

## Before opening a pull request

- Search the existing issues and pull requests.
- Open an issue before starting a broad API, schema, or architecture change.
- Keep each pull request focused on one change.
- Use public, synthetic, or fully sanitized examples.

Do not commit credentials, proprietary data, private prompts, production
traces, or generated experiment dumps.

## Development setup

Python 3.10 or newer is required.

```bash
git clone https://github.com/GioiaZheng/rag-observatory.git
cd rag-observatory
python -m venv .venv
python -m pip install -e ".[dev]"
pre-commit install
```

Activate the virtual environment using the command appropriate for your shell.

## Checks

Run the same core checks used by CI:

```bash
ruff check .
ruff format --check .
mypy src
python -m unittest discover -s tests
pre-commit run --all-files
```

For changes that affect packaging, also run:

```bash
python -m pip install build twine
python -m build
python -m twine check --strict dist/*
python scripts/verify_distribution.py dist/
```

## Tests and evidence

- Add a regression test for a bug fix.
- Update fixtures when a trace contract or report shape changes.
- Keep fixtures small enough to review in Git.
- Separate observed results from planned work or hypotheses.
- Do not present synthetic examples as dataset-scale evidence.

Documentation changes should link to the implementation, fixture, report, or
issue that supports the claim when one exists.

## Pull requests

Describe:

1. what changed and why;
2. the checks you ran;
3. any compatibility, data, or privacy implications;
4. what remains out of scope.

The pull request template contains a short checklist. A maintainer may ask for
a smaller scope when a change combines unrelated behavior.

## Security reports

Do not open a public issue for a suspected vulnerability. Follow
[SECURITY.md](SECURITY.md) instead.
