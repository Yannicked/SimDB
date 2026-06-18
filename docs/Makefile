# Minimal makefile for Sphinx documentation.
#
# The documentation source lives directly in this directory (docs/). The CLI
# reference and Python API pages are generated automatically by conf.py during
# the build, so `make html` produces a complete site with no extra steps.

SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

clean:
	rm -rf "$(BUILDDIR)"
	rm -f reference/cli.md
	rm -f reference/python-api/simdb*.rst reference/python-api/modules.rst

.PHONY: help clean Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
