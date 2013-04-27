#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import libchess


class CommonTestCase(unittest.TestCase):

    def test_opposite_color(self):
        self.assertEqual(libchess.opposite_color("w"), "b")
        self.assertEqual(libchess.opposite_color("b"), "w")


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

        # Test non-default constructor.
        white_rook = libchess.Piece.from_color_and_type("w", "r")
        self.assertEqual(white_rook.symbol, "R")


class SquareTestCase(unittest.TestCase):

    def test(self):
        # Properties.
        a2 = libchess.Square("a2")
        self.assertEqual(a2.rank, 1)
        self.assertEqual(a2.file, 0)
        self.assertEqual(a2.name, "a2")
        self.assertEqual(a2.file_name, "a")

    def test_x88_index(self):
        f7 = libchess.Square("f7")
        self.assertEqual(f7.x88_index, 21)

        c8 = libchess.Square("c8")
        self.assertEqual(libchess.Square.from_x88_index(2), c8)


class MoveTestCase(unittest.TestCase):

    def test(self):
        # Properties.
        move = libchess.Move.from_uci("e7e8q")
        self.assertEqual(move.source, libchess.Square("e7"))
        self.assertEqual(move.target, libchess.Square("e8"))
        self.assertEqual(move.promotion, "q")
        self.assertEqual(move.full_promotion, "queen")


class PositionTestCase(unittest.TestCase):

    def test_board(self):
        position = libchess.Position()

        # Read.
        self.assertEqual(position[libchess.Square("a1")], libchess.Piece("R"))
        self.assertEqual(position[libchess.Square("e8")], libchess.Piece("k"))
        self.assertTrue(position[libchess.Square("h3")] is None)

        # Write.
        e2 = libchess.Square("e2")
        e4 = libchess.Square("e4")
        position[e4] = position[e2]
        del position[e2]
        self.assertEqual(position[e4], libchess.Piece("P"))
        self.assertTrue(position[e2] is None)

    def test_board_shorthand(self):
        position = libchess.Position()

        self.assertEqual(position["f8"], libchess.Piece("b"))

        del position["a1"]
        self.assertTrue(position["a1"] is None)

        position["h8"] = libchess.Piece("q")
        self.assertEqual(position["h8"], libchess.Piece("q"))

    def test_ep_file(self):
        position = libchess.Position()
        self.assertTrue(position.ep_file is None)
        position.ep_file = "e"
        self.assertEqual(position.ep_file, "e")
        position.ep_file = None
        self.assertTrue(position.ep_file is None)

    def test_turn(self):
        position = libchess.Position()
        self.assertEqual(position.turn, "w")
        position.turn = "b"
        self.assertEqual(position.turn, "b")
        position.toggle_turn()
        self.assertEqual(position.turn, "w")

if __name__ == "__main__":
    unittest.main()
