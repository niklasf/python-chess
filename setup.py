#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2014 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
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

import distutils
import os
import setuptools

def read(filename):
    """Utility function that returns a files contents."""
    return open(os.path.join(os.path.dirname(__file__), filename)).read()

setuptools.setup(
    name="python-chess",
    version="0.1.0",
    author="Niklas Fiekas",
    author_email="niklas.fiekas@tu-clausthal.de",
    description="A chess library.",
    long_description=read("README.rst"),
    license="GPL3",
    keywords="chess fen pgn polyglot",
    url="http://github.com/niklasf/python-chess",
    packages=["chess"],
    scripts=["scripts/ecotool", "scripts/python-chess"],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Games/Entertainment :: Board Games",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
