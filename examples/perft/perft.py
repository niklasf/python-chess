#!/usr/bin/env python3

"""
Run perft test to check correctness and speed of the legal move generator.
"""

import multiprocessing
import multiprocessing.pool
import functools
import time
import argparse
import sys

from typing import Callable, Iterator, Optional, TextIO, Type

import chess
import chess.variant


def perft(depth: int, board: chess.Board) -> int:
    if depth == 1:
        return board.legal_moves.count()
    elif depth > 1:
        count = 0

        for move in board.legal_moves:
            board.push(move)
            count += perft(depth - 1, board)
            board.pop()

        return count
    else:
        return 1


def parallel_perft(pool: multiprocessing.pool.Pool, depth: int, board: chess.Board) -> int:
    if depth == 1:
        return board.legal_moves.count()
    elif depth > 1:
        def successors(board: chess.Board) -> Iterator[chess.Board]:
            for move in board.legal_moves:
                board_after = board.copy(stack=False)
                board_after.push(move)
                yield board_after

        return sum(pool.imap_unordered(functools.partial(perft, depth - 1), successors(board)))
    else:
        return 1


def sdiv(a: float, b: float) -> float:
    try:
        return a / b
    except ZeroDivisionError:
        return float("Inf")


def main(perft_file: TextIO, VariantBoard: Type[chess.Board], perft_f: Callable[[int, chess.Board], int], max_depth: Optional[int], max_nodes: Optional[int]) -> None:
    current_id = None
    board = VariantBoard(chess960=True)
    column = 0
    total_nodes = 0
    start_time = time.perf_counter()

    for line in perft_file:
        # Skip comments and empty lines.
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("%"):
            continue

        cmd, arg = line.split(None, 1)
        if cmd == "id":
            current_id = arg
        elif cmd == "epd":
            board.set_epd(arg)
        elif cmd == "perft":
            depth, nodes = map(int, arg.split(None, 1))
            if (max_depth and depth > max_depth) or (max_nodes and nodes > max_nodes):
                continue

            perft_nodes = perft_f(depth, board)
            if nodes != perft_nodes:
                print()
                print()
                print(f" !!! Failure in {current_id or '<no-name>'}")
                print(f"     epd {board.epd()}")
                print(f"     perft {depth} {nodes} (got {perft_nodes} instead)")
                print()
                print(board)
                print()
                for move in sorted(board.legal_moves, key=lambda m: m.uci()):
                    board.push(move)
                    print(f"{move}: {perft_f(depth - 1, board)}")
                    board.pop()
                sys.exit(1)

            total_nodes += perft_nodes
            print(".", end="", flush=True)
            column += 1

            if column >= 40:
                column = 0
                sys.stdout.write(f" nodes {total_nodes} nps {sdiv(total_nodes, time.perf_counter() - start_time):.0f}\n")
        else:
            print()
            print("Unknown command:", cmd, arg)
            sys.exit(2)

    if column:
        sys.stdout.write(f" nodes {total_nodes} nps {sdiv(total_nodes, time.perf_counter() - start_time):.0f}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("perft", nargs="+", type=argparse.FileType("r"),
        help="Perft test suite(s)")
    parser.add_argument("--max-depth", type=int, help="Skip deeper perft tests")
    parser.add_argument("--max-nodes", type=int, default=1000000,
        help="Skip larger perft tests. Defaults to 1000000")
    parser.add_argument("-v", "--variant", default="standard",
        help="Use a non-standard chess variant")
    parser.add_argument("-t", "--threads", type=int, help="Number of threads")

    args = parser.parse_args()
    VariantBoard = chess.variant.find_variant(args.variant)

    if args.threads == 1:
        perft_f = perft
    else:
        pool = multiprocessing.Pool(args.threads)
        perft_f = functools.partial(parallel_perft, pool)

    for perft_file in args.perft:
        print("###", perft_file.name)
        main(perft_file, VariantBoard, perft_f, args.max_depth, args.max_nodes)
