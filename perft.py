#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# A test set of more than 6000 positions. The perft node count for a given depth
# is the number of legal move sequences from that position. This can be used
# to check correctness and speed of the legal move generator.
#
# The original test suite was created by Marcel van Kervinck and found at
# http://marcelk.net/rookie/nostalgia/v3/perft-random.epd

from __future__ import print_function

import chess
import unittest
import sys


def perft(board, depth):
    if depth > 1:
        count = 0

        for move in board.legal_moves:
            board.push(move)
            count += perft(board, depth - 1)
            board.pop()

        return count
    elif depth == 1:
        return len(board.legal_moves)
    else:
        return 1


def into_check_perft(board, depth):
    if depth >= 1:
        count = 0

        for move in board.pseudo_legal_moves:
            if board.is_into_check(move):
                continue

            board.push(move)
            count += into_check_perft(board, depth - 1)
            board.pop()

        return count
    else:
        return 1


def debug_perft(board, depth):
    if depth >= 1:
        count =  0

        for move in board.pseudo_legal_moves:
            assert move in board.pseudo_legal_moves, (move, board)

            if board.is_into_check(move):
                assert move not in board.legal_moves, (move, board)
                continue

            assert move in board.legal_moves, (move, board)

            board.push(move)
            count += debug_perft(board, depth - 1)
            board.pop()

        return count
    else:
        return 1


class PerftTestCase(unittest.TestCase):

    def execute_test(self, method, maxnodes):
        current_id = None
        board = chess.Board()

        for line in open("data/perft-random.epd"):
            s = line.split()
            if not s:
                pass
            elif s[0] == "id":
                current_id = s[1]
                sys.stdout.write(".")
                sys.stdout.flush()
            elif s[0] == "epd":
                board.set_epd(" ".join(s[1:]))
            elif s[0] == "perft":
                depth = int(s[1])
                nodes = int(s[2])
                if nodes < maxnodes:
                    self.assertEqual(method(board, depth), nodes, current_id)

        sys.stdout.write("\n")
        sys.stdout.flush()

    def test_fast(self):
        self.execute_test(perft, 1000)

    def test_into_check(self):
        self.execute_test(into_check_perft, 1000)

    def test_debug(self):
        self.execute_test(debug_perft, 100)

    def test_speed(self):
        self.execute_test(perft, 10000)


if __name__ == "__main__":
    unittest.main()
