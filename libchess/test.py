#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import libchess

class PieceTestCase(unittest.TestCase):
    def test(self):
        black_pawn = libchess.Piece("p")
        self.assertEqual(black_pawn.type, "p")
        self.assertEqual(black_pawn.symbol, "p")
        self.assertEqual(black_pawn.color, "b")

        white_queen = libchess.Piece("Q")
        self.assertEqual(white_queen.type, "q")
        self.assertEqual(white_queen.symbol, "Q")
        self.assertEqual(white_queen.color, "w")

        self.assertEqual(black_pawn, libchess.Piece("p"))

if __name__ == "__main__":
    unittest.main()
