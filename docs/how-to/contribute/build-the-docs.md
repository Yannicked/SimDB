# Build the documentation

This documentation is built with [Sphinx](https://www.sphinx-doc.org/) and
[MyST](https://myst-parser.readthedocs.io/) (Markdown), using the
`sphinx-immaterial` theme. It is published on
[Read the Docs](https://simdb.readthedocs.io/).

## Install the docs toolchain

From a checkout, install the `build-docs` extra. Because the build imports and
runs `simdb`, install the package itself too:

```bash
pip install -e ".[build-docs]"
```

## Build

```bash
cd docs
make html
```

The site is written to `docs/_build/html`. Open `docs/_build/html/index.html`
in a browser. Use `make clean` to remove the build output and generated files.

## How the build works

The documentation source lives directly in `docs/` (there is no separate copy
step). Two parts are generated automatically at build time by `conf.py`, so they
never drift from the code:

- **`reference/cli.md`** is rendered from `cli.md.in` by capturing the live
  `simdb --help` output (`generate_cli_docs.py`).
- **`reference/python-api/`** is produced by `sphinx-apidoc` from the source
  docstrings.

Both are git-ignored; do not commit them. Because they are generated from the
installed package, `simdb` must be importable in the build environment (it is,
if you installed the package as shown above).

## Writing conventions

- Pages are Markdown (MyST). Use `{toctree}`, `{note}`, `{warning}`, and similar
  fenced directives.
- The documentation follows a [Diataxis](https://diataxis.fr/) structure:
  tutorials, how-to guides, reference, and explanation. Put new pages in the
  section that matches their purpose and add them to the toctree in
  `docs/index.md`.
- Cross-link between pages with relative Markdown links.
