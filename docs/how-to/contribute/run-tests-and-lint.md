# Run tests, linting, and type checks

SimDB's CI runs four checks on every push and pull request, against Python 3.11,
3.12, and 3.13. Run them locally before opening a pull request.

## Tests

From the project root:

```bash
pytest
```

Tests run with coverage (configured in `pyproject.toml`).

## Formatting and linting (Ruff)

SimDB uses [Ruff](https://docs.astral.sh/ruff/) for both formatting and linting.
The configuration is in `pyproject.toml`.

```bash
python -m ruff format --check    # check formatting
python -m ruff format            # auto-format
python -m ruff check             # lint
python -m ruff check --fix       # auto-fix lint issues
```

## Type checking (Ty)

SimDB uses [Ty](https://github.com/astral-sh/ty) for static type checking:

```bash
python -m ty check src
```

## CI order

The pipeline (`.github/workflows/build_and_test.yml`) runs, in order:

1. Formatting (`ruff format --check`)
2. Linting (`ruff check`)
3. Type checking (`ty check src`)
4. Tests (`pytest` with coverage)

Make sure all four pass locally first.
