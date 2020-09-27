#!/usr/bin/env python3

"""List all Chess960 starting positions."""

import sys
import timeit
import chess


def main(bench_only: bool = False) -> None:
    board = chess.Board.empty(chess960=True)

    for scharnagl in range(0, 960):
        board.set_chess960_pos(scharnagl)

        if not bench_only:
            print(str(scharnagl).rjust(3), board.fen())


if __name__ == "__main__":
    if "bench" in sys.argv:
        print(timeit.timeit(
            stmt="main(bench_only=True)",
            setup="from __main__ import main",
            number=10))
    else:
        main()
