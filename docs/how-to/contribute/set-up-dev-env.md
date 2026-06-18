# Set up a development environment

This guide sets up SimDB for local development.

## Clone and check out

```bash
git clone https://github.com/iterorganization/SimDB.git
cd SimDB
git checkout develop
```

`develop` is the main development branch; open pull requests against it.

## Create a virtual environment and install

Install SimDB with the `dev` dependency group, which pulls in everything needed
for testing, linting, type checking, and running the server:

```bash
python3 -m venv venv --prompt SimDB
source venv/bin/activate
pip install -e . --group dev
```

Alternatively, use [uv](https://docs.astral.sh/uv/) to install all
dependencies:

```bash
uv sync
```

## Verify

```bash
simdb --version
pytest
```

## Next steps

- [Run tests, linting, and type checks](run-tests-and-lint.md).
- [Run database migrations](run-migrations.md).
- [Build the documentation](build-the-docs.md).
