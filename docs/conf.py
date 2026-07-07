# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

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
# Optional backends that need system libraries or are not pip-installable; mock
# them so autodoc can still import the modules that reference them.
autodoc_mock_imports = ["uda", "ldap", "easyad", "keycloak"]

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


def setup(app):
    app.connect("config-inited", _run_generators)
