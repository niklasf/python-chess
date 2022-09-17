import sys
import os

# Import the chess module.
sys.path.insert(0, os.path.abspath(".."))
import chess

# Do not resolve these.
autodoc_type_aliases = {
    "Square": "chess.Square",
    "Color": "chess.Color",
    "PieceType": "chess.PieceType",
    "Bitboard": "chess.Bitboard",
    "IntoSquareSet": "chess.IntoSquareSet",
}

# Autodoc.
extensions = ["sphinx.ext.autodoc", "sphinx.ext.viewcode", "sphinx.ext.intersphinx"]
autodoc_member_order = "bysource"
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# The suffix of source filenames.
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# General information about the project.
project = "python-chess"
copyright = "2014–2022, Niklas Fiekas"

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
