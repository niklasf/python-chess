#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2016 Niklas Fiekas <niklas.fiekas@backscattering.de>
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

from __future__ import print_function

import sys
import timeit
import chess


def main(bench_only=False):
    board = chess.Board.empty(chess960=True)

    for sharnagl in range(0, 960):
        board.set_chess960_pos(sharnagl)

        if not bench_only:
            print(str(sharnagl).rjust(3), board.fen())


if __name__ == "__main__":
    if "bench" in sys.argv:
        print(timeit.timeit(
            stmt="main(bench_only=True)",
            setup="from __main__ import main",
            number=10))
    else:
        main()
