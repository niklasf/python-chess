import asyncio
import sys
import os
import typing

def _rewrite(path):
    """Rewrite source file to postpone evaluation of type annotations."""
    with open(path) as f:
        contents = f.read()
    with open(path, "w") as f:
        f.write("from __future__ import annotations\n")
        f.write(contents)

if "READTHEDOCS" in os.environ:
    _rewrite("../chess/engine.py")
    _rewrite("../chess/gaviota.py")
    _rewrite("../chess/__init__.py")
    _rewrite("../chess/pgn.py")
    _rewrite("../chess/polyglot.py")
    _rewrite("../chess/svg.py")
    _rewrite("../chess/syzygy.py")
    _rewrite("../chess/variant.py")

# Do not resolve type aliases in annotations.
typing.get_type_hints = lambda obj, *_unused: obj

# Import the chess module.
sys.path.insert(0, os.path.abspath('..'))
import chess

# Autodoc.
extensions = ["sphinx.ext.autodoc", "sphinx.ext.viewcode"]
autodoc_member_order = 'bysource'

# The suffix of source filenames.
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# General information about the project.
project = "python-chess"
copyright = "2014–2020, Niklas Fiekas"

# The version.
version = chess.__version__
release = chess.__version__

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ["_build"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# The theme to use for HTML and HTML Help pages. See the documentation for
# a list of builtin themes.
html_theme = "default"
