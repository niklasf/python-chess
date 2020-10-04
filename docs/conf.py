import sys
import os
import typing

# Do not resolve these type aliases.
autodoc_type_aliases = {
    "Square": "chess.Square",
    "Color": "chess.Color",
    "PieceType": "chess.PieceType",
    "Bitboard": "chess.Bitboard",
    "IntoSquareSet": "chess.IntoSquareSet",
}

# Use a hack to not resolve autodoc_type_aliases before Sphinx 3.3.
# See https://github.com/sphinx-doc/sphinx/issues/6518.
_get_type_hints = typing.get_type_hints
def get_type_hints(obj, globalns=None, localns=None):
    if localns is None:
        localns = {}
    localns.update(autodoc_type_aliases)
    return _get_type_hints(obj, globalns, localns)
typing.get_type_hints = get_type_hints

# Import the chess module.
sys.path.insert(0, os.path.abspath('..'))
import chess

# Autodocument the project and order the output by source.
extensions = ["sphinx.ext.autodoc", "sphinx.ext.viewcode"]
autodoc_member_order = "bysource"

# Add a suffix for source filenames.
source_suffix = ".rst"

# Name the master toctree document.
master_doc = "index"

# Add general information about the project.
project = "python-chess"
copyright = "2014–2020, Niklas Fiekas"

# Add a version number for the project.
version = chess.__version__
release = chess.__version__

# Exclude these patterns, relative to source directory, that match files and
# directories when looking for source files.
exclude_patterns = ["_build"]

# Use a Pygments (syntax highlighting) style.
pygments_style = "sphinx"

# Use a theme to use for HTML and HTML Help pages. See the documentation for
# a list of built-in themes.
html_theme = "default"
