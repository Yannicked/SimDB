# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import logging as pylogging
import os
import subprocess
import sys
from pathlib import Path

from sphinx.util import logging

# Make the SimDB package importable for autodoc.
sys.path.insert(0, os.path.abspath("../src"))
import simdb  # noqa: E402  (must follow the sys.path insert above)

logger = logging.getLogger(__name__)
DOCS_DIR = Path(__file__).parent.resolve()

# -- Project information -----------------------------------------------------

project = "IMAS Simulation Database Management Tool"
copyright = "2018-2025, ITER Organization"
author = "ITER Organization"

version = ".".join(simdb.version.split(".")[:2])
project += f" Version {version}"
release = simdb.__version__

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "myst_parser",
    "sphinx_immaterial",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

master_doc = "index"
language = "en"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
pygments_style = None

# -- MyST (Markdown) configuration -------------------------------------------

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "substitution",
]
# Auto-generate anchors for headings up to level 3 so that cross-document links
# such as ``[](../reference/manifest-format.md#metadata)`` resolve.
myst_heading_anchors = 3

# -- Autodoc configuration ---------------------------------------------------

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}
# Several classes wrap third-party bases (SQLAlchemy Session/TypeDecorator,
# Cerberus Validator) and override methods without their own docstring. Do not
# fall back to the base class docstring for those: the inherited text is full of
# SQLAlchemy/Cerberus-specific roles and cross-references (``:term:``, ``:ref:``,
# ``:paramref:``) that do not resolve in these docs and produce warnings.
autodoc_inherit_docstrings = False
# Optional backends that need system libraries or are not pip-installable; mock
# them so autodoc can still import the modules that reference them.
autodoc_mock_imports = ["uda", "ldap", "easyad", "keycloak"]

# The auto-generated Python API reference produces a handful of warnings that are
# inherent to running autodoc/apidoc over code that subclasses SQLAlchemy and
# Cerberus, and cannot be fixed in the source without disproportionate effort:
#   * ref.python  - apidoc's per-module pages (``-e``) create duplicate targets
#     for re-exported names (e.g. ``Simulation``, the ``type`` fields), so bare
#     cross-references are ambiguous.
#   * ref.param / ref.ref - stray SQLAlchemy type-var / label references.
#   * misc.highlighting_failure - a Cerberus ``types_mapping`` default value
#     whose repr is not valid Python and so cannot be syntax-highlighted.
# None of these come from authored content (the hand-written pages carry no
# Python-domain cross-references).
suppress_warnings = [
    "ref.python",
    "ref.param",
    "ref.ref",
    "misc.highlighting_failure",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# -- HTML output -------------------------------------------------------------

html_theme = "sphinx_immaterial"
html_title = "SimDB"
html_static_path = ["_static"]

html_theme_options = {
    "palette": [
        {
            "media": "(prefers-color-scheme: light)",
            "scheme": "default",
            "primary": "blue",
            "accent": "light-blue",
            "toggle": {
                "icon": "material/lightbulb-outline",
                "name": "Switch to dark mode",
            },
        },
        {
            "media": "(prefers-color-scheme: dark)",
            "scheme": "slate",
            "primary": "blue",
            "accent": "light-blue",
            "toggle": {
                "icon": "material/lightbulb",
                "name": "Switch to light mode",
            },
        },
    ],
    "features": [
        "navigation.tabs",
        "navigation.top",
        "toc.follow",
        "content.action.edit",
        "search.share",
    ],
    "repo_url": "https://github.com/iterorganization/SimDB",
    "repo_name": "SimDB",
    # Show an "edit this page" link. Joined onto repo_url; docs live under docs/
    # on the default branch.
    "edit_uri": "blob/develop/docs",
}

htmlhelp_basename = "simdb"

# -- Generated documentation -------------------------------------------------
#
# reference/cli.md and reference/python-api/* are generated at build time (from
# `simdb --help` and sphinx-apidoc) so they cannot drift from the code. Running
# them from config-inited keeps `sphinx-build` self-contained, including on RTD.


def _generate_cli_reference() -> None:
    script = DOCS_DIR / "generate_cli_docs.py"
    subprocess.run([sys.executable, str(script)], check=True, cwd=DOCS_DIR)


def _generate_api_reference() -> None:
    from sphinx.ext import apidoc

    out_dir = DOCS_DIR / "reference" / "python-api"
    # apidoc overwrites but never removes pages for modules that no longer exist,
    # so a renamed/deleted module would leave a stale ``.rst`` that fails to
    # import. Clear the generated pages first for a clean, reproducible tree.
    for stale in out_dir.glob("simdb*.rst"):
        stale.unlink()
    apidoc.main(
        ["-f", "-e", "-M", "-o", str(out_dir), str(DOCS_DIR / ".." / "src" / "simdb")]
    )
    # ``modules.rst`` is the apidoc-generated top-level toc; we use our own
    # hand-written ``index.md`` instead, so drop it to avoid an orphan warning.
    (out_dir / "modules.rst").unlink(missing_ok=True)


def _run_generators(app, config) -> None:
    for name, fn in (("CLI reference", _generate_cli_reference),
                     ("API reference", _generate_api_reference)):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - degrade gracefully
            logger.warning(
                "Could not generate %s (is `simdb` installed in this "
                "environment?): %s",
                name,
                exc,
            )


class _SuppressParameterNameMismatch(pylogging.Filter):
    """Drop sphinx-immaterial's "Parameter name X does not match ..." warning.

    sphinx-immaterial cross-links each documented parameter to the member's
    signature. Pydantic/Cerberus-decorated members (manifest models, the Cerberus
    ``CustomValidator``) expose a wrapped runtime signature that autodoc cannot
    match, so the check fires spuriously. The warning is emitted without a
    warning type, so it cannot be silenced through ``suppress_warnings``; filter
    it out at the logging layer instead.
    """

    def filter(self, record: pylogging.LogRecord) -> bool:
        return "does not match any of the parameters" not in record.getMessage()


def setup(app):
    pylogging.getLogger(
        "sphinx.sphinx_immaterial.apidoc.python.parameter_objects"
    ).addFilter(_SuppressParameterNameMismatch())
    app.connect("config-inited", _run_generators)
