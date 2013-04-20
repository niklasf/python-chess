#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import libchess

class PieceTestCase(unittest.TestCase):
    def test(self):
        # Properties of a black piece.
        black_pawn = libchess.Piece("p")
        self.assertEqual(black_pawn.type, "p")
        self.assertEqual(black_pawn.symbol, "p")
        self.assertEqual(black_pawn.color, "b")
        self.assertEqual(black_pawn.full_color, "black")
        self.assertEqual(black_pawn.full_type, "pawn")

        # Properties of a white piece.
        white_queen = libchess.Piece("Q")
        self.assertEqual(white_queen.type, "q")
        self.assertEqual(white_queen.symbol, "Q")
        self.assertEqual(white_queen.color, "w")
        self.assertEqual(white_queen.full_color, "white")
        self.assertEqual(white_queen.full_type, "queen")

        # Comparison.
        self.assertEqual(black_pawn, libchess.Piece("p"))
        self.assertNotEqual(black_pawn, white_queen)
        self.assertNotEqual(black_pawn, None)
        self.assertFalse(black_pawn != libchess.Piece("p"))

        # String representation.
        self.assertEqual(str(black_pawn), "p")

        # Test dictionary with pieces.
        a = dict()
        a[black_pawn] = "foo"
        a[white_queen] = "bar"
        a[libchess.Piece("Q")] = "baz"
        self.assertEqual(a[black_pawn], "foo")
        self.assertEqual(a[white_queen], "baz")

if __name__ == "__main__":
    unittest.main()
