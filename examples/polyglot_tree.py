#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Print a polyglot opening book in tree form."""

import chess
import chess.polyglot
import argparse


def print_tree(args, visited, level=0):
    if level >= args.depth:
        return

    zobrist_hash = chess.polyglot.zobrist_hash(args.board)
    if zobrist_hash in visited:
        return

    visited.add(zobrist_hash)

    for entry in args.book.find_all(zobrist_hash):
        print("{}├─ \033[1m{}\033[0m (weight: {}, learn: {})".format(
            "|  " * level,
            args.board.san(entry.move()),
            entry.weight,
            entry.learn))

        args.board.push(entry.move())
        print_tree(args, visited, level + 1)
        args.board.pop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book", type=chess.polyglot.open_reader)
    parser.add_argument("--depth", type=int, default=5)
    parser.add_argument("--fen", type=chess.Board, default=chess.Board(), dest="board")
    args = parser.parse_args()
    print_tree(args, visited=set())
