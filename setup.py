#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2018 Niklas Fiekas <niklas.fiekas@backscattering.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import io
import os
import platform
import re
import sys

import setuptools


if sys.version_info < (3, ):
    raise ImportError(
        """You are installing python-chess on Python 2.

Python 2 support has been dropped. Consider upgrading to Python 3, or using
the 0.23.x branch, which will be maintained until the end of 2018.
""")

import chess


def read_description():
    """
    Reads the description from README.rst and substitutes mentions of the
    latest version with a concrete version number.
    """
    description = io.open(os.path.join(os.path.dirname(__file__), "README.rst"), encoding="utf-8").read()

    # Link to the documentation of the specific version.
    description = description.replace(
        "//python-chess.readthedocs.io/en/latest/",
        "//python-chess.readthedocs.io/en/v{}/".format(chess.__version__))

    # Use documentation badge for the specific version.
    description = description.replace(
        "//readthedocs.org/projects/python-chess/badge/?version=latest",
        "//readthedocs.org/projects/python-chess/badge/?version=v{}".format(chess.__version__))

    # Show Travis CI build status of the concrete version.
    description = description.replace(
        "//travis-ci.org/niklasf/python-chess.svg?branch=master",
        "//travis-ci.org/niklasf/python-chess.svg?branch=v{}".format(chess.__version__))

    # Remove doctest comments.
    description = re.sub("\s*# doctest:.*", "", description)

    return description


def extra_dependencies():
    return {
        "test": ["spur"] if platform.python_implementation() == "CPython" else [],
    }


setuptools.setup(
    name="python-chess",
    version=chess.__version__,
    author=chess.__author__,
    author_email=chess.__email__,
    description=chess.__doc__.replace("\n", " ").strip(),
    long_description=read_description(),
    license="GPL3",
    keywords="chess fen pgn polyglot syzygy gaviota uci xboard",
    url="https://github.com/niklasf/python-chess",
    packages=["chess"],
    test_suite="test",
    python_requires=">=3.4",
    extras_require=extra_dependencies(),
    tests_require=extra_dependencies().get("test"),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Games/Entertainment :: Board Games",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
