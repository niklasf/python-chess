#!/usr/bin/python3

import chess
import unittest

class MoveTestCase(unittest.TestCase):

    def test_uci_parsing(self):
        self.assertEqual(chess.Move.from_uci("b5c7").uci(), "b5c7")
        self.assertEqual(chess.Move.from_uci("e7e8q").uci(), "e7e8q")


class BitboardTestCase(unittest.TestCase):

    def test_move_making(self):
        bitboard = chess.Bitboard()
        bitboard.push(chess.Move(chess.E2, chess.E4))

if __name__ == "__main__":
    unittest.main()
