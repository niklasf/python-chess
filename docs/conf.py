import sys
import os
import typing

# Do not resolve these.
autodoc_type_aliases = {
    "Square": "chess.Square",
    "Color": "chess.Color",
    "PieceType": "chess.PieceType",
    "Bitboard": "chess.Bitboard",
    "IntoSquareSet": "chess.IntoSquareSet",
}

# Hack to not resolve autodoc_type_aliases before Sphinx 3.3.
# See https://github.com/sphinx-doc/sphinx/issues/6518.
_get_type_hints = typing.get_type_hints
def get_type_hints(obj, globalns=None, localns=None):
    if localns is None:
        localns = {}
    localns.update(autodoc_type_aliases)
    return _get_type_hints(obj, globalns, localns)
typing.get_type_hints = get_type_hints

# Import the chess module.
sys.path.insert(0, os.path.abspath(".."))
import chess

# Autodoc.
extensions = ["sphinx.ext.autodoc", "sphinx.ext.viewcode"]
autodoc_member_order = "bysource"

# The suffix of source filenames.
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# General information about the project.
project = "python-chess"
copyright = "2014–2021, Niklas Fiekas"

# The version.
version = chess.__version__
release = chess.__version__

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ["_build"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# The theme to use for HTML and HTML Help pages. See the documentation for
# a list of built-in themes.
html_theme = "default"
