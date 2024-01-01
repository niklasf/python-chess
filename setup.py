#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import platform
import re
import sys
import textwrap

import setuptools


if sys.version_info < (3, ):
    raise ImportError(textwrap.dedent("""\
        You are trying to install python-chess on Python 2.

        The last compatible branch was 0.23.x, which was supported until the
        end of 2018. Consider upgrading to Python 3.
        """))

if sys.version_info < (3, 8):
    raise ImportError(textwrap.dedent("""\
        You are trying to install python-chess.

        Since version 1.11.0, python-chess requires Python 3.8 or later.
        Since version 1.0.0, python-chess requires Python 3.7 or later.
        """))

import chess


def read_description():
    """
    Reads the description from README.rst and substitutes mentions of the
    latest version with a concrete version number.
    """
    with open(os.path.join(os.path.dirname(__file__), "README.rst"), encoding="utf-8") as f:
        description = f.read()

    # Link to the documentation of the specific version.
    description = description.replace(
        "//python-chess.readthedocs.io/en/latest/",
        "//python-chess.readthedocs.io/en/v{}/".format(chess.__version__))

    # Use documentation badge for the specific version.
    description = description.replace(
        "//readthedocs.org/projects/python-chess/badge/?version=latest",
        "//readthedocs.org/projects/python-chess/badge/?version=v{}".format(chess.__version__))

    # Remove doctest comments.
    description = re.sub(r"\s*# doctest:.*", "", description)

    return description


setuptools.setup(
    name="chess",
    version=chess.__version__,
    author=chess.__author__,
    author_email=chess.__email__,
    description=chess.__doc__.replace("\n", " ").strip(),
    long_description=read_description(),
    long_description_content_type="text/x-rst",
    license="GPL-3.0+",
    keywords="chess fen epd pgn polyglot syzygy gaviota uci xboard",
    url="https://github.com/niklasf/python-chess",
    packages=["chess"],
    test_suite="test",
    zip_safe=False,  # For mypy
    package_data={
        "chess": ["py.typed"],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Games/Entertainment :: Board Games",
        "Topic :: Games/Entertainment :: Turn Based Strategy",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Typing :: Typed",
    ],
    project_urls={
        "Documentation": "https://python-chess.readthedocs.io",
    },
    obsoletes=["python_chess"],
)
