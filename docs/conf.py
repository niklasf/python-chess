# -*- coding: utf-8 -*-

import asyncio
import sys
import os

import sphinx
import sphinx.ext.autodoc
import sphinx.domains.python

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
copyright = "2014–2019, Niklas Fiekas"

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

# Mark coroutine functions and methods.
def setup(app):
    app.add_directive_to_domain("py", "coroutine", PyCoroutineFunction)
    app.add_directive_to_domain("py", "coroutinemethod", PyCoroutineMethod)
    app.add_autodocumenter(FunctionDocumenter)
    app.add_autodocumenter(MethodDocumenter)

    return {
        "version": "1.0",
        "parallel_read_safe": True,
    }

class PyCoroutineMixin:
    def handle_signature(self, sig, signode):
        ret = super().handle_signature(sig, signode)
        signode.insert(0, sphinx.addnodes.desc_annotation("coroutine ", "coroutine "))
        return ret

class PyCoroutineFunction(PyCoroutineMixin, sphinx.domains.python.PyModulelevel):
    def run(self):
        self.name = "py:function"
        return super().run()

class PyCoroutineMethod(PyCoroutineMixin, sphinx.domains.python.PyClassmember):
    def run(self):
        self.name = "py:method"
        return super().run()

class FunctionDocumenter(sphinx.ext.autodoc.FunctionDocumenter):
    def import_object(self):
        ret = super().import_object()
        if ret and asyncio.iscoroutinefunction(self.parent.__dict__.get(self.object_name)):
            self.directivetype = "coroutine"
        return ret

class MethodDocumenter(sphinx.ext.autodoc.MethodDocumenter):
    def import_object(self):
        ret = super().import_object()
        if ret and asyncio.iscoroutinefunction(self.parent.__dict__.get(self.object_name)):
            self.directivetype = "coroutinemethod"
        return ret
