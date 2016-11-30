#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""List all Chess960 starting positions."""

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
